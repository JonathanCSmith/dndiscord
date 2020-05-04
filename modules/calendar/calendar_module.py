from discord.ext import commands

from module_properties import Module
from modules.calendar import calendar
from modules.calendar.calendar import Calendar
from modules.game.game_state_listener import GameStateListener
from utils import constants
from utils.errors import CommandRunError


class CalendarManager(Module):
    def __init__(self, manager):
        super().__init__("calendar_manager", manager)
        self.game_master = self.manager.get_module("game_master")
        self.start_dates = dict()
        if not self.game_master:
            raise RuntimeError("Cannot use the calendar manager without the Game Master module.")

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('`This command can\'t be used in DM channels.`')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    async def get_calendar_for_context(self, ctx):
        # Get our game
        game = self.game_master.get_active_game_for_context(ctx)
        if game is None:
            return None

        unique_id = str(ctx.guild.id) + game.get_name()

        if unique_id not in self.start_dates:
            data = await self.game_master.load_game_data(ctx, "calendar", "calendar.json")

            if data is not None:
                self.start_dates[unique_id] = data
                return data
            else:
                return None

        else:
            return self.start_dates[unique_id]

    async def set_calendar_for_context(self, ctx, calendar):
        # Get our game
        game = self.game_master.get_active_game_for_context(ctx)
        if game is None:
            return

        unique_id = str(ctx.guild.id) + game.get_name()
        self.start_dates[unique_id] = calendar
        await self.game_master.save_game_data(ctx, "calendar", "calendar.json", calendar)


    @commands.command(name="calendar:initialize")
    async def _calendar_initialize(self, ctx: commands.Context, *, vars: str):
        # Validate that we have permissions to access this
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "calendar", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get any existing
        calendar_start_days = await self.get_calendar_for_context(ctx)
        if calendar_start_days is not None:
            return await ctx.send("`A calendar is already initialized for this game`")

        # Args
        nums = vars.split()
        if len(nums) != 3:
            return await ctx.send("`A calendar must be initialized with the following property <year> <month> <day>")

        try:
            year = int(nums[0])
            month = int(nums[1])
            day = int(nums[2])
        except:
            return await ctx.send("`The provided numbers must be convertable to ints.`")

        if year < 0 or month < 1 or month > 12 or day < 1 or day > 32:
            return await ctx.send("Years must be non negative, months must be between 1 and 12 and days between 1 and 32")

        # Create and save
        calendar_start_days = Calendar(year, month, day)
        days_passed = self.game_master.get_active_game_for_context(ctx).get_days_passed()
        day = calendar.convert(calendar_start_days, days_passed)
        await self.set_calendar_for_context(ctx, calendar_start_days)
        return await ctx.send("`Calendar initialized, the current day is: " + day + "`")

    @commands.command(name="calendar")
    async def _calendar(self, ctx: commands.Context):
        # Validate that we have permissions to access this
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "calendar", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get our start date
        calendar_start_days = await self.get_calendar_for_context(ctx)
        if calendar_start_days is None:
            return await ctx.send("`A calendar is not initialized for this game yet`")

        days_passed = self.game_master.get_active_game_for_context(ctx).get_days_passed()
        return await ctx.send("`Today is: " + calendar.convert(calendar_start_days, days_passed) + "`")

