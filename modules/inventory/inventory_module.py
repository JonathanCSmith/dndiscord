from discord.ext import commands

from module_properties import Module
from utils import decorators
from utils.permissions import CommandRunError


class InventoryManager(Module):
    def __init__(self, manager):
        super().__init__("InventoryManager", manager)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.command(name="stash")
    @decorators.can_run(module_source="inventory", command="inventory")
    async def _inventory(self, ctx: commands.Context, *, info: str):
        pass

    @commands.command(name="store")
    @decorators.can_run(module_source="inventory", command="inventory")
    async def _inventory(self, ctx: commands.Context, *, info: str):
        pass

    def run_check(self, ctx, module_source=None, command=None):

        if module_source == "inventory":

            # We need to be running a session for the inventory command
            session_manager = self.manager.get_module("SessionManager")
            if session_manager is not None and not session_manager.get_session():
                raise CommandRunError("A session is required in order to run the inventory features.")

        return True
