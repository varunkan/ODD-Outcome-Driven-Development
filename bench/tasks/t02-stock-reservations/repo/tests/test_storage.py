import os
import tempfile
import unittest

from inventory import storage
from inventory.ledger import Ledger


class StorageTests(unittest.TestCase):

    def setUp(self):
        self.ledger = Ledger()
        self.ledger.add_item('BOLT-M8', 'Bolt M8', reorder_level=20)
        self.ledger.add_item('NUT-M8', 'Nut M8')
        self.ledger.receive('BOLT-M8', 100)
        self.ledger.ship('BOLT-M8', 40, note='order 17')

    def test_a_saved_ledger_reads_back_the_same(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'stock.json')
            storage.save(self.ledger, path)
            copy = storage.read(path)
        self.assertEqual(copy.skus(), ['BOLT-M8', 'NUT-M8'])
        self.assertEqual(copy.on_hand('BOLT-M8'), 60)
        self.assertEqual(copy.on_hand('NUT-M8'), 0)
        self.assertEqual(copy.item('BOLT-M8'), self.ledger.item('BOLT-M8'))
        self.assertEqual(copy.history(), self.ledger.history())

    def test_a_file_with_an_unknown_version_is_refused(self):
        data = storage.dump(self.ledger)
        data['version'] = 99
        with self.assertRaises(ValueError):
            storage.load(data)


if __name__ == '__main__':
    unittest.main()
