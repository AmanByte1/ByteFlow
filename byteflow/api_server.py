"""
ByteFlow Core API Server  v2
=============================
Robust, production-ready API with:
- Proper error handling & friendly error messages
- Model validation on startup
- Request timeouts
- Health checks
- Memory upgrade (persistent cross-session)
- Voice endpoint
- File manager endpoint
- Task scheduler
- Code assistant
"""

from __future__ import annotations
import sys, os, json, asyncio, re, time, uuid
from pathlib import Path
from typing import Optional
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Run: pip install fastapi uvicorn[standard] pydantic")
    sys.exit(1)

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from byteflow.agent import Agent
from byteflow.providers.ollama_provider import OllamaProvider
from byteflow.builtin_tools import register_builtin_tools

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="ByteFlow Core API", version="2.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_agent = None
_automator = None
_model = "llama2"
_start_time = time.time()
_request_count = 0
_error_count = 0


# ── Friendly error messages ───────────────────────────────────────────────────
def friendly_error(e: Exception) -> str:
    msg = str(e)
    if "model" in msg and "not found" in msg:
        return (
            f"Model '{_model}' is not installed in Ollama. "
            f"Fix: run 'ollama pull {_model}' in your terminal. "
            f"Or check available models with 'ollama list'."
        )
    if "Connection refused" in msg or "ConnectError" in msg:
        return (
            "Cannot connect to Ollama. "
            "Fix: open a terminal and run 'ollama serve', then try again."
        )
    if "timed out" in msg.lower():
        return "Request timed out. The model is taking too long — try a shorter message or restart Ollama."
    if "out of memory" in msg.lower() or "OOM" in msg:
        return "Ollama ran out of memory. Try a smaller model like 'phi' or 'gemma:2b'."
    return f"Error: {msg}"


# ── Agent & automator ─────────────────────────────────────────────────────────
def get_agent() -> Agent:
    global _agent
    if _agent is None:
        provider = OllamaProvider(model=_model)
        _agent = Agent(provider=provider)
        register_builtin_tools(_agent)
        auto = get_automator()
        if auto:
            from byteflow.tools import Tool
            for task in auto.registry.all():
                if task.safe:
                    _agent.register_tool(Tool(task.name, task.func, task.description))
    return _agent


def get_automator():
    global _automator
    if _automator is None:
        try:
            from byteflow_automator import Automator
            _automator = Automator()
        except ImportError:
            pass
    return _automator


# ── Request models ────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    mode: str = "run"
    timeout: int = 120

class AutomateRequest(BaseModel):
    task: str
    args: list = []
    kwargs: dict = {}

class NLAutomateRequest(BaseModel):
    goal: str

class MemoryRequest(BaseModel):
    key: str
    value: str
    tags: list[str] = []

class ScheduleRequest(BaseModel):
    name: str
    command: str
    delay_seconds: int = 0
    cron: Optional[str] = None   # "HH:MM" for daily

class VoiceRequest(BaseModel):
    text: str                    # STT done on frontend; we get text here
    respond_as_text: bool = True

class FileRequest(BaseModel):
    path: str
    content: Optional[str] = None
    operation: str = "read"      # read | write | list | delete | info

class CodeRequest(BaseModel):
    instruction: str
    code: Optional[str] = None   # existing code to fix/review
    execute: bool = False
    language: str = "python"


# ── Scheduled tasks store ─────────────────────────────────────────────────────
_scheduled: dict[str, dict] = {}


# ── Routes — Health ───────────────────────────────────────────────────────────
@app.get("/status")
async def status():
    auto = get_automator()
    uptime = int(time.time() - _start_time)
    return {
        "status": "online",
        "model": _model,
        "uptime_seconds": uptime,
        "uptime_human": f"{uptime // 3600}h {(uptime % 3600) // 60}m",
        "requests_total": _request_count,
        "errors_total": _error_count,
        "agent_ready": _agent is not None,
        "automator_ready": auto is not None,
        "automator_tasks": len(auto.registry) if auto else 0,
        "scheduled_tasks": len(_scheduled),
        "version": "2.0.0",
    }


@app.get("/health")
async def health():
    """Lightweight ping — just confirms server is alive."""
    return {"ok": True, "ts": datetime.now().isoformat()}


@app.get("/models")
async def models():
    """List models available in Ollama."""
    try:
        import ollama
        result = ollama.list()
        names = [m.model for m in result.models]
        return {"models": names, "current": _model}
    except Exception as e:
        return {"models": [], "current": _model, "error": friendly_error(e)}


