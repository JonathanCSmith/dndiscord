class Calendar:
    special_months = [1, 4, 7, 9, 11]

    def __init__(self, year, month, day):
        self.year = year
        self.month = month

        if day > 31 and month not in Calendar.special_months:
            raise RuntimeError("Invalid Date")

        if day == 32 and (month != 1 or year % 4 != 0):
            raise RuntimeError("Invalid Date")

        self.day = day


months = [
    "Hammer",
    "Alturiak",
    "Ches",
    "Tarsakh",
    "Mirtul",
    "Kythorn",
    "Flamerule",
    "Eleasis",
    "Eleint",
    "Marpenoth",
    "Uktar",
    "Nightal"
]

special_days = {
    31: "Midwinter",
    122: "Greengrass",
    213: "Midsummer",
    274: "Highharvestide",
    335: "Feat of the Moon"
}

shieldmeet = 214

lookup = {
    1: "st",
    2: "nd",
    3: "rd"
}


def build_day_map(calendar):
    day_map = dict()
    day_count = 0
    modifier = 0
    for month in months:
        if month == "Nightal" or month == "Hammer" or month == "Alturiak":
            seasonal = " and it's winter!"

        elif month == "Ches" or month == "Tarsakh" or month == "Mirtul":
            seasonal = " and it's spring!"

        elif month == "Kythorn" or month == "Flamerule" or month == "Eleasis":
            seasonal = " and it's summer!"

        else:
            seasonal = " ant it's autumn!"

        for i in range(1, 31):
            day_count += 1
            old_day_count = -1
            while True:
                # No change
                if old_day_count == day_count:
                    break

                old_day_count = day_count
                if day_count == shieldmeet and calendar.year % 4 == 0:
                    day_map[day_count] = "Shieldmeet" + seasonal
                    day_count += 1
                    modifier += 1

                elif day_count - modifier in special_days:
                    day_map[day_count] = special_days[day_count - modifier] + seasonal
                    day_count += 1

            day_map[day_count] = str(i) + (lookup[i] if i in lookup else "th") + " of " + month + seasonal

    if len(day_map) != calc_days_in_year(calendar):
        raise RuntimeError("You fucked up somewhere")

    return day_map


def calc_start_index(calendar):
    index = ((calendar.month - 1) * 30) + calendar.day
    if index > 32 and calendar.year % 4 == 0:
        index += 1

    for day, item in special_days.items():
        if index - calendar.day + 1 >= day:  # Shieldmeet would break this conditional if there was a celebration in the next month
            index += 1

    return index


def calc_days_in_year(calendar):
    return 366 if calendar.year % 4 == 0 else 365


def convert(calendar, days_passed):
    while True:
        start_index = calc_start_index(calendar)
        days_in_current_year = calc_days_in_year(calendar)

        if start_index + days_passed > days_in_current_year:
            calendar.year += 1
            calendar.month = 1
            calendar.day = 1
            days_passed -= (days_in_current_year - start_index)
        else:
            day_map = build_day_map(calendar)
            day_text = day_map[start_index + days_passed]
            return day_map[start_index + days_passed]
