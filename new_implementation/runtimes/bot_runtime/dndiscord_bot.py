import asyncio

from new_implementation.bots.bots import EditMessageReceiveBot, SecondaryBot
from new_implementation.runtimes.bot_runtime.core_cog import CoreCog
from new_implementation.core.engine import Engine
from new_implementation.data.data import DataAccessObject
from new_implementation.data.guild import GuildData
from new_implementation.data.user import UserData
from new_implementation.modules.music.music import MusicCog
from new_implementation.utils import utils


class DNDiscordBot(EditMessageReceiveBot, Engine):
    def __init__(self, config):
        EditMessageReceiveBot.__init__(self, command_prefix="!", description="Core DnDiscord Bot")
        Engine.__init__(self, "bot")

        # Basic props
        self.config = config
        self.purge_mutex = False
        self.music_module = False
        self.ambiance_module = False
        self.guild_cache = dict()
        self.user_cache = dict()
        self.active_sessions = dict()

        # Parse the configs
        self.__parse_config()

        # Core commands
        self.add_cog(CoreCog(self))

        # Ancillary bots if required
        self.ancillary_bot = SecondaryBot(self, command_prefix="!", description="Ancillary DnDiscord Bot")

        # Optional Cogs
        if self.music_module:
            self.add_cog(MusicCog(self))

    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.start(self.config["discord_token"]))

        # Setup our ancillary bot
        if "ancillary_token" in self.config:
            loop.create_task(self.ancillary_bot.start(self.config["ancillary_token"]))
        else:
            self.ambiance_module = False

        loop.run_forever()

    def is_ambiance_enabled(self):
        return self.ambiance_module

    async def get_guild_data_for_context(self, invocation_context):
        guild_id = utils.get_guild_id_from_context(invocation_context)
        if guild_id in self.guild_cache:
            guild_data = self.guild_cache[guild_id]
            return guild_data

        else:
            dao = DataAccessObject()
            dao = await self.resource_handler.load_resource_from_guild_resources(guild_id, "guild_data.json", dao)
            guild_data = dao.get_payload()
            if guild_data is None:
                guild_data = GuildData(guild_id)
                dao.set_payload(guild_data)
                await self.resource_handler.save_resource_in_guild_resources(guild_id, "guild_data.json", dao)

            self.guild_cache[guild_id] = guild_data
            return guild_data

    async def save_guild_data_for_context(self, invocation_context):
        guild_id = utils.get_guild_id_from_context(invocation_context)
        guild_data = self.guild_cache[guild_id]
        dao = DataAccessObject()
        if guild_data is not None:
            dao.set_payload(guild_data)
        else:
            dao.set_payload(GuildData(guild_id))

        await self.resource_handler.save_resource_in_guild_resources(guild_id, "guild_data.json", dao)

    async def get_user_data_for_context(self, invocation_context):
        user_id = utils.get_user_id_from_context(invocation_context)
        return await self.get_user_data(invocation_context, user_id)

    async def get_user_data(self, invocation_context, user_id: str):
        if user_id in self.user_cache:
            user_data = self.user_cache[user_id]
            return user_data

        else:
            dao = DataAccessObject()
            dao = await self.resource_handler.load_resource_from_user_resources(user_id, "user_data.json", dao)
            user_data = dao.get_payload()
            if user_data is None:
                user_data = UserData(user_id)
                dao.set_payload(user_data)
                await self.resource_handler.save_resource_in_user_resources(user_id, "user_data.json", dao)

            self.user_cache[user_id] = user_data
            return user_data

    async def save_user_data_for_context(self, invocation_context):
        user_id = utils.get_user_id_from_context(invocation_context)
        user_data = self.user_cache[user_id]
        dao = DataAccessObject()
        if user_data is not None:
            dao.set_payload(user_data)
        else:
            dao.set_payload(UserData(user_id))

        await self.resource_handler.save_resource_in_user_resources(user_id, "user_data.json", dao)

    async def save_user_data(self, invocation_context, user):
        dao = DataAccessObject()
        dao.set_payload(user)
        await self.resource_handler.save_resource_in_user_resources(user.get_user_id(), "user_data.json", dao)

    def get_active_game_for_context(self, invocation_context):
        guild_id = utils.get_guild_id_from_context(invocation_context)
        return self.active_sessions[guild_id] if guild_id in self.active_sessions else None

    def set_active_game_for_context(self, invocation_context, game):
        self.active_sessions[utils.get_guild_id_from_context(invocation_context)] = game

    async def end_active_game_for_context(self, ctx):
        game = self.active_sessions[utils.get_guild_id_from_context(ctx)]
        await self.save_game(ctx, game)
        del self.active_sessions[utils.get_guild_id_from_context(ctx)]

    async def get_game(self, invocation_context, game_name):
        guild_id = utils.get_guild_id_from_context(invocation_context)
        dao = DataAccessObject()
        dao = await self.resource_handler.load_resource_from_game_resources(guild_id, game_name + ".json", dao)
        return dao.get_payload()

    async def save_game(self, invocation_context, game):
        guild_id = utils.get_guild_id_from_context(invocation_context)
        dao = DataAccessObject()
        dao.set_payload(game)
        await self.resource_handler.save_resource_in_game_resources(guild_id, game.get_name() + ".json", dao)

    async def delete_game(self, invocation_context, game):
        guild_id = utils.get_guild_id_from_context(invocation_context)
        await self.resource_handler.delete_resource_from_game_resources(guild_id, game.get_name() + ".json")

    def __parse_config(self):
        self.music_module = bool(self.config["music_player"]) if "music_player" in self.config else False
        self.ambiance_module = bool(self.config["ambiance_player"]) if "ambiance_player" in self.config else False