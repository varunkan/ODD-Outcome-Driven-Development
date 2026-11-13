import unittest

from inventory.errors import InsufficientStock, UnknownSku
from inventory.ledger import Ledger, Movement


class LedgerTests(unittest.TestCase):

    def setUp(self):
        self.ledger = Ledger()
        self.ledger.add_item('BOLT-M8', 'Bolt M8', reorder_level=20)
        self.ledger.add_item('NUT-M8', 'Nut M8')

    def test_receiving_and_shipping_move_stock(self):
        self.ledger.receive('BOLT-M8', 100)
        self.ledger.ship('BOLT-M8', 40, note='order 17')
        self.assertEqual(self.ledger.on_hand('BOLT-M8'), 60)
        self.assertEqual(self.ledger.on_hand('NUT-M8'), 0)
        self.assertEqual(self.ledger.history('BOLT-M8'),
                         [Movement('receive', 'BOLT-M8', 100, ''), Movement('ship', 'BOLT-M8', 40, 'order 17')])

    def test_shipping_more_than_is_in_stock_is_refused(self):
        self.ledger.receive('BOLT-M8', 5)
        with self.assertRaises(InsufficientStock) as caught:
            self.ledger.ship('BOLT-M8', 6)
        self.assertEqual((caught.exception.sku, caught.exception.requested), ('BOLT-M8', 6))
        self.assertEqual(self.ledger.on_hand('BOLT-M8'), 5)
        self.ledger.ship('BOLT-M8', 5)
        self.assertEqual(self.ledger.on_hand('BOLT-M8'), 0)

    def test_bad_input_is_refused(self):
        with self.assertRaises(UnknownSku):
            self.ledger.receive('WASHER', 1)
        for bad in (0, -3, 1.5, '4'):
            with self.assertRaises(ValueError):
                self.ledger.receive('BOLT-M8', bad)
        with self.assertRaises(ValueError):
            self.ledger.add_item('BOLT-M8', 'Bolt again')

    def test_stock_count_records_the_difference(self):
        self.ledger.receive('NUT-M8', 30)
        self.assertEqual(self.ledger.adjust('NUT-M8', 27, note='count'), -3)
        self.assertEqual(self.ledger.adjust('NUT-M8', 27), 0)
        self.assertEqual(self.ledger.on_hand('NUT-M8'), 27)
        self.assertEqual(self.ledger.history('NUT-M8')[-1], Movement('adjust', 'NUT-M8', -3, 'count'))


if __name__ == '__main__':
    unittest.main()
