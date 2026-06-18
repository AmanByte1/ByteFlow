from .memory import Memory

class Agent:
    def __init__(self):
        self.memory = Memory()

    def remember(self, key, value):
        self.memory.store(key, value)

    def recall(self, key):
        return self.memory.get(key)

    def run(self, prompt):
        return f"Hello from ByteFlow! You said: {prompt}"