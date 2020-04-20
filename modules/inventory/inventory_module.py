from discord.ext import commands

from module_properties import Module
from utils.errors import CommandRunError


class InventoryManager(Module):
    def __init__(self, manager):
        super().__init__("InventoryManager", manager)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('An error occurred: {}'.format(str(error)))

    def is_in_game(self, ctx):
        game_manager = self.manager.get_module("GameManager")
        if game_manager and game_manager.get_game():
            return game_manager.is_adventurer(ctx.author.id)

        return False

    @commands.command(name="stash")
    async def _inventory(self, ctx: commands.Context, *, info: str):
        pass

    @commands.command(name="store")
    async def _inventory(self, ctx: commands.Context, *, info: str):
        pass
