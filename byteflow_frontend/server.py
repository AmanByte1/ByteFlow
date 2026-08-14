"""
ByteFlow Frontend Server  (v2 — zero ByteFlow imports)
=======================================================
Thin HTTP proxy + phone UI. Does NOT import byteflow or byteflow_automator.
Instead it talks to them over HTTP.

Architecture:
  Phone browser  ──►  byteflow_frontend (this file, port 7860)
                            │
                            ▼  HTTP
                       byteflow_core API  (port 7861)
                            │
                            ├── ByteFlow Agent (brain)
                            └── byteflow_automator

byteflow_frontend is intentionally tiny: serve HTML, proxy requests,
hold WebSocket connections. That's it. ByteFlow stays lightweight.

Run both:
    python -m byteflow_frontend        # starts frontend on :7860
    python -m byteflow.api_server      # starts core API on :7861
Or together:
    python -m byteflow_frontend --with-core
"""

from __future__ import annotations
import asyncio
import json
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    import httpx
except ImportError:
    import sys
    print(
        "\n[ByteFlow Frontend] Missing dependencies.\n"
        "Run: pip install fastapi uvicorn[standard] httpx pydantic\n"
    )
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
HERE   = Path(__file__).parent
STATIC = HERE / "static"

CORE_URL = os.environ.get("BYTEFLOW_CORE_URL", "http://localhost:7861")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="ByteFlow Frontend", version="2.0.0", docs_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

if STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

_connections: list[WebSocket] = []


# ── Request models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    mode: str = "run"

class AutomateRequest(BaseModel):
    task: str
    args: list = []
    kwargs: dict = {}

class NLAutomateRequest(BaseModel):
    goal: str


# ── Broadcast helpers ─────────────────────────────────────────────────────────
async def broadcast(event: str, data: dict):
    dead = []
    payload = {"event": event, "data": data, "ts": datetime.now().isoformat()}
    for ws in _connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)


# ── Core proxy helpers ────────────────────────────────────────────────────────
async def _core_get(path: str, **kwargs):
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.get(f"{CORE_URL}{path}", **kwargs)
        return r.json()

async def _core_post(path: str, body: dict):
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{CORE_URL}{path}", json=body)
        return r.json()


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    html = STATIC / "index.html"
    return HTMLResponse(html.read_text(encoding="utf-8") if html.exists() else "<h1>ByteFlow</h1>")


@app.get("/api/status")
async def status():
    try:
        core = await _core_get("/status")
        core["frontend"] = "online"
        core["core_url"] = CORE_URL
        return core
    except Exception:
        return {
            "frontend": "online",
            "core": "offline",
            "core_url": CORE_URL,
            "hint": f"Start ByteFlow core: python -m byteflow.api_server",
        }


@app.post("/api/chat")
async def chat(req: ChatRequest):
    await broadcast("thinking", {"message": req.message})
    try:
        data = await _core_post("/chat", {"message": req.message, "mode": req.mode})
        await broadcast("response", data)
        return data
    except Exception as e:
        await broadcast("error", {"message": str(e)})
        return JSONResponse({"error": str(e), "hint": "Is ByteFlow core running?"}, 503)


@app.post("/api/automate")
async def automate(req: AutomateRequest):
    await broadcast("automating", {"task": req.task})
    try:
        data = await _core_post("/automate", {"task": req.task, "args": req.args, "kwargs": req.kwargs})
        await broadcast("automate_result", data)
        return data
    except Exception as e:
        return JSONResponse({"error": str(e)}, 503)


@app.post("/api/automate/nl")
async def automate_nl(req: NLAutomateRequest):
    await broadcast("automating", {"goal": req.goal})
    try:
        data = await _core_post("/automate/nl", {"goal": req.goal})
        await broadcast("automate_result", data)
        return data
    except Exception as e:
        return JSONResponse({"error": str(e)}, 503)


@app.get("/api/tasks")
async def tasks(category: Optional[str] = None):
    try:
        params = {"category": category} if category else {}
        return await _core_get("/tasks", params=params)
    except Exception:
        return {"tasks": [], "total": 0}


@app.get("/api/memory")
async def memory(n: int = 20):
    try:
        return await _core_get("/memory", params={"n": n})
    except Exception:
        return {"history": []}


@app.get("/api/profile")
async def profile():
    try:
        return await _core_get("/profile")
    except Exception:
        return {"facts": []}


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _connections.append(ws)
    await ws.send_json({"event": "connected", "data": {}, "ts": datetime.now().isoformat()})
    try:
        while True:
            data = await ws.receive_json()
            event = data.get("event")
            if event == "chat":
                body = data.get("data", {})
                await broadcast("thinking", {"message": body.get("message", "")})
                try:
                    result = await _core_post("/chat", body)
                    await ws.send_json({"event": "response", "data": result, "ts": datetime.now().isoformat()})
                except Exception as e:
                    await ws.send_json({"event": "error", "data": {"message": str(e)}, "ts": datetime.now().isoformat()})
            elif event == "ping":
                await ws.send_json({"event": "pong", "data": {}, "ts": datetime.now().isoformat()})
    except WebSocketDisconnect:
        if ws in _connections:
            _connections.remove(ws)


