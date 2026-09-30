"""Policy Checker — GUI blueprint.

Serves a browser-based Dockerfile policy playground.
Each of the 8 OPA/Conftest policies has a corresponding form field.
On submit the backend generates a Dockerfile from the field values,
commits it to the current branch, pushes to GitHub, and returns the
GitHub Actions URL so the evaluator can watch the CI run live.
"""

import os
import subprocess
import tempfile
import shutil

from flask import Blueprint, jsonify, render_template_string, request

checker_bp = Blueprint("checker", __name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKERFILE_PATH = os.path.join(PROJECT_ROOT, "Dockerfile")
POLICY_DIR = os.path.join(PROJECT_ROOT, "policies")
GITHUB_ACTIONS_URL = "https://github.com/aniiyer-host/DevOps_Lab_CA/actions"

def _build_dockerfile(
    base_image: str,
    workdir: str,
    copy_source: str,
    secret_key: str,
    secret_value: str,
    user_value: str,
    include_user: bool,
    include_healthcheck: bool,
) -> str:
    lines = []
    lines.append(f"FROM {base_image}")
    lines.append("")

    if workdir.strip():
        lines.append(f"WORKDIR {workdir.strip()}")
        lines.append("")

    lines.append("COPY app/requirements.txt .")
    lines.append("")
    lines.append("RUN pip install --no-cache-dir -r requirements.txt")
    lines.append("")

    copy_src = copy_source.strip() or "app/"
    lines.append(f"COPY {copy_src} .")
    lines.append("")

    # If the user provides a secret key, add the ENV instruction (even if value is blank)
    sk = secret_key.strip()
    sv = secret_value.strip()
    if sk:
        lines.append(f"ENV {sk}={sv}")
        lines.append("")

    lines.append("RUN useradd --create-home appuser")
    lines.append("")

    if include_user:
        lines.append(f"USER {user_value.strip() or 'appuser'}")
        lines.append("")

    lines.append("EXPOSE 5000")
    lines.append("")

    if include_healthcheck:
        lines.append(
            "HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 "
            'CMD python -c "import urllib.request; '
            "urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2)\""
        )
        lines.append("")

    lines.append('CMD ["python", "app.py"]')
    return "\n".join(lines)


def _run_conftest(dockerfile_content: str) -> dict:
    conftest_bin = shutil.which("conftest")
    if not conftest_bin:
        return {"error": "conftest not found on PATH — install it locally to use the preview."}

    with tempfile.NamedTemporaryFile(mode="w", suffix="Dockerfile", delete=False, dir=PROJECT_ROOT) as tmp:
        tmp.write(dockerfile_content)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [conftest_bin, "test", tmp_path, "--policy", POLICY_DIR, "--parser", "dockerfile"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        output = (result.stdout + result.stderr).strip()
        passed = result.returncode == 0
        return {"passed": passed, "output": output}
    finally:
        os.unlink(tmp_path)


def _commit_and_push(dockerfile_content: str) -> dict:
    try:
        with open(DOCKERFILE_PATH, "w") as f:
            f.write(dockerfile_content)

        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        branch = branch_result.stdout.strip() or "aditya-update"

        subprocess.run(["git", "add", "Dockerfile"], cwd=PROJECT_ROOT, check=True)

        commit_result = subprocess.run(
            ["git", "commit", "-m", "chore(checker): update Dockerfile via policy checker GUI"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        if commit_result.returncode != 0:
            msg = commit_result.stdout.strip() or commit_result.stderr.strip()
            return {"pushed": False, "message": msg, "actions_url": GITHUB_ACTIONS_URL}

        push_result = subprocess.run(
            ["git", "push", "origin", branch],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        if push_result.returncode != 0:
            return {"pushed": False, "message": push_result.stderr.strip(), "actions_url": GITHUB_ACTIONS_URL}

        return {"pushed": True, "branch": branch, "actions_url": GITHUB_ACTIONS_URL}
    except Exception as exc:
        return {"pushed": False, "message": str(exc), "actions_url": GITHUB_ACTIONS_URL}


@checker_bp.route("/checker")
def checker_page():
    return render_template_string(CHECKER_HTML)

@checker_bp.route("/api/policy-preview", methods=["POST"])
def policy_preview():
    data = request.get_json(force=True)
    dockerfile = _build_dockerfile(**_extract_fields(data))
    result = _run_conftest(dockerfile)
    result["dockerfile"] = dockerfile
    return jsonify(result)

@checker_bp.route("/api/policy-push", methods=["POST"])
def policy_push():
    data = request.get_json(force=True)
    dockerfile = _build_dockerfile(**_extract_fields(data))
    result = _commit_and_push(dockerfile)
    result["dockerfile"] = dockerfile
    return jsonify(result)

def _extract_fields(data: dict) -> dict:
    return {
        "base_image":        data.get("base_image",        "python:3.12-slim"),
        "workdir":           data.get("workdir",           "/app"),
        "copy_source":       data.get("copy_source",       "app/"),
        "secret_key":        data.get("secret_key",        ""),
        "secret_value":      data.get("secret_value",      ""),
        "user_value":        data.get("user_value",        "appuser"),
        "include_user":      bool(data.get("include_user",        True)),
        "include_healthcheck": bool(data.get("include_healthcheck", True)),
    }

CHECKER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Dockerfile Policy Validation</title>
  <style>
    :root {
      --bg: #0d1117; --card-bg: #161b22; --border: #30363d; --border-focus: #58a6ff;
      --text: #c9d1d9; --text-muted: #8b949e; --text-light: #f0f6fc;
      --pass: #2ea043; --pass-bg: rgba(46, 160, 67, 0.15);
      --fail: #f85149; --fail-bg: rgba(248, 81, 73, 0.1);
      --btn-primary: #238636; --btn-primary-hover: #2ea043;
      --btn-secondary: #21262d; --btn-secondary-hover: #30363d;
      --btn-accent: #1f6feb; --btn-accent-hover: #388bfd;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      background: var(--bg); color: var(--text); min-height: 100vh; padding: 2.5rem 1rem;
      line-height: 1.5;
    }
    .container { max-width: 950px; margin: 0 auto; }
    h1 { font-size: 1.5rem; font-weight: 600; color: var(--text-light); margin-bottom: 0.5rem; }
    .subtitle { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 2.5rem; }
    
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 2rem; }
    @media (max-width: 650px) { .grid { grid-template-columns: 1fr; } }
    
    .card {
      background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 1.25rem;
    }
    .card-title { font-size: 0.95rem; font-weight: 600; color: var(--text-light); margin-bottom: 0.25rem; }
    .card-desc { font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem; }
    
    label { display: block; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem; }
    input[type="text"] {
      width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: 4px;
      color: var(--text); padding: 0.5rem 0.75rem; font-size: 0.85rem;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; outline: none; transition: 0.2s;
    }
    input[type="text"]:focus { border-color: var(--border-focus); box-shadow: 0 0 0 1px var(--border-focus); }
    
    .toggle-row { display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem; }
    .toggle-label { font-size: 0.85rem; color: var(--text); }
    .toggle { position: relative; width: 40px; height: 22px; flex-shrink: 0; }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; inset: 0; background: var(--border); border-radius: 22px; cursor: pointer; transition: 0.2s; }
    .slider::before {
      content: ""; position: absolute; width: 16px; height: 16px; left: 3px; bottom: 3px;
      background: #fff; border-radius: 50%; transition: 0.2s;
    }
    .toggle input:checked + .slider { background: var(--btn-primary); }
    .toggle input:checked + .slider::before { transform: translateX(18px); }

    .actions { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 2rem; border-top: 1px solid var(--border); padding-top: 2rem; }
    button {
      padding: 0.5rem 1rem; border: 1px solid transparent; border-radius: 5px; font-size: 0.85rem; font-weight: 500; cursor: pointer; transition: 0.2s;
    }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-primary { background: var(--btn-primary); color: #fff; }
    .btn-primary:hover:not(:disabled) { background: var(--btn-primary-hover); }
    .btn-accent { background: var(--btn-accent); color: #fff; }
    .btn-accent:hover:not(:disabled) { background: var(--btn-accent-hover); }
    .btn-secondary { background: var(--btn-secondary); border-color: var(--border); color: var(--text-light); }
    .btn-secondary:hover:not(:disabled) { background: var(--btn-secondary-hover); border-color: var(--text-muted); }
    
    #btn-actions { display: none; }

    .spinner {
      display: inline-block; width: 14px; height: 14px; margin-right: 6px;
      border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff;
      border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .results-container { display: none; }
    .status-banner {
      padding: 1rem 1.25rem; border-radius: 6px; margin-bottom: 1.5rem; font-weight: 600; font-size: 0.95rem; border: 1px solid transparent;
    }
    .banner-pass { background: var(--pass-bg); border-color: var(--pass); color: var(--pass); }
    .banner-fail { background: var(--fail-bg); border-color: var(--fail); color: var(--fail); }
    .banner-info { background: rgba(88, 166, 255, 0.1); border-color: #58a6ff; color: #58a6ff; }
    
    .policy-list { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 2rem; }
    .policy-item {
      background: var(--card-bg); border: 1px solid var(--border); border-radius: 6px; padding: 1rem;
      border-left: 4px solid var(--border);
    }
    .policy-item.failed { border-left-color: var(--fail); }
    .policy-item.passed { border-left-color: var(--pass); }
    
    .policy-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; }
    .policy-title { font-weight: 600; font-size: 0.9rem; color: var(--text-light); }
    .badge { padding: 0.15rem 0.5rem; border-radius: 2em; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
    .badge-pass { background: var(--pass-bg); color: var(--pass); }
    .badge-fail { background: var(--fail-bg); color: var(--fail); }
    
    .policy-meta { font-size: 0.8rem; color: var(--text-muted); }
    .policy-reason { margin-top: 0.5rem; font-size: 0.8rem; color: var(--text); padding: 0.5rem; background: var(--bg); border-radius: 4px; border: 1px solid var(--border); }
    .reason-label { font-weight: 600; color: var(--fail); margin-right: 0.25rem; }

    details summary { cursor: pointer; font-size: 0.85rem; color: var(--text-muted); user-select: none; font-weight: 500; }
    details summary:hover { color: var(--text-light); }
    .code-preview {
      background: var(--bg); border: 1px solid var(--border); border-radius: 6px; padding: 1rem;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 0.8rem;
      color: var(--text-light); white-space: pre-wrap; overflow-x: auto; margin-top: 0.75rem;
    }
  </style>
</head>
<body>
<div class="container">
  <h1>Dockerfile Policy Validation</h1>
  <p class="subtitle">Modify configurations to test the CI policy gate. Preview executes policies locally; Commit & Push triggers the GitHub Actions CI pipeline.</p>

  <div class="grid">
    <!-- Policy 1 -->
    <div class="card">
      <div class="card-title">Base Image Configuration</div>
      <div class="card-desc">Validates approved base image and prevents mutable 'latest' tags.</div>
      <label>FROM Instruction</label>
      <input type="text" id="base_image" value="python:3.12-slim" placeholder="e.g. python:3.12-slim" />
    </div>

    <!-- Policy 2 -->
    <div class="card">
      <div class="card-title">Runtime Execution User</div>
      <div class="card-desc">Ensures the container drops root privileges at runtime.</div>
      <label>USER Value</label>
      <input type="text" id="user_value" value="appuser" placeholder="e.g. appuser, root, 0" />
    </div>

    <!-- Policy 3 -->
    <div class="card">
      <div class="card-title">Explicit USER Declaration</div>
      <div class="card-desc">Enforces that the Dockerfile explicitly declares a user context.</div>
      <div class="toggle-row">
        <span class="toggle-label">Include USER instruction</span>
        <label class="toggle"><input type="checkbox" id="include_user" checked /><span class="slider"></span></label>
      </div>
    </div>

    <!-- Policy 4 -->
    <div class="card">
      <div class="card-title">Working Directory</div>
      <div class="card-desc">Requires an explicit WORKDIR to prevent path confusion vulnerabilities.</div>
      <label>WORKDIR Path</label>
      <input type="text" id="workdir" value="/app" placeholder="e.g. /app" />
    </div>

    <!-- Policy 5 -->
    <div class="card">
      <div class="card-title">Service Health Monitoring</div>
      <div class="card-desc">Requires HEALTHCHECK so orchestrators can detect zombie processes.</div>
      <div class="toggle-row">
        <span class="toggle-label">Include HEALTHCHECK instruction</span>
        <label class="toggle"><input type="checkbox" id="include_healthcheck" checked /><span class="slider"></span></label>
      </div>
    </div>

    <!-- Policy 6 -->
    <div class="card">
      <div class="card-title">Sensitive File Ingestion</div>
      <div class="card-desc">Prevents copying sensitive local context (like .env or .git) into the image.</div>
      <label>COPY Source Path</label>
      <input type="text" id="copy_source" value="app/" placeholder="e.g. app/, .env, .git" />
    </div>

    <!-- Policy 7 + 8 -->
    <div class="card" style="grid-column: 1 / -1;">
      <div class="card-title">Hardcoded Secrets Detection</div>
      <div class="card-desc">Detects secret-like keys (e.g., API_TOKEN, PASSWORD) assigned static values in ENV instructions. Both key and value must be provided to simulate an ENV assignment.</div>
      <div style="display:flex; gap:1rem;">
        <div style="flex:1">
          <label>ENV Key</label>
          <input type="text" id="secret_key" value="" placeholder="e.g. API_TOKEN (Leave blank to omit)" />
        </div>
        <div style="flex:1">
          <label>ENV Value</label>
          <input type="text" id="secret_value" value="" placeholder="e.g. a1b2c3d4 (Leave blank to omit)" />
        </div>
      </div>
    </div>
  </div>

  <div class="actions">
    <button id="btn-preview" class="btn-primary">Run Local Preview</button>
    <button id="btn-push" class="btn-accent">Commit & Push to CI</button>
    <button id="btn-actions" class="btn-secondary" onclick="window.open('https://github.com/aniiyer-host/DevOps_Lab_CA/actions','_blank')">View GitHub Actions</button>
    <button id="btn-reset" class="btn-secondary" onclick="resetFields()">Reset to Defaults</button>
  </div>

  <div class="results-container" id="results">
    <div id="status-bar" class="status-banner"></div>
    <div id="policy-list" class="policy-list"></div>
    <details>
      <summary>View Generated Dockerfile Source</summary>
      <div class="code-preview" id="df-preview"></div>
    </details>
  </div>
</div>

<script>
  const DEFAULTS = {
    base_image: "python:3.12-slim",
    user_value: "appuser",
    include_user: true,
    workdir: "/app",
    include_healthcheck: true,
    copy_source: "app/",
    secret_key: "",
    secret_value: "",
  };

  const POLICY_SCHEMA = [
    { title: "Non-Root Execution", msg: "Container must not run as root", reason: "The runtime user is configured as root or UID 0. This drastically increases the impact of container escape vulnerabilities." },
    { title: "Immutable Base Tags", msg: "Base images must not use the latest tag", reason: "The ':latest' tag was detected. This introduces non-deterministic builds and silent vulnerability drift." },
    { title: "Approved Base Image", msg: "Dockerfile must use the approved base image: python:3.12-slim", reason: "An unapproved base image is being used. Only python:3.12-slim has been vetted for this pipeline." },
    { title: "Explicit User Context", msg: "Dockerfile must explicitly define a non-root USER", reason: "No USER instruction was found. Docker defaults to root execution if not explicitly overridden." },
    { title: "Health Monitoring", msg: "Dockerfile must define a HEALTHCHECK", reason: "Missing HEALTHCHECK instruction. The orchestrator cannot automatically restart the container if the application crashes." },
    { title: "Explicit Working Directory", msg: "Dockerfile must explicitly define a WORKDIR", reason: "No WORKDIR declared. Subsequent instructions execute relative to the root filesystem, risking path confusion." },
    { title: "Sensitive File Exclusion", msg: "COPY/ADD must not include .git, .env, or .ssh paths", reason: "A restricted path (.env, .git, or .ssh) is being copied into the immutable image layer where it can be extracted." },
    { title: "No Hardcoded Credentials", msg: "Do not hardcode secret values in Dockerfile ENV or ARG instructions", reason: "A known secret-pattern key was assigned a static literal value, which is visible in 'docker history'." }
  ];

  function getFields() {
    return {
      base_image:          document.getElementById("base_image").value,
      user_value:          document.getElementById("user_value").value,
      include_user:        document.getElementById("include_user").checked,
      workdir:             document.getElementById("workdir").value,
      include_healthcheck: document.getElementById("include_healthcheck").checked,
      copy_source:         document.getElementById("copy_source").value,
      secret_key:          document.getElementById("secret_key").value,
      secret_value:        document.getElementById("secret_value").value,
    };
  }

  function resetFields() {
    document.getElementById("base_image").value = DEFAULTS.base_image;
    document.getElementById("user_value").value  = DEFAULTS.user_value;
    document.getElementById("include_user").checked        = DEFAULTS.include_user;
    document.getElementById("workdir").value     = DEFAULTS.workdir;
    document.getElementById("include_healthcheck").checked = DEFAULTS.include_healthcheck;
    document.getElementById("copy_source").value = DEFAULTS.copy_source;
    document.getElementById("secret_key").value  = DEFAULTS.secret_key;
    document.getElementById("secret_value").value= DEFAULTS.secret_value;
    document.getElementById("results").style.display = "none";
    document.getElementById("btn-actions").style.display = "none";
  }

  function renderResults(data, mode) {
    const resultsDiv = document.getElementById("results");
    const statusBar  = document.getElementById("status-bar");
    const policyList = document.getElementById("policy-list");
    const dfPreview  = document.getElementById("df-preview");

    resultsDiv.style.display = "block";
    dfPreview.textContent = data.dockerfile || "";

    if (mode === "push") {
      if (data.pushed) {
        statusBar.className = "status-banner banner-info";
        statusBar.textContent = "Repository updated. The CI pipeline has been triggered on GitHub.";
        document.getElementById("btn-actions").style.display = "inline-block";
      } else {
        statusBar.className = "status-banner banner-info";
        statusBar.textContent = "Notice: " + (data.message || "Dockerfile unchanged.");
        document.getElementById("btn-actions").style.display = "inline-block";
      }
      policyList.innerHTML = "";
      return;
    }

    if (data.error) {
      statusBar.className = "status-banner banner-fail";
      statusBar.textContent = "Execution Error: " + data.error;
      policyList.innerHTML = "";
      return;
    }

    const passed = data.passed;
    const output = data.output || "";
    
    statusBar.className = "status-banner " + (passed ? "banner-pass" : "banner-fail");
    statusBar.textContent = passed 
      ? "Validation Passed: Dockerfile complies with all security policies." 
      : "Validation Failed: Dockerfile violates one or more security policies.";

    policyList.innerHTML = POLICY_SCHEMA.map(p => {
      // Direct string inclusion ensures we correctly parse conftest output
      const failed = output.includes(p.msg);
      
      const badgeClass = failed ? "badge-fail" : "badge-pass";
      const badgeText = failed ? "Violation" : "Compliant";
      const itemClass = failed ? "failed" : "passed";
      
      const reasonHtml = failed 
        ? `<div class="policy-reason"><span class="reason-label">Failure Reason:</span>${p.reason}</div>`
        : "";

      return `
        <div class="policy-item ${itemClass}">
          <div class="policy-header">
            <span class="policy-title">${p.title}</span>
            <span class="badge ${badgeClass}">${badgeText}</span>
          </div>
          <div class="policy-meta">${p.msg}</div>
          ${reasonHtml}
        </div>
      `;
    }).join("");
  }

  function toggleLoading(btnId, isLoading) {
    const btn = document.getElementById(btnId);
    if (isLoading) {
      btn.dataset.originalText = btn.textContent;
      btn.innerHTML = `<span class="spinner"></span> Analyzing...`;
      btn.disabled = true;
    } else {
      btn.textContent = btn.dataset.originalText;
      btn.disabled = false;
    }
  }

  document.getElementById("btn-preview").addEventListener("click", async () => {
    toggleLoading("btn-preview", true);
    
    // Hide results immediately when starting a new scan
    document.getElementById("results").style.display = "none";
    
    try {
      const res = await fetch("/api/policy-preview", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(getFields()),
      });
      const data = await res.json();
      
      // Artificial 5-second delay for demo purposes
      await new Promise(r => setTimeout(r, 5000));
      
      renderResults(data, "preview");
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      toggleLoading("btn-preview", false);
    }
  });

  document.getElementById("btn-push").addEventListener("click", async () => {
    if (!confirm("This will commit the Dockerfile changes and push them to the current Git branch. Proceed?")) return;
    toggleLoading("btn-push", true);
    try {
      const res = await fetch("/api/policy-push", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(getFields()),
      });
      renderResults(await res.json(), "push");
    } catch (e) {
      alert("Error: " + e.message);
    } finally {
      toggleLoading("btn-push", false);
    }
  });
</script>
</body>
</html>
"""
