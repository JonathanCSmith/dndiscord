import os
import shutil

from discord.ext import commands

from modules.inventory.inventory_module import InventoryManager
from modules.game.game_master import GameMaster
from modules.music.harpers_module import Harpers
from modules.tavern_simulator.tavern_module import TavernSimulator
from utils import dice, data

"""
Common func in DNDBot

TODO: Get Module -> Get Cog ? Any reason to duplicate this functionality?
"""


class DNDiscordDataStore:
    def __init__(self, guilds=None):
        if not guilds:
            guilds = dict()
        self.guilds = guilds

    def __set_guild_entry(self, guild_id, value):
        self.guilds[guild_id] = value

    def __get_guild_entry(self, guild_id):
        return self.guilds[guild_id]

    def set_module_entry(self, guild_id, module, value):
        if guild_id not in self.guilds:
            self.guilds[guild_id] = dict()

        self.guilds[guild_id][module] = value

    def get_module_entry(self, guild_id, module):
        if guild_id in self.guilds:
            return self.guilds[guild_id][module]

        return None


class DNDiscordBot:
    is_music_module_enabled = True
    is_inventory_module_enabled = True
    is_tavern_module_enabled = True
    is_party_management_enabled = True

    def __init__(self, token):
        self.token = token
        self.data_path = os.path.join(".", "bot_data")
        self.data_store = None
        self.modules = dict()
        self.description = '''dnd is AWESOME'''
        self.bot = commands.Bot(command_prefix='!', description=self.description)
        self.add_basic_commands(self.bot)

        # We should always enable our game manager as it manages permissions and data!
        game_module_new = GameMaster(self)
        self.add_module(game_module_new)

        # Check for our music bot modules
        if DNDiscordBot.is_music_module_enabled:
            music_module = Harpers(self)
            self.add_module(music_module)

        # Check for our inventory module
        if DNDiscordBot.is_inventory_module_enabled:
            inventory_module = InventoryManager(self)
            self.add_module(inventory_module)

        # Rest module

        # Handbook module

        # Campaign management

        # Check for our tavern module
        if DNDiscordBot.is_tavern_module_enabled:
            tavern_module = TavernSimulator(self)
            self.add_module(tavern_module)

    def add_module(self, module):
        self.bot.add_cog(module)
        self.modules[module.get_name()] = module

    def get_module(self, name):
        if name in self.modules:
            return self.modules[name]

        return None

    def get_bot(self):
        return self.bot

    async def get_guild_data_for_module_from_bot_data_store(self, ctx, module_name):
        if not self.data_store:
            self.data_store = await self._load_data_from_complete_folder_path(self.data_path, "dndiscord_data.json")

        if not self.data_store:
            self.data_store = DNDiscordDataStore()
            await self._save_data_in_complete_folder_path(self.data_path, "dndiscord_data.json", self.data_store)

        return self.data_store.get_module_entry(str(ctx.guild.id), module_name)

    async def set_guild_data_for_module_in_bot_data_store(self, ctx, module_name, value):
        await self.get_guild_data_for_module_from_bot_data_store(ctx, module_name)
        self.data_store.set_module_entry(str(ctx.guild.id), module_name, value)
        return await self._save_data_in_complete_folder_path(self.data_path, "dndiscord_data.json", self.data_store)

    def get_bot_member(self, ctx):
        return ctx.guild.get_member(ctx.bot.user.id)

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
        await self.delete(os.path.join(self._get_guild_folder_path(ctx), path_modifier))

    async def delete(self, path):
        path = os.path.join(self.data_path, path)
        if os.path.exists(path):
            shutil.rmtree(path)

    @DeprecationWarning
    async def save_data_for_user_in_context(self, ctx, data_name, data):
        path = "user_data" + os.path.sep + str(ctx.author.id)
        await self.save_data(path, data_name, data)

    async def save_data_at(self, file, item):
        path = os.path.join(self.data_path, file)
        dir = os.path.dirname(path)
        if not os.path.isdir(dir):
            os.makedirs(dir)

        data.save(item, path)

    @DeprecationWarning
    async def save_data(self, module_information, data_name, item_to_save):
        path = os.path.join(self.data_path, module_information)
        if not os.path.exists(path):
            os.makedirs(path)

        if not data_name.endswith(".json"):
            data_name = data_name + ".json"

        file_path = os.path.join(path, data_name)
        data.save(item_to_save, file_path)

    @DeprecationWarning
    async def load_data_for_user_in_context(self, ctx, data_name):
        path = "user_data" + os.path.sep + str(ctx.author.id)
        return await self.load_data(path, data_name)

    @DeprecationWarning
    async def load_data_at(self, file):
        file = os.path.join(self.data_path, file)
        if not os.path.isfile(file):
            return None

        return data.load(file)

    @DeprecationWarning
    async def load_data(self, module_information, data_name):
        path = os.path.join(self.data_path, module_information)
        if not os.path.exists(path):
            return None

        if not data_name.endswith(".json"):
            data_name = data_name + ".json"

        file_path = os.path.join(path, data_name)
        if not os.path.isfile(file_path):
            return None

        return data.load(file_path)

    async def create(self, path):
        path = os.path.join(self.data_path, path)
        os.makedirs(path)

    def run(self):
        self.bot.run(self.token)

    def add_basic_commands(self, bot):
        @bot.event
        async def on_ready():
            print('Logged in as')
            print(bot.user.name)
            print(bot.user.id)
            print('------')

        @bot.command()
        async def hello(ctx):
            """Says world"""
            await ctx.send("Hello intrepid adventurer!")

        @bot.command()
        async def roll(ctx, dice_type):
            """Rolls the dice"""
            try:
                dice_type = int(dice_type)
                await ctx.send(dice.roll(dice_type))

            except:
                if "d" in dice_type:
                    splitz = dice_type.split("d")
                elif "D" in dice_type:
                    splitz = dice_type.split("D")

                else:
                    await ctx.send("Fuck off with your: " + str(dice_type))
                    return

                if len(splitz) == 2:
                    try:
                        if splitz[0] == "":
                            count = 1
                        else:
                            count = int(splitz[0])

                        if count == 0 or count > 100:
                            await ctx.send("Fuck off with your " + str(count) + " dice.")
                            return

                        type = int(splitz[1])

                        outcomes = list()
                        for i in range(0, count):
                            outcomes.append(dice.roll(type))

                        await ctx.send("Results are: " + str(outcomes))

                    except:
                        await ctx.send("Fuck off with your: " + str(dice_type))


config_data = data.load("./config.json")
dnd_bot = DNDiscordBot(config_data["discord_token"])
dnd_bot.run()
