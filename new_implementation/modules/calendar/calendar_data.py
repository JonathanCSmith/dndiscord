from new_implementation.data.data import SerializationModifier
from new_implementation.utils import utils


class Reminder:
    def __init__(self, absolute_tick_date, description, author_id, reminder_type, recurring=0):
        self.absolute_tick_date = absolute_tick_date
        self.description = description
        self.author_id = author_id
        self.reminder_type = reminder_type
        self.recurring = recurring

    def get_absolute_tick_date(self):
        return self.absolute_tick_date

    def get_description(self):
        return self.description

    def get_author_id(self):
        return self.author_id

    def get_reminder_type(self):
        return self.reminder_type

    def get_recurring(self):
        return self.recurring


class CalendarData:
    def __init__(self, archetype_id, ticks_passed=0, reminders=None):
        self.archetype_id = archetype_id
        self.ticks_passed = ticks_passed

        if reminders is None:
            reminders = list()
        self.reminders = reminders

    def get_archetype_id(self):
        return self.archetype_id

    def increment_ticks(self):
        self.ticks_passed += 1

    def get_ticks_passed(self):
        return self.ticks_passed

    def get_reminders(self):
        return self.reminders

    def add_reminder(self, user_id: str, reminder_type, ticks, description, recurring):
        reminder = Reminder(ticks + self.ticks_passed, description, user_id, reminder_type, recurring)
        self.reminders.append(reminder)
        return reminder

    async def remove_reminder(self, author_id, description):
        identified_reminder = None
        for reminder in self.reminders:
            if reminder.get_description() == description:
                # Note - below is a hidden gotchya. We allow GMs to be removed here under the assumption that GM reminders can only be created by GMs therefore their author ID would match
                if reminder.get_reminder_type() == "private" or reminder.get_reminder_type() == "GM":
                    if reminder.get_author_id() == author_id:
                        identified_reminder = reminder
                        break

                else:
                    identified_reminder = reminder
                    break

        if identified_reminder:
            self.reminders.remove(identified_reminder)
            return True

        return False


class CalendarHandler:
    def get_description(self, calendar_data: CalendarData):
        pass

    def get_expected_date_format(self):
        pass

    def generate_elapsed_ticks_text(self, calendar_data: CalendarData):
        pass

    def extract_trailing_date(self, info):
        pass

    async def generate_current_time(self, calendar_data: CalendarData):
        pass

    async def get_start_time(self, calendar_data: CalendarData):
        pass

    async def increment_ticks(self, calendar_data: CalendarData):
        pass

    async def calculate_ticks_until(self, date, calendar_data: CalendarData):
        pass

    async def translate_reminder(self, reminder: Reminder, calendar_data: CalendarData):
        pass


class CalendarResourcePack(SerializationModifier):
    def __init__(self, path_to_calendar_data, path_to_calendar_handler):
        super().__init__()
        self.add_item_to_be_ignored("data")
        self.add_item_to_be_ignored("handler")

        self.path_to_calendar_data = path_to_calendar_data
        self.path_to_calendar_handler = path_to_calendar_handler
        self.data = utils.load_class(self.path_to_calendar_data, CalendarData)
        self.handler = utils.load_class(self.path_to_calendar_handler, CalendarHandler)()

    def get_handler(self):
        return self.handler

    def get_custom_calendar_data(self, resource_pack_key):
        return self.data(resource_pack_key)


class CalendarHolderData:
    def __init__(self):
        self.calendars = dict()

    def add_calendar(self, key, calendar):
        self.calendars[key] = calendar

    def get_calendars(self):
        return self.calendars

