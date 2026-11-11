"""Rows of a stock file. A row is `SKU;quantity`. Blank lines and lines starting with `#` are skipped."""
from .quantity import parse_quantity


def parse_row(line):
    """(sku, quantity) for one row. Raises ValueError for a row that is not `SKU;quantity`."""
    parts = line.strip().split(';')
    if len(parts) != 2:
        raise ValueError('expected SKU;quantity, got %r' % (line,))
    sku = parts[0].strip()
    if not sku:
        raise ValueError('row has no SKU: %r' % (line,))
    return sku, parse_quantity(parts[1])


def read_rows(lines):
    """Every row in lines as a list of (sku, quantity).

    A row that cannot be read raises ValueError naming its line number, counted from 1.
    """
    rows = []
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        try:
            rows.append(parse_row(stripped))
        except ValueError as error:
            raise ValueError('line %d: %s' % (number, error)) from None
    return rows
