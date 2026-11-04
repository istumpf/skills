"""Trap data for the invoice-totals comparison case."""

CHANGE = "invoice-totals"
MODULE = "invoice"
TRAPS = ["SpecScenarios", "ExactParsing", "StrictParsing", "LineHalfUp", "CouponRules",
         "TaxExactHalfUp", "PerLineRounding", "CouponAfterLineDiscounts",
         "GroupedParsingRegression", "NoMutation", "ExistingApi"]
# The task group that introduces each trap's rule; a stack layer must pass every
# trap owned by its group or a lower one.
TRAP_GROUPS = {"ExactParsing": 1, "StrictParsing": 1, "ExistingApi": 1, "LineHalfUp": 2,
               "CouponRules": 3, "TaxExactHalfUp": 4, "PerLineRounding": 5,
               "CouponAfterLineDiscounts": 5, "GroupedParsingRegression": 5, "NoMutation": 5}
# One plausible mistake per trap, applied to the reference implementation. The
# offline suite checks that each mutant fails its own trap and no other.
MUTANTS = {
    "ExactParsing": ("return int(whole) * 100 + int(fraction)",
                     'return int(float(f"{whole}.{fraction}") * 100)'),
    "StrictParsing": ('_AMOUNT = re.compile(r"(', '_AMOUNT = re.compile(r"\\+?('),
    "ExistingApi": ("{whole:,}", "{whole}"),
    "LineHalfUp": ("    if discount_percent > 100:\n"
                   '        raise ValueError(f"invalid discount: {discount_percent!r}")\n', ""),
    "CouponRules": ("return min(discount, subtotal_cents)", "return discount"),
    "TaxExactHalfUp": ("return _half_up(taxable_cents * Decimal(rate) / 100)",
                       "return round(taxable_cents * float(rate) / 100)"),
    "PerLineRounding": ('subtotal = sum(line_total(parse_amount(line["price"]), line["quantity"],\n'
                        '                              line.get("discount_percent", 0)) for line in lines)',
                        'subtotal = _half_up(sum(Decimal(parse_amount(line["price"]) * line["quantity"]\n'
                        '                        * (100 - line.get("discount_percent", 0))) / 100 for line in lines))'),
    "CouponAfterLineDiscounts": ("discount = coupon_discount(subtotal, coupon)",
                                 'discount = coupon_discount(sum(parse_amount(line["price"]) * line["quantity"]\n'
                                 '                                   for line in lines), coupon)'),
    "GroupedParsingRegression": (r"(\d{1,3}(?:,\d{3})+|\d+)", r"([\d,]+)"),
    "NoMutation": ('def build_invoice(lines, coupon=None, tax_rate="0"):\n',
                   'def build_invoice(lines, coupon=None, tax_rate="0"):\n'
                   "    for line in lines:\n"
                   '        line.setdefault("discount_percent", 0)\n'),
}
# Tasks that cannot be proven inside the evaluation repository.
UNPROVABLE_TASKS = []
