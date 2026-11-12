import unittest

from ledgerbook import Ledger

from helpers import march


class LedgerTest(unittest.TestCase):
    def test_ids_count_up_and_are_never_reused(self):
        ledger = Ledger()
        first = ledger.add('2024-03-01', 'checking', 'salary', 1000)
        second = ledger.add('2024-03-02', 'checking', 'rent', -500)
        ledger.remove(second)
        third = ledger.add('2024-03-03', 'checking', 'rent', -400)
        self.assertEqual((first, second, third), (1, 2, 3))

    def test_entries_are_copies_in_date_order(self):
        ledger = Ledger()
        late = ledger.add('2024-03-05', 'checking', 'rent', -500)
        early = ledger.add('2024-03-01', 'checking', 'salary', 1000)
        entries = ledger.entries()
        self.assertEqual([entry.id for entry in entries], [early, late])
        entries[0].amount = 1
        self.assertEqual(ledger.get(early).amount, 1000)

    def test_malformed_fields_are_refused(self):
        ledger = Ledger()
        for args in (('2024-02-30', 'checking', 'x', 1), ('2024-3-1', 'checking', 'x', 1),
                     ('2024-03-01', 'check;ing', 'x', 1), ('2024-03-01', 'checking', 'x', 0),
                     ('2024-03-01', 'checking', 'x', 1.5), ('2024-03-01', 'checking', 'x', 1, 'two\nlines')):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    ledger.add(*args)
        self.assertEqual(len(ledger), 0)

    def test_edit(self):
        ledger = Ledger()
        entry_id = ledger.add('2024-03-01', 'checking', 'salary', 1000)
        ledger.edit(entry_id, amount=1200, memo='corrected')
        self.assertEqual((ledger.get(entry_id).amount, ledger.get(entry_id).memo), (1200, 'corrected'))
        with self.assertRaises(ValueError):
            ledger.edit(entry_id, id=7)

    def test_balances(self):
        ledger = march()
        self.assertEqual(ledger.balance('checking'), 100000 + 250000 - 4599 - 12000 - 90000 + 1500 - 50000 - 3000)
        self.assertEqual(ledger.balance('checking', until='2024-02-29'), 100000)
        self.assertEqual(ledger.balances(), {'checking': 191901, 'savings': 550000})
        self.assertEqual(ledger.balance('nowhere'), 0)
