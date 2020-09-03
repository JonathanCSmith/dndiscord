from new_implementation.modules.calendar.calendar_data import CalendarHandler, CalendarData, Reminder

# TODO: Translation integration
from new_implementation.utils import strings

"""


demo waterdeep resource pack - note wont work because of the lack of class info!:

    resource_pack.json:
        {
            "files_to_load": ["calendar_format.json"]
        }

    calendar_format.json:
        {
            "path_to_calendar_handler": "waterdeep_calendar.py"
        }

"""


class WaterdeepCalendarData(CalendarData):
    def __init__(self, archetype_id, ticks_passed=0, reminders=None):
        super().__init__(archetype_id=archetype_id, ticks_passed=ticks_passed, reminders=reminders)

        self.start_year = 1440
        self.start_month = 1
        self.start_day = 1

        self.current_year = 1440
        self.current_month = 1
        self.current_day = 1

    def copy(self):
        new_calendar = WaterdeepCalendarData(self.archetype_id, self.ticks_passed, self.reminders)
        new_calendar.start_year = self.start_year
        new_calendar.start_month = self.start_month
        new_calendar.start_day = self.start_day
        new_calendar.current_year = self.current_year
        new_calendar.current_month = self.current_month
        new_calendar.current_day = self.current_day
        return new_calendar

    def copy_start(self):
        new_calendar = WaterdeepCalendarData(self.archetype_id, self.ticks_passed, self.reminders)
        new_calendar.start_year = self.start_year
        new_calendar.start_month = self.start_month
        new_calendar.start_day = self.start_day
        new_calendar.current_year = self.start_year
        new_calendar.current_month = self.start_month
        new_calendar.current_day = self.start_day
        return new_calendar

    def date_equals(self, date):
        return self.current_year == date[0] and self.current_month == date[1] and self.current_day == date[2]


class WaterdeepCalendarHandler(CalendarHandler):
    def __init__(self):
        self.start_year = 1440
        self.start_month = 1
        self.start_day = 1
        self.year_conditional_modifiers = [(4, 7, 32, "Shieldmeet: a quadrennial event")]
        self.months = [
            ("Hammer", 31, " and it's winter!"),
            ("Alturiak", 30, " and it's winter!"),
            ("Ches", 30, " and it's spring!"),
            ("Tarsakh", 31, " and it's spring!"),
            ("Mirtul", 30, " and it's spring!"),
            ("Kythorn", 30, " and it's summer!"),
            ("Flamerule", 31, " and it's summer!"),
            ("Eleasis", 30, " and it's summer!"),
            ("Eleint", 31, " and it's autumn!"),
            ("Marpenoth", 30, " and it's autumn!"),
            ("Uktar", 31, " and it's autumn!"),
            ("Nightal", 30, " and it's winter!")
        ]
        self.special_days = [
            (1, 31, "Midwinter"),
            (4, 31, "Greengras"),
            (7, 31, "Midsummer"),
            (7, 32, "Shieldmeet"),
            (9, 31, "Highharvestide"),
            (11, 31, "The Feast of the Moon")
        ]

    def get_description(self, calendar_data: WaterdeepCalendarData):
        return "A day based calendar for the sword coast."

    def get_expected_date_format(self):
        return "YEAR MONTH DAY (e.g. 1440 1 1 - the 1st of Hammer, 1440)"

    def generate_elapsed_ticks_text(self, calendar_data: WaterdeepCalendarData):
        ticks = calendar_data.get_ticks_passed()
        return str(ticks) + " days have passed in this adventure"

    def extract_trailing_date(self, info):
        days = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(days), "", 1).strip()
        month = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(month), "", 1).trim()
        year = strings.get_trailing_number(info)
        info = strings.replace_count_reverse(info, str(year), "", 1).trim()

        if days and month and year:
            return info, [year, month, days]

    async def generate_current_time(self, calendar_data: WaterdeepCalendarData):
        return "Today is the " + await self._translate_date(calendar_data.current_year, calendar_data.current_month, calendar_data.current_day)

    async def get_start_time(self, calendar_data: WaterdeepCalendarData):
        return "This game started on the " + await self._translate_date(calendar_data.start_year, calendar_data.start_month, calendar_data.start_day)

    async def increment_ticks(self, calendar_data: WaterdeepCalendarData):
        # Get this months properties
        max_day_for_month = await self.__get_max_day_count_for_month(calendar_data.current_year, calendar_data.current_month)
        if 1 <= calendar_data.current_day < max_day_for_month:
            calendar_data.current_day += 1

        # Increment month
        elif calendar_data.current_day == max_day_for_month:
            calendar_data.current_day = 1

            # If we are in the last month
            if calendar_data.current_month == len(self.months):
                calendar_data.current_year += 1
                calendar_data.current_month = 1
            else:
                calendar_data.current_month += 1

        calendar_data.increment_ticks()

    async def calculate_ticks_until(self, date, calendar_data: WaterdeepCalendarData):
        calendar_data_copy = calendar_data.copy()
        while not calendar_data_copy.date_equals(date):
            await self.increment_ticks(calendar_data_copy)

        return calendar_data_copy.ticks_passed - calendar_data.ticks_passed

    async def translate_reminder(self, reminder: Reminder, calendar_data: WaterdeepCalendarData):
        start_calendar = calendar_data.copy_start()
        start_calendar = await self._calculate_date_after_ticks(reminder.get_absolute_tick_date(), start_calendar)
        return "Reminder on: " + await self._translate_date(start_calendar.current_year, start_calendar.current_month, start_calendar.current_day) + " of: " + reminder.get_description()

    async def _translate_date(self, year, month, day):
        translation_string = ""

        # Day
        if day == 1:
            translation_string += "1st of "
        elif day == 2:
            translation_string += "2nd of "
        elif day == 3:
            translation_string += "3rd of "
        else:
            translation_string += str(day) + "th of "

        # Month
        translation_string += self.months[month][0]

        # Year
        translation_string += " " + str(year)

        # Season
        translation_string += self.months[month][2]

        # If special day!
        for special_day in self.special_days:
            if month == special_day[0] and day == special_day[1]:
                translation_string += " Today is special because its the celebration of " + special_day[2]

        # If its a leap year
        for year_conditional_modifier in self.year_conditional_modifiers:
            if self.__does_year_conditional_modifier_apply_this_year(year, year_conditional_modifier[0]) and month == year_conditional_modifier[1] and day == year_conditional_modifier[2]:
                translation_string += " In addition, the rare occurance of " + year_conditional_modifier[3] + " is occuring."

        return translation_string

    async def _calculate_date_after_ticks(self, ticks, calendar_data: WaterdeepCalendarData):
        while not ticks == 0:
            calendar_data = await self.increment_ticks(calendar_data)
            ticks -= 1

        return calendar_data

    async def __get_max_day_count_for_month(self, year, month):
        # Normal month days
        month_tuple = self.months[month]
        month_days = month_tuple[1]

        # Check year conditional modifiers
        for item in self.year_conditional_modifiers:
            if self.__does_year_conditional_modifier_apply_this_year(year, item[0]) and month == item[1]:
                return month_days + 1

        return month_days

    def __does_year_conditional_modifier_apply_this_year(self, year, divisior):
        return year % divisior == 0
