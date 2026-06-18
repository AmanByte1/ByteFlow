from byteflow import Agent
from byteflow.providers.ollama_provider import OllamaProvider

def add(a, b):
    return a + b

agent = Agent(provider=OllamaProvider())

agent.register_tool("add", add)

print(agent.run("add 10 and 20"))