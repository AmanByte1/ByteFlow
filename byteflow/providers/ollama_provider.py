"""
ByteFlow Ollama Provider
=========================
Wraps the Ollama Python client. Supports model aliases (q1, mb, l3, etc.)
and automatic model switching via voice commands.
"""
from __future__ import annotations


class OllamaProvider:
    def __init__(self, model: str = "llama3", num_predict: int = 2048):
        """
        model: full model name OR alias (q1, mb, l3, buddy, etc.)
        num_predict: max tokens per response
        """
        try:
            import ollama
        except ImportError as e:
            raise ImportError(
                "OllamaProvider requires the 'ollama' package. "
                "Install it with: pip install ollama"
            ) from e

        # Resolve alias → full model name
        from byteflow.model_registry import resolve_model
        self._ollama = ollama
        self.model = resolve_model(model)
        self.num_predict = num_predict

    def switch_model(self, model: str) -> str:
        """Switch to a different model. Returns the resolved model name."""
        from byteflow.model_registry import resolve_model
        self.model = resolve_model(model)
        return self.model

    def generate(self, prompt: str) -> str:
        response = self._ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": self.num_predict},
        )
        return response["message"]["content"]

    def list_local_models(self) -> list[str]:
        """List models currently installed in Ollama."""
        try:
            result = self._ollama.list()
            return [m.model for m in result.models]
        except Exception:
            return []

    def __repr__(self):
        return f"OllamaProvider(model={self.model!r})"
