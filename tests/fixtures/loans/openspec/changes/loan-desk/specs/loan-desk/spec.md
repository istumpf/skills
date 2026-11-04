## ADDED Requirements

### Requirement: Due dates
The library SHALL expose `due_date(checkout, kind)` that adds the loan period to `checkout`: 21 days for `"book"` and 7 days for `"dvd"`. When the library is closed on that day, the due date SHALL be the next day it is open. `checkout` SHALL be a `datetime.date`; a `datetime.datetime` or any other type SHALL raise `TypeError`. Any other kind SHALL raise `ValueError`.

#### Scenario: Book due date
- **WHEN** called with `date(2026, 11, 2)` and `"book"`
- **THEN** it returns `date(2026, 11, 23)`

#### Scenario: Due date on a Sunday
- **WHEN** called with `date(2026, 11, 1)` and `"dvd"`
- **THEN** it returns `date(2026, 11, 9)`

### Requirement: Overdue days
The library SHALL expose `days_overdue(due, returned)` that returns the number of open days after `due` up to and including `returned`, and `0` when `returned` is on or before `due`.

#### Scenario: Returned late
- **WHEN** called with `date(2026, 11, 23)` and `date(2026, 11, 25)`
- **THEN** it returns `2`

#### Scenario: Returned early
- **WHEN** called with `date(2026, 11, 23)` and `date(2026, 11, 20)`
- **THEN** it returns `0`

### Requirement: Fines
The library SHALL expose `fine_cents(kind, days)` for `days` overdue days. A book is charged 25 cents for each overdue day after the first; a DVD is charged 100 cents for each overdue day. `days` SHALL be a non-negative integer, and any other value SHALL raise `ValueError`.

#### Scenario: DVD fine
- **WHEN** called with `"dvd"` and `3`
- **THEN** it returns `300`

#### Scenario: Not overdue
- **WHEN** called with `"book"` and `0`
- **THEN** it returns `0`

### Requirement: Renewals
The library SHALL expose `renew(loan, today)` that returns a new loan whose due date is the loan period for its kind counted from the current due date, moved to the next open day as for due dates, with `"renewals"` increased by one. A loan SHALL NOT be renewed when `today` is after its due date or when it has already been renewed twice; either case SHALL raise `ValueError`.

#### Scenario: Renew on the due date
- **WHEN** a book loan due `date(2026, 11, 23)` with `0` renewals is renewed on `date(2026, 11, 23)`
- **THEN** the new loan is due `date(2026, 12, 14)` with `1` renewal

#### Scenario: Overdue loan
- **WHEN** a loan due `date(2026, 11, 23)` is renewed on `date(2026, 11, 24)`
- **THEN** it raises `ValueError`

### Requirement: Holds
The library SHALL expose `place_hold(holds, patron)` that returns a new tuple with `patron` appended to the tuple `holds`; a patron already in `holds` SHALL raise `ValueError`. `renew` SHALL accept an optional `holds` tuple, defaulting to empty. A loan SHALL NOT be renewed while a patron other than its borrower holds the item; that case SHALL raise `ValueError`.

#### Scenario: Place a hold
- **WHEN** called with `("ana",)` and `"bo"`
- **THEN** it returns `("ana", "bo")`

#### Scenario: Renewal blocked by a hold
- **WHEN** a loan borrowed by `"ana"` is renewed on its due date with holds `("bo",)`
- **THEN** it raises `ValueError`

### Requirement: Receipts
The library SHALL expose `receipt(loans, today)` that returns a dict with `"overdue_items"`, the number of loans due before `today`, and `"total_cents"`, the sum of each such loan's fine for its overdue days on `today`.

#### Scenario: One overdue DVD
- **WHEN** called with one DVD loan due `date(2026, 11, 23)` on `date(2026, 11, 25)`
- **THEN** it returns `{"overdue_items": 1, "total_cents": 200}`

#### Scenario: Nothing overdue
- **WHEN** called with no loans
- **THEN** it returns `{"overdue_items": 0, "total_cents": 0}`
