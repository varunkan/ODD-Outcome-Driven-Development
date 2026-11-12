"""Money is whole cents (int) everywhere. This is the one place it becomes text."""


def format_cents(cents):
    """1234 -> '12.34', -7 -> '-0.07'."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise ValueError('cents must be an int, got %r' % (cents,))
    sign = '-' if cents < 0 else ''
    whole, part = divmod(abs(cents), 100)
    return '%s%d.%02d' % (sign, whole, part)
