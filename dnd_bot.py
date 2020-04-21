import os
import shutil

from discord.ext import commands

from modules.inventory.inventory_module import InventoryManager
from modules.music.music_module import MusicPlayer
from modules.game.game_module import GameMaster
from modules.tavern_simulator.tavern_module import TavernSimulator
from utils import dice, data

"""
Common func in DNDBot
"""


class DNDBot:
    is_music_module_enabled = True
    is_inventory_module_enabled = True
    is_tavern_module_enabled = True

    def __init__(self, token):
        self.token = token
        self.data_path = os.path.join(".", "bot_data")
        self.modules = dict()
        self.description = '''dnd is AWESOME'''
        self.bot = commands.Bot(command_prefix='!', description=self.description)
        self.add_basic_commands(self.bot)

        # We should always enable our game manager as it manages permissions and data!
        game_module = GameMaster(self)
        self.add_module(game_module)

        # Check for our music bot modules
        if DNDBot.is_music_module_enabled:
            music_module = MusicPlayer(self)
            self.add_module(music_module)

        # Check for our inventory module
        if DNDBot.is_inventory_module_enabled:
            inventory_module = InventoryManager(self)
            self.add_module(inventory_module)

        # Rest module

        # Handbook module

        # Campaign management

        # Check for our tavern module
        if DNDBot.is_tavern_module_enabled:
            tavern_module = TavernSimulator(self)
            self.add_module(tavern_module)

    def add_module(self, module):
        self.bot.add_cog(module)
        self.modules[module.get_name()] = module

    def get_module(self, name):
        return self.modules[name]

    def get_bot(self):
        return self.bot

    def get_bot_member(self, ctx):
        return ctx.guild.get_member(ctx.bot.user.id)

    async def save_data_for_user_in_context(self, ctx, data_name, data):
        path = "user_data" + os.path.sep + str(ctx.author.id)
        await self.save_data(path, data_name, data)

    async def load_data_for_user_in_context(self, ctx, data_name):
        path = "user_data" + os.path.sep + str(ctx.author.id)
        return await self.load_data(path, data_name)

    async def save_data_at(self, file, item):
        path = os.path.join(self.data_path, file)
        dir = os.path.dirname(path)
        if not os.path.isdir(dir):
            os.makedirs(dir)

        data.save(item, path)

    async def save_data(self, module_information, data_name, item_to_save):
        path = os.path.join(self.data_path, module_information)
        if not os.path.exists(path):
            os.makedirs(path)

        if not data_name.endswith(".json"):
            data_name = data_name + ".json"

        file_path = os.path.join(path, data_name)
        data.save(item_to_save, file_path)

    async def load_data_at(self, file):
        file = os.path.join(self.data_path, file)
        if not os.path.isfile(file):
            return None

        return data.load(file)

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

    async def delete(self, path):
        path = os.path.join(self.data_path, path)
        if os.path.exists(path):
            shutil.rmtree(path)

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
dnd_bot = DNDBot(config_data["discord_token"])
dnd_bot.run()
