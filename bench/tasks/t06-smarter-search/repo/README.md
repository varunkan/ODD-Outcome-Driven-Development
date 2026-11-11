# catalog

The product catalog behind a small shop's stock tool: the products, the stock-list file they are kept in, and ways to
find things. Python 3, standard library only.

## What is in it

`catalog.products`: what we sell.

- `Product(sku, name, price, tags=())`: `price` is in whole cents; tags are kept in lower case.
- `Catalog()`: `add(product)`, `get(sku)`, `remove(sku)`, `products()` (in the order they were added), `len(catalog)`
  and `sku in catalog`.

`catalog.search`: finding things.

- `search(catalog, query)`: products whose name contains the query, in the order they were added. A blank query
  finds nothing.
- `by_tag(catalog, tag)`: products carrying a tag.
- `in_price_range(catalog, low, high)`: products priced from `low` to `high` cents, cheapest first.
- `tags_in_use(catalog)`: every tag with the number of products carrying it.

`catalog.loader`: the stock list, one product per line.

- `load_lines(lines)` builds a `Catalog` from lines such as `L-1 | Desk Lamp | 19.99 | lighting, office`.
- `dump_lines(catalog)` writes them back.
- `parse_price("19.99")` gives `1999`; `format_price(1999)` gives `"19.99"`.

## Example

```python
from catalog.loader import load_lines
from catalog.search import by_tag, search

catalog = load_lines([
    "L-1 | Desk Lamp | 19.99 | lighting, office",
    "K-1 | Kettle    | 25.00 | kitchen",
])
[product.sku for product in search(catalog, "Lamp")]      # ["L-1"]
[product.name for product in by_tag(catalog, "kitchen")]  # ["Kettle"]
```

## Tests

```
python3 -m unittest
```