# ── Routes — Chat ─────────────────────────────────────────────────────────────
@app.post("/chat")
async def chat(req: ChatRequest):
    global _request_count, _error_count
    _request_count += 1
    try:
        agent = get_agent()
        loop = asyncio.get_event_loop()

        async def _run_with_timeout(fn, *args):
            return await asyncio.wait_for(
                loop.run_in_executor(None, fn, *args),
                timeout=req.timeout
            )

        if req.mode == "chat":
            response = await _run_with_timeout(agent.chat, req.message)

        elif req.mode == "search":
            try:
                response = await _run_with_timeout(agent.chat_with_search, req.message)
            except AttributeError:
                response = await _run_with_timeout(agent.chat, req.message)

        elif req.mode == "code":
            result = await _run_with_timeout(
                lambda: agent.code(req.message, execute=True)
            )
            code = result.get("code", "")
            explanation = result.get("explanation", "")
            output = ""
            if result.get("result"):
                r = result["result"]
                output = r.stdout or r.stderr or ""
            response = explanation
            if code:
                response += f"\n\n```python\n{code}\n```"
            if output:
                response += f"\n\n**Output:**\n```\n{output}\n```"

        else:  # run
            raw = await _run_with_timeout(agent.run, req.message)
            response = str(raw) if not isinstance(raw, str) else raw

        return {"response": response, "mode": req.mode, "ok": True}

    except asyncio.TimeoutError:
        _error_count += 1
        return JSONResponse({
            "ok": False,
            "error": f"Request timed out after {req.timeout}s. Try a shorter message.",
            "response": "Sorry, that took too long. Please try again with a shorter question."
        }, 408)
    except Exception as e:
        _error_count += 1
        msg = friendly_error(e)
        return JSONResponse({"ok": False, "error": msg, "response": msg}, 500)


# ── Routes — Voice ────────────────────────────────────────────────────────────
@app.post("/voice")
async def voice(req: VoiceRequest):
    """
    Receive text from phone STT → run through ByteFlow → return response.
    TTS is handled on the frontend (Web Speech API).
    """
    global _request_count
    _request_count += 1
    try:
        agent = get_agent()
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, agent.run, req.text),
            timeout=90
        )
        return {
            "ok": True,
            "input": req.text,
            "response": str(response),
            "speak": str(response),   # frontend reads this aloud
        }
    except asyncio.TimeoutError:
        return JSONResponse({"ok": False, "error": "Timed out", "speak": "Sorry, I timed out."}, 408)
    except Exception as e:
        msg = friendly_error(e)
        return JSONResponse({"ok": False, "error": msg, "speak": msg}, 500)


# ── Routes — File Manager ─────────────────────────────────────────────────────
@app.post("/files")
async def files(req: FileRequest):
    """File manager: read, write, list, delete, info."""
    auto = get_automator()
    if not auto:
        return JSONResponse({"ok": False, "error": "Automator not available"}, 503)

    op = req.operation.lower()
    path = req.path

    try:
        if op == "read":
            result = auto.run_task("read_file", path)
        elif op == "list":
            result = auto.run_task("list_folder", path)
        elif op == "info":
            result = auto.run_task("file_info", path)
        elif op == "write":
            if req.content is None:
                return JSONResponse({"ok": False, "error": "content required for write"}, 400)
            result = auto.run_task("write_file", path, req.content, True)
        elif op == "delete":
            result = auto.run_task("preview_delete", path)
        elif op == "search":
            folder = str(Path(path).parent)
            keyword = Path(path).name
            result = auto.run_task("search_files", folder, keyword)
        else:
            return JSONResponse({"ok": False, "error": f"Unknown operation: {op}"}, 400)

        return {
            "ok": True,
            "operation": op,
            "path": path,
            "result": result,
        }
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)


