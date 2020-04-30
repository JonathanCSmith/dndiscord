import os

from discord.ext import commands

from module_properties import Module
from modules.game.game_state_listener import GameStateListener
from modules.inventory.inventory import Inventory
from utils import constants
from utils.currency import CurrencyError
from utils.errors import CommandRunError
from utils.messages import LongMessage
from utils.strings import get_trailing_number, replace_count_reverse

"""
TODO: Personal Inventory Support
"""


class InventoryManager(Module, GameStateListener):
    def __init__(self, manager):
        super().__init__("inventory_manager", manager)
        self.inventories = dict()
        self.game_master = self.manager.get_module("game_master")
        if self.game_master:
            self.game_master.register_game_state_listener(self)
        else:
            raise RuntimeError("Cannot use the tavern simulator without the Game Master module.")

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.inventory = await self.get_inventory(ctx)

    async def get_inventory(self, ctx: commands.Context, game=None):
        # Validate that we have permissions to access this
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "inventory", permissions_level=constants.party_member)
        if not permissions_check:
            # Ignore the reason as otherwise this will spam
            return None

        # Placeholders
        inventory_id = str(ctx.guild.id)

        # If we are in a game we want to load that
        if game:
            inventory_id += game.get_name()

        else:
            game = self.game_master.get_active_game_for_context(ctx)
            if game:
                inventory_id += game.get_name()
            else:
                return None

        # Check our in memory inventories
        inventory = self.inventories.get(inventory_id)

        # Check if there is a file form of the inventory
        if not inventory:
            inventory = await self.game_master.load_game_data(ctx, "inventory", "inventory.json")
            if inventory and inventory.get_inventory_id() != inventory_id:
                raise CommandRunError("`The inventory id of the file loaded doesn't match what we would expect. To prevent issues we cannot load the requested inventory.`")

        # Create a new inventory, save to disk and store locally
        if not inventory:
            inventory = Inventory(inventory_id)
            await self.save_inventory(ctx, inventory)
            self.inventories[inventory_id] = inventory

        # Or just store locally
        else:
            self.inventories[inventory_id] = inventory

        return inventory

    async def save_inventory(self, ctx, inventory):
        return await self.game_master.save_game_data(ctx, "inventory", "inventory.json", inventory)

    async def unload_inventory(self, ctx: commands.Context, game=None):
        inventory = await self.get_inventory(ctx, game)
        if inventory:
            await self.save_inventory(ctx, inventory)
            del self.inventories[inventory.get_inventory_id()]

    async def game_created(self, ctx, game):
        pass

    async def game_started(self, ctx, game):
        await self.get_inventory(ctx)

    async def game_about_to_end(self, ctx, game):
        await self.unload_inventory(ctx, game)

    async def game_deleting(self, ctx, game):
        # TODO: DELETE DATA
        await self.unload_inventory(ctx, game)

    """
    COMMANDS SECTION
    """

    @commands.command(name="inventory")
    async def _inventory_list(self, ctx: commands.Context):
        # Attempt to load our inventory
        if not ctx.inventory:
            return await ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running!`")

        # Lets just list every item in the inventory!
        await ctx.send("`Your stash contains the following items:`")
        long_message = LongMessage()
        # Check if we actually have anything
        if ctx.inventory.size() == 0:
            long_message.add("\tYour inventory is empty!")
        else:
            for item in ctx.inventory:
                long_message.add("\t" + str(item))

        # Always print our currency
        currency = ctx.inventory.get_currency()
        long_message.add(None)
        long_message.add("Your purse has the following coinage:")
        for key, value in currency.items():
            long_message.add("\t" + str(value) + " " + key)

        async with ctx.typing():
            for message in long_message:
                await ctx.send(message)

    @commands.command(name="inventory:store:gold")
    async def _store_gold(self, ctx: commands.Context, *, amount: int):
        # Attempt to load our inventory
        if not ctx.inventory:
            return await ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running!`")

        # Add the item to our inventory
        item = await ctx.inventory.add_object_to_inventory("gold", amount, 0)
        await ctx.send("`You have stored: " + str(item) + "`")

        # Save the changed inventory
        return await self.save_inventory(ctx, ctx.inventory)

    @commands.command(name="inventory:store:silver")
    async def _store_silver(self, ctx: commands.Context, *, amount: int):
        # Attempt to load our inventory
        if not ctx.inventory:
            return await ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running!`")

        # Add the item to our inventory
        item = await ctx.inventory.add_object_to_inventory("silver", amount, 0)
        await ctx.send("`You have stored: " + str(item) + "`")

        # Save the changed inventory
        return await self.save_inventory(ctx, ctx.inventory)

    @commands.command(name="inventory:store:copper")
    async def _store_copper(self, ctx: commands.Context, *, amount: int):
        # Attempt to load our inventory
        if not ctx.inventory:
            return await ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running!`")

        # Add the item to our inventory
        item = await ctx.inventory.add_object_to_inventory("copper", amount, 0)
        await ctx.send("`You have stored: " + str(item) + "`")

        # Save the changed inventory
        return await self.save_inventory(ctx, ctx.inventory)

    @commands.command(name="inventory:store")
    async def _inventory_store(self, ctx: commands.Context, *, info: str):
        # Attempt to load our inventory
        if not ctx.inventory:
            return await ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running!`")

        # Get the weight
        weight = get_trailing_number(info)
        info = replace_count_reverse(info, str(weight), "", 1).strip()
        if weight is None:
            return await ctx.send("`In the current iteration of your inventory goblin it's required that you provide three arguments to stash. Item name, amount, weight per item!`")

        # Get the amount
        amount = get_trailing_number(info)
        info = replace_count_reverse(info, str(amount), "", 1).strip()
        if not amount:
            return await ctx.send("`In the current iteration of your inventory goblin it's required that you provide three arguments to stash. Item name, amount, weight per item!`")

        # Add the item to our inventory
        item = await ctx.inventory.add_object_to_inventory(info, amount, float(weight))
        await ctx.send("`You now have: " + str(item) + "`")

        # Save the changed inventory
        return await self.save_inventory(ctx, ctx.inventory)

    @commands.command(name="inventory:remove")
    async def _inventory_remove(self, ctx: commands.Context, *, info: str):
        # Attempt to load our inventory
        if not ctx.inventory:
            return await ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running!`")

        # Lets parse our arguments
        args = info.split()
        if len(args) != 2:
            return await ctx.send("`In the current iteration of your inventory goblin it's required that you provide three arguments to stash. Item name and amount!`")

        # Check if our inventory has the items and the correct amount
        try:
            if await ctx.inventory.remove(args[0], int(args[1])):
                # Save the changed inventory
                await self.save_inventory(ctx, ctx.inventory)
                return await ctx.send("`Removed: " + args[1] + " " + args[0] + "`")
            else:
                return await ctx.send("`I cannot remove the requested items as either it is not in your stash or there is not enough!`")

        except CurrencyError:
            return await ctx.send("`You currently do not have enough money to do what you are trying to do!`")

    @commands.command(name="inventory:permissions")
    async def _inventory_permissions(self, ctx: commands.Context, *, type: int):
        # Validate that we have permissions to access this
        if not ctx.inventory:
            return ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running.`")

        # Get the game master
        await self.game_master.set_game_permissions_for_context(ctx, "inventory:inventory", type)
        return await ctx.send("`Changed privilege level to: " + str(type) + "`")

    @commands.command(name="inventory:clear")
    async def _inventory_clear(self, ctx: commands.Context):
        # Validate that we have permissions to access this
        if not ctx.inventory:
            return ctx.send("`It looks like you don't have access to any inventories with this guild. Ensure that a game is running.`")

        # Extra perms check
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "inventory:clear", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Clear the inventory
        ctx.inventory.clear()
        await self.save_inventory(ctx, ctx.inventory)
        return ctx.send("`The inventory has been cleared.`")