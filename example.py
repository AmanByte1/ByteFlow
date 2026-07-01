from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider
from byteflow.tools import Tool

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

agent = Agent(provider=OllamaProvider())

# REGISTER TOOLS HERE
agent.register_tool(Tool("add", add, "adds two numbers"))
agent.register_tool(Tool("multiply", multiply, "multiplies two numbers"))

# RUN (tool calling)
print(agent.run("add 10 and 20"))
print(agent.run("multiply 5 and 6"))

# CHAT (plain Q&A, with persistent memory across runs)
# Run this script twice to see it remember context between runs.
memory_agent = Agent(provider=OllamaProvider(), memory_path="byteflow_memory.json")
print(memory_agent.chat("Remember that my favorite language is Python."))
print(memory_agent.chat("What's my favorite language?"))