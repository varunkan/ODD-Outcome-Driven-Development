"""Orders and their lines. Prices are whole cents."""


class LineItem:
    """One line of an order: a product, how many of it, and a percentage discount."""

    def __init__(self, name, unit_price_cents, quantity=1, discount_percent=0):
        if unit_price_cents < 0:
            raise ValueError('unit_price_cents must not be negative')
        if quantity < 1:
            raise ValueError('quantity must be at least 1')
        if not 0 <= discount_percent <= 100:
            raise ValueError('discount_percent must be from 0 to 100')
        self.name = name
        self.unit_price_cents = unit_price_cents
        self.quantity = quantity
        self.discount_percent = discount_percent

    def __repr__(self):
        return 'LineItem(%r, %r, quantity=%r, discount_percent=%r)' % (
            self.name, self.unit_price_cents, self.quantity, self.discount_percent)


class Order:
    """A list of lines, in the order they were added."""

    def __init__(self):
        self.lines = []

    def add(self, name, unit_price_cents, quantity=1, discount_percent=0):
        """Append a line and return it."""
        line = LineItem(name, unit_price_cents, quantity, discount_percent)
        self.lines.append(line)
        return line
