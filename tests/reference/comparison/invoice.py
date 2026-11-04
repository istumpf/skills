from decimal import ROUND_HALF_UP, Decimal
import re

CURRENCY = "USD"
_AMOUNT = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?", re.ASCII)
_RATE = re.compile(r"\d+(?:\.\d+)?", re.ASCII)


def format_cents(cents):
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{part:02d}"


def _half_up(value):
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _whole(value, low, name):
    if type(value) is not int or value < low:
        raise ValueError(f"invalid {name}: {value!r}")


def parse_amount(text):
    match = _AMOUNT.fullmatch(text.strip())
    if not match:
        raise ValueError(f"invalid amount: {text!r}")
    whole, fraction = match.group(1).replace(",", ""), (match.group(2) or "").ljust(2, "0")
    return int(whole) * 100 + int(fraction)


def line_total(unit_cents, quantity, discount_percent=0):
    _whole(quantity, 1, "quantity")
    _whole(discount_percent, 0, "discount")
    if discount_percent > 100:
        raise ValueError(f"invalid discount: {discount_percent!r}")
    return _half_up(Decimal(unit_cents * quantity * (100 - discount_percent)) / 100)


def coupon_discount(subtotal_cents, coupon):
    if coupon["type"] == "percent":
        discount = _half_up(Decimal(subtotal_cents * coupon["value"]) / 100)
    elif coupon["type"] == "fixed":
        discount = coupon["value"]
    else:
        raise ValueError(f"unknown coupon type: {coupon['type']!r}")
    return min(discount, subtotal_cents)


def tax_cents(taxable_cents, rate):
    if not _RATE.fullmatch(rate):
        raise ValueError(f"invalid rate: {rate!r}")
    return _half_up(taxable_cents * Decimal(rate) / 100)


def build_invoice(lines, coupon=None, tax_rate="0"):
    subtotal = sum(line_total(parse_amount(line["price"]), line["quantity"],
                              line.get("discount_percent", 0)) for line in lines)
    discount = coupon_discount(subtotal, coupon) if coupon else 0
    tax = tax_cents(subtotal - discount, tax_rate)
    return {"subtotal": subtotal, "coupon_discount": discount, "tax": tax,
            "total": subtotal - discount + tax}
