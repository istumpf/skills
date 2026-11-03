# Deliberately plausible but wrong: one mistake per hidden trap.
CURRENCY = "USD"


def format_cents(cents):
    sign = "-" if cents < 0 else ""
    whole, part = divmod(abs(cents), 100)
    return f"{sign}${whole:,}.{part:02d}"


def parse_amount(text):
    text = text.strip().replace(",", "")
    if not text or text.startswith("-") or "." in text and len(text.split(".")[1]) > 2:
        raise ValueError(text)
    return int(float(text) * 100)


def line_total(unit_cents, quantity, discount_percent=0):
    if quantity <= 0:
        raise ValueError(quantity)
    return round(unit_cents * quantity * (100 - discount_percent) / 100)


def coupon_discount(subtotal_cents, coupon):
    if coupon["type"] == "percent":
        return round(subtotal_cents * coupon["value"] / 100)
    return coupon["value"]


def tax_cents(taxable_cents, rate):
    return round(taxable_cents * float(rate) / 100)


def build_invoice(lines, coupon=None, tax_rate="0"):
    for line in lines:
        line.setdefault("discount_percent", 0)
    gross = sum(parse_amount(l["price"]) * l["quantity"] * (100 - l["discount_percent"]) / 100 for l in lines)
    subtotal = round(gross)
    list_price = sum(parse_amount(l["price"]) * l["quantity"] for l in lines)
    discount = coupon_discount(list_price, coupon) if coupon else 0
    tax = tax_cents(subtotal - discount, tax_rate)
    return {"subtotal": subtotal, "coupon_discount": discount, "tax": tax,
            "total": subtotal - discount + tax}
