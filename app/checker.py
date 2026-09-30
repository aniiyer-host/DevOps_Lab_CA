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

# ---------------------------------------------------------------------------
# Project root — two levels up from this file (app/checker.py → project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKERFILE_PATH = os.path.join(PROJECT_ROOT, "Dockerfile")
POLICY_DIR = os.path.join(PROJECT_ROOT, "policies")
GITHUB_ACTIONS_URL = "https://github.com/aniiyer-host/DevOps_Lab_CA/actions"


# ---------------------------------------------------------------------------
# Dockerfile generator
# ---------------------------------------------------------------------------

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
    lines: list[str] = []

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

    # Optional hardcoded secret
    sk = secret_key.strip()
    sv = secret_value.strip()
    if sk and sv:
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


# ---------------------------------------------------------------------------
# Local conftest preview (fast, no push needed)
# ---------------------------------------------------------------------------

def _run_conftest(dockerfile_content: str) -> dict:
    """Write content to a temp file and run conftest against it."""
    conftest_bin = shutil.which("conftest")
    if not conftest_bin:
        return {"error": "conftest not found on PATH — install it locally to use the preview."}

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="Dockerfile", delete=False, dir=PROJECT_ROOT
    ) as tmp:
        tmp.write(dockerfile_content)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [conftest_bin, "test", tmp_path, "--policy", POLICY_DIR, "--parser", "dockerfile"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        output = (result.stdout + result.stderr).strip()
        passed = result.returncode == 0
        return {"passed": passed, "output": output}
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Git commit + push
# ---------------------------------------------------------------------------

def _commit_and_push(dockerfile_content: str) -> dict:
    """Overwrite Dockerfile, commit, and push to current branch."""
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
            # Nothing changed — already compliant / same file
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@checker_bp.route("/checker")
def checker_page():
    return render_template_string(CHECKER_HTML)


@checker_bp.route("/api/policy-preview", methods=["POST"])
def policy_preview():
    """Run conftest locally and return instant pass/fail — no push."""
    data = request.get_json(force=True)
    dockerfile = _build_dockerfile(**_extract_fields(data))
    result = _run_conftest(dockerfile)
    result["dockerfile"] = dockerfile
    return jsonify(result)


@checker_bp.route("/api/policy-push", methods=["POST"])
def policy_push():
    """Commit + push Dockerfile and return GitHub Actions URL."""
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


# ---------------------------------------------------------------------------
# Inline HTML template
# ---------------------------------------------------------------------------

CHECKER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Dockerfile Policy Checker</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 2rem 1rem;
    }

    .container { max-width: 900px; margin: 0 auto; }

    h1 {
      font-size: 1.6rem;
      font-weight: 700;
      margin-bottom: .25rem;
      display: flex;
      align-items: center;
      gap: .5rem;
    }
    .subtitle { color: #8b949e; font-size: .9rem; margin-bottom: 2rem; }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }

    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 1rem 1.25rem;
    }

    .card label {
      display: block;
      font-size: .78rem;
      font-weight: 600;
      color: #8b949e;
      text-transform: uppercase;
      letter-spacing: .05em;
      margin-bottom: .4rem;
    }

    .policy-name {
      font-size: .85rem;
      font-weight: 600;
      color: #e6edf3;
      margin-bottom: .15rem;
    }

    .policy-desc {
      font-size: .75rem;
      color: #8b949e;
      margin-bottom: .6rem;
      line-height: 1.4;
    }

    input[type="text"] {
      width: 100%;
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      color: #e6edf3;
      padding: .45rem .7rem;
      font-size: .85rem;
      font-family: "SFMono-Regular", Consolas, monospace;
      outline: none;
      transition: border-color .15s;
    }
    input[type="text"]:focus { border-color: #388bfd; }

    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .toggle {
      position: relative;
      width: 44px;
      height: 24px;
      flex-shrink: 0;
    }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .slider {
      position: absolute;
      inset: 0;
      background: #30363d;
      border-radius: 24px;
      cursor: pointer;
      transition: background .2s;
    }
    .slider::before {
      content: "";
      position: absolute;
      width: 18px; height: 18px;
      left: 3px; bottom: 3px;
      background: #fff;
      border-radius: 50%;
      transition: transform .2s;
    }
    .toggle input:checked + .slider { background: #238636; }
    .toggle input:checked + .slider::before { transform: translateX(20px); }

    .actions {
      display: flex;
      gap: .75rem;
      flex-wrap: wrap;
      margin-bottom: 1.5rem;
    }

    button {
      padding: .6rem 1.2rem;
      border: none;
      border-radius: 6px;
      font-size: .9rem;
      font-weight: 600;
      cursor: pointer;
      transition: opacity .15s, transform .1s;
    }
    button:active { transform: scale(.97); }
    button:disabled { opacity: .5; cursor: default; }

    #btn-preview  { background: #238636; color: #fff; }
    #btn-push     { background: #1f6feb; color: #fff; }
    #btn-actions  { background: #161b22; color: #e6edf3; border: 1px solid #30363d; display: none; }
    #btn-reset    { background: transparent; color: #8b949e; border: 1px solid #30363d; }

    .results {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 1.25rem;
      margin-bottom: 1.5rem;
      display: none;
    }
    .results h2 { font-size: 1rem; margin-bottom: .75rem; }

    .policy-result {
      display: flex;
      align-items: flex-start;
      gap: .6rem;
      padding: .4rem 0;
      border-bottom: 1px solid #21262d;
      font-size: .85rem;
    }
    .policy-result:last-child { border-bottom: none; }
    .icon { font-size: 1rem; flex-shrink: 0; margin-top: .05rem; }

    .badge {
      display: inline-block;
      padding: .15rem .5rem;
      border-radius: 4px;
      font-size: .72rem;
      font-weight: 700;
      margin-left: auto;
      flex-shrink: 0;
    }
    .pass  { background: #1a3a1f; color: #3fb950; }
    .fail  { background: #3a1a1a; color: #f85149; }
    .msg   { color: #8b949e; font-size: .8rem; margin-top: .15rem; }

    .status-bar {
      border-radius: 6px;
      padding: .6rem 1rem;
      font-size: .85rem;
      font-weight: 600;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: .5rem;
    }
    .status-pass { background: #1a3a1f; color: #3fb950; border: 1px solid #238636; }
    .status-fail { background: #3a1a1a; color: #f85149; border: 1px solid #da3633; }
    .status-push { background: #1c2e4a; color: #58a6ff; border: 1px solid #1f6feb; }
    .status-warn { background: #3a2a0a; color: #d29922; border: 1px solid #9e6a03; }

    .dockerfile-preview {
      background: #0d1117;
      border: 1px solid #21262d;
      border-radius: 6px;
      padding: .75rem 1rem;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: .78rem;
      line-height: 1.6;
      white-space: pre;
      overflow-x: auto;
      margin-top: .75rem;
      color: #c9d1d9;
    }

    details summary {
      cursor: pointer;
      font-size: .82rem;
      color: #8b949e;
      margin-top: .5rem;
      user-select: none;
    }
    details summary:hover { color: #e6edf3; }

    .spinner {
      display: inline-block;
      width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: spin .6s linear infinite;
      vertical-align: middle;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    @media (max-width: 600px) {
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<div class="container">
  <h1>🔒 Dockerfile Policy Checker</h1>
  <p class="subtitle">Modify any field to test a policy. Preview runs conftest locally (instant). Push commits to GitHub and triggers CI.</p>

  <div class="grid" id="fields">

    <!-- Policy 1: Base image (covers deny-latest + require-approved-image) -->
    <div class="card">
      <div class="policy-name">📦 Base Image</div>
      <div class="policy-desc">Must be <code>python:3.12-slim</code>. Using <code>:latest</code> or any other image fails two policies.</div>
      <label>FROM</label>
      <input type="text" id="base_image" value="python:3.12-slim" />
    </div>

    <!-- Policy 2: USER value (deny-root) -->
    <div class="card">
      <div class="policy-name">👤 Runtime User</div>
      <div class="policy-desc">Container must not run as <code>root</code> or UID <code>0</code>.</div>
      <label>USER value</label>
      <input type="text" id="user_value" value="appuser" />
    </div>

    <!-- Policy 3: Include USER instruction (require-explicit-user) -->
    <div class="card">
      <div class="policy-name">🪪 USER Instruction</div>
      <div class="policy-desc">Dockerfile must contain an explicit <code>USER</code> instruction. Toggle off to remove it.</div>
      <div class="toggle-row">
        <span style="font-size:.85rem">Include <code>USER</code> instruction</span>
        <label class="toggle">
          <input type="checkbox" id="include_user" checked />
          <span class="slider"></span>
        </label>
      </div>
    </div>

    <!-- Policy 4: WORKDIR (require-workdir) -->
    <div class="card">
      <div class="policy-name">📁 WORKDIR</div>
      <div class="policy-desc">Must declare an explicit working directory. Clear the field to remove it entirely.</div>
      <label>WORKDIR path</label>
      <input type="text" id="workdir" value="/app" />
    </div>

    <!-- Policy 5: HEALTHCHECK (require-healthcheck) -->
    <div class="card">
      <div class="policy-name">💓 HEALTHCHECK</div>
      <div class="policy-desc">Docker must be able to determine if the container is healthy. Toggle off to remove it.</div>
      <div class="toggle-row">
        <span style="font-size:.85rem">Include <code>HEALTHCHECK</code></span>
        <label class="toggle">
          <input type="checkbox" id="include_healthcheck" checked />
          <span class="slider"></span>
        </label>
      </div>
    </div>

    <!-- Policy 6: COPY source (deny-sensitive-copy) -->
    <div class="card">
      <div class="policy-name">📋 COPY Source</div>
      <div class="policy-desc">Must not copy <code>.env</code>, <code>.ssh</code>, or <code>.git</code> into the image.</div>
      <label>COPY source path</label>
      <input type="text" id="copy_source" value="app/" />
    </div>

    <!-- Policy 7 + 8: Hardcoded secret (deny-hardcoded-secrets) -->
    <div class="card" style="grid-column: span 2;">
      <div class="policy-name">🔑 ENV Secret (Hardcoded Secret Test)</div>
      <div class="policy-desc">Adding a secret-like key (<code>API_TOKEN</code>, <code>PASSWORD</code>, etc.) with a literal value triggers the hardcoded-secret policy. Leave blank for no ENV instruction.</div>
      <div style="display:flex; gap:.75rem;">
        <div style="flex:1">
          <label>ENV key (e.g. API_TOKEN)</label>
          <input type="text" id="secret_key" value="" placeholder="leave blank = no ENV" />
        </div>
        <div style="flex:1">
          <label>ENV value (e.g. abc-secret-123)</label>
          <input type="text" id="secret_value" value="" placeholder="leave blank = no ENV" />
        </div>
      </div>
    </div>

  </div><!-- /grid -->

  <div class="actions">
    <button id="btn-preview">⚡ Preview (local, instant)</button>
    <button id="btn-push">🚀 Commit &amp; Push to GitHub</button>
    <button id="btn-actions" onclick="window.open('https://github.com/aniiyer-host/DevOps_Lab_CA/actions','_blank')">👀 View GitHub Actions</button>
    <button id="btn-reset" onclick="resetFields()">↩ Reset to Compliant</button>
  </div>

  <div class="results" id="results">
    <h2>Results</h2>
    <div id="status-bar"></div>
    <div id="policy-list"></div>
    <details>
      <summary>Show generated Dockerfile</summary>
      <div class="dockerfile-preview" id="df-preview"></div>
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

  // Known policy messages from conftest output
  const POLICY_LABELS = [
    { key: "root",       msg: "Container must not run as root",                        field: "user_value" },
    { key: "latest",     msg: "Base images must not use the latest tag",               field: "base_image" },
    { key: "approved",   msg: "Dockerfile must use the approved base image",           field: "base_image" },
    { key: "user",       msg: "Dockerfile must explicitly define a non-root USER",     field: "include_user" },
    { key: "healthcheck",msg: "Dockerfile must define a HEALTHCHECK",                  field: "include_healthcheck" },
    { key: "workdir",    msg: "Dockerfile must explicitly define a WORKDIR",           field: "workdir" },
    { key: "copyadd",    msg: "COPY/ADD must not include .git, .env, or .ssh paths",   field: "copy_source" },
    { key: "secret",     msg: "Do not hardcode secret values in Dockerfile ENV or ARG instructions", field: "secret_key" },
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

  function parseResults(output, passed) {
    // Parse conftest output lines to find which policies failed
    const failures = [];
    if (output) {
      output.split("\\n").forEach(line => {
        const m = line.match(/FAIL[^-]*-\\s*(.*)/);
        if (m) failures.push(m[1].trim());
      });
    }

    return POLICY_LABELS.map(p => {
      const failed = !passed && failures.some(f => f.toLowerCase().includes(p.msg.toLowerCase().slice(0, 20)));
      // If all failed (passed=false, no specific match) mark unknown
      return { label: p.msg, failed };
    });
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
        statusBar.className = "status-bar status-push";
        statusBar.innerHTML = "🚀 Pushed to GitHub! CI pipeline triggered. Click <strong>View GitHub Actions</strong> to watch it run.";
        document.getElementById("btn-actions").style.display = "inline-block";
      } else {
        statusBar.className = "status-bar status-warn";
        statusBar.innerHTML = "⚠️ Push note: " + (data.message || "nothing to commit (Dockerfile unchanged).");
        document.getElementById("btn-actions").style.display = "inline-block";
      }
      policyList.innerHTML = "";
      return;
    }

    // Preview mode
    if (data.error) {
      statusBar.className = "status-bar status-warn";
      statusBar.innerHTML = "⚠️ " + data.error;
      policyList.innerHTML = "";
      return;
    }

    const passed = data.passed;
    statusBar.className = "status-bar " + (passed ? "status-pass" : "status-fail");
    statusBar.innerHTML  = passed
      ? "✅ All 8 policies passed — Dockerfile is compliant."
      : "❌ One or more policy checks failed — CI build would be blocked.";

    // Parse raw output for per-policy status
    const output = data.output || "";
    const failLines = output.split("\\n")
      .filter(l => l.includes("FAIL"))
      .map(l => l.replace(/^.*FAIL[^-]*-\\s*/, "").trim());

    policyList.innerHTML = POLICY_LABELS.map(p => {
      const isFail = failLines.some(f => f.toLowerCase().startsWith(p.msg.toLowerCase().slice(0, 25)));
      return `
        <div class="policy-result">
          <span class="icon">${isFail ? "❌" : "✅"}</span>
          <span>${p.msg}</span>
          <span class="badge ${isFail ? "fail" : "pass"}">${isFail ? "FAIL" : "PASS"}</span>
        </div>`;
    }).join("");
  }

  function setLoading(btn, loading) {
    btn.disabled = loading;
    if (loading) {
      btn.dataset.orig = btn.innerHTML;
      btn.innerHTML = '<span class="spinner"></span> ' + (btn.id === "btn-push" ? "Pushing…" : "Running…");
    } else {
      btn.innerHTML = btn.dataset.orig || btn.innerHTML;
    }
  }

  document.getElementById("btn-preview").addEventListener("click", async () => {
    const btn = document.getElementById("btn-preview");
    setLoading(btn, true);
    try {
      const res  = await fetch("/api/policy-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(getFields()),
      });
      const data = await res.json();
      renderResults(data, "preview");
    } catch (e) {
      alert("Request failed: " + e.message);
    } finally {
      setLoading(btn, false);
    }
  });

  document.getElementById("btn-push").addEventListener("click", async () => {
    if (!confirm("This will commit and push the generated Dockerfile to GitHub on the current branch. Continue?")) return;
    const btn = document.getElementById("btn-push");
    setLoading(btn, true);
    try {
      const res  = await fetch("/api/policy-push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(getFields()),
      });
      const data = await res.json();
      renderResults(data, "push");
    } catch (e) {
      alert("Request failed: " + e.message);
    } finally {
      setLoading(btn, false);
    }
  });
</script>
</body>
</html>
"""
