from discord.ext import commands

from utils import constants


class Module(commands.Cog):
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.bot = self.manager.get_bot()

    def get_name(self):
        return self.name
