import unittest

from pricebook import Catalog, MemoryBackend


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def stocked(**options):
    backend = MemoryBackend()
    catalog = Catalog(backend, **options)
    catalog.add('TEA-1', name='Green tea', category='drinks', price=450)
    catalog.add('TEA-2', name='Black tea', category='drinks', price=400)
    catalog.add('CUP-1', name='Mug', category='kitchen', price=900)
    return backend, catalog


class ReadThroughTest(unittest.TestCase):
    def test_second_get_costs_no_query(self):
        backend, catalog = stocked()
        before = backend.reads
        first = catalog.get('TEA-1')
        second = catalog.get('TEA-1')
        self.assertEqual(first, {'sku': 'TEA-1', 'name': 'Green tea', 'category': 'drinks', 'price': 450})
        self.assertEqual(second, first)
        self.assertEqual(backend.reads, before + 1)

    def test_unknown_sku(self):
        _, catalog = stocked()
        with self.assertRaises(KeyError):
            catalog.get('NOPE')

    def test_get_many_loads_only_what_is_not_cached(self):
        backend, catalog = stocked()
        catalog.get('TEA-1')
        before = backend.reads
        found = catalog.get_many(['TEA-1', 'TEA-2', 'NOPE'])
        self.assertEqual(sorted(found), ['TEA-1', 'TEA-2'])
        self.assertEqual(found['TEA-2']['price'], 400)
        self.assertEqual(backend.reads, before + 1)

    def test_listing_is_ordered_and_cached(self):
        backend, catalog = stocked()
        before = backend.reads
        listing = catalog.list_category('drinks')
        self.assertEqual([record['sku'] for record in listing], ['TEA-1', 'TEA-2'])
        self.assertEqual(catalog.list_category('drinks'), listing)
        self.assertEqual(backend.reads, before + 1)
        self.assertEqual(catalog.list_category('garden'), [])

    def test_entries_expire(self):
        clock = FakeClock()
        backend, catalog = stocked(ttl=60, clock=clock)
        catalog.get('TEA-1')
        before = backend.reads
        clock.now += 61
        catalog.get('TEA-1')
        self.assertEqual(backend.reads, before + 1)

    def test_flush_forgets_everything(self):
        backend, catalog = stocked()
        catalog.get('TEA-1')
        catalog.list_category('drinks')
        before = backend.reads
        catalog.flush()
        catalog.get('TEA-1')
        catalog.list_category('drinks')
        self.assertEqual(backend.reads, before + 2)


class WritingTest(unittest.TestCase):
    def test_added_product_shows_in_its_listing(self):
        _, catalog = stocked()
        catalog.list_category('drinks')
        catalog.add('TEA-3', name='Mint tea', category='drinks', price=420)
        self.assertEqual([record['sku'] for record in catalog.list_category('drinks')], ['TEA-1', 'TEA-2', 'TEA-3'])

    def test_add_rejects_a_taken_sku_and_bad_values(self):
        _, catalog = stocked()
        with self.assertRaises(ValueError):
            catalog.add('TEA-1', name='Other tea', category='drinks', price=100)
        with self.assertRaises(ValueError):
            catalog.add('TEA-9', name='Free tea', category='drinks', price=-1)

    def test_update_is_stored_in_the_backend(self):
        backend, catalog = stocked()
        returned = catalog.update('TEA-1', price=500, name='Green tea 100g')
        stored = backend.load('TEA-1')
        self.assertEqual(stored, {'sku': 'TEA-1', 'name': 'Green tea 100g', 'category': 'drinks', 'price': 500})
        self.assertEqual(returned, stored)

    def test_update_rejects_unknown_sku_and_field(self):
        _, catalog = stocked()
        with self.assertRaises(KeyError):
            catalog.update('NOPE', price=1)
        with self.assertRaises(ValueError):
            catalog.update('TEA-1', colour='green')
        with self.assertRaises(ValueError):
            catalog.update('TEA-1', price='cheap')


if __name__ == '__main__':
    unittest.main()
