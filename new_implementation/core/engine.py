from discord.ext import commands
from discord.ext.commands import Bot, Cog


class CommandRunError(commands.CommandError):
    def __init__(self, detail, *args, **kwargs):
        self.detail = detail


class DnDiscordCog(Cog):
    def __init__(self, bot, engine):
        self.bot = bot
        self.engine = engine

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('`This command can\'t be used in DM channels.`')

        return True

    # async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
    #     if isinstance(error, CommandRunError):
    #         await ctx.send(error.detail)
    #         return
    #
    #     await ctx.send('`An error occurred: {}`'.format(str(error)))


class Engine:
    def __init__(self):
        pass


class EditMessageReceiveBot(Bot):
    def __init__(self, **options):
        super().__init__(**options)

    # Replay messages on edit
    async def on_message_edit(self, before, after):
        await self.on_message(after)
