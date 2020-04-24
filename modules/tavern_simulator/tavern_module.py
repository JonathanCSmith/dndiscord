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

    0) Initial: Large plot of land with three buildings and a garden area in the north ward.
        a) Main building: Dilapidated but standing. Destroyed and non functional furnishings. Broken shutters and no glazing. Leaky roof. No water. Crumbling basement.
        b) Kitchen & Utilities: Collapsed
        c) Stables and large goods store: Collapsed
        d) Garden: Overgrown
        
    1) Allow the players to view the current status of the tavern
        a) Building status
        b) Contracts <and remaining duration>
        c) Current staff
        d) Patron types visiting
        e) Currently offered services
        
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

    # TODO:
    async def game_created(self, ctx, game):
        pass

    async def game_started(self, ctx, game):
        pass

    async def game_ended(self, ctx, game):
        pass

    async def game_deleted(self, ctx, game):
        pass

    @commands.command(name="tavern:initialize")
    async def _initialize(self, ctx: commands.Context, *, pack: str = ""):
        """
        1) Can we run this
        2) Check if a tavern is running for this game already, if so return
        3) Identify a data_pack based on data_pack - if not present default
        4) Load the data pack
        5) Save it into local
        """
        # Check if we are running a game
        if not self.game_master.is_game_running_for_context(ctx):
            return ctx.send("`A game must be running in order to interact with the tavern.`")

        # Can this user initiate the call to this command
        if not await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:initialize", special_roles=constants.owner_or_role):
            return await ctx.send("`You do not have permission to run that command.`")

        # Check if we have a tavern here!
        tavern = await self.get_tavern_for_context(ctx)
        if tavern:
            return await ctx.send("`There is already a tavern operating in your current game!`")

        # Look for a data pack base on our input.
        data_pack = None
        data_packs_path = os.path.join(self.name, "data_packs")

        # First check our guild specific dir and our local bot directory
        if pack != "" and pack != "FORCE":
            await ctx.send("`Attempting to load data pack: " + pack + "`")
            data_pack = await DataPack.load_data_pack(self.manager, ctx, data_packs_path, pack)

        # Fallback to default_data_oack
        named_data_pack_path = os.path.join(data_packs_path, "default_data_pack")
        if not data_pack and pack != "FORCE":
            await ctx.send("`Could not find a data pack named: " + pack + " using default instead.`")
            data_pack = await DataPack.load_data_pack(self.manager, ctx, data_packs_path, "default_data_pack")

        # If its still not full we can dump our code based one to file and use that
        if data_pack is None or pack == "FORCE":
            await ctx.send("`Using the in code data pack.`")
            data_pack = default_data_pack.create_default_data_pack(data_packs_path)
            await data_pack.save(self.manager, ctx)

        # Check that we actually have data
        if data_pack is None:
            return await ctx.send("`No data pack could be loaded!`")

        # Create a tavern
        tavern = await Tavern.load_tavern(self.manager, self.game_master, ctx, "tavern", data_pack)
        await self.set_tavern_for_context(ctx, tavern)
        return await ctx.send("`Successfully created a tavern for your adventuring party!`")

    @commands.command(name="status")
    async def _status(self, ctx: commands.Context):
        """
        1) Check if the user is in the game
        2) Gather the tavern
        3) Print relevant information
        """

    @commands.command(name="purchase_tavern")
    @commands.has_any_role("GM", "@admin")
    async def _purchase(self, ctx: commands.Context, *, terms: str):
        """
        1) Can we run this
        2) We should check if a data pack is loaded for this game, return if not
        """
