import unittest

from catalog.loader import dump_lines, format_price, load_lines, parse_price
from catalog.products import Catalog, Product


class CatalogTests(unittest.TestCase):

    def test_products_are_added_fetched_and_removed(self):
        catalog = Catalog()
        lamp = catalog.add(Product('L-1', 'Desk Lamp', 1999, tags=('Lighting', 'office')))
        catalog.add(Product('K-1', 'Kettle', 2500))
        self.assertEqual(catalog.get('L-1'), lamp)
        self.assertEqual(lamp.tags, ('lighting', 'office'))
        self.assertEqual([product.sku for product in catalog.products()], ['L-1', 'K-1'])
        self.assertIn('K-1', catalog)
        self.assertEqual(catalog.remove('K-1').name, 'Kettle')
        self.assertEqual(len(catalog), 1)
        with self.assertRaises(KeyError):
            catalog.get('K-1')

    def test_duplicate_skus_and_bad_products_are_refused(self):
        catalog = Catalog()
        catalog.add(Product('L-1', 'Desk Lamp', 1999))
        with self.assertRaises(ValueError):
            catalog.add(Product('L-1', 'Another Lamp', 2100))
        for sku, name, price in (('', 'Desk Lamp', 1999), ('L-2', ' ', 1999), ('L-2', 'Desk Lamp', -1),
                                 ('L-2', 'Desk Lamp', 19.99)):
            with self.assertRaises(ValueError):
                Product(sku, name, price)


class LoaderTests(unittest.TestCase):

    def test_prices_convert_both_ways(self):
        self.assertEqual(parse_price('19.99'), 1999)
        self.assertEqual(parse_price('12'), 1200)
        self.assertEqual(parse_price('12.5'), 1250)
        self.assertEqual(format_price(1250), '12.50')
        self.assertEqual(format_price(5), '0.05')
        for bad in ('', 'free', '12.', '1.999', '-3'):
            with self.assertRaises(ValueError):
                parse_price(bad)

    def test_a_stock_list_is_read_and_written_back(self):
        lines = ['# lighting', 'L-1 | Desk Lamp | 19.99 | lighting, office', '', 'K-1 | Kettle | 25.00']
        catalog = load_lines(lines)
        self.assertEqual(catalog.get('L-1'), Product('L-1', 'Desk Lamp', 1999, ('lighting', 'office')))
        self.assertEqual(dump_lines(catalog), ['L-1 | Desk Lamp | 19.99 | lighting, office', 'K-1 | Kettle | 25.00'])
        with self.assertRaises(ValueError):
            load_lines(['L-1 | Desk Lamp'])


if __name__ == '__main__':
    unittest.main()
