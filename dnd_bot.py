import os
import shutil

from discord.ext import commands

from data.file_system import BotFileSystem
from modules.calendar.calendar_module import CalendarManager
from modules.inventory.inventory_module import InventoryManager
from modules.game.game_master import GameMaster
from modules.harpers.harpers_module import Harpers
from modules.reminder.reminder_module import ReminderManager
from modules.services.services_module import ServicesManager
from modules.business_simulator.business_module import BusinessSimulator
from utils import dice, data
from utils.translations import TranslationSource, TranslationManager

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


class EditMessageReceiveBot(commands.Bot):
    def __init__(self, **options):
        super().__init__(**options)

    # Replay messages on edit
    async def on_message_edit(self, before, after):
        await self.on_message(after)


class Engine:
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.translation_manager = TranslationManager()

    def get_file_manager(self):
        return self.file_manager

    def get_translation_manager(self):
        return self.translation_manager


class DNDiscordBot(Engine):
    is_music_module_enabled = True
    is_inventory_module_enabled = True
    is_business_module_enabled = True
    is_party_management_enabled = True
    is_services_module_enabled = True
    is_calendar_module_enabled = True
    is_reminder_module_enabled = True

    def __init__(self, token):
        super().__init__(BotFileSystem(os.path.join(".", "bot_data")))
        self.token = token
        self.modules = dict()
        self.translation_manager = TranslationManager()
        self.current_localization = "default"
        self.description = '''dnd is AWESOME'''
        self.bot = EditMessageReceiveBot(command_prefix='!', description=self.description)
        self.add_basic_commands(self.bot)

        # We should always enable our game manager as it manages permissions and data!
        game_module_new = GameMaster(self)
        self.add_module(game_module_new)

        # Check for our harpers bot modules
        if DNDiscordBot.is_music_module_enabled:
            music_module = Harpers(self)
            self.add_module(music_module)

        # Check for our inventory module
        if DNDiscordBot.is_inventory_module_enabled:
            inventory_module = InventoryManager(self)
            self.add_module(inventory_module)

        # Rest module
        if DNDiscordBot.is_services_module_enabled:
            inventory_module = ServicesManager(self)
            self.add_module(inventory_module)

        # Calendar module
        if DNDiscordBot.is_calendar_module_enabled:
            calendar_manager = CalendarManager(self)
            self.add_module(calendar_manager)

        # Reminder module
        if DNDiscordBot.is_reminder_module_enabled:
            reminder_manager = ReminderManager(self)
            self.add_module(reminder_manager)

        # Handbook module

        # Campaign management

        # Check for our business module
        if DNDiscordBot.is_business_module_enabled:
            business_module = BusinessSimulator(self)
            self.add_module(business_module)

    def add_module(self, module):
        self.bot.add_cog(module)
        self.modules[module.get_name()] = module

    def get_module(self, name):
        if name in self.modules:
            return self.modules[name]

        return None

    def get_bot(self):
        return self.bot

    def get_bot_member(self, ctx):
        return ctx.guild.get_member(ctx.bot.user.id)

    async def get_translation_for_current_localization(self, ctx, key):
        return await self.translation_manager.get_translation(self.current_localization, ctx, key)

    async def load_translations_package(self, ctx, translation_source: TranslationSource):
        return await self.translation_manager.load_translations(self, ctx, translation_source)

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
        async def reload_translations(ctx):
            if ctx.author.guild_permissions.administrator:
                await self.translation_manager.reload_translations(self, ctx)
                return await ctx.send("`Reloaded translation packs.`")
            return await ctx.send("`You are not administrator.`")

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
