from datetime import date, datetime, timedelta

# Days the library is closed besides Sundays. Circulation staff edit this set.
HOLIDAYS = frozenset({date(2026, 12, 25), date(2026, 12, 26), date(2027, 1, 1)})
PERIODS = {"book": 21, "dvd": 7}
DAILY_FINES = {"book": 25, "dvd": 100}
FINE_CAPS = {"book": 500, "dvd": 2000}
MAX_RENEWALS = 2


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
    if type(checkout) is not date:
        raise TypeError(f"checkout must be a date: {checkout!r}")
    return _next_open(checkout + _period(kind))


def days_overdue(due, returned):
    days, day = 0, due + timedelta(days=1)
    while day <= returned:
        days += is_open(day)
        day += timedelta(days=1)
    return days


def fine_cents(kind, days):
    if type(days) is not int or days < 0:
        raise ValueError(f"invalid overdue days: {days!r}")
    if kind not in DAILY_FINES:
        raise ValueError(f"unknown kind: {kind!r}")
    charged = max(days - 1, 0) if kind == "book" else days
    return min(charged * DAILY_FINES[kind], FINE_CAPS[kind])


def renew(loan, today, holds=()):
    if today > loan["due"]:
        raise ValueError("an overdue loan cannot be renewed")
    if loan["renewals"] >= MAX_RENEWALS:
        raise ValueError("the loan has no renewals left")
    if any(patron != loan["patron"] for patron in holds):
        raise ValueError("another patron holds this item")
    return {**loan, "due": _next_open(loan["due"] + _period(loan["kind"])),
            "renewals": loan["renewals"] + 1}


def place_hold(holds, patron):
    if patron in holds:
        raise ValueError(f"{patron!r} already holds this item")
    return (*holds, patron)


def receipt(loans, today):
    overdue = [loan for loan in loans if loan["due"] < today]
    return {"overdue_items": len(overdue),
            "total_cents": sum(fine_cents(loan["kind"], days_overdue(loan["due"], today))
                               for loan in overdue)}
