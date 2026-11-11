"""Plain-text receipts."""

from .totals import line_total_cents, order_discount_cents, order_total_cents

WIDTH = 40


def format_cents(cents):
    """1234 -> '12.34'. Negative amounts keep their sign."""
    sign = '-' if cents < 0 else ''
    cents = abs(cents)
    return '%s%d.%02d' % (sign, cents // 100, cents % 100)


def _row(label, amount):
    return label.ljust(WIDTH - len(amount)) + amount


def render_receipt(order):
    """One row per line, then what the discounts saved (if anything), then the total."""
    rows = []
    for line in order.lines:
        label = '%d x %s' % (line.quantity, line.name)
        if line.discount_percent:
            label += ' (-%d%%)' % line.discount_percent
        rows.append(_row(label, format_cents(line_total_cents(line))))
    saved = order_discount_cents(order)
    if saved:
        rows.append(_row('You saved', format_cents(saved)))
    rows.append(_row('TOTAL', format_cents(order_total_cents(order))))
    return '\n'.join(rows)
