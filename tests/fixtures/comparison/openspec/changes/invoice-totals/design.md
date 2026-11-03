## Context

`invoice.py` already exposes `CURRENCY` and `format_cents(cents)`. Callers pass catalog price strings and expect integer cents back.

## Goals / Non-Goals

Goals: exact, deterministic money arithmetic using only the standard library.
Non-goals: multiple currencies, locale-aware parsing, and persistence.

## Decisions

- Represent every amount as an integer number of cents.
- Never use binary floating point for money or rates; use integers or `decimal.Decimal`.
- Every rounding step rounds half up to a whole cent.
- Round each line total separately; the subtotal is the sum of rounded line totals.
- Apply the coupon to the subtotal before tax. Tax is charged on the subtotal minus the coupon discount.
- `build_invoice` reuses `parse_amount`, `line_total`, `coupon_discount`, and `tax_cents` rather than reimplementing them.

## Risks / Trade-offs

Later groups extend earlier behavior. Extensions must keep every earlier scenario passing.
