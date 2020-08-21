import os

from discord.ext import commands

from bot.core_module import DNDiscordCoreModule
from core import Engine
from data.file_system import BotFileSystem


class EditMessageReceiveBot(commands.Bot):
    def __init__(self, **options):
        super().__init__(**options)

    # Replay messages on edit
    async def on_message_edit(self, before, after):
        await self.on_message(after)


class DNDiscordBot:
    def __init__(self, token):
        super().__init__()
        self.bot = EditMessageReceiveBot(command_prefix="!", description="A discord bot that helps with D&D things.... and whatever else I can think of that would be useful.")
        self.token = token
        self.current_localization = "default"

        self.core = DNDiscordCoreModule(self)

    def run(self):
        self.bot.run(self.token)
