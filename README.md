# Automated Policy-Gated Secure Container CI/CD Pipeline

A DevSecOps-oriented CI/CD pipeline that automatically tests, security-validates, builds, and deploys a containerized configuration management REST API service using **GitHub Actions, Docker, Docker Compose, and Open Policy Agent (OPA) with Conftest**.

The project demonstrates how **Policy as Code** can be integrated directly into a CI pipeline so that insecure container configurations are detected and rejected before the Docker image is built.

---

## Project Overview

Traditional CI/CD pipelines primarily focus on whether an application works correctly. This project adds a security validation layer to the pipeline.

Before a Docker image is built, the Dockerfile is evaluated against predefined security policies using **OPA/Conftest**.

The pipeline workflow:

```text
Developer
    │
    ▼
  GitHub
    │
    ▼
GitHub Actions
    │
    ├── Automated Tests (Pytest)
    │
    ├── OPA/Conftest Security Policies
    │       │
    │       └── Policy Failure → Pipeline Stops
    │
    └── Docker Image Build
            │
            ▼
      Docker Compose
            │
            ▼
    Running Application
```

The primary objective is to ensure that security requirements are enforced automatically rather than relying entirely on manual review.

---

## Objectives

* Implement a CI/CD pipeline using GitHub Actions.
* Containerize an application using Docker.
* Implement security policies using Open Policy Agent (OPA).
* Use Conftest to evaluate Dockerfile configurations.
* Automatically reject insecure container configurations.
* Build the Docker image only after security validation succeeds.
* Deploy the container using Docker Compose.
* Demonstrate policy enforcement through intentional CI failures and recovery scenarios.

---

## Technologies Used

| Technology        | Purpose                      |
| ----------------- | ---------------------------- |
| Git               | Version control              |
| GitHub            | Source code hosting          |
| GitHub Actions    | CI/CD automation             |
| Python / Flask    | Application framework        |
| Flask-SQLAlchemy  | Database ORM                 |
| Pytest            | Automated testing            |
| Docker            | Application containerization |
| Docker Compose    | Container deployment         |
| Open Policy Agent | Policy engine                |
| Conftest          | Policy testing               |
| Rego              | Policy definition language   |

---

## Project Structure

```text
secure-container-cicd/
│
├── app/
│   ├── __init__.py         # Application factory pattern & extension init
│   ├── app.py              # Blueprint routes & entrypoint
│   ├── models.py           # SQLAlchemy Configuration model
│   ├── config/             # Environment-specific configuration package
│   │   ├── __init__.py
│   │   ├── default.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── .env.example
│   └── requirements.txt    # Application dependencies
│
├── tests/
│   └── test_app.py         # Pytest suite with app/client fixtures
│
├── fixtures/
│   └── Dockerfile.*        # Intentionally insecure policy demonstrations
│
├── policies/
│   └── dockerfile.rego     # OPA Rego policies
│
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions workflow
│
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── context.md
└── README.md
```

---

# Application Capabilities

The application is a realistic **Configuration Management REST API service** built with Flask, SQLAlchemy ORM, and blueprint-based routing.

It provides environment management artifacts and database entities that are validated by the Policy-as-Code pipeline.

### Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/` | Service root status and environment info |
| `GET` | `/health` | Service health check |
| `GET` | `/configs` | List all configuration records |
| `POST` | `/configs` | Create a new configuration (`key`, `value`, `description`, `environment`) |
| `GET` | `/configs/<id>` | Get configuration by ID |
| `PUT` | `/configs/<id>` | Update configuration fields (`value`, `description`, `environment`) |
| `DELETE` | `/configs/<id>` | Delete configuration record |
| `GET` | `/configs/<key>` | Get configuration by key string |

### Example API Usage

#### List Configurations
```bash
curl http://localhost:5000/configs
```

Example response:
```json
{
  "count": 1,
  "data": [
    {
      "created_at": "2026-09-26T13:54:21.054836",
      "description": "Production environment flag",
      "environment": "development",
      "id": 1,
      "key": "app.env",
      "updated_at": "2026-09-26T13:54:21.054841",
      "value": "production"
    }
  ],
  "status": "success"
}
```

#### Create Configuration
```bash
curl -X POST http://localhost:5000/configs \
  -H "Content-Type: application/json" \
  -d '{"key": "db.timeout", "value": "30", "description": "Database timeout in seconds"}'
```

---

# Docker Configuration

The application is containerized using security principles:

* Approved base image: `python:3.12-slim`.
* Mutable `latest` tag is prohibited.
* Dedicated non-root user `appuser` created and used.
* Explicit `/app` working directory and HTTP health check are configured.
* Application dependencies installed securely inside container.
* Port 5000 exposed.

---

# Policy as Code

