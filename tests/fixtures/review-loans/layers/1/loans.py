from datetime import date, timedelta

# Days the library is closed besides Sundays. Circulation staff edit this set.
HOLIDAYS = frozenset({date(2026, 12, 25), date(2026, 12, 26), date(2027, 1, 1)})
PERIODS = {"book": 21, "dvd": 7}


def is_open(day):
    return day.weekday() != 6 and day not in HOLIDAYS


def _period(kind):
    if kind not in PERIODS:
        raise ValueError(f"unknown kind: {kind!r}")
    return timedelta(days=PERIODS[kind])


def _next_open(day):
    while not is_open(day):
        day += timedelta(days=1)
    return day


def due_date(checkout, kind):
    # Exact type check: datetime is a subclass of date and must be rejected.
    if type(checkout) is not date:
        raise TypeError(f"checkout must be a date: {checkout!r}")
    return _next_open(checkout + _period(kind))
