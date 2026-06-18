class Workflow:
    def __init__(self):
        self.steps = []

    def add_step(self, func):
        self.steps.append(func)

    def run(self, data):
        result = data

        for step in self.steps:
            result = step(result)

        return result