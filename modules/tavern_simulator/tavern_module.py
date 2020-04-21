import os

from discord.ext import commands

from module_properties import Module
from modules.tavern_simulator.data_packs import default_data_pack
from modules.tavern_simulator.model.data_pack import DataPack
from modules.tavern_simulator.model.tavern import Tavern
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
"""


class TavernSimulator(Module):
    def __init__(self, manager):
        super().__init__("tavern_simulator", manager)

        self.taverns = dict()

        # TODO: We should load taverns here

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        elif not self.manager.get_module("game_master"):
            raise CommandRunError("This module cannot be run without the game_master module.")

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('An error occurred: {}'.format(str(error)))

    def is_running_game_and_is_gm(self, ctx):
        game_master = self.manager.get_module("game_master")
        return game_master.get_game() and game_master.get_gm() == ctx.author.id

    @commands.command(name="initialize")
    @commands.has_any_role("GM", "@admin")
    async def _initialize(self, ctx: commands.Context, *, pack: str = ""):
        """
        1) Can we run this
        2) Check if a tavern is running for this game already, if so return
        3) Identify a data_pack based on data_pack - if not present default
        4) Load the data pack
        5) Save it into local
        """

        # Are we a gm
        if not self.is_running_game_and_is_gm(ctx):
            raise CommandRunError("Only the GM can initialize the purchase of a tavern!")

        # Is there a tavern already running for this session
        game_master = self.manager.get_module("game_master")
        if game_master.get_game() in self.taverns:
            raise CommandRunError("A tavern is already initialized for this game!")

        # Parse the input strings to look for a data pack
        data_packs_path = os.path.join(".", self.name, "data_packs")
        data_pack = None
        if pack != "" and pack != "FORCE":
            data_pack = await self.manager.load_data(data_packs_path, pack)

        # Load default file if not forced
        if data_pack is None and pack != "FORCE":
            await ctx.send("Could not find data_pack: " + pack + " using default instead")
            data_pack = DataPack(os.path.join(data_packs_path, "default_data_pack"))
            await data_pack.load(self.manager)

        # If its still not full we can dump our code based one to file and use that
        if data_pack is None or pack == "FORCE":
            data_pack = default_data_pack.create_default_data_pack(data_packs_path)
            await data_pack.save(self.manager)

        # Check that we actually have data
        if data_pack is None:
            raise CommandRunError("No default data pack detected!")

        # Check that we can create our tavern
        tavern_path = os.path.join(game_master.get_game_data_path(), self.name)
        tavern_file = os.path.join(tavern_path, "tavern_status.json")
        if os.path.isfile(tavern_file):
            return await ctx.send("There is a save file present at game: " + game_master.get_game_data_path() + "/tavern/tavern_status.json. This will need to be manually removed for now.")

        # Create a tavern - note this should handle the file saving at the same time!
        tavern_state = await Tavern.create_tavern(self.manager, tavern_file, data_pack)
        self.taverns[game_master.get_game()] = tavern_state
        return await ctx.send("Successfully created a tavern for your adventuring party!")

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

        if not self.is_running_game_and_is_gm(ctx):
            raise CommandRunError("Only the GM can initialize the purchase of a tavern")
