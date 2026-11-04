from decimal import Decimal
import re

CURRENCY = "USD"
_AMOUNT = re.compile(r"(\d+)(?:\.(\d{1,2}))?")
_RATE = re.compile(r"\d+(?:\.\d+)?")


def format_cents(cents):
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{part:02d}"


def parse_amount(text):
    match = _AMOUNT.fullmatch(text.strip())
    if not match:
        raise ValueError(f"invalid amount: {text!r}")
    fraction = (match.group(2) or "").ljust(2, "0")
    return int(match.group(1)) * 100 + int(fraction)


def line_total(unit_cents, quantity, discount_percent=0):
    if type(quantity) is not int or quantity < 1:
        raise ValueError(f"invalid quantity: {quantity!r}")
    if type(discount_percent) is not int or not 0 <= discount_percent <= 100:
        raise ValueError(f"invalid discount: {discount_percent!r}")
    return round(Decimal(unit_cents * quantity * (100 - discount_percent)) / 100)


def coupon_discount(subtotal_cents, coupon):
    if coupon["type"] == "percent":
        # Half up for non-negative integers without leaving integer arithmetic.
        return (subtotal_cents * coupon["value"] + 50) // 100
    if coupon["type"] == "fixed":
        return coupon["value"]
    raise ValueError(f"unknown coupon type: {coupon['type']!r}")


def tax_cents(taxable_cents, rate):
    if not _RATE.fullmatch(rate):
        raise ValueError(f"invalid rate: {rate!r}")
    return int((taxable_cents * Decimal(rate) + 50) // 100)
