"""
ByteFlow Automation Workflows
==============================
"If X then Y" rules that run in the background.

Examples:
  - If disk > 90% → send Telegram alert
  - If file ~/build.log changes → run tests
  - If time is 09:00 → run morning routine shortcut
  - If git has uncommitted changes at 18:00 → remind via notification
  - If CPU > 80% for 60s → kill top process

Workflows are persisted in byteflow_workflows.json and survive restarts.
"""

from __future__ import annotations
import os
import json
import threading
import time
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


WORKFLOWS_FILE = Path(__file__).parent.parent / "byteflow_workflows.json"


# ══════════════════════════════════════════════════════════════
# Triggers
# ══════════════════════════════════════════════════════════════

def check_trigger(trigger: dict) -> bool:
    """Evaluate a trigger condition. Returns True if condition is met."""
    kind = trigger.get("kind", "")

    if kind == "disk_above":
        path = trigger.get("path", "/")
        threshold = trigger.get("threshold", 90)
        try:
            usage = shutil.disk_usage(path)
            pct = (usage.used / usage.total) * 100
            return pct >= threshold
        except Exception:
            return False

    elif kind == "cpu_above":
        threshold = trigger.get("threshold", 80)
        try:
            import psutil
            return psutil.cpu_percent(interval=1) >= threshold
        except ImportError:
            return False

    elif kind == "file_exists":
        path = os.path.expanduser(trigger.get("path", ""))
        return os.path.exists(path)

    elif kind == "file_changed":
        path = os.path.expanduser(trigger.get("path", ""))
        last = trigger.get("_last_mtime", 0)
        if not os.path.exists(path):
            return False
        mtime = os.path.getmtime(path)
        if last and mtime > last:
            trigger["_last_mtime"] = mtime
            return True
        trigger["_last_mtime"] = mtime
        return False

    elif kind == "time_of_day":
        target = trigger.get("time", "09:00")   # HH:MM
        now = datetime.now().strftime("%H:%M")
        last_fired_day = trigger.get("_last_fired_day", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if now == target and last_fired_day != today:
            trigger["_last_fired_day"] = today
            return True
        return False

    elif kind == "command_output":
        cmd = trigger.get("command", "")
        contains = trigger.get("contains", "")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            return contains.lower() in output.lower() if contains else bool(output.strip())
        except Exception:
            return False

    elif kind == "process_running":
        name = trigger.get("process", "").lower()
        try:
            import psutil
            return any(name in p.name().lower() for p in psutil.process_iter(["name"]))
        except ImportError:
            result = subprocess.run(["tasklist" if os.name=="nt" else "pgrep", "-f", name],
                                    capture_output=True, text=True)
            return name in result.stdout.lower()

    elif kind == "interval":
        interval = trigger.get("seconds", 3600)
        last = trigger.get("_last_fired", 0)
        if time.time() - last >= interval:
            trigger["_last_fired"] = time.time()
            return True
        return False

    return False


# ══════════════════════════════════════════════════════════════
# Actions
# ══════════════════════════════════════════════════════════════

def run_action(action: dict) -> str:
    """Execute a workflow action. Returns result string."""
    kind = action.get("kind", "")

    if kind == "shell":
        cmd = action.get("command", "")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return result.stdout.strip() or result.stderr.strip() or f"[exit {result.returncode}]"
        except Exception as e:
            return f"Error: {e}"

    elif kind == "notify":
        title = action.get("title", "ByteFlow")
        body = action.get("body", "")
        system = __import__("platform").system()
        try:
            if system == "Windows":
                subprocess.run(["msg", "*", f"{title}: {body}"], capture_output=True)
            elif system == "Darwin":
                subprocess.run(["osascript", "-e", f'display notification "{body}" with title "{title}"'])
            else:
                subprocess.run(["notify-send", title, body])
            return f"Notification sent: {title}"
        except Exception as e:
            return f"Notify error: {e}"

    elif kind == "telegram":
        from byteflow.integrations import get_integrations
        ig = get_integrations()
        result = ig.telegram.send(action.get("message", "ByteFlow alert"))
        return "Telegram sent" if result.get("ok") else f"Telegram error: {result.get('error')}"

    elif kind == "email":
        from byteflow.integrations import get_integrations
        ig = get_integrations()
        result = ig.email.send(
            to=action.get("to", ""),
            subject=action.get("subject", "ByteFlow Alert"),
            body=action.get("body", ""),
        )
        return "Email sent" if result.get("ok") else f"Email error: {result.get('error')}"

    elif kind == "slack":
        from byteflow.integrations import get_integrations
        ig = get_integrations()
        result = ig.slack.send(action.get("message", "ByteFlow alert"))
        return "Slack sent" if result.get("ok") else f"Slack error: {result.get('error')}"

    elif kind == "shortcut":
        shortcut_id = action.get("shortcut_id", "")
        from byteflow.settings import get_settings
        shortcuts = get_settings().get_shortcuts()
        sc = next((s for s in shortcuts if s["id"] == shortcut_id), None)
        if not sc:
            return f"Shortcut '{shortcut_id}' not found"
        results = []
        for step in sc.get("steps", []):
            r = subprocess.run(step, shell=True, capture_output=True, text=True, timeout=30)
            results.append(r.stdout.strip() or r.stderr.strip())
        return "\n".join(results)

    elif kind == "kill_process":
        name = action.get("process", "")
        try:
            import psutil
            killed = []
            for p in psutil.process_iter(["name"]):
                if name.lower() in p.name().lower():
                    p.terminate()
                    killed.append(p.name())
            return f"Killed: {', '.join(killed)}" if killed else f"No process '{name}' found"
        except ImportError:
            return "psutil not installed"

    return f"Unknown action: {kind}"


# ══════════════════════════════════════════════════════════════
# Workflow data
# ══════════════════════════════════════════════════════════════

@dataclass
class WorkflowRun:
    ts: str
    trigger_fired: bool
    action_result: str
    ok: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Workflow:
    workflow_id: str
    name: str
    description: str = ""
    enabled: bool = True
    trigger: dict = field(default_factory=dict)
    actions: list[dict] = field(default_factory=list)
    check_interval: int = 30
    last_checked: float = 0
    last_fired: float = 0
    run_count: int = 0
    runs: list[dict] = field(default_factory=list)  # last 20 runs

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Workflow":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ══════════════════════════════════════════════════════════════
# Workflow Engine
# ══════════════════════════════════════════════════════════════

class WorkflowEngine:
    """Runs workflows in background. Evaluates triggers, fires actions."""

    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._load()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            now = time.time()
            for wf in list(self._workflows.values()):
                if not wf.enabled:
                    continue
                if now - wf.last_checked < wf.check_interval:
                    continue
                wf.last_checked = now
                try:
                    fired = check_trigger(wf.trigger)
                    if fired:
                        results = []
                        ok = True
                        for action in wf.actions:
                            result = run_action(action)
                            results.append(result)
                        wf.last_fired = now
                        wf.run_count += 1
                        run = WorkflowRun(
                            ts=datetime.now().isoformat(),
                            trigger_fired=True,
                            action_result="\n".join(results),
                            ok=ok,
                        )
                        wf.runs = (wf.runs + [run.to_dict()])[-20:]
                        self._save()
                except Exception:
                    pass
            time.sleep(5)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add(self, workflow_id: str, name: str, trigger: dict,
            actions: list[dict], description: str = "",
            check_interval: int = 30) -> dict:
        wf = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            trigger=trigger,
            actions=actions,
            check_interval=check_interval,
        )
        self._workflows[workflow_id] = wf
        self._save()
        return {"ok": True, "workflow_id": workflow_id, "name": name}

    def remove(self, workflow_id: str) -> dict:
        if workflow_id not in self._workflows:
            return {"ok": False, "error": "Not found"}
        del self._workflows[workflow_id]
        self._save()
        return {"ok": True}

    def toggle(self, workflow_id: str) -> dict:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"ok": False, "error": "Not found"}
        wf.enabled = not wf.enabled
        self._save()
        return {"ok": True, "enabled": wf.enabled}

    def trigger_now(self, workflow_id: str) -> dict:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"ok": False, "error": "Not found"}
        results = []
        for action in wf.actions:
            results.append(run_action(action))
        wf.run_count += 1
        run = WorkflowRun(ts=datetime.now().isoformat(), trigger_fired=True,
                          action_result="\n".join(results), ok=True)
        wf.runs = (wf.runs + [run.to_dict()])[-20:]
        self._save()
        return {"ok": True, "results": results}

    def all(self) -> list[dict]:
        return [wf.to_dict() for wf in self._workflows.values()]

    def get(self, workflow_id: str) -> Optional[dict]:
        wf = self._workflows.get(workflow_id)
        return wf.to_dict() if wf else None

    def stats(self) -> dict:
        return {
            "total": len(self._workflows),
            "enabled": sum(1 for wf in self._workflows.values() if wf.enabled),
            "total_runs": sum(wf.run_count for wf in self._workflows.values()),
        }

    # ── Persistence ───────────────────────────────────────────────────────────

    def _save(self):
        data = {wid: wf.to_dict() for wid, wf in self._workflows.items()}
        try:
            tmp = Path(str(WORKFLOWS_FILE) + ".tmp")
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(WORKFLOWS_FILE)
        except Exception as e:
            print(f"[Workflows] Save failed: {e}")

    def _load(self):
        if not WORKFLOWS_FILE.exists():
            return
        try:
            data = json.loads(WORKFLOWS_FILE.read_text(encoding="utf-8"))
            for wid, wd in data.items():
                self._workflows[wid] = Workflow.from_dict(wd)
        except Exception as e:
            print(f"[Workflows] Load failed: {e}")


_engine: WorkflowEngine = None

def get_workflow_engine() -> WorkflowEngine:
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
        _engine.start()
    return _engine
