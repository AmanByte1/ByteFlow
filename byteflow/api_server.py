"""
ByteFlow Core API Server
========================
This is the ONLY file that imports byteflow and byteflow_automator.
It exposes ByteFlow's brain as a simple HTTP API on localhost:7861.

The frontend, phone app, automator, or any other tool can talk to
ByteFlow through this — without needing to import it directly.

Run:
    python -m byteflow.api_server
    python -m byteflow.api_server --port 7861 --model mistral
"""

from __future__ import annotations
import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Run: pip install fastapi uvicorn[standard] pydantic")
    sys.exit(1)

# ── ByteFlow imports (only here) ──────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from byteflow.agent import Agent
from byteflow.providers.ollama_provider import OllamaProvider
from byteflow.builtin_tools import register_builtin_tools

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="ByteFlow Core API", version="1.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_agent = None
_automator = None
_model = "llama2"


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        provider = OllamaProvider(model=_model)
        _agent = Agent(provider=provider)
        register_builtin_tools(_agent)

        # Register automator tasks as tools on the agent too
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
    mode: str = "run"   # run | chat | code | search

class AutomateRequest(BaseModel):
    task: str
    args: list = []
    kwargs: dict = {}

class NLAutomateRequest(BaseModel):
    goal: str


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/status")
async def status():
    auto = get_automator()
    return {
        "status": "online",
        "model": _model,
        "agent_ready": True,
        "automator_ready": auto is not None,
        "automator_tasks": len(auto.registry) if auto else 0,
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    agent = get_agent()
    loop = asyncio.get_event_loop()

    if req.mode == "chat":
        response = await loop.run_in_executor(None, agent.chat, req.message)
    elif req.mode == "search":
        response = await loop.run_in_executor(None, agent.chat_with_search, req.message)
    elif req.mode == "code":
        result = await loop.run_in_executor(None, lambda: agent.code(req.message, execute=True))
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
        raw = await loop.run_in_executor(None, agent.run, req.message)
        response = str(raw) if not isinstance(raw, str) else raw

    return {"response": response, "mode": req.mode}


@app.post("/automate")
async def automate(req: AutomateRequest):
    auto = get_automator()
    if not auto:
        return JSONResponse({"error": "byteflow_automator not installed"}, 503)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, lambda: auto.run_task(req.task, *req.args, **req.kwargs)
    )
    result_str = json.dumps(result, default=str) if isinstance(result, (dict, list)) else str(result)
    return {"task": req.task, "result": result_str}


@app.post("/automate/nl")
async def automate_nl(req: NLAutomateRequest):
    agent = get_agent()
    auto = get_automator()
    if not auto:
        # fall back to agent.run
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, agent.run, req.goal)
        return {"task": "agent.run", "result": str(result)}

    import re
    task_summary = auto.registry.summary()
    prompt = (
        f"Automation tasks available:\n{task_summary}\n\n"
        f"User wants: {req.goal}\n\n"
        f"Which task? Reply ONLY as JSON: {{\"task\": \"name\", \"args\": [...]}} "
        f"or {{\"task\": null}} if none fits."
    )
    loop = asyncio.get_event_loop()
    plan_str = await loop.run_in_executor(None, agent.chat, prompt)
    try:
        m = re.search(r"\{.*\}", plan_str, re.DOTALL)
        plan = json.loads(m.group()) if m else {}
    except Exception:
        plan = {}

    task_name = plan.get("task")
    args = plan.get("args", [])

    if task_name and task_name in auto.registry:
        result = await loop.run_in_executor(None, lambda: auto.run_task(task_name, *args))
        result_str = json.dumps(result, default=str) if isinstance(result, (dict, list)) else str(result)
        return {"task": task_name, "args": args, "result": result_str}

    # fallback
    result = await loop.run_in_executor(None, agent.run, req.goal)
    return {"task": "agent.run", "result": str(result)}


@app.get("/tasks")
async def tasks(category: Optional[str] = None):
    auto = get_automator()
    if not auto:
        return {"tasks": [], "total": 0}
    items = auto.registry.by_category(category) if category else auto.registry.all()
    return {
        "tasks": [{"name": t.name, "description": t.description,
                   "category": t.category, "example": t.example, "safe": t.safe}
                  for t in items],
        "total": len(items),
    }


@app.get("/memory")
async def memory(n: int = 20):
    agent = get_agent()
    return {"history": agent.memory.get_recent(n)}


@app.get("/profile")
async def profile():
    agent = get_agent()
    return {"facts": agent.profile.all_facts()}


# ── Launcher ──────────────────────────────────────────────────────────────────
def start(port: int = 7861, model: str = "llama2"):
    global _model
    _model = model
    print(f"\n  ByteFlow Core API  →  http://localhost:{port}")
    print(f"  Model: {model}\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=7861)
    p.add_argument("--model", default="llama2")
    args = p.parse_args()
    start(args.port, args.model)
