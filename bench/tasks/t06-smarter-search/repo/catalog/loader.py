"""Reading and writing the stock list: one product per line, as `SKU | Name | 12.50 | tag, tag`."""
from catalog.products import Catalog, Product


def parse_price(text):
    """Turn "12.50" (or "12" or "12.5") into 1250 cents."""
    text = text.strip()
    whole, _, cents = text.partition('.')
    if not whole.isdigit() or (cents and not cents.isdigit()) or len(cents) > 2 or text.endswith('.'):
        raise ValueError('not a price: %r' % (text,))
    return int(whole) * 100 + int(cents.ljust(2, '0'))


def format_price(cents):
    """Turn 1250 cents into "12.50"."""
    return '%d.%02d' % divmod(cents, 100)


def load_lines(lines):
    """Build a Catalog from stock-list lines. Blank lines and lines starting with # are skipped."""
    catalog = Catalog()
    for number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        fields = [field.strip() for field in line.split('|')]
        if len(fields) not in (3, 4):
            raise ValueError('line %d: expected SKU | Name | Price | tags' % number)
        tags = fields[3].split(',') if len(fields) == 4 else ()
        try:
            catalog.add(Product(fields[0], fields[1], parse_price(fields[2]), tags))
        except ValueError as problem:
            raise ValueError('line %d: %s' % (number, problem)) from None
    return catalog


def dump_lines(catalog):
    """The stock-list lines for a catalog, in the order the products were added."""
    lines = []
    for product in catalog.products():
        fields = [product.sku, product.name, format_price(product.price)]
        if product.tags:
            fields.append(', '.join(product.tags))
        lines.append(' | '.join(fields))
    return lines
