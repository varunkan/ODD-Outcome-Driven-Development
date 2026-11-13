# Old values are still served after an update

We put `pricebook.Catalog` in front of our product database because the database is slow. Last week we raised the
price of an item and the tills went on showing the old price for about five minutes, until the cached entry
expired. We use `update` for price changes, for renames and for moving a product to another category, and each of
them has the same problem.

The smallest case:

```python
>>> from pricebook import Catalog, MemoryBackend
>>> backend = MemoryBackend()
>>> catalog = Catalog(backend)
>>> catalog.add('TEA-1', name='Green tea', category='drinks', price=450)
>>> catalog.get('TEA-1')['price']
450
>>> catalog.update('TEA-1', price=500)
>>> catalog.get('TEA-1')['price']
450
```

Expected: the last line shows `500`.

What we need:

1. Once `Catalog.update(sku, **fields)` has returned, the catalog never serves the old value again. This holds for
   every way of reading: `get(sku)`, `get_many(skus)` and `list_category(category)`. It holds for every field
   `update` can change: `name`, `category` and `price`. It holds whatever was read before the update.
2. The cache stays. The database is slow, so reading the same thing again, with nothing written in between, must
   not go back to the backend: `backend.reads` on the `MemoryBackend` must not go up. Switching the cache off, or
   making entries expire sooner, is not a fix.

The interface stays as it is:

- `pricebook.MemoryBackend()`, with the counter `backend.reads`
- `pricebook.Catalog(backend)`
- `catalog.add(sku, name, category, price)`
- `catalog.update(sku, **fields)`
- `catalog.get(sku)` returns the record, a dictionary with the keys `sku`, `name`, `category` and `price`
- `catalog.get_many(skus)` returns `{sku: record}`
- `catalog.list_category(category)` returns the records of that category as a list, ordered by sku
