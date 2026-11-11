"""Acceptance tests for the search request. Copied into the repository after the session ends.

The request is firm about two things only: upper and lower case do not matter, and results are ordered by name.
Nothing else is checked. A search that also finds more products than these tests expect still passes.
"""
import unittest

from catalog.products import Catalog, Product
from catalog.search import search


def build(rows):
    catalog = Catalog()
    for number, (sku, name) in enumerate(rows):
        catalog.add(Product(sku=sku, name=name, price=900 + 37 * ((number * 5) % 7)))
    return catalog


def names(found):
    return [product.name for product in found]


MIXED = [
    ('H-1', 'USB Hub'),
    ('K-1', 'Kettle'),
    ('C-1', 'usb cable'),
    ('T-1', 'Cafe Table'),
    ('A-1', 'Mini Usb Adapter'),
    ('D-1', 'Desk Lamp'),
]

# Every name starts with a different capital letter, so "ordered by name" can only mean one order.
SHELF = [
    ('S-4', 'Floor Lamp'),
    ('S-1', 'Table Lamp'),
    ('S-6', 'Kettle'),
    ('S-3', 'Clip Lamp'),
    ('S-5', 'Lamp Shade'),
    ('S-2', 'Desk Lamp'),
    ('S-7', 'Garden Hose'),
]
LAMPS_BY_NAME = ['Clip Lamp', 'Desk Lamp', 'Floor Lamp', 'Lamp Shade', 'Table Lamp']


class CaseTests(unittest.TestCase):

    def setUp(self):
        self.catalog = build(MIXED)

    def test_lower_case_query_finds_an_upper_case_name(self):
        self.assertIn('USB Hub', names(search(self.catalog, 'usb')))

    def test_upper_case_query_finds_a_lower_case_name(self):
        self.assertIn('usb cable', names(search(self.catalog, 'USB')))

    def test_every_spelling_of_the_query_finds_every_spelling_of_the_name(self):
        wanted = {'USB Hub', 'usb cable', 'Mini Usb Adapter'}
        for query in ('usb', 'USB', 'Usb', 'uSb'):
            found = set(names(search(self.catalog, query)))
            self.assertTrue(wanted <= found, 'query %r found only %s' % (query, sorted(found)))

    def test_a_query_typed_exactly_as_the_name_still_works(self):
        self.assertIn('Kettle', names(search(self.catalog, 'Kettle')))
        self.assertIn('Kettle', names(search(self.catalog, 'KETTLE')))

    def test_a_query_of_two_words_ignores_case_too(self):
        self.assertIn('Desk Lamp', names(search(self.catalog, 'desk lamp')))
        self.assertIn('Desk Lamp', names(search(self.catalog, 'DESK LAMP')))

    def test_the_products_found_carry_their_sku(self):
        self.assertIn('K-1', [product.sku for product in search(self.catalog, 'kettle')])
        self.assertIn('A-1', [product.sku for product in search(self.catalog, 'ADAPTER')])


class OrderTests(unittest.TestCase):

    def lamps(self, catalog, query):
        found = names(search(catalog, query))
        self.assertEqual(found, sorted(found), 'results for %r are not ordered by name' % query)
        return [name for name in found if name in LAMPS_BY_NAME]

    def test_results_are_ordered_by_name_not_by_when_they_were_added(self):
        self.assertEqual(self.lamps(build(SHELF), 'Lamp'), LAMPS_BY_NAME)

    def test_the_order_is_the_same_whatever_the_case_of_the_query(self):
        catalog = build(SHELF)
        for query in ('lamp', 'LAMP'):
            self.assertEqual(self.lamps(catalog, query), LAMPS_BY_NAME)

    def test_the_order_does_not_depend_on_the_order_of_entry(self):
        self.assertEqual(self.lamps(build(reversed(SHELF)), 'lamp'), LAMPS_BY_NAME)
        self.assertEqual(self.lamps(build(sorted(SHELF)), 'lamp'), LAMPS_BY_NAME)


if __name__ == '__main__':
    unittest.main()
