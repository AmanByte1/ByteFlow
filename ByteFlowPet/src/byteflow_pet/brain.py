from __future__ import annotations

from pathlib import Path
from typing import Optional


class ByteFlowBrain:
    def __init__(self, data_dir: Path, model: str = "llama3"):
        self.data_dir = data_dir
        self.model = model
        self.agent = None
        self.status = "ByteFlow not connected."
        self._connect()

    def _connect(self) -> None:
        try:
            from byteflow.agent import Agent
            from byteflow.builtin_tools import register_builtin_tools
            from byteflow.desktop_tools import register_desktop_tools
            from byteflow.providers.ollama_provider import OllamaProvider
        except Exception as exc:
            self.status = f"ByteFlow import failed: {exc}"
            return

        memory_path = self.data_dir / "byteflow_memory.json"
        try:
            provider = OllamaProvider(model=self.model)
            self.agent = Agent(provider=provider, memory_path=str(memory_path))
            register_builtin_tools(self.agent)
            register_desktop_tools(self.agent)
            self.status = f"ByteFlow connected with model '{self.model}'."
        except Exception as exc:
            self.agent = None
            self.status = f"ByteFlow setup failed: {exc}"

    def ask(self, message: str, pet_context: Optional[str] = None) -> str:
        if not self.agent:
            return (
                "I can remember and do trained actions, but my ByteFlow brain "
                f"is not connected yet. {self.status}"
            )

        prompt = message
        if pet_context:
            prompt = (
                "You are living inside a desktop pet UI. Use this pet state "
                "as context, but answer naturally.\n\n"
                f"Pet state:\n{pet_context}\n\nUser message:\n{message}"
            )

        try:
            result = self.agent.run(prompt)
        except Exception as exc:
            return f"ByteFlow error: {exc}"

        if isinstance(result, dict) and "code" in result:
            reply = result.get("explanation") or result.get("code") or ""
            if result.get("executed") and result.get("result") is not None:
                reply += "\n\n" + result["result"].format()
            return str(reply)
        return str(result)
