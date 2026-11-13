import unittest

from pricebook import Catalog, MemoryBackend


def stocked():
    backend = MemoryBackend()
    catalog = Catalog(backend)
    catalog.add('TEA-1', name='Green tea', category='drinks', price=450)
    catalog.add('TEA-2', name='Black tea', category='drinks', price=400)
    catalog.add('CUP-1', name='Mug', category='kitchen', price=900)
    return backend, catalog


def skus(records):
    return [record['sku'] for record in records]


def by_sku(records):
    return {record['sku']: record for record in records}


class ReportedCaseTest(unittest.TestCase):
    def test_get_shows_the_new_price(self):
        backend = MemoryBackend()
        catalog = Catalog(backend)
        catalog.add('TEA-1', name='Green tea', category='drinks', price=450)
        self.assertEqual(catalog.get('TEA-1')['price'], 450)
        catalog.update('TEA-1', price=500)
        self.assertEqual(catalog.get('TEA-1')['price'], 500)

    def test_update_before_anything_was_read(self):
        _, catalog = stocked()
        catalog.update('TEA-1', price=500)
        self.assertEqual(catalog.get('TEA-1')['price'], 500)
        self.assertEqual(by_sku(catalog.list_category('drinks'))['TEA-1']['price'], 500)

    def test_fields_that_were_not_updated_are_kept(self):
        _, catalog = stocked()
        catalog.get('TEA-1')
        catalog.update('TEA-1', price=500)
        self.assertEqual(catalog.get('TEA-1'),
                         {'sku': 'TEA-1', 'name': 'Green tea', 'category': 'drinks', 'price': 500})


class EveryReadMethodTest(unittest.TestCase):
    def test_get_many_shows_the_new_price(self):
        _, catalog = stocked()
        self.assertEqual(catalog.get_many(['TEA-1', 'TEA-2'])['TEA-1']['price'], 450)
        catalog.update('TEA-1', price=500)
        found = catalog.get_many(['TEA-1', 'TEA-2'])
        self.assertEqual(found['TEA-1']['price'], 500)
        self.assertEqual(found['TEA-2']['price'], 400)

    def test_listing_shows_the_new_price(self):
        _, catalog = stocked()
        self.assertEqual(by_sku(catalog.list_category('drinks'))['TEA-1']['price'], 450)
        catalog.update('TEA-1', price=500)
        listing = by_sku(catalog.list_category('drinks'))
        self.assertEqual(listing['TEA-1']['price'], 500)
        self.assertEqual(listing['TEA-2']['price'], 400)

    def test_listing_shows_the_new_name(self):
        _, catalog = stocked()
        catalog.list_category('drinks')
        catalog.update('TEA-2', name='Breakfast tea')
        self.assertEqual(by_sku(catalog.list_category('drinks'))['TEA-2']['name'], 'Breakfast tea')
        self.assertEqual(catalog.get('TEA-2')['name'], 'Breakfast tea')

    def test_get_shows_the_new_name_after_listing_and_get_were_both_read(self):
        _, catalog = stocked()
        catalog.get('CUP-1')
        catalog.list_category('kitchen')
        catalog.get_many(['CUP-1'])
        catalog.update('CUP-1', name='Large mug', price=1100)
        expected = {'sku': 'CUP-1', 'name': 'Large mug', 'category': 'kitchen', 'price': 1100}
        self.assertEqual(catalog.get('CUP-1'), expected)
        self.assertEqual(catalog.get_many(['CUP-1']), {'CUP-1': expected})
        self.assertEqual(catalog.list_category('kitchen'), [expected])


class MoveToAnotherCategoryTest(unittest.TestCase):
    def test_product_leaves_the_listing_it_was_in(self):
        _, catalog = stocked()
        self.assertEqual(skus(catalog.list_category('drinks')), ['TEA-1', 'TEA-2'])
        catalog.update('TEA-1', category='kitchen')
        self.assertEqual(skus(catalog.list_category('drinks')), ['TEA-2'])

    def test_product_joins_the_listing_it_moved_to(self):
        _, catalog = stocked()
        self.assertEqual(skus(catalog.list_category('kitchen')), ['CUP-1'])
        catalog.update('TEA-1', category='kitchen')
        self.assertEqual(skus(catalog.list_category('kitchen')), ['CUP-1', 'TEA-1'])

    def test_both_listings_and_the_record_agree_after_a_move(self):
        _, catalog = stocked()
        catalog.get('TEA-1')
        catalog.list_category('drinks')
        catalog.list_category('kitchen')
        catalog.update('TEA-1', category='kitchen', price=475)
        self.assertEqual(catalog.get('TEA-1')['category'], 'kitchen')
        self.assertEqual(skus(catalog.list_category('drinks')), ['TEA-2'])
        moved = by_sku(catalog.list_category('kitchen'))['TEA-1']
        self.assertEqual(moved, {'sku': 'TEA-1', 'name': 'Green tea', 'category': 'kitchen', 'price': 475})

    def test_move_into_a_category_that_was_listed_while_empty(self):
        _, catalog = stocked()
        self.assertEqual(catalog.list_category('gifts'), [])
        catalog.update('CUP-1', category='gifts')
        self.assertEqual(skus(catalog.list_category('gifts')), ['CUP-1'])
        self.assertEqual(catalog.list_category('kitchen'), [])


class SeveralUpdatesTest(unittest.TestCase):
    def test_every_update_is_seen_by_every_read(self):
        _, catalog = stocked()
        for price in (460, 470, 480):
            catalog.update('TEA-1', price=price)
            with self.subTest(price=price):
                self.assertEqual(catalog.get('TEA-1')['price'], price)
                self.assertEqual(catalog.get_many(['TEA-1'])['TEA-1']['price'], price)
                self.assertEqual(by_sku(catalog.list_category('drinks'))['TEA-1']['price'], price)

    def test_update_and_update_back(self):
        _, catalog = stocked()
        catalog.list_category('drinks')
        catalog.update('TEA-1', category='kitchen')
        catalog.list_category('drinks')
        catalog.list_category('kitchen')
        catalog.update('TEA-1', category='drinks')
        self.assertEqual(skus(catalog.list_category('drinks')), ['TEA-1', 'TEA-2'])
        self.assertEqual(skus(catalog.list_category('kitchen')), ['CUP-1'])
        self.assertEqual(catalog.get('TEA-1')['category'], 'drinks')


class StillCachedTest(unittest.TestCase):
    def read_everything(self, catalog):
        return (catalog.get('TEA-1'), catalog.get_many(['TEA-1', 'TEA-2']), catalog.list_category('drinks'))

    def test_repeated_reads_cost_no_backend_read(self):
        backend, catalog = stocked()
        first = self.read_everything(catalog)
        before = backend.reads
        self.assertEqual(self.read_everything(catalog), first)
        self.assertEqual(self.read_everything(catalog), first)
        self.assertEqual(backend.reads, before)

    def test_reads_after_an_update_are_cached_again(self):
        backend, catalog = stocked()
        self.read_everything(catalog)
        catalog.update('TEA-1', price=500)
        first = self.read_everything(catalog)
        self.assertEqual(first[0]['price'], 500)
        before = backend.reads
        self.assertEqual(self.read_everything(catalog), first)
        self.assertEqual(backend.reads, before)


if __name__ == '__main__':
    unittest.main()
