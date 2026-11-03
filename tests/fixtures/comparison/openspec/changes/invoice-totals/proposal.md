## Why

Checkout needs exact invoice totals from catalog prices, line discounts, coupons, and sales tax.

## What Changes

- Parse catalog price strings into integer cents.
- Compute discounted line totals.
- Compute coupon discounts.
- Compute sales tax from a decimal rate.
- Build an invoice summary from catalog lines, accepting thousands separators in catalog prices.

## Capabilities

### New Capabilities
- `invoice-totals`: Exact money arithmetic for invoice lines, coupons, tax, and totals.

### Modified Capabilities

None.

## Impact

Only the Python module `invoice.py` and its tests are affected. The existing `CURRENCY` constant and `format_cents(cents)` remain unchanged.
