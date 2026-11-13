import unittest

from catalog.products import Catalog, Product
from catalog.search import by_tag, in_price_range, search, tags_in_use


class SearchTests(unittest.TestCase):

    def setUp(self):
        self.catalog = Catalog()
        self.catalog.add(Product('L-1', 'Desk Lamp', 1999, tags=('lighting', 'office')))
        self.catalog.add(Product('K-1', 'Kettle', 2500, tags=('kitchen',)))
        self.catalog.add(Product('C-1', 'Office Chair', 8900, tags=('office', 'furniture')))
        self.catalog.add(Product('M-1', 'Coffee Mug', 650, tags=('kitchen',)))

    def test_search_finds_a_product_by_part_of_its_name(self):
        self.assertEqual([product.sku for product in search(self.catalog, 'Lamp')], ['L-1'])
        self.assertEqual([product.sku for product in search(self.catalog, 'Coffee')], ['M-1'])
        self.assertEqual(search(self.catalog, 'Blender'), [])

    def test_products_are_found_by_tag(self):
        self.assertEqual([product.sku for product in by_tag(self.catalog, 'Office')], ['L-1', 'C-1'])
        self.assertEqual(by_tag(self.catalog, 'garden'), [])
        self.assertEqual(tags_in_use(self.catalog), {'lighting': 1, 'office': 2, 'kitchen': 2, 'furniture': 1})

    def test_products_are_found_by_price(self):
        self.assertEqual([product.sku for product in in_price_range(self.catalog, 600, 2500)], ['M-1', 'L-1', 'K-1'])
        self.assertEqual(in_price_range(self.catalog, 0, 100), [])
        with self.assertRaises(ValueError):
            in_price_range(self.catalog, 500, 100)


if __name__ == '__main__':
    unittest.main()
