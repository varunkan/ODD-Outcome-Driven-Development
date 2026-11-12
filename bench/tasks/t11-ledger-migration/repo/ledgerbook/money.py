"""Amounts are whole cents everywhere inside ledgerbook. These two functions are the only way in and out as text."""
import re

_AMOUNT = re.compile(r'^([+-]?)(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?$')


def parse_amount(text):
    """'12.50' -> 1250, '-3' -> -300, '1,234.5' -> 123450. Raises ValueError for anything else."""
    if not isinstance(text, str):
        raise ValueError('an amount is text, got %r' % (text,))
    match = _AMOUNT.match(text.strip())
    if not match:
        raise ValueError('not an amount: %r' % text)
    sign, whole, fraction = match.groups()
    cents = int(whole.replace(',', '')) * 100 + int((fraction or '0').ljust(2, '0'))
    return -cents if sign == '-' else cents


def format_amount(cents, thousands=False):
    """1250 -> '12.50', -5 -> '-0.05'. With thousands=True: 123450 -> '1,234.50'."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise ValueError('cents must be an int, got %r' % (cents,))
    sign = '-' if cents < 0 else ''
    whole, fraction = divmod(abs(cents), 100)
    whole_text = '{:,}'.format(whole) if thousands else str(whole)
    return '%s%s.%02d' % (sign, whole_text, fraction)
