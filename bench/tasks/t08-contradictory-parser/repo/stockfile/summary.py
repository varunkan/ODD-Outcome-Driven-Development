"""Figures worked out from the rows of a stock file."""


def total_by_sku(rows):
    """{sku: summed quantity} for rows of (sku, quantity). A SKU that appears twice is added up."""
    totals = {}
    for sku, quantity in rows:
        totals[sku] = totals.get(sku, 0) + quantity
    return totals


def largest(rows, count=3):
    """The `count` SKUs with the highest total, as (sku, total), highest first. Ties are ordered by SKU."""
    if count < 0:
        raise ValueError('count must be zero or more')
    ranked = sorted(total_by_sku(rows).items(), key=lambda item: (-item[1], item[0]))
    return ranked[:count]
