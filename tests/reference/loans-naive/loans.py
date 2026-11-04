# Deliberately plausible but wrong: one mistake per hidden trap.
from datetime import date, timedelta

HOLIDAYS = frozenset({date(2026, 12, 25), date(2026, 12, 26), date(2027, 1, 1)})
PERIODS = {"book": 21, "dvd": 7}


def is_open(day):
    return day.weekday() != 6 and day not in HOLIDAYS


def due_date(checkout, kind):
    if not isinstance(checkout, date):
        raise TypeError(checkout)
    if kind not in PERIODS:
        raise ValueError(kind)
    due = checkout + timedelta(days=PERIODS[kind])
    if not is_open(due):
        due += timedelta(days=1)
    return due


def days_overdue(due, returned):
    return max((returned - due).days, 0)


def fine_cents(kind, days):
    if days < 0:
        raise ValueError(days)
    return days * (25 if kind == "book" else 100)


def renew(loan, today, holds=()):
    if today > loan["due"] or holds:
        raise ValueError("cannot renew")
    loan["renewals"] += 1
    loan["due"] = due_date(today, loan["kind"])
    return loan


def place_hold(holds, patron):
    if patron in holds:
        raise ValueError(patron)
    return (*holds, patron)


def receipt(loans, today):
    overdue = [loan for loan in loans if loan["due"] < today]
    return {"overdue_items": len(overdue),
            "total_cents": sum(fine_cents(l["kind"], (today - l["due"]).days) for l in overdue)}
