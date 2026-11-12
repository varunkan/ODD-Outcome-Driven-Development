import os
import tempfile
import unittest

from ledgerbook import Ledger, dumps, load, loads, report, save

# Files exactly as the version before statuses wrote them (the format in its README).
OLD_FILE = (
    'ledgerbook 1\n'
    '1;2023-11-30;checking;opening;80000;opening balance\n'
    '2;2023-12-01;checking;rent;-75000;rent; December; paid late\n'
    '3;2023-12-02;checking;groceries;-2300;duplicate;void\n'
    '5;2023-12-03;savings;transfer;20000;\n'
    '6;2023-12-04;checking;groceries;-1200;market;pending\n'
    '7;2023-12-05;checking;misc;-50;;\n'
    '8;2023-12-06;checking;misc;-25;cleared\n'
)


def statuses(ledger):
    return {entry.id: entry.status for entry in ledger.entries()}


def memos(ledger):
    return {entry.id: entry.memo for entry in ledger.entries()}


class OldFilesTest(unittest.TestCase):
    def test_old_file_loads_with_every_entry_cleared(self):
        ledger = loads(OLD_FILE)
        self.assertEqual(sorted(statuses(ledger)), [1, 2, 3, 5, 6, 7, 8])
        self.assertEqual(set(statuses(ledger).values()), {'cleared'})

    def test_old_memos_are_kept_exactly(self):
        self.assertEqual(memos(loads(OLD_FILE)), {
            1: 'opening balance', 2: 'rent; December; paid late', 3: 'duplicate;void', 5: '',
            6: 'market;pending', 7: ';', 8: 'cleared'})

    def test_old_file_totals(self):
        ledger = loads(OLD_FILE)
        checking = 80000 - 75000 - 2300 - 1200 - 50 - 25
        self.assertEqual(ledger.balances(), {'checking': checking, 'savings': 20000})
        self.assertEqual(ledger.cleared_balance('checking'), checking)
        self.assertEqual(report.monthly(ledger, 2023, 12)['entries'], 6)
        self.assertEqual(report.monthly(ledger, 2023, 12)['pending'], 0)

    def test_old_file_on_disk_saved_again_loads_the_same(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'shop.ledger')
            with open(path, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write(OLD_FILE)
            first = load(path)
            save(first, path)
            again = load(path)
        self.assertEqual(statuses(again), statuses(first))
        self.assertEqual(memos(again), memos(first))
        self.assertEqual(again.entries(), first.entries())

    def test_old_file_ids_continue(self):
        ledger = loads(OLD_FILE)
        self.assertEqual(ledger.add('2024-01-01', 'checking', 'misc', -1), 9)


class NewFilesTest(unittest.TestCase):
    def ledger(self):
        ledger = Ledger()
        ledger.add('2024-03-01', 'checking', 'salary', 250000, 'March pay')
        ledger.add('2024-03-02', 'checking', 'groceries', -4599, 'market; bread and cheese', status='pending')
        ledger.add('2024-03-03', 'checking', 'groceries', -2300, 'imported twice;void', status='void')
        ledger.add('2024-03-04', 'checking', 'misc', -100, ';pending;', status='cleared')
        ledger.add('2024-03-05', 'savings', 'misc', 700, '', status='pending')
        ledger.add('2024-03-06', 'savings', 'misc', 300, 'cleared', status='void')
        ledger.remove(1)
        return ledger

    def test_statuses_and_memos_round_trip(self):
        ledger = self.ledger()
        again = loads(dumps(ledger))
        self.assertEqual(statuses(again), {2: 'pending', 3: 'void', 4: 'cleared', 5: 'pending', 6: 'void'})
        self.assertEqual(memos(again), memos(ledger))
        self.assertEqual(again.entries(), ledger.entries())

    def test_round_trip_through_a_file_keeps_the_totals(self):
        ledger = self.ledger()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'shop.ledger')
            save(ledger, path)
            again = load(path)
        self.assertEqual(again.balances(), {'checking': -4599 - 100, 'savings': 700})
        self.assertEqual(again.cleared_balance('checking'), -100)
        self.assertEqual(report.monthly(again, 2024, 3), report.monthly(ledger, 2024, 3))
        self.assertEqual(again.add('2024-03-07', 'checking', 'misc', -1), 7)

    def test_status_changed_after_loading_is_saved(self):
        ledger = loads(dumps(self.ledger()))
        ledger.set_status(3, 'cleared')
        ledger.set_status(5, 'void')
        self.assertEqual(statuses(loads(dumps(ledger))), {2: 'pending', 3: 'cleared', 4: 'cleared', 5: 'void',
                                                          6: 'void'})


if __name__ == '__main__':
    unittest.main()
