from discord.ext import commands

from utils import constants


class Module(commands.Cog):
    def __init__(self, name, engine):
        self.name = name
        self.engine = engine
        self.bot = self.engine.get_bot()

    def get_name(self):
        return self.name