@app.get("/files/browse")
async def browse(path: str = "~"):
    """Browse a directory — returns files and folders separately."""
    import os, glob
    expanded = os.path.expanduser(path)
    try:
        entries = os.listdir(expanded)
        folders, files = [], []
        for e in sorted(entries):
            full = os.path.join(expanded, e)
            if e.startswith("."): continue
            if os.path.isdir(full):
                folders.append({"name": e, "path": full, "type": "folder"})
            else:
                size = os.path.getsize(full)
                folders_list = files
                files.append({
                    "name": e, "path": full, "type": "file",
                    "ext": Path(e).suffix,
                    "size": size,
                    "size_human": f"{size/1024:.1f}KB" if size < 1e6 else f"{size/1e6:.1f}MB",
                    "modified": datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M"),
                })
        return {
            "ok": True,
            "path": expanded,
            "parent": str(Path(expanded).parent),
            "folders": folders,
            "files": files,
            "total": len(folders) + len(files),
        }
    except PermissionError:
        return JSONResponse({"ok": False, "error": f"Permission denied: {expanded}"}, 403)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)


# ── Routes — Code Assistant ───────────────────────────────────────────────────
@app.post("/code")
async def code_assistant(req: CodeRequest):
    """
    AI code assistant:
    - Write new code from instruction
    - Fix/review existing code
    - Explain code
    - Execute Python code
    """
    global _request_count, _error_count
    _request_count += 1
    try:
        agent = get_agent()
        loop = asyncio.get_event_loop()

        if req.code:
            prompt = (
                f"Language: {req.language}\n"
                f"Task: {req.instruction}\n\n"
                f"Existing code:\n```{req.language}\n{req.code}\n```\n\n"
                f"Respond with the improved/fixed code and a brief explanation."
            )
        else:
            prompt = (
                f"Write {req.language} code to: {req.instruction}\n"
                f"Respond with the code and a brief explanation."
            )

        if req.execute and req.language == "python":
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: agent.code(prompt, execute=True)),
                timeout=60
            )
            code_out = result.get("code", "")
            explanation = result.get("explanation", "")
            run_result = result.get("result")
            output = ""
            if run_result:
                output = run_result.stdout or run_result.stderr or ""
            return {
                "ok": True,
                "code": code_out,
                "explanation": explanation,
                "output": output,
                "executed": True,
            }
        else:
            response = await asyncio.wait_for(
                loop.run_in_executor(None, agent.chat, prompt),
                timeout=90
            )
            # Extract code block if present
            code_match = re.search(rf"```{req.language}\n(.*?)```", response, re.DOTALL)
            code_out = code_match.group(1).strip() if code_match else ""
            return {
                "ok": True,
                "code": code_out,
                "explanation": response,
                "output": "",
                "executed": False,
            }
    except asyncio.TimeoutError:
        _error_count += 1
        return JSONResponse({"ok": False, "error": "Code generation timed out."}, 408)
    except Exception as e:
        _error_count += 1
        return JSONResponse({"ok": False, "error": friendly_error(e)}, 500)


# ── Routes — Task Scheduler ───────────────────────────────────────────────────
@app.post("/schedule")
async def schedule(req: ScheduleRequest, background_tasks: BackgroundTasks):
    """Schedule an automation task or shell command."""
    task_id = str(uuid.uuid4())[:8]
    _scheduled[task_id] = {
        "id": task_id,
        "name": req.name,
        "command": req.command,
        "created": datetime.now().isoformat(),
        "status": "pending",
        "result": None,
    }

    async def _run_delayed():
        if req.delay_seconds > 0:
            await asyncio.sleep(req.delay_seconds)
        try:
            auto = get_automator()
            if auto:
                result = auto.run_task("run_command", req.command)
            else:
                import subprocess
                r = subprocess.run(req.command, shell=True, capture_output=True, text=True, timeout=60)
                result = r.stdout or r.stderr
            _scheduled[task_id]["status"] = "done"
            _scheduled[task_id]["result"] = str(result)
            _scheduled[task_id]["completed"] = datetime.now().isoformat()
        except Exception as e:
            _scheduled[task_id]["status"] = "error"
            _scheduled[task_id]["result"] = str(e)

    background_tasks.add_task(_run_delayed)

    return {
        "ok": True,
        "task_id": task_id,
        "name": req.name,
        "command": req.command,
        "delay_seconds": req.delay_seconds,
        "message": f"Scheduled '{req.name}' (ID: {task_id})" + (
            f" — runs in {req.delay_seconds}s" if req.delay_seconds else " — runs now"
        ),
    }


@app.get("/schedule")
async def list_scheduled():
    return {"tasks": list(_scheduled.values()), "total": len(_scheduled)}


@app.get("/schedule/{task_id}")
async def get_scheduled(task_id: str):
    task = _scheduled.get(task_id)
    if not task:
        return JSONResponse({"ok": False, "error": f"No task with ID '{task_id}'"}, 404)
    return task


