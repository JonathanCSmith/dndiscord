from discord.ext import commands


class CommandRunError(commands.CommandError):
    def __init__(self, detail, *args, **kwargs):
        self.detail = detail
