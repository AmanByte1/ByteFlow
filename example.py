from byteflow import Agent

agent = Agent()

agent.remember("name", "Aman")

print(agent.recall("name"))