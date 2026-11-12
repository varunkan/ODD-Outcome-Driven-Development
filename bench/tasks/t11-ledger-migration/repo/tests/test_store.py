import os
import tempfile
import unittest

from ledgerbook import Ledger, LedgerFormatError, load, loads, save, dumps

from helpers import march

WRITTEN_IN_2023 = (
    'ledgerbook 1\n'
    '1;2023-11-30;checking;opening;80000;opening balance\n'
    '2;2023-12-01;checking;rent;-75000;rent; December; paid late\n'
    '\n'
    '4;2023-12-03;savings;transfer;20000;\n'
)


class StoreTest(unittest.TestCase):
    def test_round_trip(self):
        ledger = march()
        again = loads(dumps(ledger))
        self.assertEqual(again.entries(), ledger.entries())

    def test_file_round_trip(self):
        ledger = march()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'shop.ledger')
            save(ledger, path)
            save(ledger, path)
            self.assertEqual(load(path).entries(), ledger.entries())
            self.assertEqual(os.listdir(directory), ['shop.ledger'])

    def test_reads_a_file_written_earlier(self):
        ledger = loads(WRITTEN_IN_2023)
        self.assertEqual([entry.id for entry in ledger.entries()], [1, 2, 4])
        self.assertEqual(ledger.get(2).memo, 'rent; December; paid late')
        self.assertEqual(ledger.get(4).memo, '')
        self.assertEqual(ledger.balances(), {'checking': 5000, 'savings': 20000})
        self.assertEqual(ledger.add('2024-01-01', 'checking', 'x', 1), 5)

    def test_memo_with_semicolons_survives(self):
        ledger = Ledger()
        ledger.add('2024-03-01', 'checking', 'misc', -100, ';a;b;;c;')
        self.assertEqual(loads(dumps(ledger)).get(1).memo, ';a;b;;c;')

    def test_refuses_what_it_cannot_read(self):
        for text in ('', 'hello\n', 'ledgerbook 1\n1;2024-03-01;checking\n', 'ledgerbook 1\nx;2024-03-01;a;b;1;m\n',
                     'ledgerbook 1\n1;2024-03-01;a;b;1;m\n1;2024-03-02;a;b;2;m\n'):
            with self.subTest(text=text):
                with self.assertRaises(LedgerFormatError):
                    loads(text)
