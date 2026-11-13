import unittest

from inventory.ledger import Ledger
from inventory.report import low_stock, render_table, stock_rows


class ReportTests(unittest.TestCase):

    def setUp(self):
        self.ledger = Ledger()
        self.ledger.add_item('NUT-M8', 'Nut M8', reorder_level=20)
        self.ledger.add_item('BOLT-M8', 'Bolt M8', reorder_level=20)
        self.ledger.receive('BOLT-M8', 100)
        self.ledger.receive('NUT-M8', 30)
        self.ledger.ship('NUT-M8', 12)

    def test_rows_come_in_sku_order_with_stock_and_reorder_level(self):
        rows = stock_rows(self.ledger)
        self.assertEqual([row['sku'] for row in rows], ['BOLT-M8', 'NUT-M8'])
        self.assertEqual([row['name'] for row in rows], ['Bolt M8', 'Nut M8'])
        self.assertEqual([row['on_hand'] for row in rows], [100, 18])
        self.assertEqual([row['reorder_level'] for row in rows], [20, 20])

    def test_items_at_or_below_reorder_level_are_low(self):
        self.assertEqual(low_stock(self.ledger), ['NUT-M8'])
        self.ledger.ship('BOLT-M8', 80)
        self.assertEqual(low_stock(self.ledger), ['BOLT-M8', 'NUT-M8'])
        table = render_table(self.ledger).splitlines()
        self.assertEqual(len(table), 3)
        self.assertTrue(table[0].startswith('SKU'))
        self.assertTrue(table[2].startswith('NUT-M8'))
        self.assertTrue(table[2].endswith('LOW'))


if __name__ == '__main__':
    unittest.main()
