"""Acceptance tests for stock reservations on the ledger. Copied into the repository after the session ends."""
import unittest

from inventory.errors import InsufficientStock, UnknownSku
from inventory.ledger import Ledger


def stocked():
    ledger = Ledger()
    ledger.add_item('BOLT', 'Bolt', reorder_level=3)
    ledger.add_item('NUT', 'Nut', reorder_level=0)
    ledger.receive('BOLT', 10)
    ledger.receive('NUT', 4)
    return ledger


class ReserveTests(unittest.TestCase):

    def setUp(self):
        self.ledger = stocked()

    def test_reserving_lowers_available_and_leaves_on_hand(self):
        self.assertEqual(self.ledger.available('BOLT'), 10)
        self.ledger.reserve('BOLT', 4, 'SO-1')
        self.assertEqual(self.ledger.available('BOLT'), 6)
        self.assertEqual(self.ledger.on_hand('BOLT'), 10)
        self.assertEqual(self.ledger.available('NUT'), 4)

    def test_everything_available_can_be_reserved_and_not_one_more(self):
        self.ledger.reserve('BOLT', 10, 'SO-1')
        self.assertEqual(self.ledger.available('BOLT'), 0)
        with self.assertRaises(InsufficientStock):
            self.ledger.reserve('BOLT', 1, 'SO-2')
        self.assertEqual(self.ledger.available('BOLT'), 0)

    def test_refused_reservation_holds_nothing(self):
        self.ledger.reserve('BOLT', 6, 'SO-1')
        with self.assertRaises(InsufficientStock):
            self.ledger.reserve('BOLT', 5, 'SO-2')
        self.assertEqual(self.ledger.available('BOLT'), 4)
        self.assertEqual(self.ledger.release('SO-2'), 0)
        with self.assertRaises(InsufficientStock):
            self.ledger.reserve('BOLT', 5, 'SO-1')
        self.assertEqual(self.ledger.available('BOLT'), 4)
        self.assertEqual(self.ledger.release('SO-1'), 6)

    def test_reserving_again_for_the_same_order_adds_up(self):
        self.ledger.reserve('BOLT', 3, 'SO-1')
        self.ledger.reserve('BOLT', 2, 'SO-1')
        self.assertEqual(self.ledger.available('BOLT'), 5)
        self.assertEqual(self.ledger.release('SO-1'), 5)
        self.assertEqual(self.ledger.available('BOLT'), 10)

    def test_quantity_must_be_a_positive_whole_number(self):
        for bad in (0, -1, 2.5):
            with self.assertRaises(ValueError):
                self.ledger.reserve('BOLT', bad, 'SO-1')
        self.assertEqual(self.ledger.available('BOLT'), 10)
        self.assertEqual(self.ledger.release('SO-1'), 0)

    def test_unknown_sku_is_refused(self):
        with self.assertRaises(UnknownSku):
            self.ledger.reserve('WASHER', 1, 'SO-1')
        with self.assertRaises(UnknownSku):
            self.ledger.available('WASHER')


class ReleaseTests(unittest.TestCase):

    def setUp(self):
        self.ledger = stocked()

    def test_release_frees_only_that_order(self):
        self.ledger.reserve('BOLT', 3, 'SO-1')
        self.ledger.reserve('BOLT', 2, 'SO-2')
        self.assertEqual(self.ledger.available('BOLT'), 5)
        self.assertEqual(self.ledger.release('SO-1'), 3)
        self.assertEqual(self.ledger.available('BOLT'), 8)
        self.assertEqual(self.ledger.release('SO-2'), 2)
        self.assertEqual(self.ledger.available('BOLT'), 10)

    def test_release_covers_every_sku_the_order_holds(self):
        self.ledger.reserve('BOLT', 3, 'SO-1')
        self.ledger.reserve('NUT', 4, 'SO-1')
        self.assertEqual(self.ledger.available('NUT'), 0)
        self.assertEqual(self.ledger.release('SO-1'), 7)
        self.assertEqual(self.ledger.available('BOLT'), 10)
        self.assertEqual(self.ledger.available('NUT'), 4)

    def test_releasing_an_order_that_holds_nothing_returns_zero(self):
        self.assertEqual(self.ledger.release('SO-404'), 0)
        self.ledger.reserve('BOLT', 3, 'SO-1')
        self.assertEqual(self.ledger.release('SO-404'), 0)
        self.assertEqual(self.ledger.release('SO-1'), 3)
        self.assertEqual(self.ledger.release('SO-1'), 0)
        self.assertEqual(self.ledger.available('BOLT'), 10)
        self.assertEqual(self.ledger.on_hand('BOLT'), 10)


class ShipTests(unittest.TestCase):

    def setUp(self):
        self.ledger = stocked()
        self.ledger.reserve('BOLT', 7, 'SO-1')

    def test_ship_cannot_take_reserved_stock(self):
        with self.assertRaises(InsufficientStock):
            self.ledger.ship('BOLT', 4)
        self.assertEqual(self.ledger.on_hand('BOLT'), 10)
        self.assertEqual(self.ledger.available('BOLT'), 3)

    def test_ship_can_take_exactly_what_is_available(self):
        self.ledger.ship('BOLT', 3)
        self.assertEqual(self.ledger.on_hand('BOLT'), 7)
        self.assertEqual(self.ledger.available('BOLT'), 0)
        with self.assertRaises(InsufficientStock):
            self.ledger.ship('BOLT', 1)
        self.assertEqual(self.ledger.release('SO-1'), 7)

    def test_a_released_order_can_be_shipped(self):
        self.assertEqual(self.ledger.release('SO-1'), 7)
        self.ledger.ship('BOLT', 7)
        self.assertEqual(self.ledger.on_hand('BOLT'), 3)
        self.assertEqual(self.ledger.available('BOLT'), 3)

    def test_received_stock_is_available(self):
        self.ledger.reserve('BOLT', 3, 'SO-2')
        self.assertEqual(self.ledger.available('BOLT'), 0)
        self.ledger.receive('BOLT', 5)
        self.assertEqual(self.ledger.on_hand('BOLT'), 15)
        self.assertEqual(self.ledger.available('BOLT'), 5)


if __name__ == '__main__':
    unittest.main()
