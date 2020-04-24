from discord.ext import commands

from utils import constants


class Module(commands.Cog):
    def __init__(self, name, manager):
        self.name = name
        self.manager = manager
        self.bot = self.manager.get_bot()

    def get_name(self):
        return self.name

    async def get_module_data(self, ctx, id):
        module_data = await self.manager.get_guild_data_for_module_from_bot_data_store(ctx, self.name)
        if not module_data or id not in module_data:
            return constants.admin
        else:
            return module_data[id]