Security requirements are defined as Rego policies in:

```text
policies/dockerfile.rego
```

Conftest parses the `Dockerfile` and evaluates it against these policies.

### Active Security Controls

| Policy | Purpose | Example violation | Remediation |
| --- | --- | --- | --- |
| Deny root execution | Keep the container process non-root, including UID `0`. | `USER root` or `USER 0` | Create/use an unprivileged account, such as `appuser`. |
| Deny `latest` | Avoid silently changing base-image contents between builds. | `FROM python:latest` | Use an explicit version tag. |
| Require approved base image | Limit the build to the reviewed `python:3.12-slim` image. | `FROM python:3.12` | Use exactly `python:3.12-slim`. |
| Require explicit `USER` | Make the runtime identity visible and reviewable. | No `USER` instruction | Add `USER appuser` after creating the account. |
| Require `HEALTHCHECK` | Let Docker report whether the service responds to its health endpoint. | Missing `HEALTHCHECK` | Add a check for `/health` with a bounded timeout. |
| Require `WORKDIR` | Make relative paths and command execution predictable. | Missing `WORKDIR` | Declare the application directory, such as `WORKDIR /app`. |
| Deny sensitive `COPY`/`ADD` sources | Avoid copying repository metadata and common local-secret paths into image layers. | `COPY .env /app/.env` or `ADD .ssh /app/.ssh` | Exclude the path from the build context and copy only required files. |
| Deny hardcoded secret assignments | Catch obvious literal values assigned to secret-like `ENV`/`ARG` keys. | `ENV API_TOKEN=hardcoded-demo-token` | Supply secrets at runtime through an appropriate secret mechanism; do not bake them into the image. |

The secret rule inspects only secret-like `ENV`/`ARG` assignments. It permits common variable references and placeholders; it is a guard against obvious mistakes, not a general-purpose secret scanner.
`fixtures/Dockerfile.secret-reference` is a passing example: it uses `${API_TOKEN}` and includes ordinary `PASSWORD_LABEL` and `RUN` text without triggering the rule.

### Security Rationale — Why Each Policy Exists

Each policy maps directly to a real attack vector or failure mode observed in production container environments.

| Policy | Attack / Risk Prevented | Real-World Context |
| --- | --- | --- |
| **Deny root execution** | If a container process is compromised, running as root gives an attacker host-level privileges during a container escape. | CVE-2019-5736 (runc vulnerability) allowed container breakout — impact was drastically amplified for root-running containers. Non-root containers confine the blast radius to the container only. |
| **Deny `latest` tag** | The `latest` tag is mutable — the upstream image it points to can change silently between builds. A build that passes today may ship a newly-vulnerable OS layer tomorrow with no code change. | Silent base-image drift is a recognised supply chain risk. Pinning to an explicit digest or version tag ensures reproducible, auditable builds. |
| **Require approved base image** | Arbitrary base images may contain malware, backdoors, or unpatched CVEs. Restricting to a single vetted image eliminates an entire class of supply chain attack. | Typosquatting attacks on Docker Hub (e.g. `pythn`, `pyhton`) have distributed trojaned images to unsuspecting users. An allowlist makes this impossible at build time. |
| **Require explicit `USER`** | Docker's default runtime user is `root`. Without an explicit `USER` instruction, every container runs with full privileges unless overridden at `docker run` time — a dangerous implicit assumption. | The CIS Docker Benchmark (rule 4.1) mandates non-root container users as a baseline security control precisely because the default is root. |
| **Require `HEALTHCHECK`** | Without a health check, Docker and orchestrators cannot distinguish a crashed application from a healthy one. A broken service continues receiving traffic silently, causing hidden downtime. | Health checks are mandatory in production Docker Compose and Kubernetes deployments. Their absence is a common cause of "zombie" containers that appear running but serve errors. |
| **Require `WORKDIR`** | Without an explicit `WORKDIR`, `RUN`, `COPY`, and `CMD` instructions execute relative to `/` (the filesystem root). Files can be silently placed in unexpected locations, overwriting system binaries or configuration. | This is a path-confusion vulnerability class — predictable working directories are a prerequisite for reproducible and auditable builds. |
| **Deny sensitive `COPY`/`ADD` sources** | Docker image layers are immutable and cumulative. Even if a secret file is deleted in a later layer, it remains fully readable in the earlier layer via `docker history` or by exporting the image tarball. | Thousands of public Docker Hub images have been found to contain `.env` files with live database credentials, AWS keys, and API tokens — baked in and never removed. |
| **Deny hardcoded secrets in `ENV`/`ARG`** | `ENV` values are stored in the image manifest and are visible to anyone with `docker inspect` or `docker history` access — including anyone who pulls the image from a registry. | GitGuardian's State of Secrets Sprawl report consistently identifies hardcoded credentials in container images as one of the top sources of cloud credential exposure. |

