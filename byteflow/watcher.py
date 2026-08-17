"""
ByteFlow Proactive Watcher
===========================
Runs background checks and fires notifications when things need attention.

Watches:
  - Disk space (alert when > threshold %)
  - Git repos (new commits, uncommitted changes)
  - Process CPU hogs
  - Custom file watchers (file changed → alert)
  - Custom command watchers (run command → check output)

All alerts are stored in a queue the frontend polls via /watch/alerts.
"""

from __future__ import annotations
import os
import time
import threading
import subprocess
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable


@dataclass
class Alert:
    alert_id: str
    kind: str          # "disk" | "git" | "process" | "file" | "custom"
    title: str
    body: str
    level: str = "info"   # "info" | "warning" | "error"
    ts: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.alert_id, "kind": self.kind,
            "title": self.title, "body": self.body,
            "level": self.level, "ts": self.ts, "read": self.read,
        }


@dataclass
class WatchRule:
    rule_id: str
    name: str
    kind: str
    enabled: bool = True
    config: dict = field(default_factory=dict)
    last_checked: float = 0
    interval: int = 60   # seconds between checks


class ProactiveWatcher:
    """
    Background thread that runs watch rules and queues alerts.
    Frontend polls /watch/alerts to get new alerts.
    """

    MAX_ALERTS = 200

    def __init__(self):
        self._rules: dict[str, WatchRule] = {}
        self._alerts: list[Alert] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._alert_counter = 0
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Register default watch rules."""
        self._rules["disk_main"] = WatchRule(
            "disk_main", "Disk Space", "disk",
            config={"path": "/", "threshold": 85},
            interval=300,
        )
        self._rules["cpu_hogs"] = WatchRule(
            "cpu_hogs", "CPU Hogs", "process",
            config={"threshold": 80, "top_n": 3},
            interval=120,
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────────

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
            for rule in list(self._rules.values()):
                if not rule.enabled:
                    continue
                if now - rule.last_checked >= rule.interval:
                    rule.last_checked = now
                    try:
                        self._run_rule(rule)
                    except Exception as e:
                        pass  # Never crash the watcher thread
            time.sleep(10)

    def _run_rule(self, rule: WatchRule):
        if rule.kind == "disk":
            self._check_disk(rule)
        elif rule.kind == "process":
            self._check_cpu(rule)
        elif rule.kind == "git":
            self._check_git(rule)
        elif rule.kind == "file":
            self._check_file(rule)
        elif rule.kind == "custom":
            self._check_custom(rule)

    # ── Built-in checks ────────────────────────────────────────────────────────

    def _check_disk(self, rule: WatchRule):
        path = rule.config.get("path", "/")
        threshold = rule.config.get("threshold", 85)
        try:
            usage = shutil.disk_usage(path)
            pct = (usage.used / usage.total) * 100
            if pct >= threshold:
                free_gb = usage.free / 1e9
                self._add_alert(
                    kind="disk",
                    title="⚠️ Disk Space Low",
                    body=f"Drive {path} is {pct:.1f}% full. Only {free_gb:.1f} GB free.",
                    level="warning" if pct < 95 else "error",
                )
        except Exception:
            pass

    def _check_cpu(self, rule: WatchRule):
        threshold = rule.config.get("threshold", 80)
        top_n = rule.config.get("top_n", 3)
        try:
            import psutil
            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent"]):
                try:
                    cpu = p.info["cpu_percent"] or 0
                    if cpu >= threshold:
                        procs.append((p.info["name"], cpu, p.pid))
                except Exception:
                    pass
            procs.sort(key=lambda x: x[1], reverse=True)
            if procs[:top_n]:
                lines = ", ".join(f"{n} ({c:.0f}%)" for n, c, _ in procs[:top_n])
                self._add_alert(
                    kind="process",
                    title="🔥 High CPU Usage",
                    body=f"Processes using high CPU: {lines}",
                    level="warning",
                )
        except ImportError:
            pass

    def _check_git(self, rule: WatchRule):
        repo = rule.config.get("repo", ".")
        try:
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=os.path.expanduser(repo),
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split("\n")
                self._add_alert(
                    kind="git",
                    title="📝 Uncommitted Changes",
                    body=f"Repo {repo}: {len(lines)} uncommitted change(s)",
                    level="info",
                )

            # Check for new remote commits
            subprocess.run(["git", "fetch"], cwd=os.path.expanduser(repo),
                           capture_output=True, timeout=15)
            behind = subprocess.run(
                ["git", "rev-list", "--count", "HEAD..@{u}"],
                cwd=os.path.expanduser(repo),
                capture_output=True, text=True, timeout=10
            )
            count = int(behind.stdout.strip() or 0)
            if count > 0:
                self._add_alert(
                    kind="git",
                    title="⬇️ New Commits Available",
                    body=f"Repo {repo}: {count} new commit(s) on remote. Run git pull.",
                    level="info",
                )
        except Exception:
            pass

    def _check_file(self, rule: WatchRule):
        path = rule.config.get("path", "")
        last_mtime = rule.config.get("last_mtime", 0)
        if not path or not os.path.exists(os.path.expanduser(path)):
            return
        mtime = os.path.getmtime(os.path.expanduser(path))
        if last_mtime and mtime > last_mtime:
            self._add_alert(
                kind="file",
                title="📄 File Changed",
                body=f"{path} was modified at {datetime.fromtimestamp(mtime).strftime('%H:%M:%S')}",
                level="info",
            )
        rule.config["last_mtime"] = mtime

    def _check_custom(self, rule: WatchRule):
        cmd = rule.config.get("command", "")
        expect = rule.config.get("expect", "")
        if not cmd:
            return
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True,
                text=True, timeout=15
            )
            output = result.stdout.strip() or result.stderr.strip()
            if expect and expect.lower() not in output.lower():
                self._add_alert(
                    kind="custom",
                    title=f"⚠️ {rule.name}",
                    body=f"Expected '{expect}' not found in output: {output[:200]}",
                    level="warning",
                )
            elif not expect and output:
                self._add_alert(
                    kind="custom",
                    title=f"📋 {rule.name}",
                    body=output[:300],
                    level="info",
                )
        except Exception as e:
            pass

    # ── Alert management ───────────────────────────────────────────────────────

    def _add_alert(self, kind: str, title: str, body: str, level: str = "info"):
        with self._lock:
            self._alert_counter += 1
            alert = Alert(
                alert_id=str(self._alert_counter),
                kind=kind, title=title, body=body, level=level,
            )
            self._alerts.append(alert)
            if len(self._alerts) > self.MAX_ALERTS:
                self._alerts = self._alerts[-self.MAX_ALERTS:]

    def get_alerts(self, unread_only: bool = False, limit: int = 50) -> list[dict]:
        with self._lock:
            alerts = self._alerts
            if unread_only:
                alerts = [a for a in alerts if not a.read]
            return [a.to_dict() for a in reversed(alerts[-limit:])]

    def mark_read(self, alert_id: str = None):
        with self._lock:
            for a in self._alerts:
                if alert_id is None or a.alert_id == alert_id:
                    a.read = True

    def unread_count(self) -> int:
        with self._lock:
            return sum(1 for a in self._alerts if not a.read)

    def clear_alerts(self):
        with self._lock:
            self._alerts = []

    # ── Rule management ────────────────────────────────────────────────────────

    def add_rule(self, rule_id: str, name: str, kind: str,
                 config: dict, interval: int = 60) -> WatchRule:
        rule = WatchRule(rule_id, name, kind, config=config, interval=interval)
        self._rules[rule_id] = rule
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def toggle_rule(self, rule_id: str) -> dict:
        rule = self._rules.get(rule_id)
        if not rule:
            return {"ok": False, "error": "Rule not found"}
        rule.enabled = not rule.enabled
        return {"ok": True, "enabled": rule.enabled}

    def get_rules(self) -> list[dict]:
        return [
            {"id": r.rule_id, "name": r.name, "kind": r.kind,
             "enabled": r.enabled, "interval": r.interval,
             "config": r.config, "last_checked": r.last_checked}
            for r in self._rules.values()
        ]

    def trigger_now(self, rule_id: str) -> dict:
        """Manually trigger a rule right now."""
        rule = self._rules.get(rule_id)
        if not rule:
            return {"ok": False, "error": "Rule not found"}
        try:
            self._run_rule(rule)
            return {"ok": True, "message": f"Rule '{rule.name}' triggered"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ── Global instance ────────────────────────────────────────────────────────────
_watcher: ProactiveWatcher = None

def get_watcher() -> ProactiveWatcher:
    global _watcher
    if _watcher is None:
        _watcher = ProactiveWatcher()
        _watcher.start()
    return _watcher
