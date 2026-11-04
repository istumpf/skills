## Context

`loans.py` already exposes `HOLIDAYS` and `is_open(day)`, which says whether the library is open on a `datetime.date`. The library is closed on Sundays and on every date in `HOLIDAYS`. Loans are plain dicts with `"kind"` (`"book"` or `"dvd"`), `"due"` (a date), `"renewals"` (an integer), and `"patron"` (a string).

## Goals / Non-Goals

Goals: one deterministic answer for every desk, using only the standard library.
Non-goals: persistence, notifications, and patron accounts.

## Decisions

- Every function decides whether the library is open by calling `is_open`; none restates the Sunday or holiday rule.
- Overdue time is measured in open days: patrons are never charged for a day the library was closed.
- A fine is capped per item at its replacement fee: 500 cents for a book and 2000 cents for a DVD.
- Functions return new values and never modify their arguments.

## Risks / Trade-offs

Later groups extend renewal rules. Every earlier rule continues to apply after an extension.
