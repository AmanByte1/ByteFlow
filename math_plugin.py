from byteflow.plugin import Plugin

class MathPlugin(Plugin):
    def __init__(self):
        super().__init__("MathPlugin")

    def setup(self, agent):
        agent.register_tool(
            "multiply",
            lambda a, b: a * b
        )