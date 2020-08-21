import os
from enum import Enum

from discord.ext import commands

from bot.core_data import GuildData
from bot.message_utilities import send_message
from core import Module, Engine
from data.file_system import BotFileSystem

"""
The core of this module is responsible for understanding the context of command execution, the filesystem paths and the permissions system.

Runtime:
    Guilds:
        <guild_id>
            Games:
                <game_name>
    Modules:
        <module_id>

"""


class Context(Enum):
    GLOBAL = 0
    MODULES = 1
    USERS = 2
    GUILDS = 3
    GAMES = 4


class BotEngine(Engine):
    def __init__(self, bot):
        super().__init__(BotFileSystem(os.path.join(".", "bot_data")))
        self.bot = bot
        self.modules = dict()

    def add_module(self, module):
        self.bot.add_cog(module)
        self.modules[module.get_name()] = module


class DNDiscordCoreModule(Module):
    def __init__(self, parent):
        super().__init__("dndiscord_core", parent)
        self.engine = BotEngine(parent.get_bot())

        self.guild_data = dict()
        self.active_games = dict()

    def get_file_manager(self):
        return self.engine.get_file_manager()

    async def load_or_create_guild_data(self, ctx, guild_id):
        file_manager = self.get_file_manager()
        guild_data = await file_manager.load_file_from_context(Context.GUILDS, guild_id, "core_data.json")
        if guild_data is None:
            guild_data = GuildData(guild_id)

        return guild_data

    async def get_guild_data(self, ctx):
        guild_id = str(ctx.guild.id)
        if guild_id not in self.guild_data:
            guild_data = await self.load_or_create_guild_data(ctx, guild_id)
            self.guild_data[guild_id] = guild_data

        return self.guild_data[guild_id]

    async def get_active_games_for_user(self, ctx):
        guild_data = await self.get_guild_data(ctx)
        author = str(ctx.author.id)
        games = list()
        for game in guild_data.get_games():
            if author in game.get_adventurers():
                games.append(game.get_name())

        return games

    @commands.command(name="membership")
    async def _membership(self, ctx: commands.Context):
        """
        Informs a user of what games they are currently members of

        :param ctx:
        :return:
        """
        games = self.get_active_games_for_user(ctx)
        return await send_message(ctx, "You are currently active in the game: " + str(games))

    @commands.command(name="running")
    async def _running(self, ctx: commands.Context):
        """
        Informs a user of what games (that they are a member of) is currently running.
        :param ctx:
        :return:
        """

        active_games = list()
        for game in self.active_games:
            if game.is_adventurer(str(ctx.author.id)):
                active_games.append(game.get_name())

        return await send_message(ctx, "The following games that you are an adventurer in are currently running: " + str(active_games))

    @commands.command(name="join")
    async def _join(self, ctx: commands.Context, *, game_to_join: str):
        pass

    @commands.command(name="leave")
    async def _leave(self, ctx: commands.Context, *, game_to_leave: str):
        pass

    @commands.command(name="kick")
    async def _kick(self, ctx: commands.Context, *, user_to_kick: str):
        pass
