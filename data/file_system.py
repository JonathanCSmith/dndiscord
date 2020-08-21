import os
import shutil

from core import FileSystem
from utils import data


class BotFileSystem(FileSystem):
    def __init__(self, path):
        super().__init__()
        self.data_path = path

    def _get_guild_folder_path(self, ctx):
        return os.path.join(self.data_path, "guilds", str(ctx.guild.id))

    def _get_user_folder_path(self, ctx):
        return os.path.join(self.data_path, "users", str(ctx.author.id))

    async def load_data_from_data_path_for_guild(self, ctx, path_modifier, file_name):
        folder_path = os.path.join(self._get_guild_folder_path(ctx), path_modifier)
        return await self._load_data_from_complete_folder_path(folder_path, file_name)

    async def load_data_from_data_path_for_user(self, ctx, path_modifier, file_name):
        folder_path = os.path.join(self._get_user_folder_path(ctx), path_modifier)
        return await self._load_data_from_complete_folder_path(folder_path, file_name)

    async def load_data_from_data_path(self, path_modifier, file_name):
        folder_path = os.path.join(self.data_path, path_modifier)
        return await self._load_data_from_complete_folder_path(folder_path, file_name)

    async def _load_data_from_complete_folder_path(self, folder_path, file_name):
        if not file_name.endswith(".json"):
            file_name += ".json"

        file = os.path.join(folder_path, file_name)
        if not os.path.isfile(file):
            return None
        else:
            return data.load(file)

    async def save_data_in_data_path_for_guild(self, ctx, path_modifier, file_name, item_to_save):
        folder_path = os.path.join(self._get_guild_folder_path(ctx), path_modifier)
        await self._save_data_in_complete_folder_path(folder_path, file_name, item_to_save)

    async def save_data_in_data_path_for_user(self, ctx, path_modifier, file_name, item_to_save):
        folder_path = os.path.join(self._get_user_folder_path(ctx), path_modifier)
        await self._save_data_in_complete_folder_path(folder_path, file_name, item_to_save)

    async def save_data_in_data_path(self, path_modifier, file_name, item_to_save):
        folder_path = os.path.join(self.data_path, path_modifier)
        await self._save_data_in_complete_folder_path(folder_path, file_name, item_to_save)

    async def _save_data_in_complete_folder_path(self, folder_path, file_name, item_to_save):
        if not file_name.endswith(".json"):
            file_name += ".json"

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file = os.path.join(folder_path, file_name)
        data.save(item_to_save, file)

    async def delete_in_data_path_for_guild(self, ctx, path_modifier):
        await self.__delete(os.path.join(self._get_guild_folder_path(ctx), path_modifier))

    async def __delete(self, path):
        path = os.path.join(self.data_path, path)
        if os.path.exists(path):
            shutil.rmtree(path)

    async def create(self, path):
        path = os.path.join(self.data_path, path)
        os.makedirs(path)