@app.delete("/schedule/{task_id}")
async def delete_scheduled(task_id: str):
    if task_id in _scheduled:
        del _scheduled[task_id]
        return {"ok": True, "message": f"Removed task {task_id}"}
    return JSONResponse({"ok": False, "error": "Not found"}, 404)


# ── Routes — Memory (upgraded) ────────────────────────────────────────────────
@app.get("/memory")
async def memory(n: int = 20):
    agent = get_agent()
    try:
        history = agent.memory.get_recent(n)
    except Exception:
        history = []
    return {"history": history, "count": len(history)}


@app.post("/memory")
async def save_memory(req: MemoryRequest):
    """Explicitly save a fact to ByteFlow's memory."""
    agent = get_agent()
    try:
        agent.memory.save(req.key, req.value)
        return {"ok": True, "saved": {req.key: req.value}}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)


@app.delete("/memory")
async def clear_memory():
    """Clear all conversation history."""
    agent = get_agent()
    try:
        agent.memory.clear()
        return {"ok": True, "message": "Memory cleared"}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)


@app.get("/profile")
async def profile():
    agent = get_agent()
    try:
        facts = agent.profile.all_facts()
    except Exception:
        facts = []
    return {"facts": facts}


# ── Routes — Automate ─────────────────────────────────────────────────────────
@app.post("/automate")
async def automate(req: AutomateRequest):
    auto = get_automator()
    if not auto:
        return JSONResponse({"ok": False, "error": "byteflow_automator not installed"}, 503)
    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: auto.run_task(req.task, *req.args, **req.kwargs)),
            timeout=60
        )
        result_str = json.dumps(result, default=str) if isinstance(result, (dict, list)) else str(result)
        return {"ok": True, "task": req.task, "result": result_str}
    except asyncio.TimeoutError:
        return JSONResponse({"ok": False, "error": "Task timed out"}, 408)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)


@app.post("/automate/nl")
async def automate_nl(req: NLAutomateRequest):
    agent = get_agent()
    auto = get_automator()

    if not auto:
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, agent.run, req.goal),
                timeout=90
            )
            return {"ok": True, "task": "agent.run", "result": str(result)}
        except Exception as e:
            return JSONResponse({"ok": False, "error": friendly_error(e)}, 500)

    task_summary = auto.registry.summary()
    prompt = (
        f"Automation tasks available:\n{task_summary}\n\n"
        f"User wants: {req.goal}\n\n"
        f"Which task? Reply ONLY as JSON: {{\"task\": \"name\", \"args\": [...]}} "
        f"or {{\"task\": null}} if none fits."
    )
    loop = asyncio.get_event_loop()
    try:
        plan_str = await asyncio.wait_for(
            loop.run_in_executor(None, agent.chat, prompt),
            timeout=60
        )
    except asyncio.TimeoutError:
        return JSONResponse({"ok": False, "error": "Planning timed out"}, 408)
    except Exception as e:
        return JSONResponse({"ok": False, "error": friendly_error(e)}, 500)

    try:
        m = re.search(r"\{.*\}", plan_str, re.DOTALL)
        plan = json.loads(m.group()) if m else {}
    except Exception:
        plan = {}

    task_name = plan.get("task")
    args = plan.get("args", [])

    if task_name and task_name in auto.registry:
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: auto.run_task(task_name, *args)),
                timeout=60
            )
            result_str = json.dumps(result, default=str) if isinstance(result, (dict, list)) else str(result)
            return {"ok": True, "task": task_name, "args": args, "result": result_str}
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, 500)

    # fallback to agent
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, agent.run, req.goal),
            timeout=90
        )
        return {"ok": True, "task": "agent.run", "result": str(result)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": friendly_error(e)}, 500)


@app.get("/tasks")
async def tasks(category: Optional[str] = None):
    auto = get_automator()
    if not auto:
        return {"tasks": [], "total": 0}
    items = auto.registry.by_category(category) if category else auto.registry.all()
    return {
        "tasks": [
            {"name": t.name, "description": t.description,
             "category": t.category, "example": t.example, "safe": t.safe}
            for t in items
        ],
        "total": len(items),
        "categories": list(set(t.category for t in auto.registry.all())),
    }


# ── Launcher ──────────────────────────────────────────────────────────────────
def start(port: int = 7861, model: str = "llama2"):
    global _model
    _model = model

    # Validate model exists before starting
    try:
        import ollama
        available = [m.model for m in ollama.list().models]
        # Match partial names (llama3 matches llama3:latest)
        matched = next((m for m in available if model in m or m.startswith(model)), None)
        if not matched:
            print(f"\n  ⚠️  Model '{model}' not found in Ollama!")
            print(f"  Available: {', '.join(available) if available else 'none'}")
            print(f"  Fix: ollama pull {model}\n")
            if available:
                _model = available[0].split(":")[0]
                print(f"  Auto-switching to: {_model}\n")
        else:
            _model = matched.split(":")[0] if ":" in matched else matched
    except Exception:
        pass  # Ollama not running yet, will fail on first request with friendly message

    print(f"\n{'='*48}")
    print(f"  ByteFlow Core API  v2.0")
    print(f"{'='*48}")
    print(f"  URL   : http://localhost:{port}")
    print(f"  Docs  : http://localhost:{port}/docs")
    print(f"  Model : {_model}")
    print(f"{'='*48}\n")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=7861)
    p.add_argument("--model", default="llama2")
    args = p.parse_args()
    start(args.port, args.model)


