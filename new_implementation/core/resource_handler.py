import os

from enum import Enum

from new_implementation.data.data import DataAccessObject, SerializationModifier
from new_implementation.utils import utils


class ResourceLocation(Enum):
    APPLICATION = 0
    GUILD = 1
    USER = 2
    GAME = 3


class ResourcePack(SerializationModifier):
    def __init__(self, files_to_load):
        super().__init__()
        self.datasets = dict()
        self.add_item_to_be_ignored("datasets")

        self.files_to_load = files_to_load

    def get_data_to_load(self):
        return self.files_to_load

    def get_dataset(self, key):
        if key in self.datasets:
            return self.datasets[key]
        return None

    def add_dataset(self, key, dataset):
        self.datasets[key] = dataset


class ResourceHandler:
    def __init__(self, engine):
        self.engine = engine
        self.engine_context = os.path.join(os.getcwd(), self.engine.get_engine_name() + "_data")  # get the current path

    async def list_resource_packs_in_locations(self, locations, invocation_context, search_context, type_parent):
        resources = list()
        guild_id = utils.get_guild_id_from_context(invocation_context)
        user_id = utils.get_user_id_from_context(invocation_context)

        # Look in our default application context
        if ResourceLocation.APPLICATION in locations:
            search_path = os.path.join(self.engine_context, search_context)
            results = os.listdir(search_path)
            for result in results:
                if await self.is_resource_pack(os.path.join(search_path, result)):
                    resources.append(search_context + ":" + result)

        # Look in the guild context
        if ResourceLocation.GUILD in locations:
            search_path = os.path.join(self.engine_context, "guilds", guild_id, search_context)
            results = os.listdir(search_path)
            for result in results:
                if await self.is_resource_pack(os.path.join(search_path, result)):
                    resources.append("guild:" + guild_id + ":" + search_context + ":" + result)

        # Look in the users context
        if ResourceLocation.USER in locations:
            search_path = os.path.join(self.engine_context, "users", user_id, search_context)
            results = os.listdir(search_path)
            for result in results:
                if await self.is_resource_pack(os.path.join(search_path, result)):
                    resources.append("user:" + user_id + ":" + search_context + ":" + result)

        # Look in the games context
        if ResourceLocation.GAME in locations:

            # Check if we are running a game
            game = self.engine.get_game_for_context(invocation_context)
            if game is not None:
                game_id = game.get_name()
                search_path = os.path.join(self.engine_context, "guilds", guild_id, "games", game_id, search_context)
                results = os.listdir(search_path)
                for result in results:
                    if await self.is_resource_pack(os.path.join(search_path, result)):
                        resources.append("guild:" + guild_id + ":game:" + game_id + ":" + search_context + ":" + result)

        return resources

    async def is_resource_pack(self, path):
        if not os.path.isdir(path):
            return False

        if os.path.isfile(os.path.join(path, "resource_pack.json")):
            return True

    async def load_resource_pack(self, resource_pack_identifier):
        path = self.convert_id_to_path(resource_pack_identifier)

        # Resource pack descriptor
        generic_dao = DataAccessObject()
        await generic_dao.load(os.path.join(path, "resource_pack.json"))

        # Validate in a totally non-pythonic manner that it is what we expect
        resource_pack = generic_dao.get_payload()
        if not isinstance(resource_pack, ResourcePack):
            return None

        # We now want to chain load any dependencies
        data_to_load = resource_pack.get_data_to_load()
        for data in data_to_load:
            generic_dao = DataAccessObject()
            await generic_dao.load(os.path.join(path, data))
            resource_pack.add_dataset(data, generic_dao.get_payload())

        return resource_pack

    def convert_id_to_path(self, path):
        parts = path.split(":")
        pack_name = parts[-1]
        search_context = parts[-2]

        # The resource pack is within guild data
        if parts[0] == "guild":
            guild_id = parts[1]

            # The resource pack is within game data
            if parts[2] == "game":
                game_id = parts[3]
                return os.path.join(self.engine_context, "guilds", guild_id, "games", game_id, search_context, pack_name)
            else:
                return os.path.join(self.engine_context, "guilds", guild_id, search_context, pack_name)

        # The resource pack is within user data
        elif parts[0] == "user":
            return os.path.join(self.engine_context, "users", parts[1], search_context, pack_name)

        # The resource pack is within the root engine data
        else:
            return os.path.join(self.engine_context, search_context, pack_name)

    async def load_resource_from_guild_resources(self, guild_id, file_name, dao):
        load_path = os.path.join(self.engine_context, "guilds", guild_id, file_name)
        await dao.load(load_path)
        return dao

    async def save_resource_in_guild_resources(self, guild_id, file_name, dao):
        save_path = os.path.join(self.engine_context, "guilds", guild_id, file_name)
        await dao.save(save_path)
        return dao

    async def load_resource_from_user_resources(self, user_id, file_name, dao):
        save_path = os.path.join(self.engine_context, "users", user_id, file_name)
        await dao.load(save_path)
        return dao

    async def save_resource_in_user_resources(self, user_id, file_name, dao):
        save_path = os.path.join(self.engine_context, "users", user_id, file_name)
        await dao.save(save_path)
        return dao

    async def load_resource_from_game_resources(self, guild_id, file_name, dao):
        save_path = os.path.join(self.engine_context, "guilds", guild_id, "games", file_name)
        await dao.load(save_path)
        return dao

    async def save_resource_in_game_resources(self, guild_id, file_name, dao):
        save_path = os.path.join(self.engine_context, "guilds", guild_id, "games", file_name)
        await dao.save(save_path)
        return dao

    async def delete_resource_from_game_resources(self, guild_id, file_name):
        path = os.path.join(self.engine_context, "guilds", guild_id, "games", file_name)
        if os.path.exists(path):
            os.remove(path)
