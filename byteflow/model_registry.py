"""
ByteFlow Model Registry
========================
Central registry of all available models with aliases.
Voice passwords like "q1" map to full model names.

Usage:
    from byteflow.model_registry import resolve_model, ALL_MODELS
    model = resolve_model("q1")  # → "qwen2.5-coder:1.5b"
"""

from __future__ import annotations

# ── Model aliases (voice passwords → full model names) ─────────────────────
ALIASES: dict[str, str] = {
    # Qwen Coder
    "q1":         "qwen2.5-coder:1.5b",
    "qwen":       "qwen2.5-coder:1.5b",
    "qwencoder":  "qwen2.5-coder:1.5b",
    "q2":         "qwen2.5-coder:7b",
    "qwen7":      "qwen2.5-coder:7b",
    # Llama
    "l3":         "llama3",
    "llama":      "llama3",
    "llama3":     "llama3",
    # My-buddy (custom)
    "mb":         "my-buddy",
    "buddy":      "my-buddy",
    "mybuddy":    "my-buddy",
    # Mistral
    "m":          "mistral",
    "mistral":    "mistral",
    # Phi
    "phi":        "phi",
    "p":          "phi",
    # Gemma
    "g":          "gemma",
    "gemma":      "gemma",
    # CodeLlama
    "cl":         "codellama",
    "code":       "codellama",
    # DeepSeek
    "ds":         "deepseek-coder",
    "deepseek":   "deepseek-coder",
    # Llama3.2
    "l32":        "llama3.2",
    "llama32":    "llama3.2",
}

# ── Model metadata ─────────────────────────────────────────────────────────
MODEL_INFO: dict[str, dict] = {
    "qwen2.5-coder:1.5b": {
        "alias": "q1",
        "label": "Qwen Coder 1.5B",
        "emoji": "⚡",
        "desc": "Fast code model, great for coding tasks",
        "size": "1.5B",
        "best_for": ["code", "quick", "lightweight"],
    },
    "qwen2.5-coder:7b": {
        "alias": "q2",
        "label": "Qwen Coder 7B",
        "emoji": "🧠",
        "desc": "Powerful code model",
        "size": "7B",
        "best_for": ["code", "analysis"],
    },
    "llama3": {
        "alias": "l3",
        "label": "Llama 3",
        "emoji": "🦙",
        "desc": "General purpose, great at reasoning",
        "size": "8B",
        "best_for": ["chat", "reasoning", "general"],
    },
    "my-buddy": {
        "alias": "mb",
        "label": "My Buddy",
        "emoji": "🤝",
        "desc": "Your custom fine-tuned model",
        "size": "custom",
        "best_for": ["chat", "custom"],
    },
    "mistral": {
        "alias": "m",
        "label": "Mistral",
        "emoji": "💨",
        "desc": "Fast and efficient",
        "size": "7B",
        "best_for": ["chat", "code", "fast"],
    },
    "phi": {
        "alias": "p",
        "label": "Phi",
        "emoji": "🔬",
        "desc": "Small but capable",
        "size": "3.8B",
        "best_for": ["quick", "lightweight"],
    },
    "codellama": {
        "alias": "cl",
        "label": "Code Llama",
        "emoji": "💻",
        "desc": "Meta's code specialist",
        "size": "7B",
        "best_for": ["code"],
    },
    "deepseek-coder": {
        "alias": "ds",
        "label": "DeepSeek Coder",
        "emoji": "🔍",
        "desc": "Strong code understanding",
        "size": "6.7B",
        "best_for": ["code", "analysis"],
    },
}


def resolve_model(name: str) -> str:
    """
    Resolve a model alias or partial name to its full Ollama model name.
    Case-insensitive. Returns the input unchanged if not a known alias.

    Examples:
        resolve_model("q1")       → "qwen2.5-coder:1.5b"
        resolve_model("buddy")    → "my-buddy"
        resolve_model("llama3")   → "llama3"
        resolve_model("unknown")  → "unknown"
    """
    key = name.strip().lower().replace("-", "").replace("_", "").replace(" ", "")
    return ALIASES.get(key, name.strip())


def get_model_info(model_name: str) -> dict:
    """Get metadata for a model. Returns empty dict if unknown."""
    full = resolve_model(model_name)
    return MODEL_INFO.get(full, {"label": full, "emoji": "🤖", "desc": "Custom model", "alias": full})


def list_available() -> list[dict]:
    """Return all known models with their info."""
    return [{"name": name, **info} for name, info in MODEL_INFO.items()]


def get_voice_aliases() -> dict[str, str]:
    """Return alias→model map for voice command matching."""
    return dict(ALIASES)
