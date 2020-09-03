from discord.ext import commands

from new_implementation.runtimes.bot_runtime.game_state_listener import GameStateListener
from new_implementation.bots.cogs import DnDiscordCog
from new_implementation.core.permissions_handler import PermissionLevel
from new_implementation.core.resource_handler import ResourceLocation
from new_implementation.modules.calendar.calendar_data import CalendarHolderData, CalendarData, CalendarResourcePack
from new_implementation.modules.calendar.calendar_state_listener import CalendarStateListener
from new_implementation.utils import strings, utils
from new_implementation.utils.message import send_message, LongMessage


class CalendarCog(DnDiscordCog, GameStateListener):
    module_data_key = "calendar_module_data"

    def __init__(self, engine):
        super().__init__(engine)

        self.calendar_resource_pack_cache = dict()
        self.engine.register_event_class(CalendarStateListener)
        self.engine.register_event_class_listener(GameStateListener, self)

    async def game_created(self, ctx, game):
        game.set_module_data(CalendarCog.module_data_key, CalendarHolderData())
        self.engine.save_game(game)

    async def game_started(self, ctx, game):
        calendar_holder = game.get_module_data(CalendarCog.module_data_key)

        # If we are just initializing the calendar then we don't need to do anything specific
        if calendar_holder is None:
            calendar_holder = CalendarHolderData()
            game.set_module_data(CalendarCog.module_data_key, calendar_holder)
            self.engine.save_game(ctx, game)
            return

        # Get associated calendars and display reminders
        else:
            await self.__today(ctx, reminder_type="private")
            await self.__today(ctx, reminder_type="party")
            await self.__today(ctx, reminder_type="GM")

    async def game_about_to_end(self, ctx, game):
        return

    async def game_deleting(self, ctx, game):
        return

    async def get_game_and_calendar_data(self, ctx):
        game = self.engine.get_active_game_for_context(ctx)
        if game is None:
            return None

        # We are going to an extra check for the calendar data here and add it just in case it does not exist
        calendar_holder = game.get_module_data(CalendarCog.module_data_key)
        if calendar_holder is None:
            calendar_holder = CalendarHolderData()
            game.set_module_data(CalendarCog.module_data_key, calendar_holder)
            self.engine.save_game(ctx, game)

        return game, calendar_holder

    async def load_resource_pack_for_calendar(self, ctx, resource_pack_key):
        if resource_pack_key not in self.calendar_resource_pack_cache:
            resource_pack = await self.engine.get_resource_handler().load_resource_pack(ctx, resource_pack_key)
            if resource_pack is None:
                return "The resource pack was not found."

            calendar_pack_data = resource_pack.get_dataset("calendar_format.json")
            if not isinstance(calendar_pack_data, CalendarResourcePack):
                return "The resource pack provided does not implement the correct parent class"

            # Cache the calendar and let the user know it was added to our game
            self.calendar_resource_pack_cache[resource_pack_key] = calendar_pack_data

        else:
            return self.calendar_resource_pack_cache[resource_pack_key]

    @commands.command(name="calendar:list_available")
    async def list_available_command(self, ctx: commands.Context):
        """
        Return a list of available calendars within the invocation context

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:list_available", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Identify all available resource packs
        possible_resource_packs = await self.engine.get_resource_handler().list_resource_packs_in_locations([ResourceLocation.GAME, ResourceLocation.GUILD, ResourceLocation.APPLICATION, ResourceLocation.USER], ctx, CalendarCog.module_key, CalendarData)
        long_message = LongMessage()
        long_message.add("The following calendars are available for your game:")
        long_message.add("")
        for possible_resource_pack in possible_resource_packs:
            long_message.add(possible_resource_pack)
        return await send_message(ctx, long_message)

    @commands.command(name="calendar:list_current")
    async def list_current_command(self, ctx: commands.Context):
        """
        Return a list of calendars currently associated with the invocation context

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:list_current", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # List all calendars
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendars = calendar_holder.get_calendars()
        long_message = LongMessage()
        long_message.add("The following calendars are running in the game: " + game.get_name())
        long_message.add("")
        for nickname, calendar in calendars.items():
            calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, calendar.get_archetype_id())
            if isinstance(calendar_resource_pack, str):
                long_message.add("Could not load resource pack for: " + nickname + " the reason being: " + calendar_resource_pack)

            else:
                calendar_handler = calendar_resource_pack.get_handler()
                long_message.add("Calendar: " + nickname + " with archetype: " + calendar.get_archetype_id() + ". Self described as: " + calendar_handler.get_description())
        return await send_message(ctx, long_message)

    @commands.command(name="calendar:initialize")
    async def initialize_command(self, ctx: commands.Context, *, keys: str):
        """
        This function is responsible for initializing a calendar within the context of a game

        :param ctx: the context of the command invocation
        :param keys: a complex string array containing the id of the resource pack as provided by the calendar:list command and the nickname that the you wish to associate with the calenedar
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:initialize", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Split on space, should be two args
        results = keys.split(" ")
        if len(results) != 2:
            return await send_message(ctx, "We require the id of the calendar and the nickname for the calendar as a space separated argument for this command to work.")
        resource_pack_key = results[0]
        nickname = results[1]

        # Check the resource pack exists
        calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, resource_pack_key)
        if isinstance(calendar_resource_pack, str):
            return await send_message(ctx, calendar_resource_pack)
        calendar_handler = calendar_resource_pack.get_handler()

        # Allow custom overrides
        calendar = calendar_handler.get_custom_calendar_data(resource_pack_key)
        if calendar is None or not isinstance(calendar, CalendarData):
            return await send_message(ctx, "The custom CalendarData implementation in the selected resource pack is not valid.")

        # Add calendar data with the information for this calendar
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar_holder.add_calendar(nickname, calendar)

        # Save the data
        self.engine.save_game(ctx, game)
        return await send_message(ctx, "Added a calendar called: " + nickname + " with archetype id: " + resource_pack_key + ". Self described as: " + calendar_handler.get_description())

    @commands.command(name="calendar:date_format")
    async def date_format_command(self, ctx: commands.Context, *, nickname: str):
        """
        Return the date format for accepted dates for the given calendar nickname

        :param nickname: The nickname tied to the calendar you wish to query

        :return: A string representation of the date format for the selected calendar
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:date_format:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        # Get the calendar holder for this game
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "There is no calendar with that nickname associated with this game")

        # Load the resource pack
        calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, calendar)
        if isinstance(calendar_resource_pack, str):
            return await send_message(ctx, calendar_resource_pack)

        # Query the calendar handler for details on the date format
        return await send_message(ctx, "The date format for calendar: " + nickname + " is: " + calendar_resource_pack.get_holder().get_expected_date_format())

    @commands.command(name="calendar:elapsed")
    async def elapsed_command(self, ctx: commands.Context, *, nickname: str):
        """
        Returns the number of ticks passed in this game. Calendars are responsible for contextualizing ticks.

        :param nickname: The nickname of the calendar to query

        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:elapsed:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        # Get the calendar holder for this game
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "There is no calendar with that nickname associated with this game")

        # Load the resource pack
        calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, calendar)
        if isinstance(calendar_resource_pack, str):
            return await send_message(ctx, calendar_resource_pack)

        # Query the calendar for its current tick state and use translations to derive the returned text
        return await send_message(ctx, calendar_resource_pack.get_holder().generate_elapsed_ticks_text(calendar))

    @commands.command(name="calendar:current")
    async def current_command(self, ctx: commands.Context, *, nickname: str):
        """
        Returns the current ticks in the context of all of the available characters.

        :param ctx: The invocation context of this command
        :param nickname: The nickname of the calendar to query
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:current:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        # Get the calendar holder for this game
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "There is no calendar with that nickname associated with this game.")

        # Load the resource pack
        calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, calendar)
        if isinstance(calendar_resource_pack, str):
            return await send_message(ctx, calendar_resource_pack)

        # Query the calendar for the current tick state and translate it to the current date in the context of the calendar
        ticks = calendar.get_ticks_passed()
        return await send_message(ctx, calendar_resource_pack.get_holder().generate_current_time(ticks))

    @commands.command(name="calendar:increment")
    async def tick_command(self, ctx: commands.Context, *, nickname: str):
        """
        Passes a tick in game. The meaning of this varies according to the calendar. It could imply a day or a year etc.
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:increment:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Get the calendar holder for this game
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "There is no calendar with that nickname associated with this game.")

        # Load the resource pack
        calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, calendar)
        if isinstance(calendar_resource_pack, str):
            return await send_message(ctx, calendar_resource_pack)
        calendar_handler = calendar_resource_pack.get_handler()

        # Increment
        calendar_handler.increment_ticks(calendar)
        await send_message(ctx, calendar_handler.generate_current_time(calendar))

        # Inform tick listeners
        for listener in self.engine.get_event_class_listeners(CalendarStateListener):
            await listener.tick_occured(ctx, game, nickname)

        # Display any reminders for today
        await self.__today(ctx, nickname=nickname, reminder_type="private")
        await self.__today(ctx, nickname=nickname, reminder_type="party")
        await self.__today(ctx, nickname=nickname, reminder_type="GM")

        # If any reminders are repeats and were due today we should re-add them!
        for reminder in calendar.get_reminders():
            if reminder.get_absolute_tick_date() == calendar.get_ticks_passed() and reminder.get_recurring() != 0:
                calendar.add_reminder(reminder.get_author_id(), reminder.get_reminder_type(), calendar.get_ticks_passed() + reminder.get_recurring(), reminder.get_description(), reminder.get_recurring())

        # Save the game
        return await self.engine.save_game(ctx, game)

    @commands.command(name="calendar:add_party_reminder_in")
    async def add_reminder_in_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur in a specified number of calendar ticks to a specified calendar for the party. Where calendar ticks can mean days, hours etc depending on the calendar.

        Takes the form !calendar:add_reminder_in <info>

        :param info:    Three arguments consisting of <calendar nickname> <reminder description> <number of calendar ticks to pass before reminder is due>.
                        <calendar nickname> and <number of calendar ticks to pass before reminder is due> are assumed to be single words with no spaces.
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_in:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        return self.__add_reminder_in(ctx, game, calendar, info=info, reminder_type="party")

    @commands.command(name="calendar:add_recurring_party_reminder_in")
    async def add_recurring_reminder_in_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur in a specified number of calendar ticks to a specified calendar for the party. Where calendar ticks can mean days, hours etc depending on the calendar.

        Takes the form !calendar:add_reminder_in <info>

        :param info:    Four arguments consisting of <calendar nickname> <reminder description> <number of calendar ticks to pass before reminder is due> <ticks until recurrence>.
                        <calendar nickname> and <number of calendar ticks to pass before reminder is due> are assumed to be single words with no spaces.
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_in:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        # Ascertain recurrence
        recurrence = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(recurrence), "", 1).strip()

        return self.__add_reminder_in(ctx, game, calendar, info=info, reminder_type="party", recurring=recurrence)

    @commands.command(name="calendar:add_private_reminder_in")
    async def add_private_reminder_in_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur in a specified number of calendar ticks to a specified calendar for the caller only. Where calendar ticks can mean days, hours etc depending on the calendar.

        Takes the form !calendar:add_reminder_in <info>

        :param info:    Three arguments consisting of <calendar nickname> <reminder description> <number of calendar ticks to pass before reminder is due>.
                        <calendar nickname> and <number of calendar ticks to pass before reminder is due> are assumed to be single words with no spaces.
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_in:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        return self.__add_reminder_in(ctx, game, calendar, info=info, reminder_type="private")

    @commands.command(name="calendar:add_recurring_private_reminder_in")
    async def add_recurring_private_reminder_in_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur in a specified number of calendar ticks to a specified calendar for the caller only. Where calendar ticks can mean days, hours etc depending on the calendar.

        Takes the form !calendar:add_reminder_in <info>

        :param info:    Four arguments consisting of <calendar nickname> <reminder description> <number of calendar ticks to pass before reminder is due> <ticks until recurrence>.
                        <calendar nickname> and <number of calendar ticks to pass before reminder is due> are assumed to be single words with no spaces.
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_in:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        # Ascertain recurrence
        recurrence = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(recurrence), "", 1).strip()

        return self.__add_reminder_in(ctx, game, calendar, info=info, reminder_type="private", recurring=recurrence)

    @commands.command(name="calendar:add_gm_reminder_in")
    async def add_gm_reminder_in(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur in a specified number of calendar ticks to a specified calendar for the GM. Where calendar ticks can mean days, hours etc depending on the calendar.

        Takes the form !calendar:add_reminder_in <info>

        :param info:    Three arguments consisting of <calendar nickname> <reminder description> <number of calendar ticks to pass before reminder is due>.
                        <calendar nickname> and <number of calendar ticks to pass before reminder is due> are assumed to be single words with no spaces.
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_gm_reminder_in:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        return self.__add_reminder_in(ctx, game, calendar, info=info, reminder_type="GM")

    @commands.command(name="calendar:add_recurring_gm_reminder_in")
    async def add_recurring_gm_reminder_in(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur in a specified number of calendar ticks to a specified calendar for the GM. Where calendar ticks can mean days, hours etc depending on the calendar.

        Takes the form !calendar:add_reminder_in <info>

        :param info:    Four arguments consisting of <calendar nickname> <reminder description> <number of calendar ticks to pass before reminder is due> <ticks until recurrence>.
                        <calendar nickname> and <number of calendar ticks to pass before reminder is due> are assumed to be single words with no spaces.
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_gm_reminder_in:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Ascertain recurrence
        recurrence = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(recurrence), "", 1).strip()

        return self.__add_reminder_in(ctx, game, calendar, info=info, reminder_type="GM", recurring=recurrence)

    async def __add_reminder_in(self, ctx: commands.Context, game, calendar, info: str, reminder_type: str, recurring=0):
        # Ascertain the remaining information
        try:
            ticks = int(strings.get_trailing_number(info))
            info = strings.replace_count_reverse(info, str(ticks), "", 1).strip()
        except ValueError:
            return await send_message(ctx, "The final part of your arguments to this function should be a round number representing the number of calendar ticks to elapse before the reminder is triggered.")

        # Get the resource pack for translations of the reminder
        calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, calendar)
        if isinstance(calendar_resource_pack, str):
            return await send_message(ctx, calendar_resource_pack)
        calendar_handler = calendar_resource_pack.get_handler()

        # Create and append a reminder
        author_id = utils.get_user_id_from_context(ctx)
        reminder = calendar.add_reminder(ticks, info, author_id, reminder_type, recurring)
        await self.engine.save_game(ctx, game)
        return await send_message(ctx, "Added reminder: " + calendar_handler.translate_reminder(reminder, calendar))

    @commands.command(name="calendar:add_party_reminder_on")
    async def add_party_reminder_on_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur on a specified date in a specified calendar for the party.

        Takes the form !calendar:add_reminder_on <info>

        :param info:    Three arguments consisting of <calendar nickname> <reminder description> <date in acceptable format to calendar>.
                        <calendar nickname> is assumed to be single word
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_on:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        return await self.__add_reminder_on(ctx, game, calendar, info=info, reminder_type="party")

    @commands.command(name="calendar:add_recurring_party_reminder_on")
    async def add_recurring_party_reminder_on_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur on a specified date in a specified calendar for the party.

        Takes the form !calendar:add_reminder_on <info>

        :param info:    Three arguments consisting of <calendar nickname> <reminder description> <date in acceptable format to calendar>.
                        <calendar nickname> is assumed to be single word
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_on:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        # Ascertain recurrence
        recurrence = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(recurrence), "", 1).strip()

        return await self.__add_reminder_on(ctx, game, calendar, info=info, reminder_type="party", recurring=recurrence)

    @commands.command(name="calendar:add_private_reminder_on")
    async def add_private_reminder_on_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur on a specified date in a specified calendar for the caller.

        Takes the form !calendar:add_reminder_on <info>

        :param info:    Four arguments consisting of <calendar nickname> <reminder description> <date in acceptable format to calendar> <ticks until recurrence>.
                        <calendar nickname> is assumed to be single word
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_on:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        return await self.__add_reminder_on(ctx, game, calendar, info=info, reminder_type="private")

    @commands.command(name="calendar:add_recurring_private_reminder_on")
    async def add_recurring_private_reminder_on_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur on a specified date in a specified calendar for the caller.

        Takes the form !calendar:add_reminder_on <info>

        :param info:    Four arguments consisting of <calendar nickname> <reminder description> <date in acceptable format to calendar> <ticks until recurrence>.
                        <calendar nickname> is assumed to be single word
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_reminder_on:" + nickname, permissions_level=PermissionLevel.PARTY)
        if not permission:
            return await send_message(ctx, reason)

        # Ascertain recurrence
        recurrence = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(recurrence), "", 1).strip()

        return await self.__add_reminder_on(ctx, game, calendar, info=info, reminder_type="private", recurring=recurrence)

    @commands.command(name="calendar:add_gm_reminder_on")
    async def add_gm_reminder_on_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur on a specified date in a specified calendar for the GM.

        Takes the form !calendar:add_reminder_on <info>

        :param info:    Three arguments consisting of <calendar nickname> <reminder description> <date in acceptable format to calendar>.
                        <calendar nickname> is assumed to be single word
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_gm_reminder_on:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        return await self.__add_reminder_on(ctx, game, calendar, info=info, reminder_type="GM")

    @commands.command(name="calendar:add_recurring_gm_reminder_on")
    async def add_recurring_gm_reminder_on_command(self, ctx: commands.Context, *, info: str):
        """
        A command to add a reminder to occur on a specified date in a specified calendar for the GM.

        Takes the form !calendar:add_reminder_on <info>

        :param info:    Four arguments consisting of <calendar nickname> <reminder description> <date in acceptable format to calendar> <ticks until recurrence>.
                        <calendar nickname> is assumed to be single word
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        info = info.replace(nickname, "").strip()
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:add_gm_reminder_on:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Ascertain recurrence
        recurrence = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(recurrence), "", 1).strip()

        return await self.__add_reminder_on(ctx, game, calendar, info=info, reminder_type="GM", recurring=recurrence)

    async def __add_reminder_on(self, ctx: commands.Context, game, calendar, info: str, reminder_type: str, recurring=0):
        # Get the resource pack for translations of the reminder
        calendar_resource_pack = await self.load_resource_pack_for_calendar(ctx, calendar)
        if isinstance(calendar_resource_pack, str):
            return await send_message(ctx, calendar_resource_pack)
        calendar_handler = calendar_resource_pack.get_handler()

        # Ascertain the remaining information
        info, date = calendar_handler.extract_trailing_date(info)
        if not info or not date:
            return await send_message(ctx, "The calendar could not parse the information you provided. It identified the following information for the date: " + str(date) + " and for description: " + str(info))
        ticks = calendar_handler.calculate_ticks_until(date, calendar)

        # Create and append a reminder
        author_id = utils.get_user_id_from_context(ctx)
        reminder = calendar.add_reminder(ticks, info, author_id, reminder_type, recurring)
        await self.engine.save_game(ctx, game)
        return await send_message(ctx, "Added reminder: " + calendar_handler.translate_reminder(reminder, calendar))

    @commands.command(name="calendar:remove_reminder")
    async def remove_reminder_command(self, ctx: commands.Context, *, info: str):
        """
        Function to remove a reminder using its EXACT description

        :param info: <nickname of the calendar> <the full description of a reminder>
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Attempt to identify the nickname of the targeted calendar
        parts = info.split(" ", 1)
        nickname = parts[0]
        game, calendar_holder = self.get_game_and_calendar_data(ctx)
        calendar = calendar_holder.get_calendar(nickname)
        if not calendar:
            return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:remove_reminder:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Loop through the reminders
        info = info.replace(nickname, "").strip()
        author_id = utils.get_user_id_from_context(ctx)
        outcome = await calendar.remove_reminder(author_id, info)

        # Inform
        if outcome:
            return await send_message(ctx, "Removed reminder with description: " + info)
        else:
            return await send_message(ctx, "Could not find a reminder with the description: " + info)

    @commands.command(name="calendar:party_today")
    async def party_today_command(self, ctx: commands.Context, *, nickname: str = ""):
        """
        Function to return what there is to do today for the party with an optional command to query a specific calendar

        :param nickname: optional nickname of the calendar to query
        """
        return await self.__today(ctx, nickname=nickname)

    @commands.command(name="calendar:private_today")
    async def private_today_command(self, ctx: commands.Context, *, nickname: str = ""):
        """
        Function to return what there is to do today for you alone with an optional command to query a specific calendar

        :param nickname: optional nickname of the calendar to query
        """
        return await self.__today(ctx, nickname=nickname, reminder_type="private")

    @commands.command(name="calendar:gm_today")
    async def gm_today_command(self, ctx: commands.Context, *, nickname: str = ""):
        """
        Function to return what there is to do today for the GM with an optional command to query a specific calendar

        :param nickname: optional nickname of the calendar to query
        """
        return await self.__today(ctx, nickname=nickname, reminder_type="GM")

    async def __today(self, ctx: commands.Context, nickname: str = "", reminder_type="party"):
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Message
        long_message = LongMessage()
        long_message.add("The following items were found to do today that you have access to: ")

        # If a nickname was provided
        author_id = utils.get_user_id_from_context(ctx)
        if nickname != "":
            long_message.add("For calendar " + nickname + ":")
            long_message.add("")

            # Check if the user is in the party for the game they want to activate. Note it will also fail if the game does not exist
            party_permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:today:" + nickname, permissions_level=PermissionLevel.PARTY)
            if not party_permission:
                return await send_message(ctx, reason)

            # Check if the user is in the party for the game they want to activate. Note it will also fail if the game does not exist
            gm_permissions, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:today:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)

            # Get the specified calendar
            game, calendar_holder = self.get_game_and_calendar_data(ctx)
            calendar = calendar_holder.get_calendar(nickname)
            if not calendar:
                return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

            # Get the reminders
            ticks = calendar.get_ticks_passed()
            reminders = calendar.get_reminders()
            for reminder in reminders:
                if reminder.get_absolute_tick_date() == ticks:
                    if reminder_type == "party":
                        long_message.add(reminder.get_description())
                    elif reminder_type == "private" and reminder.get_author_id() == author_id:
                        long_message.add(reminder.get_description())
                    elif reminder_type == "GM" and gm_permissions:
                        long_message.add(reminder.get_description())

        # Loop through our calendars
        else:
            added_header = False
            game, calendar_holder = self.get_game_and_calendar_data(ctx)
            for nickname, calendar in calendar_holder.get_calendars().items():
                # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
                party_permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:today:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)
                if not party_permission:
                    continue

                # Check if the user is in the party for the game they want to activate. Note it will also fail if the game does not exist
                gm_permissions, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:today:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)

                # Loop printing
                if added_header:
                    long_message.add("")
                    added_header = False

                # Added info
                long_message.add("For calendar " + nickname + ":")
                long_message.add("")

                # Get the reminders
                ticks = calendar.get_ticks_passed()
                reminders = calendar.get_reminders()
                for reminder in reminders:
                    if reminder.get_absolute_tick_date() == ticks:
                        if not added_header:
                            long_message.add("For calendar " + nickname + ":")
                            long_message.add("")
                            added_header = True

                        if reminder_type == "party":
                            long_message.add(reminder.get_description())
                        elif reminder_type == "private" and reminder.get_author_id() == author_id:
                            long_message.add(reminder.get_description())
                        elif reminder_type == "GM" and gm_permissions:
                            long_message.add(reminder.get_description())

        # Output
        return await send_message(ctx, long_message)  # TODO: This needs to be sent to the correct locations

    @commands.command(name="calendar:party_reminders")
    async def party_reminders_command(self, ctx: commands.Context, *, nickname: str = ""):
        """
        Function to return what there is to do for the party with an optional command to query a specific calendar

        :param nickname: optional nickname of the calendar to query
        """
        return await self.__list_reminders(ctx, nickname=nickname)

    @commands.command(name="calendar:private_reminders")
    async def private_reminders_command(self, ctx: commands.Context, *, nickname: str = ""):
        """
        Function to return what there is to do for you alone with an optional command to query a specific calendar

        :param nickname: optional nickname of the calendar to query
        """
        return await self.__list_reminders(ctx, nickname=nickname, reminder_type="private")

    @commands.command(name="calendar:gm_reminders")
    async def gm_reminders_command(self, ctx: commands.Context, *, nickname: str = ""):
        """
        Function to return what there is to do for the GM with an optional command to query a specific calendar

        :param nickname: optional nickname of the calendar to query
        """
        return await self.__list_reminders(ctx, nickname=nickname, reminder_type="GM")

    async def __list_reminders(self, ctx: commands.Context, nickname: str = "", reminder_type="party"):
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        long_message = LongMessage()
        long_message.add("The following items were found to do that you have access to: ")

        # If a nickname was provided
        author_id = utils.get_user_id_from_context(ctx)
        if nickname != "":
            long_message.add("For calendar " + nickname + ":")
            long_message.add("")

            # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
            permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:list:" + nickname, permissions_level=PermissionLevel.PARTY)
            if not permission:
                return await send_message(ctx, reason)

            # Check if the user is in the party for the game they want to activate. Note it will also fail if the game does not exist
            gm_permissions, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:today:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)

            # Get the specified calendar
            game, calendar_holder = self.get_game_and_calendar_data(ctx)
            calendar = calendar_holder.get_calendar(nickname)
            if not calendar:
                return await send_message(ctx, "The identified nickname:" + nickname + " was not a calendar associated with this guild's current game.")

            # Get the reminders
            ticks = calendar.get_ticks_passed()
            reminders = calendar.get_reminders()
            for reminder in reminders:
                if reminder.get_absolute_tick_date() >= ticks:

                    if reminder_type == "party":
                        long_message.add(reminder.get_description())
                    elif reminder_type == "private" and reminder.get_author_id() == author_id:
                        long_message.add(reminder.get_description())
                    elif reminder_type == "GM" and gm_permissions:
                        long_message.add(reminder.get_description())

        # Loop through our calendars
        else:
            added_header = False
            game, calendar_holder = self.get_game_and_calendar_data(ctx)
            for nickname, calendar in calendar_holder.get_calendars().items():
                # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
                permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:list:" + nickname, permissions_level=PermissionLevel.PARTY)
                if not permission:
                    continue

                # Check if the user is in the party for the game they want to activate. Note it will also fail if the game does not exist
                gm_permissions, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "calendar:today:" + nickname, permissions_level=PermissionLevel.GAME_MASTER)

                # Loop printing
                if added_header:
                    long_message.add("")
                    added_header = False

                # Added info
                long_message.add("For calendar " + nickname + ":")
                long_message.add("")

                # Get the reminders
                ticks = calendar.get_ticks_passed()
                reminders = calendar.get_reminders()
                for reminder in reminders:
                    if reminder.get_absolute_tick_date() >= ticks:
                        if not added_header:
                            long_message.add("For calendar " + nickname + ":")
                            long_message.add("")
                            added_header = True

                        if reminder_type == "party":
                            long_message.add(reminder.get_description())
                        elif reminder_type == "private" and reminder.get_author_id() == author_id:
                            long_message.add(reminder.get_description())
                        elif reminder_type == "GM" and gm_permissions:
                            long_message.add(reminder.get_description())

        # Output
        return await send_message(ctx, long_message) # TODO  These need to go to the correct place
