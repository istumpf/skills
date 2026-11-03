## ADDED Requirements

### Requirement: Parse amounts
The library SHALL expose `parse_amount(text)` that converts a non-negative decimal string with at most two fractional digits into integer cents, ignoring surrounding whitespace. The conversion SHALL be exact for every valid input and SHALL NOT use binary floating point. Input that is empty, negative, signed, in exponent notation, or has more than two fractional digits SHALL raise `ValueError`.

#### Scenario: Valid amounts
- **WHEN** called with `" 12.5 "`, `"7"`, or `"0.05"`
- **THEN** it returns `1250`, `700`, or `5`

#### Scenario: Invalid amounts
- **WHEN** called with `""`, `"-1"`, `"abc"`, or `"1.234"`
- **THEN** it raises `ValueError`

### Requirement: Line totals
The library SHALL expose `line_total(unit_cents, quantity, discount_percent=0)` that returns `unit_cents * quantity` reduced by `discount_percent` percent, rounded half up to a whole cent. `quantity` SHALL be a positive integer and `discount_percent` an integer from 0 through 100; other values SHALL raise `ValueError`.

#### Scenario: Discounted line
- **WHEN** called with `999`, `2`, and `10`
- **THEN** it returns `1798`

#### Scenario: Invalid quantity
- **WHEN** called with a quantity of `0`
- **THEN** it raises `ValueError`

### Requirement: Coupon discounts
The library SHALL expose `coupon_discount(subtotal_cents, coupon)` where `coupon` is a mapping with `"type"` of `"percent"` or `"fixed"` and an integer `"value"` (a percentage or cents). A percent discount SHALL round half up to a whole cent. The discount SHALL NOT exceed the subtotal. An unknown type SHALL raise `ValueError`.

#### Scenario: Percent coupon
- **WHEN** called with `2000` and `{"type": "percent", "value": 15}`
- **THEN** it returns `300`

#### Scenario: Fixed coupon
- **WHEN** called with `2000` and `{"type": "fixed", "value": 500}`
- **THEN** it returns `500`

### Requirement: Sales tax
The library SHALL expose `tax_cents(taxable_cents, rate)` where `rate` is a decimal percentage string such as `"8.875"`. The rate SHALL be interpreted exactly and the tax rounded half up to a whole cent.

#### Scenario: Fractional rate
- **WHEN** called with `1000` and `"8.875"`
- **THEN** it returns `89`

### Requirement: Invoice summary
The library SHALL expose `build_invoice(lines, coupon=None, tax_rate="0")`. Each line is a mapping with a `"price"` catalog string, an integer `"quantity"`, and an optional integer `"discount_percent"`. It SHALL return a dict of integer cents with keys `"subtotal"`, `"coupon_discount"`, `"tax"`, and `"total"`, where tax is charged after the coupon and `total` equals `subtotal - coupon_discount + tax`. It SHALL NOT mutate its arguments.

#### Scenario: Invoice with coupon and tax
- **WHEN** called with lines `[{"price": "10.00", "quantity": 2}]`, coupon `{"type": "fixed", "value": 500}`, and tax rate `"10"`
- **THEN** it returns subtotal `2000`, coupon discount `500`, tax `150`, and total `1650`

### Requirement: Catalog thousands separators
`parse_amount` SHALL accept comma thousands separators in the integer part, such as `"1,234.50"`. Each comma SHALL be followed by exactly three digits and the first group SHALL have one to three digits. All earlier parsing requirements continue to apply.

#### Scenario: Grouped amount
- **WHEN** called with `"1,234.50"`
- **THEN** it returns `123450`
