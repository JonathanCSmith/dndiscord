from discord.ext import commands

from utils.permissions import PermissionsMixin


class Module(PermissionsMixin, commands.Cog):
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.bot = self.manager.get_bot()

    def get_name(self):
        return self.name

    def run_check(self, ctx, module_source=None, command=None):
        pass
