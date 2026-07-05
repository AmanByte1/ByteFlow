"""
Minimal example extension - proves the extension mechanism works and
gives a copyable starting point for a new one. No external
dependencies, so this always loads successfully regardless of what
else is installed.
"""

from byteflow.plugin import Plugin
from byteflow.tools import Tool


def _say_hello(name="world"):
    return f"Hello, {name}! (from the example_hello extension)"


class HelloExtensionPlugin(Plugin):
    def setup(self, agent):
        agent.register_tool(Tool(
            "example_hello",
            _say_hello,
            "a minimal example tool, for testing the extension system",
        ))


def get_plugin():
    return HelloExtensionPlugin("example_hello")
