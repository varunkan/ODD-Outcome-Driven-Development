# stockfile

Reads the stock files our suppliers send: plain text, one `SKU;quantity` row per line. Python 3 standard library
only.

```python
from stockfile import read_rows, total_by_sku, largest

rows = read_rows([
    '# count of 3 March',
    'PAL-7;1,250',
    'BOX-2; 40',
    '',
    'PAL-7;250',
])
# [('PAL-7', 1250), ('BOX-2', 40), ('PAL-7', 250)]

total_by_sku(rows)     # {'PAL-7': 1500, 'BOX-2': 40}
largest(rows, 1)       # [('PAL-7', 1500)]
```

## What is in it

- `parse_quantity(text)`: the whole number written in `text`. A leading sign, thousands commas and surrounding
  spaces are allowed. `ValueError` when there is no number.
- `format_quantity(quantity)`: the other direction, with thousands commas: `1250` gives `'1,250'`.
- `parse_row(line)`: `(sku, quantity)` for one `SKU;quantity` row.
- `read_rows(lines)`: every row of a file; blank lines and lines starting with `#` are skipped; a bad row raises
  `ValueError` with its line number.
- `total_by_sku(rows)` and `largest(rows, count=3)`: totals per SKU, and the SKUs with the highest totals.

## Tests

```
python3 -m unittest discover -s tests
```