# ── Launcher ──────────────────────────────────────────────────────────────────
def get_local_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "127.0.0.1"


def print_qr(url: str):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print("  (pip install qrcode to get a QR code here)")


def start_server(host="0.0.0.0", port=7860, core_url="http://localhost:7861",
                 open_browser=False, with_core=False, model="llama2"):
    global CORE_URL
    CORE_URL = core_url

    ip = get_local_ip()
    phone_url = f"http://{ip}:{port}"

    print("\n" + "=" * 52)
    print("  ByteFlow Frontend  (lightweight proxy)")
    print("=" * 52)
    print(f"  Phone URL : {phone_url}")
    print(f"  Local     : http://localhost:{port}")
    print(f"  Core API  : {core_url}")
    print("=" * 52)
    print()

    if with_core:
        import subprocess, sys
        subprocess.Popen(
            [sys.executable, "-m", "byteflow.api_server", "--model", model],
            cwd=str(HERE.parent)
        )
        print(f"  Started ByteFlow core on {core_url}")
        import time; time.sleep(2)

    print("  Scan with your phone:\n")
    print_qr(phone_url)
    print()

    if open_browser:
        import webbrowser; webbrowser.open(f"http://localhost:{port}")

    uvicorn.run(app, host=host, port=port, log_level="warning")


# ══════════════════════════════════════════════════════════════════════════════
# PROXY ROUTES — Phase 3 & 4 features
# All these forward to the core API
# ══════════════════════════════════════════════════════════════════════════════

# Voice
@app.post("/voice")
async def voice(request: Request):
    body = await request.json()
    return await _post("/voice", body)

# Files
@app.post("/files")
async def files(request: Request):
    body = await request.json()
    return await _post("/files", body)

@app.get("/files/browse")
async def files_browse(path: str = "~"):
    return await _get(f"/files/browse?path={path}")

# Code assistant
@app.post("/code")
async def code(request: Request):
    body = await request.json()
    return await _post("/code", body)

# Scheduler
@app.post("/schedule")
async def schedule(request: Request):
    body = await request.json()
    return await _post("/schedule", body)

@app.get("/schedule")
async def schedule_list():
    return await _get("/schedule")

@app.get("/schedule/{task_id}")
async def schedule_get(task_id: str):
    return await _get(f"/schedule/{task_id}")

@app.delete("/schedule/{task_id}")
async def schedule_delete(task_id: str):
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.delete(f"{CORE_URL}/schedule/{task_id}")
        return r.json()

# Plugin marketplace
@app.get("/plugins")
async def plugins(q: str = "", tag: str = ""):
    return await _get(f"/plugins?q={q}&tag={tag}")

@app.get("/plugins/installed")
async def plugins_installed():
    return await _get("/plugins/installed")

@app.post("/plugins/install")
async def plugin_install(request: Request):
    body = await request.json()
    return await _post("/plugins/install", body)

@app.post("/plugins/uninstall")
async def plugin_uninstall(request: Request):
    body = await request.json()
    return await _post("/plugins/uninstall", body)

@app.post("/plugins/toggle")
async def plugin_toggle(request: Request):
    body = await request.json()
    return await _post("/plugins/toggle", body)

@app.post("/plugins/create")
async def plugin_create(request: Request):
    body = await request.json()
    return await _post("/plugins/create", body)

# Devices
@app.get("/devices")
async def devices():
    return await _get("/devices")

@app.post("/devices/register")
async def device_register(request: Request):
    body = await request.json()
    return await _post("/devices/register", body)

@app.post("/devices/heartbeat")
async def device_heartbeat(request: Request):
    body = await request.json()
    return await _post("/devices/heartbeat", body)

@app.get("/devices/url")
async def device_url():
    return await _get("/devices/url")

@app.get("/devices/count")
async def device_count():
    return await _get("/devices/count")

# Memory
@app.get("/memory")
async def memory_get():
    return await _get("/memory")

@app.post("/memory")
async def memory_post(request: Request):
    body = await request.json()
    return await _post("/memory", body)

@app.delete("/memory")
async def memory_delete():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.delete(f"{CORE_URL}/memory")
        return r.json()

# Models
@app.get("/models")
async def models_list():
    return await _get("/models")


async def _get(path: str):
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{CORE_URL}{path}")
            return r.json()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 503)


async def _post(path: str, body: dict):
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{CORE_URL}{path}", json=body)
            return r.json()
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 503)


from fastapi import Request
