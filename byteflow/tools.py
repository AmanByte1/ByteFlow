class Tool:
    def __init__(self, name, func, description="", example=""):
        self.name = name
        self.func = func
        self.description = description
        self.example = example  # optional: "some phrasing -> name(args)" - see agent.py's plan()

    def run(self, *args):
        try:
            return self.func(*args)
        except Exception as e:
            return f"[Tool Error - {self.name}]: {str(e)}"