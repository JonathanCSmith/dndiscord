import asyncio
import os
import argparse

from modules.business_simulator.data import business_data_pack
from modules.business_simulator.gui.business_simulator_gui import BusinessSimulatorGUI

# This is a small standalone executable that allows you to either generate a business data pack programmatically or through the GUI
from new_implementation.bots.ancillary_bots import SecondaryBot
from new_implementation.bots.game_cog import GameCog
from new_implementation.core.engine import Engine, EditMessageReceiveBot
from new_implementation.data import data
from new_implementation.data.data import DataAccessObject
from new_implementation.data.guild import GuildData
from new_implementation.data.user import UserData
from new_implementation.handlers.permissions_handler import PermissionsHandler
from new_implementation.handlers.resource_handler import ResourceHandler
from new_implementation.modules.music.music import MusicCog
from new_implementation.utils import utils


# This is our core application containing the bots
class DNDiscord(EditMessageReceiveBot, Engine):
    def __init__(self, config):
        super().__init__(command_prefix="!", description="Core DnDiscord Bot")

        # Basic props
        self.config = config
        self.purge_mutex = False
        self.music_module = False
        self.ambiance_module = False
        self.resource_handler = ResourceHandler(self)
        self.permissions_handler = PermissionsHandler(self)
        self.guild_cache = dict()
        self.user_cache = dict()
        self.active_sessions = dict()
        self.game_state_listeners = dict()

        # Parse the configs
        self.__parse_config()

        # Core commands
        self.add_cog(GameCog(self, self))

        # Ancillary bots if required
        self.ancillary_bot = SecondaryBot(self, command_prefix="!", description="Ancillary DnDiscord Bot")

        # Optional Cogs
        if self.music_module:
            self.add_cog(MusicCog(self, self))

    def run(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.start(self.config["discord_token"]))

        # Setup our ancillary bot
        if "ancillary_token" in self.config:
            loop.create_task(self.ancillary_bot.start(self.config["ancillary_token"]))
        else:
            self.ambiance_module = False

        loop.run_forever()

    def get_resource_handler(self):
        return self.resource_handler

    def get_permission_handler(self):
        return self.permissions_handler

    def get_game_state_listeners(self):
        return self.game_state_listeners

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


# Parse the runtime arguments
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--runtime", dest="runtime", help="The runtime type of dndiscord. Valid options are: bot, pack_dump, pack_editor", type=str, default="bot", choices=['bot', 'pack_dump', 'pack_editor'])
parser.add_argument("-c", "--config", dest="config", help="The location of the configuration file for the bot", type=str, default="./config.json")
parser.add_argument("-f", "--file", dest="file", help="The location of the python file to load when attempting to dump a programmatically created data pack", type=str)
args = parser.parse_args()

# Runtime as bot
if args.runtime == "bot":

    # Load the configuration file for the bot - this is required!
    if args.config and os.path.isfile(args.config):
        config_data = data.load(args.config)
        if "discord_token" not in config_data:
            print("Invalid configuration file provided.")
            exit(1)

        dnd_bot = DNDiscord(config_data)
        dnd_bot.run()

    else:
        print("Please supply a valid configuration file.")

# Dump the default Trollskull manor pack to file
elif args.runtime == "pack_dump":
    if args.file and os.path.isfile(args.file):
        business_data_pack.generate_data_pack_from_python(args.file)
    else:
        print("Please supply a valid python file.")

# Activate the pack editor so you can edit or create data packs
elif args.runtime == "pack_editor":
    business_gui = BusinessSimulatorGUI()
    business_gui.mainloop()
