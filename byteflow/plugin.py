class Plugin:
    """
    Base class for ByteFlow plugins.

    Subclasses should override setup() to register tools,
    hooks, or other behavior onto the given agent.
    """

    def __init__(self, name):
        self.name = name

    def setup(self, agent):
        raise NotImplementedError(
            f"Plugin '{self.name}' must implement setup(agent)"
        )