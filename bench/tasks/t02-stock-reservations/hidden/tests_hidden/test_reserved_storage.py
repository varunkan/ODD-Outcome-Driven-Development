"""Acceptance tests for reservations in saved ledgers. Copied into the repository after the session ends."""
import os
import tempfile
import unittest

from inventory import storage
from inventory.errors import InsufficientStock
from inventory.ledger import Ledger

# A file exactly as the package wrote it before reservations existed.
OLD_FILE = '''{
  "history": [
    {
      "kind": "receive",
      "note": "",
      "quantity": 12,
      "sku": "BOLT"
    },
    {
      "kind": "ship",
      "note": "order 17",
      "quantity": 3,
      "sku": "BOLT"
    },
    {
      "kind": "receive",
      "note": "",
      "quantity": 4,
      "sku": "NUT"
    }
  ],
  "items": [
    {
      "name": "Bolt",
      "on_hand": 9,
      "reorder_level": 3,
      "sku": "BOLT"
    },
    {
      "name": "Nut",
      "on_hand": 4,
      "reorder_level": 0,
      "sku": "NUT"
    }
  ],
  "version": 1
}
'''


class StorageTests(unittest.TestCase):

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = os.path.join(folder.name, 'stock.json')

    def test_reservations_survive_save_and_read(self):
        ledger = Ledger()
        ledger.add_item('BOLT', 'Bolt', reorder_level=3)
        ledger.add_item('NUT', 'Nut', reorder_level=0)
        ledger.receive('BOLT', 10)
        ledger.receive('NUT', 4)
        ledger.reserve('BOLT', 4, 'SO-1')
        ledger.reserve('NUT', 1, 'SO-1')
        ledger.reserve('BOLT', 2, 'SO-2')
        storage.save(ledger, self.path)

        copy = storage.read(self.path)
        self.assertEqual((copy.on_hand('BOLT'), copy.on_hand('NUT')), (10, 4))
        self.assertEqual((copy.available('BOLT'), copy.available('NUT')), (4, 3))
        with self.assertRaises(InsufficientStock):
            copy.reserve('BOLT', 5, 'SO-3')
        with self.assertRaises(InsufficientStock):
            copy.ship('BOLT', 5)
        self.assertEqual(copy.release('SO-2'), 2)
        self.assertEqual(copy.available('BOLT'), 6)
        self.assertEqual(copy.release('SO-1'), 5)
        self.assertEqual((copy.available('BOLT'), copy.available('NUT')), (10, 4))

    def test_ledger_without_reservations_reads_back_with_nothing_reserved(self):
        ledger = Ledger()
        ledger.add_item('BOLT', 'Bolt', reorder_level=3)
        ledger.receive('BOLT', 10)
        ledger.reserve('BOLT', 4, 'SO-1')
        ledger.release('SO-1')
        storage.save(ledger, self.path)

        copy = storage.read(self.path)
        self.assertEqual(copy.available('BOLT'), 10)
        self.assertEqual(copy.release('SO-1'), 0)

    def test_file_saved_before_reservations_still_opens(self):
        with open(self.path, 'w', encoding='utf-8') as handle:
            handle.write(OLD_FILE)

        ledger = storage.read(self.path)
        self.assertEqual((ledger.on_hand('BOLT'), ledger.on_hand('NUT')), (9, 4))
        self.assertEqual((ledger.available('BOLT'), ledger.available('NUT')), (9, 4))
        self.assertEqual(ledger.release('SO-1'), 0)
        ledger.reserve('BOLT', 9, 'SO-1')
        self.assertEqual(ledger.available('BOLT'), 0)
        with self.assertRaises(InsufficientStock):
            ledger.ship('BOLT', 1)


if __name__ == '__main__':
    unittest.main()
