"""Stock reports built from a ledger."""

# (heading, row key, alignment) for each column of the text table, left to right.
COLUMNS = (
    ('SKU', 'sku', '<'),
    ('Name', 'name', '<'),
    ('On hand', 'on_hand', '>'),
    ('Reorder at', 'reorder_level', '>'),
)


def stock_rows(ledger):
    """One dict per item, in SKU order, with the keys sku, name, on_hand and reorder_level."""
    rows = []
    for sku in ledger.skus():
        item = ledger.item(sku)
        rows.append({
            'sku': sku,
            'name': item.name,
            'on_hand': ledger.on_hand(sku),
            'reorder_level': item.reorder_level,
        })
    return rows


def needs_reorder(row):
    """True when the row's stock is at or below its reorder level."""
    return row['on_hand'] <= row['reorder_level']


def low_stock(ledger):
    """SKUs whose stock is at or below the reorder level, in SKU order."""
    return [row['sku'] for row in stock_rows(ledger) if needs_reorder(row)]


def render_table(ledger):
    """The stock rows as a plain text table. Items that need reordering end with LOW."""
    rows = stock_rows(ledger)
    widths = [max([len(heading)] + [len(str(row[key])) for row in rows]) for heading, key, _ in COLUMNS]

    def line(cells):
        parts = [format(str(cell), '%s%d' % (align, width))
                 for cell, width, (_, _, align) in zip(cells, widths, COLUMNS)]
        return '  '.join(parts)

    lines = [line([heading for heading, _, _ in COLUMNS]).rstrip()]
    for row in rows:
        text = line([row[key] for _, key, _ in COLUMNS])
        if needs_reorder(row):
            text += '  LOW'
        lines.append(text.rstrip())
    return '\n'.join(lines)
