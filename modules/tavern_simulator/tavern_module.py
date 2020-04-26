import os

from discord.ext import commands

from module_properties import Module
from modules.tavern_simulator.data_packs import default_data_pack
from modules.tavern_simulator.model.data_pack import DataPack
from modules.tavern_simulator.model.tavern import Tavern
from utils import constants
from utils.errors import CommandRunError

"""
Define a current state view for the tavern
        
    2) Allow the players to determine what is available now
        a) List next services <implement a tier>
        b) List missing prerequisites and options to obtain
        c) Easily identify the costs and people to speak to.
    
    3) Allow players to change the state of the tavern over time via the GM
        a) Contract negotiations
        b) Purchase negotiations
        c) Purchase contributions
        
    4) Show tavern history
    
    5) Simulate a week and show outcomes in a log

# TODO: Centralize keywords / constants
# TODO: Find a way of mapping tag keys and tag values to translation packs. Namely:
    default_language_pack:
        key: "Human readable representation of this key"
        key.value: "Human readable representation of this value of this key" 
TODO: Document
TODO: Game end listener (THIS IS IMPORTANT)
TODO: We could make this a purchaseable module - if so I would need to reevaluate the load checks for data packs
TODO: Employee names
TODO: Employee, Contract, Customer_History, Sales_History need custom data 
"""


class TavernSimulator(Module):
    def __init__(self, manager):
        super().__init__("tavern_simulator", manager)

        self.taverns = dict()
        self.game_master = self.manager.get_module("game_master")
        if self.game_master:
            self.game_master.register_game_state_listener(self)
        else:
            raise RuntimeError("Cannot use the tavern simulator without the Game Master module.")

        # TODO: We should load taverns here

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    async def get_tavern_for_context(self, ctx):
        game = self.game_master.get_active_game_for_context(ctx)
        if game.get_name() in self.taverns:
            return self.taverns[game.get_name()]

        return None

    async def set_tavern_for_context(self, ctx, tavern):
        game = self.game_master.get_active_game_for_context(ctx)
        self.taverns[game.get_name()] = tavern
        await tavern.save(self.manager, self.game_master, ctx, "tavern")

    async def unload_tavern_for_context(self, ctx, tavern):
        game = self.game_master.get_active_game_for_context(ctx)
        tavern = self.taverns[game.get_name()]
        await tavern.save(self.manager, self.game_master, ctx, "tavern")
        del self.taverns[game.get_name()]

    async def game_created(self, ctx, game):
        pass

    async def game_started(self, ctx, game):
        tavern = await Tavern.load_tavern(self.manager, self.game_master, ctx, "tavern", None)
        if tavern is not None:
            await self.set_tavern_for_context(ctx, tavern)

    async def game_ended(self, ctx, game):
        await self.unload_tavern_for_context(ctx, game)

    async def game_deleted(self, ctx, game):
        # TODO DELTE DATA
        await self.unload_tavern_for_context(ctx, game)

    async def __get_data_pack(self, ctx, pack_name):
        data_pack = None
        data_packs_path = os.path.join(self.name, "data_packs")

        # First check our guild specific dir and our local bot directory
        if pack_name != "" and pack_name != "FORCE":
            await ctx.send("`Attempting to load data pack: " + pack_name + "`")
            data_pack = await DataPack.load_data_pack(self.manager, ctx, data_packs_path, pack_name)

        # Fallback to default_data_oack
        named_data_pack_path = os.path.join(data_packs_path, "default_data_pack")
        if not data_pack and pack_name != "FORCE":
            await ctx.send("`Could not find a data pack named: " + pack_name + " using default instead.`")
            data_pack = await DataPack.load_data_pack(self.manager, ctx, data_packs_path, "default_data_pack")

        # If its still not full we can dump our code based one to file and use that
        if data_pack is None or pack_name == "FORCE":
            await ctx.send("`Using the in code data pack.`")
            data_pack = default_data_pack.create_new_default_data_pack(data_packs_path)
            await data_pack.save(self.manager, ctx)

        return data_pack

    @commands.command(name="tavern:initialize")
    async def _initialize(self, ctx: commands.Context, *, pack: str = ""):
        # Can this user initiate the call to this command
        if not await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:initialize", permissions_level=constants.gm):
            return await ctx.send("`You do not have permission to run that command.`")

        # Check if we have a tavern here!
        tavern = await self.get_tavern_for_context(ctx)
        if tavern:
            return await ctx.send("`There is already a tavern operating in your current game!`")

        # Look for a data pack base on our input.
        data_pack = await self.__get_data_pack(ctx, pack)

        # Check that we actually have data
        if data_pack is None:
            return await ctx.send("`No data pack could be loaded!`")

        # Create a tavern
        tavern = await Tavern.load_tavern(self.manager, self.game_master, ctx, "tavern", data_pack)
        await self.set_tavern_for_context(ctx, tavern)
        return await ctx.send("`Successfully created a tavern for your adventuring party!`")

    @commands.command(name="tavern:name")
    async def _name(self, ctx: commands.Context, *, name: str = ""):
        # Can the user initiate the call to this command
        if not await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:initialize", permissions_level=constants.party_member):
            return await ctx.send("`You do not have permission to run that command.`")

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # Set the tavern and save
        tavern.set_name(name)
        return await ctx.send("`Changed the name of your tavern to: " + name + "`")

    @commands.command(name="tavern:status")
    async def _status(self, ctx: commands.Context):
        # Can this user initiate the call to this command
        if not await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:initialize", permissions_level=constants.party_member):
            return await ctx.send("`You do not have permission to run that command.`")

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # List the tavern properties in a human readable manner:
        # TODO: Create a string builder, if num chars goes over 4000 then we post and continue
        async with ctx.typing():
            await ctx.send("`Your business: " + tavern.get_name() + " has the following properties:`")
            for property, value in tavern.get_properties().items():
                await ctx.send("`" + str(property) + (" with value: " + str(value) if value is not None else "") + "`")

            # Staff
            staff = tavern.get_staff()
            count = len(staff)
            await ctx.send("`You currently have " + str(count) + " employees." + (" They are:" if count > 0 else "") + "`")
            for staff_member in staff:
                await ctx.send("`" + str(staff_member) + "`")

            # Active contracts
            contracts = tavern.get_contracts()
            await ctx.send("`You currently have " + str(len(contracts)) + " contracts ongoing.`")
            for contract in contracts:
                await ctx.send("`" + str(contract) + "`")

            # Customers
            customers = tavern.get_most_recent_customer_history()
            if customers:
                await ctx.send("`Last tenday you had the following customers: ")
                for customer_entry in customers:
                    await ctx.send("`" + str(customer_entry) + "`")
            else:
                await ctx.send("`You have had no customers over the last week.`")

            # Offering
            services = tavern.get_most_recent_sales_history()
            if services:
                await ctx.send("`Last tenday you served the following: `")
                for service in services:
                    await ctx.send("`" + str(service) + "`")
            else:
                await ctx.send("`You have had no sales over the last week.`")

    @commands.command(name="tavern:purchaseable")
    async def _purchaseable(self, ctx: commands):
        # Can this user initiate the call to this command
        if not await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:initialize", permissions_level=constants.gm):
            return await ctx.send("`You do not have permission to run that command.`")

        # TODO: This should really be in the dm's
        pass

    @commands.command(name="tavern:purchase")
    async def _purchase(self, ctx: commands.Context, *, item: str, negotiated_amount: int):
        # Can this user initiate the call to this command
        if not await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:initialize", permissions_level=constants.gm):
            return await ctx.send("`You do not have permission to run that command.`")

        pass
