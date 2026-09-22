# Automated Policy-Gated Secure Container CI/CD Pipeline

A DevSecOps-oriented CI/CD pipeline that automatically tests, security-validates, builds, and deploys a containerized application using **GitHub Actions, Docker, Docker Compose, and Open Policy Agent (OPA) with Conftest**.

The project demonstrates how **Policy as Code** can be integrated directly into a CI pipeline so that insecure container configurations are detected and rejected before the Docker image is built.

---

## Project Overview

Traditional CI/CD pipelines primarily focus on whether an application works correctly. This project adds a security validation layer to the pipeline.

Before a Docker image is built, the Dockerfile is evaluated against predefined security policies using **OPA/Conftest**.

The pipeline follows:

```text
Developer
    │
    ▼
  GitHub
    │
    ▼
GitHub Actions
    │
    ├── Automated Tests
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
* Demonstrate policy enforcement through intentional CI failures.

---

## Technologies Used

| Technology        | Purpose                      |
| ----------------- | ---------------------------- |
| Git               | Version control              |
| GitHub            | Source code hosting          |
| GitHub Actions    | CI/CD automation             |
| Python / Flask    | Application                  |
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
│   ├── app.py
│   └── requirements.txt
│
├── tests/
│   └── test_app.py
│
├── policies/
│   └── dockerfile.rego
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── README.md
```

---

# Application

The current application is a lightweight Flask API used to demonstrate the CI/CD and security pipeline.

It exposes:

### Root endpoint

```text
GET /
```

Example response:

```json
{
  "message": "Secure DevSecOps API is running",
  "status": "success"
}
```

### Health endpoint

```text
GET /health
```

Example response:

```json
{
  "status": "healthy"
}
```

The application can later be replaced with a more realistic application without changing the overall CI/CD architecture.

---

# Docker Configuration

The application is containerized using the following security principles:

* A specific Python base image is used.
* The `latest` tag is prohibited.
* A dedicated non-root user is created.
* The container explicitly switches to the non-root user.
* Application dependencies are installed inside the container.
* Only the required application port is exposed.

The container currently uses:

```dockerfile
FROM python:3.12-slim
```

and runs as:

```dockerfile
USER appuser
```

---

# Policy as Code

Security requirements are defined as Rego policies in:

```text
policies/dockerfile.rego
```

Conftest parses the Dockerfile and evaluates it against these policies.

The current policy set contains four security controls.

## 1. Prevent Root Execution

The Dockerfile must not explicitly configure:

```dockerfile
USER root
```

Violation:

```text
Container must not run as root
```

---

## 2. Prevent the `latest` Tag

Base images must not use the mutable `latest` tag.

For example:

```dockerfile
FROM python:latest
```

is rejected.

Violation:

```text
Base images must not use the latest tag
```

---

## 3. Require an Approved Base Image

The current project requires:

```dockerfile
FROM python:3.12-slim
```

An alternative base image such as:

```dockerfile
FROM ubuntu:24.04
```

is rejected.

Violation:

```text
Dockerfile must use the approved base image: python:3.12-slim
```

This policy can later be modified to support an approved list of multiple images rather than a single image.

---

## 4. Require an Explicit USER Instruction

The Dockerfile must explicitly define a user.

A Dockerfile without a `USER` instruction is rejected.

Violation:

```text
Dockerfile must explicitly define a non-root USER
```

---

# Local Testing

## 1. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r app/requirements.txt
pip install pytest
```

---

## 2. Run Application Tests

```bash
pytest
```

The application tests verify the `/` and `/health` endpoints.

---

# Running Conftest Locally

Conftest can be used to validate the Dockerfile before pushing changes.

Run:

```bash
conftest test Dockerfile --policy policies/ --parser dockerfile
```

A valid Dockerfile should pass all four policies.

---

# Docker Build

Build the image locally:

```bash
docker build -t secure-devsecops-api .
```

Run the container:

```bash
docker run -d \
  --name secure-api \
  -p 5002:5000 \
  secure-devsecops-api
