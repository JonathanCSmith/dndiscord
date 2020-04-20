from discord.ext import commands


class Module(commands.Cog):
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.bot = self.manager.get_bot()

    def get_name(self):
        return self.name

    """
    TODO: I wanted to put a permissions check generic here, but then the child method was never called - not sure why
    """
