"""Quantities as they are written in supplier stock files."""
import re

_NUMBER = re.compile(r'[+-]?\d[\d,]*')


def parse_quantity(text):
    """The whole number written in text.

    A leading sign, thousands commas and surrounding spaces are allowed: '12', ' 1,250 ', '+7', '-3'.
    Raises ValueError when text holds no number.
    """
    if not isinstance(text, str):
        raise ValueError('a quantity must be text, got %r' % (text,))
    found = _NUMBER.match(text.strip())
    if found is None:
        raise ValueError('not a quantity: %r' % (text,))
    return int(found.group().replace(',', ''))


def format_quantity(quantity):
    """A quantity written with thousands commas: 1250 -> '1,250'."""
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise ValueError('a quantity must be a whole number, got %r' % (quantity,))
    return '{:,}'.format(quantity)
