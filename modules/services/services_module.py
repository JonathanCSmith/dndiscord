from discord.ext import commands

from module_properties import Module
from utils import constants, currency
from utils.errors import CommandRunError


class ServicesManager(Module):
    def __init__(self, engine):
        super().__init__("services_manager", engine)

        self.game_master = self.engine.get_module("game_master")
        if not self.game_master:
            raise RuntimeError("Cannot use the tavern simulator without the game master module.")

        self.inventory_manager = self.engine.get_module("inventory_manager")

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    @commands.command(name="services:rest")
    async def _rest(self, ctx: commands.Context):
        # Do we have permission to run this command. A game must be running.
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "services:rest", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the current game
        game = self.game_master.get_active_game_for_context(ctx)
        player_count = str(len(game.get_adventurers()))
        if player_count == 0:
            return await ctx.send("`It looks like you don't have anyone in your adventuring party.`")

        # Check for inventory integrations
        await ctx.send("`For this rest you party will need to consume: " + player_count + " rations plus any for your companions & animals.`")

        # Lets remove it from our inventory
        # TODO: For now we just call rations directly
        if self.inventory_manager:
            await ctx.send("`Attempting to remove [ration]s from your group's inventory automatically.`")
            ctx.inventory = await self.inventory_manager.get_inventory(ctx)
            if await self.inventory_manager._inventory_remove(ctx, info="ration " + player_count):
                return await ctx.send("`The food has been consumed!`")
            else:
                return await ctx.send("`You do not have enough food! [Hint: ration is the thing you need]`")

    @commands.command(name="services:inn:rest")
    async def _rest_at_inn(self, ctx: commands.Context, *, cost_in_cp: int):
        # Do we have permission to run this command. A game must be running.
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "services:inn:rest", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the current game
        game = self.game_master.get_active_game_for_context(ctx)
        cost = str(len(game.get_adventurers()) * cost_in_cp)
        if cost == 0:
            return await ctx.send("`It looks like you don't have anyone in your adventuring party.`")

        # Check for inventory integrations
        await ctx.send("`For this rest you party will need : " + cost + " copper pieces per head not including companions and stabling.`")

        # Lets remove it from our inventory
        # TODO: For now we just call copper directly
        if self.inventory_manager:
            await ctx.send("`Attempting to remove this from your group's inventory automatically.`")
            ctx.inventory = await self.inventory_manager.get_inventory(ctx)
            if await self.inventory_manager._inventory_remove(ctx, info=currency.copper_pieces + " " + cost):
                return await ctx.send("`You have successfully paid for your rest.`")
            else:
                return await ctx.send("`You do not have enough to pay for your rest!`")

    @commands.command(name="services:inn:eat")
    async def _eat_at_inn(self, ctx: commands.Context, *, cost_in_cp: int):
        # Do we have permission to run this command. A game must be running.
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "services:inn:eat", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the current game
        game = self.game_master.get_active_game_for_context(ctx)
        cost = str(len(game.get_adventurers()) * cost_in_cp)
        if cost == 0:
            return await ctx.send("`It looks like you don't have anyone in your adventuring party.`")

        # Check for inventory integrations
        await ctx.send("`For this food you party will need : " + cost + " copper pieces not including companions and stabling.`")

        # Lets remove it from our inventory
        # TODO: For now we just call copper directly
        if self.inventory_manager:
            await ctx.send("`Attempting to remove this from your group's inventory automatically.`")
            ctx.inventory = await self.inventory_manager.get_inventory(ctx)
            if await self.inventory_manager._inventory_remove(ctx, info=currency.copper_pieces + " " + str(cost)):
                return await ctx.send("`You have successfully paid for your food.`")
            else:
                return await ctx.send("`You do not have enough to pay for your food!`")
