from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider
from byteflow.tools import Tool

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

agent = Agent(provider=OllamaProvider())

# ✅ REGISTER TOOLS HERE (IMPORTANT)
agent.register_tool(Tool("add", add, "adds two numbers"))
agent.register_tool(Tool("multiply", multiply, "multiplies two numbers"))

# RUN
print(agent.run("add 10 and 20"))
print(agent.run("multiply 5 and 6"))