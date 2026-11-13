"""Tax rates are written as percent strings, the way they appear on the invoice: '20', '5', '7.5', '0'."""
import re

_RATE = re.compile(r'^(0|[1-9]\d?)(\.\d{1,2})?$')

STANDARD = '20'
REDUCED = '5'
ZERO = '0'


def check_rate(rate):
    """Return the rate unchanged if it is a percent string from '0' to '99.99'; raise ValueError otherwise."""
    if not isinstance(rate, str) or not _RATE.match(rate):
        raise ValueError('a tax rate is a percent string such as %r or %r, got %r' % (STANDARD, '7.5', rate))
    return rate


def rate_order(rate):
    """Sort key: highest rate first, as on the printed invoice."""
    whole, _, fraction = rate.partition('.')
    return (-int(whole), -int(fraction.ljust(2, '0') or '0'))
