"""
System Automation Tasks
========================
Shell command execution, process management, environment variables,
system info, and scheduled/timed tasks.
"""

import os
import sys
import platform
import subprocess
import shutil
import psutil
from datetime import datetime
from ..registry import AutomationTask, register_task


def _run(cmd: str | list, shell: bool = False, cwd: str = None, timeout: int = 30) -> str:
    """Run a shell command safely."""
    try:
        result = subprocess.run(
            cmd, shell=shell, cwd=cwd,
            capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace"
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        combined = "\n".join(filter(None, [out, err]))
        if result.returncode != 0:
            return f"[exit {result.returncode}]\n{combined}"
        return combined or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


# ── Shell execution ────────────────────────────────────────────────────────────

def run_command(command: str, cwd: str = None, timeout: int = 30) -> str:
    """
    Execute a shell command and return its output.
    The command is run in a shell (bash/cmd), so pipes and redirection work.
    """
    return _run(command, shell=True, cwd=cwd and os.path.expanduser(cwd), timeout=timeout)


def run_script(path: str, interpreter: str = None) -> str:
    """
    Run a script file (.py, .sh, .ps1, .js, .rb, etc.).
    Auto-detects the interpreter from the file extension if not given.
    """
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return f"Error: '{path}' not found."

    ext = os.path.splitext(path)[1].lower()
    if interpreter:
        cmd = [interpreter, path]
    else:
        ext_map = {
            ".py": "python3" if shutil.which("python3") else "python",
            ".sh": "bash",
            ".zsh": "zsh",
            ".js": "node",
            ".ts": "ts-node",
            ".rb": "ruby",
            ".php": "php",
            ".ps1": "powershell",
            ".bat": "cmd /c",
        }
        interp = ext_map.get(ext)
        if not interp:
            return f"Error: unknown extension '{ext}'. Pass interpreter= explicitly."
        cmd = interp.split() + [path]

    return _run(cmd, timeout=120)


# ── System info ────────────────────────────────────────────────────────────────

def system_info() -> dict:
    """Return OS, CPU, memory, and disk info."""
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "os": f"{platform.system()} {platform.release()}",
            "python": sys.version.split()[0],
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_total_gb": round(mem.total / 1e9, 2),
            "memory_used_gb": round(mem.used / 1e9, 2),
            "memory_percent": mem.percent,
            "disk_total_gb": round(disk.total / 1e9, 2),
            "disk_used_gb": round(disk.used / 1e9, 2),
            "disk_percent": disk.percent,
            "hostname": platform.node(),
        }
    except ImportError:
        return {
            "os": f"{platform.system()} {platform.release()}",
            "python": sys.version.split()[0],
            "hostname": platform.node(),
            "note": "Install psutil for CPU/memory/disk info: pip install psutil",
        }


def list_processes(filter_name: str = None) -> list:
    """List running processes, optionally filtered by name."""
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                if filter_name and filter_name.lower() not in info["name"].lower():
                    continue
                procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(procs, key=lambda x: x.get("cpu_percent", 0), reverse=True)[:50]
    except ImportError:
        return ["Error: install psutil → pip install psutil"]


def kill_process(name_or_pid: str) -> str:
    """
    Kill a process by name or PID.
    By name: kills ALL matching processes.
    """
    try:
        killed = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                matches = (
                    str(p.pid) == str(name_or_pid) or
                    name_or_pid.lower() in p.name().lower()
                )
                if matches:
                    p.terminate()
                    killed.append(f"{p.name()} (PID {p.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if killed:
            return f"Terminated: {', '.join(killed)}"
        return f"No process found matching '{name_or_pid}'"
    except ImportError:
        return "Error: install psutil → pip install psutil"


# ── Environment ────────────────────────────────────────────────────────────────

def get_env(key: str = None) -> str | dict:
    """Get an environment variable, or all env vars if no key given."""
    if key:
        val = os.environ.get(key)
        return f"{key}={val}" if val else f"'{key}' not set."
    return dict(os.environ)


def set_env(key: str, value: str) -> str:
    """Set an environment variable for the current process."""
    os.environ[key] = value
    return f"Set {key}={value}"


def which(tool: str) -> str:
    """Find the full path of a command-line tool."""
    path = shutil.which(tool)
    return path if path else f"'{tool}' not found in PATH."


def check_tools(*tools: str) -> dict:
    """Check if multiple tools are installed. Returns {tool: found/not found}."""
    return {t: (shutil.which(t) or "NOT FOUND") for t in tools}


# ── Time / scheduling ──────────────────────────────────────────────────────────

def current_time() -> str:
    """Return the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_after_delay(command: str, seconds: int) -> str:
    """
    Run a shell command after a delay (non-blocking).
    Uses a background thread so ByteFlow doesn't block.
    """
    import threading

    def _delayed():
        import time
        time.sleep(seconds)
        subprocess.run(command, shell=True)

    t = threading.Thread(target=_delayed, daemon=True)
    t.start()
    return f"Scheduled '{command}' to run in {seconds}s (background thread)."


# ── Network ────────────────────────────────────────────────────────────────────

def ping(host: str, count: int = 4) -> str:
    """Ping a host and return the result."""
    flag = "-n" if platform.system() == "Windows" else "-c"
    return _run(["ping", flag, str(count), host], timeout=30)


def http_get(url: str) -> str:
    """Perform an HTTP GET request and return the response body (truncated)."""
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if len(body) > 2000:
                body = body[:2000] + "\n... [truncated]"
            return f"[{resp.status}] {url}\n{body}"
    except Exception as e:
        return f"HTTP GET error: {e}"


# ── Register ───────────────────────────────────────────────────────────────────

def register():
    tasks = [
        AutomationTask("run_command", run_command, "execute any shell command and return its output", "shell", "run_command('ls -la ~/projects')"),
        AutomationTask("run_script", run_script, "run a script file (.py, .sh, .js, etc.) with auto-detected interpreter", "shell", "run_script('~/build.sh')"),
        AutomationTask("system_info", system_info, "return OS, CPU, memory, and disk usage info", "system"),
        AutomationTask("list_processes", list_processes, "list running processes, optionally filtered by name", "system", "list_processes('python')"),
        AutomationTask("kill_process", kill_process, "terminate a process by name or PID", "system", "kill_process('node')", safe=False),
        AutomationTask("get_env", get_env, "get an environment variable or all env vars", "system", "get_env('PATH')"),
        AutomationTask("set_env", set_env, "set an environment variable for the current process", "system", "set_env('DEBUG', '1')"),
        AutomationTask("which", which, "find the full path of a command-line tool", "system", "which('git')"),
        AutomationTask("check_tools", check_tools, "check if multiple tools are installed (git, node, python...)", "system", "check_tools('git', 'node', 'docker')"),
        AutomationTask("current_time", current_time, "return the current date and time", "system"),
        AutomationTask("run_after_delay", run_after_delay, "schedule a command to run after N seconds (background)", "system", "run_after_delay('notify-send Done', 30)"),
        AutomationTask("ping", ping, "ping a host and return latency info", "system", "ping('google.com')"),
        AutomationTask("http_get", http_get, "perform an HTTP GET request and return the response", "system", "http_get('https://api.example.com/status')"),
    ]
    for t in tasks:
        register_task(t)
