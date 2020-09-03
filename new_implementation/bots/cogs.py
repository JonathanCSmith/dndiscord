import sys
import traceback

from discord.ext import commands
from discord.ext.commands import Cog

from new_implementation.utils.message import log, send_message


class CommandRunError(commands.CommandError):
    def __init__(self, detail, *args, **kwargs):
        self.detail = detail


class DnDiscordCog(Cog):
    def __init__(self, engine):
        self.engine = engine

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('`This command can\'t be used in DM channels.`')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # Ensure our console gets all the info
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

        # TODO: log to file

        # TODO: Conditional filtering to the logs

        # Log to discord
        if isinstance(error, CommandRunError):
            await send_message(ctx, error.detail)
            return await log(self.engine, ctx, '`An error occurred: {}`'.format(error.detail))

        await send_message(ctx, str(error))
        return await log(self.engine, ctx, '`An error occurred: {}`'.format(str(error)))
