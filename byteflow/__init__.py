"""ByteFlow package initializer.

Keep imports lightweight so package import remains safe in environments where
optional dependencies (Ollama, voice libraries, etc.) are not installed.
"""

__all__ = ["Agent", "Memory", "__version__"]
__version__ = "0.1.0"


def __getattr__(name):
    if name == "Agent":
        from .agent import Agent
        return Agent
    if name == "Memory":
        from .memory import Memory
        return Memory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
