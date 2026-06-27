from byteflow.plugin import Plugin
from byteflow.tools import Tool

class MathPlugin(Plugin):
    def __init__(self):
        super().__init__("MathPlugin")

    def setup(self, agent):
        agent.register_tool(
            Tool("multiply", lambda a, b: a * b, "multiplies two numbers")
        )