---

# Local Development & Testing

## 1. Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
pip install pytest
```

## 2. Run Application Tests

```bash
python -m pytest tests/ -v
```

All unit tests run against an isolated in-memory SQLite database and test app context.

## 3. Run Application Locally

```bash
python app/app.py
```

Or with custom port / environment:

```bash
PORT=5001 FLASK_ENV=development python app/app.py
```

---

# Running Conftest Locally

Validate policy compliance before committing:

```bash
conftest test Dockerfile --policy policies/ --parser dockerfile
```

Expected output:
```text
8 tests, 8 passed, 0 warnings, 0 failures, 0 exceptions
```

The same command is run by the `Validate Dockerfile security policies` step in GitHub Actions. Conftest exits non-zero on a policy violation; because the Docker build is a later step in the same job, GitHub Actions marks it skipped and does not build the image.

---

# Demonstration Guide: Policy Gate Failure & Recovery

To demonstrate how the Policy-as-Code pipeline catches security defects before container builds:

### Step 1: Verify Policy Compliance (Pass)
Run conftest on the repository Dockerfile:
```bash
conftest test Dockerfile --policy policies/ --parser dockerfile
```
*Result:* All 8 policy checks **PASS**.

### Step 2: Run a Reproducible Failure (Fail)
Use an intentionally insecure fixture. For example:
```bash
conftest test fixtures/Dockerfile.no-healthcheck --policy policies/ --parser dockerfile
```
*Result:* **FAIL** — `Dockerfile must define a HEALTHCHECK`. A non-zero policy result blocks the later CI build step.

Other fixtures demonstrate root execution, a mutable base tag, a missing `WORKDIR`, a sensitive copy source, and a hardcoded secret assignment:

```bash
conftest test fixtures/Dockerfile.root --policy policies/ --parser dockerfile
conftest test fixtures/Dockerfile.latest --policy policies/ --parser dockerfile
conftest test fixtures/Dockerfile.no-workdir --policy policies/ --parser dockerfile
conftest test fixtures/Dockerfile.healthcheck-none --policy policies/ --parser dockerfile
conftest test fixtures/Dockerfile.sensitive-copy --policy policies/ --parser dockerfile
conftest test fixtures/Dockerfile.sensitive-add --policy policies/ --parser dockerfile
conftest test fixtures/Dockerfile.secret --policy policies/ --parser dockerfile
```

The secret-reference example is expected to pass, confirming that variable references and ordinary text are not treated as hardcoded credentials:

```bash
conftest test fixtures/Dockerfile.secret-reference --policy policies/ --parser dockerfile
```

### Step 3: Policy Recovery (Fix & Pass)
The fixtures are demonstrations only; the project `Dockerfile` remains secure. Fix the relevant instruction in a working Dockerfile, then re-run:
```bash
conftest test Dockerfile --policy policies/ --parser dockerfile
```
*Result:* **PASS** — The Docker build stage is allowed to proceed.

---

# Docker Build & Deployment

## Docker Build

```bash
docker build -t secure-devsecops-api .
```

Run container:

```bash
docker run -d \
  --name secure-api \
  -p 5002:5000 \
  secure-devsecops-api
```

Verify non-root user inside container:

```bash
docker exec secure-api whoami
```
*Expected:* `appuser`

## Docker Compose Deployment

```bash
docker compose up -d --build
```

Verify deployment health:

```bash
curl http://localhost:5002/health
```

Clean up deployment:

```bash
docker compose down
```

---

# CI/CD Pipeline

The GitHub Actions workflow is located at `.github/workflows/ci.yml`.

Execution sequence:

```text
Checkout Repository
        ↓
Set Up Python 3.12
        ↓
Install Dependencies
        ↓
Run Pytest Suite
        ↓
Install OPA / Conftest
        ↓
Validate Dockerfile Policies (OPA)
        ↓ (Build blocked if policy fails)
Build Docker Image
```

---

# Project Status

### Completed Features

* [x] Refactored Flask API with Application Factory Pattern (`create_app()`)
* [x] Implemented SQLAlchemy ORM Configuration model & persistent storage
* [x] Implemented full CRUD REST API endpoints (`/configs`)
* [x] Environment-specific configuration classes (`Development`, `Production`, `Testing`)
* [x] Blueprint-based routing and centralized logging
* [x] Comprehensive Pytest suite with isolated test database setup/teardown
* [x] Preserved Dockerfile structure and compatibility
* [x] OPA / Conftest policy gating (8 active policy checks)
* [x] Demonstrated policy failure and recovery scenarios
* [x] Local verification & GitHub Actions CI pipeline compatibility
