from datetime import date

# Days the library is closed besides Sundays. Circulation staff edit this set.
HOLIDAYS = frozenset({date(2026, 12, 25), date(2026, 12, 26), date(2027, 1, 1)})


def is_open(day):
    return day.weekday() != 6 and day not in HOLIDAYS
