from discord.ext import commands

from module_properties import Module
from modules.game.game_state_listener import GameStateListener
from utils import constants
from utils.errors import CommandRunError
from utils.messages import LongMessage
from utils.strings import get_trailing_number


class Reminder:
    def __init__(self, item, reminder_day):
        self.item = item
        self.reminder_day = reminder_day


class ReminderManager(Module, GameStateListener):
    def __init__(self, engine):
        super().__init__("reminder_manager", engine)
        self.game_master = self.engine.get_module("game_master")
        self.reminders = dict()
        if self.game_master:
            self.game_master.register_game_state_listener(self)
        else:
            raise RuntimeError("Cannot use the reminder module without the Game Master module.")

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('`This command can\'t be used in DM channels.`')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    async def get_reminders_for_context(self, ctx):
        # Get the game
        game = self.game_master.get_active_game_for_context(ctx)
        if game is None:
            return None

        unique_id = str(ctx.guild.id) + game.get_name()
        if unique_id not in self.reminders:
            data = await self.game_master.load_game_data(ctx, "reminders", "reminders.json")

            if data is not None:
                self.reminders[unique_id] = data
                return data

            else:
                return None

        else:
            return self.reminders[unique_id]

    async def set_reminders_for_context(self, ctx, reminders):
        # Get our game
        game = self.game_master.get_active_game_for_context(ctx)
        if game is None:
            return

        unique_id = str(ctx.guild.id) + game.get_name()
        self.reminders[unique_id] = reminders
        await self.game_master.save_game_data(ctx, "reminders", "reminders.json", reminders)

    async def game_created(self, ctx, game):
        return

    async def game_started(self, ctx, game):
        # Get the game, which cannot be None at this point because of the above
        game = self.game_master.get_active_game_for_context(ctx)
        current_days = game.get_days_passed()

        # Obtain any existing
        reminders = await self.get_reminders_for_context(ctx)
        long_message = LongMessage()
        long_message.add("===================================")
        if reminders is None or len(reminders) == 0:
            long_message.add("You have nothing to do today! How nice :)")
        else:
            for reminder in reminders:
                if reminder.reminder_day == current_days:
                    long_message.add("[REMINDER]: You are supposed to do: " + reminder.item + " today.")
                elif reminder.reminder_day > current_days:
                    long_message.add("[REMINDER]: You are supposed to do: " + reminder.item + " in " + str(reminder.reminder_day - current_days) + " days.")
        long_message.add("===================================")

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.send(message)

    async def game_about_to_end(self, ctx, game):
        return

    async def game_deleting(self, ctx, game):
        return

    async def day_passed(self, ctx, game):
        game = self.game_master.get_active_game_for_context(ctx)
        current_day = game.get_days_passed()

        # Notify the channel of any reminders
        reminders = await self.get_reminders_for_context(ctx)
        to_remove = list()
        long_message = LongMessage()
        long_message.add("===================================")
        if reminders is None or len(reminders) == 0:
            long_message.add("You have nothing to do today! How nice :)")
        else:
            for reminder in reminders:
                if reminder.reminder_day == current_day:
                    long_message.add("[REMINDER]: You are supposed to do: " + reminder.item + " today.")
                elif reminder.reminder_day < current_day:
                    long_message.add("[REMINDER]: You are supposed to do: " + reminder.item + " in " + str(reminder.reminder_day - current_day) + " days.")
        long_message.add("===================================")

        # Remove the reminders we have already triggered
        for reminder in to_remove:
            reminders.remove(reminder)

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.send(message)

        # Save
        await self.set_reminders_for_context(ctx, reminders)

    @commands.command(name="reminder")
    async def _reminder(self, ctx: commands.Context, *, vars: str):
        # Validate that we have permissions to access this
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "reminders", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the game, which cannot be None at this point because of the above
        game = self.game_master.get_active_game_for_context(ctx)
        current_days = game.get_days_passed()

        # Obtain any existing
        reminders = await self.get_reminders_for_context(ctx)

        # Number of days to trigger the reminder
        days = int(get_trailing_number(vars))
        item = vars.replace(str(days), "").strip()

        # If reminders does not exist yet
        if reminders is None:
            reminders = list()

        # Add our new reminder
        reminders.append(Reminder(item, days + current_days))

        # Save our reminders
        await self.set_reminders_for_context(ctx, reminders)
        return await ctx.send("`Added reminder for: " + item + " in " + str(days) + " days.`")

    @commands.command(name="reminder:today")
    async def _todo_list(self, ctx: commands.Context):
        # Validate that we have permissions to access this
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "reminders:today", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the game, which cannot be None at this point because of the above
        game = self.game_master.get_active_game_for_context(ctx)
        current_days = game.get_days_passed()

        # Obtain any existing
        reminders = await self.get_reminders_for_context(ctx)
        long_message = LongMessage()
        long_message.add("===================================")
        if reminders is None or len(reminders) == 0:
            long_message.add("You have nothing to do today! How nice :)")
        else:
            for reminder in reminders:
                if reminder.reminder_day == current_days:
                    long_message.add("[REMINDER]: You are supposed to do: " + reminder.item + " today.")
        long_message.add("===================================")

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.send(message)

    @commands.command(name="reminders")
    async def _all_reminders(self, ctx: commands.Context):
        # Validate that we have permissions to access this
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "reminders:all", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the game, which cannot be None at this point because of the above
        game = self.game_master.get_active_game_for_context(ctx)
        current_days = game.get_days_passed()

        # Obtain any existing
        reminders = await self.get_reminders_for_context(ctx)
        reminders.sort(key=lambda x: x.reminder_day)
        long_message = LongMessage()
        long_message.add("===================================")
        if reminders is None or len(reminders) == 0:
            long_message.add("You have nothing to do today! How nice :)")
        else:
            for reminder in reminders:
                if reminder.reminder_day == current_days:
                    long_message.add("[REMINDER]: You are supposed to do: " + reminder.item + " today.")
                elif reminder.reminder_day > current_days:
                    long_message.add("[REMINDER]: You are supposed to do: " + reminder.item + " in " + str(reminder.reminder_day - current_days) + " days.")
        long_message.add("===================================")

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.send(message)
