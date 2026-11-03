## 1. Amount parsing

- [ ] 1.1 Implement `parse_amount(text)` in `invoice.py`.
- [ ] 1.2 Add parsing tests in `test_invoice.py` and run them.

## 2. Line totals

- [ ] 2.1 Implement `line_total(unit_cents, quantity, discount_percent=0)`.
- [ ] 2.2 Add line total tests and run the test suite.

## 3. Coupons

- [ ] 3.1 Implement `coupon_discount(subtotal_cents, coupon)`.
- [ ] 3.2 Add coupon tests and run the test suite.

## 4. Sales tax

- [ ] 4.1 Implement `tax_cents(taxable_cents, rate)`.
- [ ] 4.2 Add tax tests and run the test suite.

## 5. Invoice summary

- [ ] 5.1 Accept thousands separators in `parse_amount`.
- [ ] 5.2 Implement `build_invoice(lines, coupon=None, tax_rate="0")`.
- [ ] 5.3 Add invoice tests and run the complete test suite.
