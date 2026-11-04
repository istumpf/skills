import re

CURRENCY = "USD"
_AMOUNT = re.compile(r"(\d+)(?:\.(\d{1,2}))?")


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
