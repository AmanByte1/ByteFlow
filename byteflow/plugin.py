class Plugin:
    def __init__(self, name):
        self.name = name

    # def setup(self, agent):
    #     pass
    def load_plugin(self, plugin):
        for p in self.plugins:
            if p.name == plugin.name:
                return f"Plugin '{plugin.name}' already loaded"
    
        plugin.setup(self)
        self.plugins.append(plugin)

        return f"Plugin '{plugin.name}' loaded"