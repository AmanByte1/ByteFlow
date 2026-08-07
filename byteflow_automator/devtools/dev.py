"""
Developer Tools Automation
===========================
Git, Python/pip, Node/npm, Docker, and project scaffolding tasks.
All shell commands run with a timeout and captured output.
"""

import os
import subprocess
import shutil
from pathlib import Path
from ..registry import AutomationTask, register_task


def _run(cmd: list, cwd: str = None, timeout: int = 60) -> str:
    """Run a shell command, return combined stdout+stderr as string."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        combined = "\n".join(filter(None, [out, err]))
        if result.returncode != 0:
            return f"[exit {result.returncode}]\n{combined}" if combined else f"[exit {result.returncode}]"
        return combined or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except FileNotFoundError:
        return f"Error: '{cmd[0]}' not found. Is it installed?"
    except Exception as e:
        return f"Error: {e}"


def _require(tool: str) -> str | None:
    """Return error string if tool not in PATH, else None."""
    if not shutil.which(tool):
        return f"Error: '{tool}' not found in PATH. Please install it."
    return None


# ── Git ────────────────────────────────────────────────────────────────────────

def git_status(repo: str = ".") -> str:
    """Show the git status of a repository."""
    err = _require("git")
    if err: return err
    return _run(["git", "status"], cwd=os.path.expanduser(repo))


def git_log(repo: str = ".", n: int = 10) -> str:
    """Show the last n git commits."""
    err = _require("git")
    if err: return err
    return _run(["git", "log", f"--oneline", f"-{n}"], cwd=os.path.expanduser(repo))


def git_diff(repo: str = ".") -> str:
    """Show unstaged changes in the working tree."""
    err = _require("git")
    if err: return err
    return _run(["git", "diff"], cwd=os.path.expanduser(repo))


def git_branch(repo: str = ".") -> str:
    """List all branches and highlight the current one."""
    err = _require("git")
    if err: return err
    return _run(["git", "branch", "-a"], cwd=os.path.expanduser(repo))


def git_pull(repo: str = ".") -> str:
    """Pull latest changes from the remote."""
    err = _require("git")
    if err: return err
    return _run(["git", "pull"], cwd=os.path.expanduser(repo), timeout=120)


def git_add_commit(repo: str = ".", message: str = "automated commit") -> str:
    """Stage all changes and commit with a message."""
    err = _require("git")
    if err: return err
    _run(["git", "add", "-A"], cwd=os.path.expanduser(repo))
    return _run(["git", "commit", "-m", message], cwd=os.path.expanduser(repo))


def git_clone(url: str, destination: str = ".") -> str:
    """Clone a git repository into a destination folder."""
    err = _require("git")
    if err: return err
    dest = os.path.expanduser(destination)
    return _run(["git", "clone", url, dest], timeout=180)


def git_init(folder: str = ".") -> str:
    """Initialize a new git repository in a folder."""
    err = _require("git")
    if err: return err
    folder = os.path.expanduser(folder)
    os.makedirs(folder, exist_ok=True)
    return _run(["git", "init"], cwd=folder)


# ── Python / pip ───────────────────────────────────────────────────────────────

def pip_install(package: str) -> str:
    """Install a Python package with pip."""
    err = _require("pip")
    if err: err = _require("pip3")
    if err: return "Error: pip not found."
    pip = "pip3" if shutil.which("pip3") else "pip"
    return _run([pip, "install", package], timeout=120)


def pip_list() -> str:
    """List installed Python packages."""
    pip = "pip3" if shutil.which("pip3") else "pip"
    return _run([pip, "list"])


def pip_freeze(output_file: str = None) -> str:
    """Get installed packages as requirements.txt format."""
    pip = "pip3" if shutil.which("pip3") else "pip"
    result = _run([pip, "freeze"])
    if output_file and not result.startswith("Error"):
        path = os.path.expanduser(output_file)
        with open(path, "w") as f:
            f.write(result)
        return f"Saved to {path}:\n{result}"
    return result


def python_run(script: str, cwd: str = ".") -> str:
    """Run a Python script and return its output."""
    script = os.path.expanduser(script)
    py = "python3" if shutil.which("python3") else "python"
    return _run([py, script], cwd=os.path.expanduser(cwd), timeout=120)


def create_venv(path: str = ".venv") -> str:
    """Create a Python virtual environment."""
    path = os.path.expanduser(path)
    py = "python3" if shutil.which("python3") else "python"
    result = _run([py, "-m", "venv", path])
    if "Error" not in result:
        activate = os.path.join(path, "Scripts", "activate") if os.name == "nt" else os.path.join(path, "bin", "activate")
        return f"Virtual environment created at '{path}'.\nActivate with: source {activate}"
    return result


# ── Node / npm ─────────────────────────────────────────────────────────────────

def npm_install(package: str = None, cwd: str = ".") -> str:
    """Install an npm package, or run `npm install` to install all deps."""
    err = _require("npm")
    if err: return err
    cmd = ["npm", "install"] + ([package] if package else [])
    return _run(cmd, cwd=os.path.expanduser(cwd), timeout=180)


def npm_run(script: str, cwd: str = ".") -> str:
    """Run an npm script (e.g. 'start', 'build', 'test')."""
    err = _require("npm")
    if err: return err
    return _run(["npm", "run", script], cwd=os.path.expanduser(cwd), timeout=180)


def npm_list(cwd: str = ".") -> str:
    """List installed npm packages in a project."""
    err = _require("npm")
    if err: return err
    return _run(["npm", "list", "--depth=0"], cwd=os.path.expanduser(cwd))


def node_run(script: str, cwd: str = ".") -> str:
    """Run a Node.js script and return its output."""
    err = _require("node")
    if err: return err
    return _run(["node", script], cwd=os.path.expanduser(cwd), timeout=120)


# ── Docker ─────────────────────────────────────────────────────────────────────

def docker_ps() -> str:
    """List running Docker containers."""
    err = _require("docker")
    if err: return err
    return _run(["docker", "ps"])


def docker_images() -> str:
    """List available Docker images."""
    err = _require("docker")
    if err: return err
    return _run(["docker", "images"])


def docker_logs(container: str, tail: int = 50) -> str:
    """Get the last N lines of logs from a container."""
    err = _require("docker")
    if err: return err
    return _run(["docker", "logs", "--tail", str(tail), container])


def docker_compose_up(cwd: str = ".", detach: bool = True) -> str:
    """Start services with docker-compose."""
    for cmd in (["docker", "compose"], ["docker-compose"]):
        if shutil.which(cmd[0]):
            args = cmd + ["up"] + (["-d"] if detach else [])
            return _run(args, cwd=os.path.expanduser(cwd), timeout=300)
    return "Error: docker compose / docker-compose not found."


def docker_compose_down(cwd: str = ".") -> str:
    """Stop services with docker-compose."""
    for cmd in (["docker", "compose"], ["docker-compose"]):
        if shutil.which(cmd[0]):
            return _run(cmd + ["down"], cwd=os.path.expanduser(cwd), timeout=120)
    return "Error: docker compose / docker-compose not found."


# ── Project scaffolding ────────────────────────────────────────────────────────

def scaffold_python_project(name: str, path: str = "~") -> str:
    """Create a standard Python project structure."""
    base = Path(os.path.expanduser(path)) / name
    try:
        (base / "src" / name.replace("-", "_")).mkdir(parents=True, exist_ok=True)
        (base / "tests").mkdir(exist_ok=True)
        (base / "src" / name.replace("-", "_") / "__init__.py").write_text("")
        (base / "tests" / "__init__.py").write_text("")
        (base / "README.md").write_text(f"# {name}\n\n")
        (base / "pyproject.toml").write_text(
            f'[project]\nname = "{name}"\nversion = "0.1.0"\n'
            f'requires-python = ">=3.10"\n'
        )
        (base / ".gitignore").write_text(
            "__pycache__/\n*.pyc\n.venv/\ndist/\n*.egg-info/\n.env\n"
        )
        return f"Python project '{name}' created at {base}"
    except Exception as e:
        return f"Error scaffolding project: {e}"


def scaffold_node_project(name: str, path: str = "~") -> str:
    """Create a standard Node.js project structure."""
    err = _require("npm")
    base = Path(os.path.expanduser(path)) / name
    try:
        (base / "src").mkdir(parents=True, exist_ok=True)
        (base / "src" / "index.js").write_text("// Entry point\nconsole.log('Hello!');\n")
        (base / "README.md").write_text(f"# {name}\n\n")
        (base / ".gitignore").write_text("node_modules/\n.env\ndist/\n")
        pkg = {
            "name": name, "version": "1.0.0", "description": "",
            "main": "src/index.js", "scripts": {"start": "node src/index.js", "test": "echo 'no tests'"},
        }
        import json
        (base / "package.json").write_text(json.dumps(pkg, indent=2))
        return f"Node.js project '{name}' created at {base}"
    except Exception as e:
        return f"Error scaffolding project: {e}"


# ── Register ───────────────────────────────────────────────────────────────────

def register():
    tasks = [
        # Git
        AutomationTask("git_status", git_status, "show git status of a repository", "devtools", "git_status('~/myproject')"),
        AutomationTask("git_log", git_log, "show the last N git commits", "devtools", "git_log('~/myproject', 10)"),
        AutomationTask("git_diff", git_diff, "show unstaged changes in a repo", "devtools"),
        AutomationTask("git_branch", git_branch, "list all git branches", "devtools"),
        AutomationTask("git_pull", git_pull, "pull latest changes from remote", "devtools"),
        AutomationTask("git_add_commit", git_add_commit, "stage all changes and commit with a message", "devtools", "git_add_commit('.', 'fix bug')"),
        AutomationTask("git_clone", git_clone, "clone a git repository", "devtools", "git_clone('https://github.com/user/repo')"),
        AutomationTask("git_init", git_init, "initialize a new git repository", "devtools"),
        # Python
        AutomationTask("pip_install", pip_install, "install a Python package with pip", "devtools", "pip_install('requests')"),
        AutomationTask("pip_list", pip_list, "list all installed Python packages", "devtools"),
        AutomationTask("pip_freeze", pip_freeze, "export installed packages to requirements.txt format", "devtools"),
        AutomationTask("python_run", python_run, "run a Python script and return its output", "devtools", "python_run('~/script.py')"),
        AutomationTask("create_venv", create_venv, "create a Python virtual environment", "devtools", "create_venv('.venv')"),
        # Node
        AutomationTask("npm_install", npm_install, "install npm package(s) or run npm install for all deps", "devtools", "npm_install('axios', '~/myapp')"),
        AutomationTask("npm_run", npm_run, "run an npm script (start, build, test...)", "devtools", "npm_run('build', '~/myapp')"),
        AutomationTask("npm_list", npm_list, "list installed npm packages in a project", "devtools"),
        AutomationTask("node_run", node_run, "run a Node.js script", "devtools", "node_run('script.js')"),
        # Docker
        AutomationTask("docker_ps", docker_ps, "list running Docker containers", "devtools"),
        AutomationTask("docker_images", docker_images, "list available Docker images", "devtools"),
        AutomationTask("docker_logs", docker_logs, "get logs from a Docker container", "devtools", "docker_logs('my-api', 100)"),
        AutomationTask("docker_compose_up", docker_compose_up, "start services with docker-compose", "devtools"),
        AutomationTask("docker_compose_down", docker_compose_down, "stop services with docker-compose", "devtools"),
        # Scaffolding
        AutomationTask("scaffold_python_project", scaffold_python_project, "create a standard Python project folder structure", "devtools", "scaffold_python_project('my-api')"),
        AutomationTask("scaffold_node_project", scaffold_node_project, "create a standard Node.js project folder structure", "devtools", "scaffold_node_project('my-app')"),
    ]
    for t in tasks:
        register_task(t)