# ══════════════════════════════════════════════════════════════════════════════
# PLUGIN MARKETPLACE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

from byteflow.marketplace import get_marketplace

class PluginInstallRequest(BaseModel):
    plugin_id: str

class PluginCreateRequest(BaseModel):
    name: str
    description: str
    code: str
    author: str = "User"

@app.get("/plugins")
async def plugins_catalog(q: str = "", tag: str = ""):
    """Browse the plugin marketplace catalog."""
    mp = get_marketplace()
    return {"ok": True, "plugins": mp.catalog(q, tag), "status": mp.status()}

@app.get("/plugins/installed")
async def plugins_installed():
    """List all installed plugins."""
    mp = get_marketplace()
    return {"ok": True, "plugins": mp.installed(), "status": mp.status()}

@app.post("/plugins/install")
async def plugin_install(req: PluginInstallRequest):
    """Install a plugin from the marketplace."""
    mp = get_marketplace()
    result = mp.install(req.plugin_id)
    return result

@app.post("/plugins/uninstall")
async def plugin_uninstall(req: PluginInstallRequest):
    """Uninstall a plugin."""
    mp = get_marketplace()
    return mp.uninstall(req.plugin_id)

@app.post("/plugins/toggle")
async def plugin_toggle(req: PluginInstallRequest):
    """Enable or disable a plugin."""
    mp = get_marketplace()
    return mp.toggle(req.plugin_id)

@app.post("/plugins/create")
async def plugin_create(req: PluginCreateRequest):
    """Create a new custom plugin from user code."""
    mp = get_marketplace()
    return mp.create(req.name, req.description, req.code, req.author)


# ══════════════════════════════════════════════════════════════════════════════
# MULTI-DEVICE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

from byteflow.device_manager import get_device_manager
from fastapi import Request

class DeviceHeartbeatRequest(BaseModel):
    device_id: str

class DeviceRegisterRequest(BaseModel):
    name: str = "Unknown Device"

@app.get("/devices")
async def devices_list():
    """List all connected devices."""
    dm = get_device_manager()
    dm.prune()
    return dm.summary()

@app.post("/devices/register")
async def device_register(req: DeviceRegisterRequest, request: Request):
    """Register a new device (called when phone opens the UI)."""
    dm = get_device_manager()
    ua = request.headers.get("user-agent", "")
    ip = request.client.host
    device_type = dm.detect_type(ua)
    device = dm.register(req.name or f"{device_type.capitalize()}", device_type, ip, ua)
    return {
        "ok": True,
        "device_id": device.device_id,
        "type": device.type,
        "icon": dm.device_icon(device.type),
        "phone_url": dm.get_phone_url(),
        "host_ip": dm.get_host_ip(),
    }

@app.post("/devices/heartbeat")
async def device_heartbeat(req: DeviceHeartbeatRequest):
    """Keep a device marked as online."""
    dm = get_device_manager()
    ok = dm.heartbeat(req.device_id)
    return {"ok": ok}

@app.get("/devices/url")
async def device_url():
    """Get the URL phones should use to access ByteFlow."""
    dm = get_device_manager()
    return {
        "url": dm.get_phone_url(),
        "ip": dm.get_host_ip(),
        "port": dm._port,
    }

@app.get("/devices/count")
async def device_count():
    """Quick count of online devices."""
    dm = get_device_manager()
    dm.prune()
    return dm.count()
