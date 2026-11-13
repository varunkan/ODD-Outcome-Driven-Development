"""Amounts for lines and whole orders, in cents."""


def line_gross_cents(line):
    """Unit price times quantity, before the discount."""
    return line.unit_price_cents * line.quantity


def line_total_cents(line):
    """What the customer pays for one line, after its discount."""
    return int(line_gross_cents(line) * (1 - line.discount_percent / 100))


def order_subtotal_cents(order):
    """The order before discounts."""
    return sum(line_gross_cents(line) for line in order.lines)


def order_total_cents(order):
    """What the customer pays for the whole order."""
    total = 0.0
    for line in order.lines:
        total += line_gross_cents(line) * (1 - line.discount_percent / 100)
    return int(total)


def order_discount_cents(order):
    """How much the discounts took off the order."""
    return order_subtotal_cents(order) - order_total_cents(order)
