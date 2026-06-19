class Tool:
    def __init__(self, name, func, description=""):
        self.name = name
        self.func = func
        self.description = description

    def run(self, *args):
        try:
            return self.func(*args)
        except Exception as e:
            return f"[Tool Error - {self.name}]: {str(e)}"