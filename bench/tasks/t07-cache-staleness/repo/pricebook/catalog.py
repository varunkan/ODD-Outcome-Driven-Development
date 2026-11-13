"""The catalog: every read goes through a cache, and only a miss reaches the backend."""
import time

from .cache import TTLCache

EDITABLE = ('name', 'category', 'price')


def _checked(record):
    for field in ('sku', 'name', 'category'):
        value = record[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError('%s must be a non-empty string' % field)
    price = record['price']
    if isinstance(price, bool) or not isinstance(price, int) or price < 0:
        raise ValueError('price must be a whole number of cents, zero or more')
    return record


class Catalog:
    """Products read through a cache.

    A record is a dictionary with the keys sku, name, category and price (whole cents). Every record handed out is
    a copy: changing it changes nothing in the catalog.
    """

    def __init__(self, backend, ttl=300.0, clock=time.monotonic):
        self._backend = backend
        self._items = TTLCache(ttl, clock)        # sku -> record
        self._listings = TTLCache(ttl, clock)     # category -> records ordered by sku

    # reading

    def get(self, sku):
        """The record with this sku. Raises KeyError when there is none."""
        record = self._items.get(sku)
        if record is None:
            record = self._backend.load(sku)
            self._items.put(sku, record)
        return dict(record)

    def get_many(self, skus):
        """{sku: record} for the given skus. Skus that do not exist are left out."""
        found = {}
        to_load = []
        for sku in skus:
            record = self._items.get(sku)
            if record is None:
                to_load.append(sku)
            else:
                found[sku] = dict(record)
        if to_load:
            for sku, record in self._backend.load_many(to_load).items():
                self._items.put(sku, record)
                found[sku] = dict(record)
        return found

    def list_category(self, category):
        """The records in the category, ordered by sku. An unknown category is an empty list."""
        records = self._listings.get(category)
        if records is None:
            records = sorted(self._backend.find_by_category(category), key=lambda record: record['sku'])
            self._listings.put(category, records)
        return [dict(record) for record in records]

    # writing

    def add(self, sku, name, category, price):
        """Store a new product and return its record. Raises ValueError when the sku is already taken."""
        record = _checked({'sku': sku, 'name': name, 'category': category, 'price': price})
        if self._backend.exists(sku):
            raise ValueError('sku already exists: %r' % (sku,))
        self._backend.save(record)
        self._listings.discard(category)
        return dict(record)

    def update(self, sku, **fields):
        """Change name, category or price of a product and return the new record.

        Raises KeyError when the sku does not exist and ValueError for a field that cannot be changed.
        """
        unknown = sorted(set(fields) - set(EDITABLE))
        if unknown:
            raise ValueError('cannot update %s' % ', '.join(unknown))
        record = self._backend.load(sku)
        record.update(fields)
        _checked(record)
        self._backend.save(record)
        return dict(record)

    def flush(self):
        """Forget everything cached. The next reads go to the backend."""
        self._items.clear()
        self._listings.clear()
