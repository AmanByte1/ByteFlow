"""
ByteFlow Multi-Device Manager
==============================
Tracks all devices connected to this ByteFlow instance.
Provides:
  - Device registration (phone, tablet, laptop, browser)
  - Real-time presence via heartbeat
  - Shared state sync (active model, memory count, etc.)
  - QR code URL generation
  - Network IP detection for phone access
"""

from __future__ import annotations
import os
import socket
import time
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Device:
    device_id: str
    name: str
    type: str            # "phone" | "tablet" | "laptop" | "browser" | "desktop"
    ip: str
    user_agent: str = ""
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: float = field(default_factory=time.time)
    active: bool = True

    def is_online(self, timeout: float = 30.0) -> bool:
        return (time.time() - self.last_seen) < timeout

    def to_dict(self) -> dict:
        d = asdict(self)
        d["online"] = self.is_online()
        d["last_seen_ago"] = f"{int(time.time() - self.last_seen)}s ago"
        return d


class DeviceManager:
    """
    Tracks all devices connected to ByteFlow.
    Devices register themselves with a heartbeat; stale ones are pruned.
    """

    def __init__(self):
        self._devices: dict[str, Device] = {}
        self._host_ip: Optional[str] = None
        self._port: int = 7860

    # ── Network ───────────────────────────────────────────────────────────────

    def get_host_ip(self) -> str:
        """Get the local network IP for phone access."""
        if self._host_ip:
            return self._host_ip
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._host_ip = ip
            return ip
        except Exception:
            return "127.0.0.1"

    def get_phone_url(self, port: int = None) -> str:
        """Get the URL phones should use to connect."""
        p = port or self._port
        return f"http://{self.get_host_ip()}:{p}"

    def set_port(self, port: int):
        self._port = port

    # ── Device lifecycle ──────────────────────────────────────────────────────

    def register(self, name: str, device_type: str, ip: str, user_agent: str = "") -> Device:
        """Register or update a device."""
        # Check if this IP+type already exists
        existing = next(
            (d for d in self._devices.values() if d.ip == ip and d.type == device_type),
            None
        )
        if existing:
            existing.last_seen = time.time()
            existing.active = True
            return existing

        device = Device(
            device_id=str(uuid.uuid4())[:8],
            name=name,
            type=device_type,
            ip=ip,
            user_agent=user_agent,
        )
        self._devices[device.device_id] = device
        return device

    def heartbeat(self, device_id: str) -> bool:
        """Update last-seen timestamp for a device."""
        if device_id in self._devices:
            self._devices[device_id].last_seen = time.time()
            return True
        return False

    def disconnect(self, device_id: str):
        """Mark a device as disconnected."""
        if device_id in self._devices:
            self._devices[device_id].active = False

    def prune(self, timeout: float = 120.0):
        """Remove devices that haven't been seen for a while."""
        cutoff = time.time() - timeout
        stale = [did for did, d in self._devices.items() if d.last_seen < cutoff]
        for did in stale:
            del self._devices[did]

    # ── Query ─────────────────────────────────────────────────────────────────

    def all(self) -> list[Device]:
        return list(self._devices.values())

    def online(self) -> list[Device]:
        return [d for d in self._devices.values() if d.is_online()]

    def by_type(self, device_type: str) -> list[Device]:
        return [d for d in self._devices.values() if d.type == device_type]

    def count(self) -> dict:
        all_d = self.all()
        return {
            "total": len(all_d),
            "online": len([d for d in all_d if d.is_online()]),
            "phones": len([d for d in all_d if d.type in ("phone", "tablet")]),
            "desktops": len([d for d in all_d if d.type in ("laptop", "desktop", "browser")]),
        }

    def summary(self) -> dict:
        return {
            "host_ip": self.get_host_ip(),
            "phone_url": self.get_phone_url(),
            "devices": [d.to_dict() for d in self.all()],
            "counts": self.count(),
        }

    # ── Device type detection from User-Agent ─────────────────────────────────

    @staticmethod
    def detect_type(user_agent: str) -> str:
        ua = user_agent.lower()
        if "ipad" in ua or ("android" in ua and "mobile" not in ua):
            return "tablet"
        if "iphone" in ua or ("android" in ua and "mobile" in ua):
            return "phone"
        if "mobile" in ua:
            return "phone"
        if "macintosh" in ua or "windows" in ua or "linux" in ua:
            return "desktop"
        return "browser"

    @staticmethod
    def device_icon(device_type: str) -> str:
        return {"phone": "📱", "tablet": "📲", "laptop": "💻",
                "desktop": "🖥️", "browser": "🌐"}.get(device_type, "📡")


# ── Global instance ────────────────────────────────────────────────────────────
_manager = DeviceManager()

def get_device_manager() -> DeviceManager:
    return _manager
