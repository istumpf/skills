## Why

The circulation desk computes due dates, overdue fines, renewals, and holds by hand, and patrons get different answers at different desks.

## What Changes

- Compute due dates from the checkout date and item kind.
- Count overdue days.
- Compute overdue fines.
- Renew loans.
- Place holds, and refuse renewals of items other patrons are waiting for.
- Summarize a patron's overdue loans on a receipt.

## Capabilities

### New Capabilities
- `loan-desk`: Due dates, overdue fines, renewals, holds, and receipts for library loans.

### Modified Capabilities

None.

## Impact

Only the Python module `loans.py` and its tests are affected. The existing `HOLIDAYS` set and `is_open(day)` remain unchanged; circulation staff maintain `HOLIDAYS` by hand.
