from discord.ext import commands

from utils.translations import TranslationManager


class CommandRunError(commands.CommandError):
    def __init__(self, detail, *args, **kwargs):
        self.detail = detail


class Module(commands.Cog):
    def __init__(self, name, engine):
        self.name = name
        self.engine = engine

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    def get_name(self):
        return self.name


class FileSystem:
    def load_data_pack_by_path(self):
        pass


class Engine:
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.translation_manager = TranslationManager()

    def get_file_manager(self):
        return self.file_manager

    def get_translation_manager(self):
        return self.translation_manager