```

Verify:

```bash
curl http://localhost:5002/health
```

Check the container user:

```bash
docker exec secure-api whoami
```

Expected:

```text
appuser
```

---

# Docker Compose Deployment

The project uses Docker Compose to provide a reproducible deployment configuration.

Start the application:

```bash
docker compose up -d --build
```

Check the deployment:

```bash
docker compose ps
```

Verify the application:

```bash
curl http://localhost:5002/
```

Health check:

```bash
curl http://localhost:5002/health
```

Stop the deployment:

```bash
docker compose down
```

---

# CI/CD Pipeline

The GitHub Actions workflow is located at:

```text
.github/workflows/ci.yml
```

The pipeline performs the following stages:

```text
Checkout Repository
        ↓
Set Up Python
        ↓
Install Dependencies
        ↓
Run Pytest
        ↓
Install Conftest
        ↓
Validate Dockerfile Policies
        ↓
Build Docker Image
```

The security policy stage occurs **before the Docker image build**.

Therefore:

```text
Policy PASS
    ↓
Docker Build
```

while:

```text
Policy FAIL
    ↓
Pipeline Stops
    ↓
Docker Build does not execute
```

---

# Security Gate Demonstrations

The policy enforcement has been tested using intentionally insecure Dockerfiles.

## Test 1 — Root User

Changing:

```dockerfile
USER appuser
```

to:

```dockerfile
USER root
```

causes the Conftest stage to fail.

Result:

```text
pytest                         PASS
Conftest policy validation    FAIL
Docker build                  SKIPPED
```

---

## Test 2 — Unapproved Base Image

Changing:

```dockerfile
FROM python:3.12-slim
```

to:

```dockerfile
FROM ubuntu:24.04
```

causes the approved-base-image policy to fail.

Result:

```text
pytest                         PASS
Conftest policy validation    FAIL
Docker build                  SKIPPED
```

---

## Test 3 — Mutable `latest` Tag

Changing:

```dockerfile
FROM python:3.12-slim
```

to:

```dockerfile
FROM python:latest
```

causes the `latest` tag policy to fail.

Result:

```text
pytest                         PASS
Conftest policy validation    FAIL
Docker build                  SKIPPED
```

These tests demonstrate that the security policies are actively enforcing CI pipeline behavior rather than simply existing as documentation.

---

# DevSecOps Security Model

The project follows the principle of shifting security checks earlier into the software development lifecycle.

Instead of:

```text
Code
 ↓
Build
 ↓
Deploy
 ↓
Security Review
```

the project implements:

```text
Code
 ↓
Automated Tests
 ↓
Security Policy Validation
 ↓
Build
 ↓
Deploy
```

This allows insecure container configurations to be rejected automatically before deployment.

---

# Current Security Controls

| Control                     | Enforcement    |
| --------------------------- | -------------- |
| No root container execution | OPA/Conftest   |
| No `latest` base-image tag  | OPA/Conftest   |
| Approved base image         | OPA/Conftest   |
| Explicit USER instruction   | OPA/Conftest   |
| Application functionality   | Pytest         |
| Containerization            | Docker         |
| Deployment reproducibility  | Docker Compose |
| CI automation               | GitHub Actions |

---

# Future Enhancements

The current application is intentionally lightweight so that the DevSecOps pipeline can be demonstrated clearly.

Future versions can introduce a more realistic application and additional security policies, such as:

* Approved package versions
* Dependency vulnerability checks
* Required health checks
* Required Docker `LABEL` metadata
* Restricted exposed ports
* Resource limits
* Read-only container filesystem
* Dropping unnecessary Linux capabilities
* Prohibiting privileged containers
* Secrets detection
* Image vulnerability scanning
* SBOM generation
* Container image signing
* Policy validation for Docker Compose
* Separate development and production configurations

The policy set should evolve according to the requirements of the final application rather than adding security controls that are unrelated to the application's architecture.

---

# Project Status

### Completed

* [x] Flask application
* [x] Automated application tests
* [x] Docker containerization
* [x] Non-root container execution
* [x] OPA/Conftest integration
* [x] Four Dockerfile security policies
* [x] Local policy validation
* [x] GitHub Actions CI pipeline
* [x] Automated policy gating
* [x] Docker image build in CI
* [x] Docker Compose deployment
* [x] Security-failure demonstrations

### Next Development Stage

Replace the demonstration Flask application with a more realistic application and extend the policy set according to its actual security and deployment requirements.

---

# Core Concept

The central concept of this project is:

> **Security policies should be executable controls within the CI/CD pipeline rather than recommendations that are checked only after deployment.**

The pipeline therefore treats security policy violations as build-blocking conditions.
