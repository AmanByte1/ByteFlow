"""
ByteFlow Automator
==================
A dedicated, general-purpose automation layer for ByteFlow.

ByteFlow stays lightweight - its Agent/brain stays clean.
This module handles all desktop automation, dev tools, file ops,
process management, and command execution - delegated out here.

Usage:
    from byteflow_automator import Automator
    from byteflow.providers.ollama_provider import OllamaProvider

    provider = OllamaProvider()
    automator = Automator(provider=provider)
    result = automator.run("open vscode and create a new python file")
"""

from .automator import Automator
from .registry import TaskRegistry

__all__ = ["Automator", "TaskRegistry"]
__version__ = "1.0.0"
