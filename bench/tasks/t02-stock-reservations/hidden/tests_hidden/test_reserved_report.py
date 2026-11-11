"""Acceptance tests for reservations in the stock report. Copied into the repository after the session ends."""
import re
import unittest

from inventory.ledger import Ledger
from inventory.report import low_stock, render_table, stock_rows


def stocked():
    ledger = Ledger()
    ledger.add_item('BOLT', 'Bolt', reorder_level=3)
    ledger.add_item('NUT', 'Nut', reorder_level=0)
    ledger.receive('BOLT', 10)
    ledger.receive('NUT', 4)
    return ledger


def rows_by_sku(ledger):
    return {row['sku']: row for row in stock_rows(ledger)}


class RowsTests(unittest.TestCase):

    def test_rows_without_reservations(self):
        rows = rows_by_sku(stocked())
        self.assertEqual((rows['BOLT']['on_hand'], rows['BOLT']['reserved'], rows['BOLT']['available']), (10, 0, 10))
        self.assertEqual((rows['NUT']['on_hand'], rows['NUT']['reserved'], rows['NUT']['available']), (4, 0, 4))

    def test_rows_add_up_what_every_order_holds(self):
        ledger = stocked()
        ledger.reserve('BOLT', 4, 'SO-1')
        ledger.reserve('BOLT', 2, 'SO-2')
        rows = rows_by_sku(ledger)
        self.assertEqual((rows['BOLT']['on_hand'], rows['BOLT']['reserved'], rows['BOLT']['available']), (10, 6, 4))
        self.assertEqual((rows['NUT']['on_hand'], rows['NUT']['reserved'], rows['NUT']['available']), (4, 0, 4))
        ledger.release('SO-1')
        rows = rows_by_sku(ledger)
        self.assertEqual((rows['BOLT']['on_hand'], rows['BOLT']['reserved'], rows['BOLT']['available']), (10, 2, 8))


class LowStockTests(unittest.TestCase):

    def test_low_stock_goes_by_available(self):
        ledger = stocked()
        self.assertEqual(list(low_stock(ledger)), [])
        ledger.reserve('BOLT', 6, 'SO-1')
        self.assertEqual(list(low_stock(ledger)), [])
        ledger.reserve('BOLT', 1, 'SO-2')
        self.assertEqual(list(low_stock(ledger)), ['BOLT'])
        ledger.reserve('NUT', 4, 'SO-2')
        self.assertEqual(sorted(low_stock(ledger)), ['BOLT', 'NUT'])
        ledger.release('SO-2')
        self.assertEqual(list(low_stock(ledger)), [])


class TableTests(unittest.TestCase):

    def setUp(self):
        ledger = stocked()
        ledger.reserve('BOLT', 4, 'SO-1')
        self.lines = render_table(ledger).splitlines()

    def test_new_columns_sit_between_on_hand_and_reorder_at(self):
        headings = [line for line in self.lines if 'Reserved' in line]
        self.assertEqual(len(headings), 1)
        heading = headings[0]
        for title in ('On hand', 'Reserved', 'Available', 'Reorder at'):
            self.assertIn(title, heading)
        self.assertLess(heading.index('On hand'), heading.index('Reserved'))
        self.assertLess(heading.index('Reserved'), heading.index('Available'))
        self.assertLess(heading.index('Available'), heading.index('Reorder at'))

    def test_each_item_line_shows_its_numbers_in_column_order(self):
        def numbers(sku):
            found = [line for line in self.lines if re.search(r'\b%s\b' % sku, line)]
            self.assertEqual(len(found), 1)
            return re.findall(r'\d+', found[0])

        self.assertEqual(numbers('BOLT'), ['10', '4', '6', '3'])
        self.assertEqual(numbers('NUT'), ['4', '0', '4', '0'])


if __name__ == '__main__':
    unittest.main()
