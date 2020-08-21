import os
import shutil

from enum import Enum

#
# Use cases:
#     * List the available 'resources' across guild storage in given module.
#
#     *
#
#     *
#
#     *
#
#     *
#
#     *
#
#     *
#
#     *
#
#
from new_implementation.utils import utils


class ResourceLocation(Enum):
    APPLICATION = 0
    GUILD = 1
    USER = 2
    GAME = 3


class ResourceContext:
    pass


class ResourceHandler:
    def __init__(self, application):
        self.application = application
        self.application_context = os.path.join(os.getcwd(), "bot_data")  # get the current path

    def list_resources_in_locations(self, locations, invocation_context, search_context):
        resources = list()

        # Look in our default application context
        if ResourceLocation.APPLICATION in locations:
            search_path = os.path.join(self.application_context, search_context)
            results = os.listdir(search_path)
            for result in results:
                resources.append(result)

        # Look in the guild context
        if ResourceLocation.GUILD in locations:
            search_path = os.path.join(self.application_context, "guilds", utils.get_guild_id_from_context(invocation_context), search_context)
            results = os.listdir(search_path)
            for result in results:
                resources.append(result)

        # Look in the users context
        if ResourceLocation.USER in locations:
            search_path = os.path.join(self.application_context, "users", utils.get_user_id_from_context(invocation_context), search_context)
            results = os.listdir(search_path)
            for result in results:
                resources.append(result)

        # Look in the games context
        if ResourceLocation.GAME in locations:

            # Check if we are running a game
            game = self.application.get_game_for_context(invocation_context)
            if game is not None:
                search_path = os.path.join(self.application_context, "guilds", utils.get_guild_id_from_context(invocation_context), "games", self.application.get_game_for_context(invocation_context), search_context)
                results = os.listdir(search_path)
                for result in results:
                    resources.append(result)

        return resources

    async def load_resource_from_guild_resources(self, guild_id, file_name, dao):
        save_path = os.path.join(self.application_context, "guilds", guild_id, file_name)
        await dao.load(save_path)
        return dao

    async def save_resource_in_guild_resources(self, guild_id, file_name, dao):
        save_path = os.path.join(self.application_context, "guilds", guild_id, file_name)
        await dao.save(save_path)
        return dao

    async def load_resource_from_user_resources(self, user_id, file_name, dao):
        save_path = os.path.join(self.application_context, "users", user_id, file_name)
        await dao.load(save_path)
        return dao

    async def save_resource_in_user_resources(self, user_id, file_name, dao):
        save_path = os.path.join(self.application_context, "users", user_id, file_name)
        await dao.save(save_path)
        return dao

    async def load_resource_from_game_resources(self, guild_id, file_name, dao):
        save_path = os.path.join(self.application_context, "guilds", guild_id, "games", file_name)
        await dao.load(save_path)
        return dao

    async def save_resource_in_game_resources(self, guild_id, file_name, dao):
        save_path = os.path.join(self.application_context, "guilds", guild_id, "games", file_name)
        await dao.save(save_path)
        return dao

    async def delete_resource_from_game_resources(self, guild_id, file_name):
        path = os.path.join(self.application_context, "guilds", guild_id, "games", file_name)
        if os.path.exists(path):
            os.remove(path)
