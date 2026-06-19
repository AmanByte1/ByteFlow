class Memory:
    def __init__(self):
        self.history = []

    def add(self, role, content):
        self.history.append({
            "role": role,
            "content": content
        })

    def get_recent(self, n=5):
        return self.history[-n:]

    def clear(self):
        self.history = []