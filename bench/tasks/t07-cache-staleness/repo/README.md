# pricebook

A product catalog with a read-through cache. The backend that holds the records is slow, so the catalog keeps what
it has read and answers from memory until the entry expires. Python 3 standard library only.

```python
from pricebook import Catalog, MemoryBackend

backend = MemoryBackend()
catalog = Catalog(backend)
catalog.add('TEA-1', name='Green tea', category='drinks', price=450)
catalog.add('TEA-2', name='Black tea', category='drinks', price=400)

catalog.get('TEA-1')
# {'sku': 'TEA-1', 'name': 'Green tea', 'category': 'drinks', 'price': 450}
catalog.get_many(['TEA-1', 'TEA-2', 'NOPE'])
# {'TEA-1': {...}, 'TEA-2': {...}}
[record['sku'] for record in catalog.list_category('drinks')]
# ['TEA-1', 'TEA-2']
```

## What is in it

- `MemoryBackend()`: the source of truth. `exists`, `load`, `load_many`, `find_by_category` and `save` each stand
  for one query; `backend.reads` and `backend.writes` count them.
- `Catalog(backend, ttl=300.0, clock=time.monotonic)`: the cached front. A record is a dictionary with the keys
  `sku`, `name`, `category` and `price` (whole cents).
  - `get(sku)`: one record; `KeyError` when there is none.
  - `get_many(skus)`: `{sku: record}`; skus that do not exist are left out.
  - `list_category(category)`: the records in a category, ordered by sku.
  - `add(sku, name, category, price)`: a new product; `ValueError` when the sku is taken.
  - `update(sku, **fields)`: change `name`, `category` or `price`.
  - `flush()`: forget everything cached.
- `TTLCache(ttl=300.0, clock=time.monotonic)`: the cache underneath: `get`, `put`, `discard`, `clear`.

## Caching

The first read of a record or of a category listing goes to the backend. Later reads of the same thing are answered
from memory for `ttl` seconds and cost no query. Records handed out are copies.

## Tests

```
python3 -m unittest discover -s tests
```
