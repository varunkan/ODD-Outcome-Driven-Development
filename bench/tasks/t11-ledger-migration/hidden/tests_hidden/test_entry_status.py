import unittest

from ledgerbook import Ledger, report
from ledgerbook import balances as balance_functions
from ledgerbook.budget import Budget


def shop():
    """Checking and savings over February to April. Returns the ledger and the ids by name."""
    ledger = Ledger()
    ids = {}
    ids['open'] = ledger.add('2024-02-27', 'checking', 'opening', 100000, 'opening balance')
    ids['save_open'] = ledger.add('2024-02-28', 'savings', 'opening', 500000, 'opening balance')
    ids['pay'] = ledger.add('2024-03-01', 'checking', 'salary', 250000, 'March pay')
    ids['market'] = ledger.add('2024-03-02', 'checking', 'groceries', -4599, 'market; bread and cheese')
    ids['card'] = ledger.add('2024-03-29', 'checking', 'groceries', -2500, 'card, not cleared', status='pending')
    ids['twice'] = ledger.add('2024-03-09', 'checking', 'groceries', -12000, 'imported twice')
    ids['bounced'] = ledger.add('2024-03-12', 'savings', 'interest', 7000, 'bounced')
    ids['rent'] = ledger.add('2024-03-15', 'checking', 'rent', -90000, 'rent; March')
    ids['refund'] = ledger.add('2024-03-30', 'checking', 'groceries', 800, 'refund, pending', status='pending')
    ids['april'] = ledger.add('2024-04-02', 'checking', 'groceries', -3000, 'April')
    ledger.set_status(ids['twice'], 'void')
    ledger.set_status(ids['bounced'], 'void')
    return ledger, ids


CHECKING = 100000 + 250000 - 4599 - 2500 - 90000 + 800 - 3000      # void -12000 left out, pending counted
SAVINGS = 500000                                                   # void +7000 left out


class StatusFieldTest(unittest.TestCase):
    def test_default_is_cleared(self):
        ledger = Ledger()
        entry_id = ledger.add('2024-03-01', 'checking', 'salary', 1000)
        self.assertEqual(ledger.get(entry_id).status, 'cleared')
        self.assertEqual(ledger.entries()[0].status, 'cleared')

    def test_add_and_set_status(self):
        ledger, ids = shop()
        self.assertEqual(ledger.get(ids['card']).status, 'pending')
        self.assertEqual(ledger.get(ids['twice']).status, 'void')
        ledger.set_status(ids['card'], 'cleared')
        self.assertEqual(ledger.get(ids['card']).status, 'cleared')
        ledger.set_status(ids['twice'], 'cleared')
        self.assertEqual(ledger.get(ids['twice']).status, 'cleared')

    def test_unknown_status_is_refused_and_changes_nothing(self):
        ledger, ids = shop()
        for bad in ('Cleared', 'cancelled', '', None):
            with self.subTest(status=bad):
                with self.assertRaises(ValueError):
                    ledger.add('2024-03-03', 'checking', 'misc', -100, 'x', status=bad)
                with self.assertRaises(ValueError):
                    ledger.set_status(ids['card'], bad)
        self.assertEqual(len(ledger.entries()), 10)
        self.assertEqual(ledger.get(ids['card']).status, 'pending')

    def test_set_status_on_a_missing_id(self):
        ledger, _ = shop()
        with self.assertRaises(KeyError):
            ledger.set_status(999, 'void')

    def test_void_entries_stay_listed(self):
        ledger, ids = shop()
        listed = {entry.id: entry for entry in ledger.entries()}
        self.assertEqual(listed[ids['twice']].status, 'void')
        self.assertEqual(listed[ids['twice']].amount, -12000)
        self.assertEqual(ledger.get(ids['bounced']).memo, 'bounced')
        self.assertEqual([entry.id for entry in ledger.entries(category='interest')], [ids['bounced']])


class BalancesTest(unittest.TestCase):
    def test_balance_leaves_out_void_and_counts_pending(self):
        ledger, _ = shop()
        self.assertEqual(ledger.balance('checking'), CHECKING)
        self.assertEqual(ledger.balance('savings'), SAVINGS)
        self.assertEqual(ledger.balances(), {'checking': CHECKING, 'savings': SAVINGS})

    def test_balance_until(self):
        ledger, _ = shop()
        self.assertEqual(ledger.balance('checking', until='2024-03-10'), 100000 + 250000 - 4599)
        self.assertEqual(ledger.balances(until='2024-03-31'), {'checking': CHECKING + 3000, 'savings': SAVINGS})

    def test_balance_functions(self):
        ledger, _ = shop()
        entries = ledger.entries()
        self.assertEqual(balance_functions.balance(entries, 'checking'), CHECKING)
        self.assertEqual(balance_functions.balances(entries), {'checking': CHECKING, 'savings': SAVINGS})
        self.assertEqual(balance_functions.net_worth(entries), CHECKING + SAVINGS)

    def test_cleared_balance(self):
        ledger, ids = shop()
        self.assertEqual(ledger.cleared_balance('checking'), CHECKING + 2500 - 800)
        self.assertEqual(ledger.cleared_balance('checking', until='2024-03-31'), CHECKING + 2500 - 800 + 3000)
        self.assertEqual(ledger.cleared_balance('savings'), SAVINGS)
        ledger.set_status(ids['card'], 'cleared')
        self.assertEqual(ledger.cleared_balance('checking'), CHECKING - 800)
        self.assertEqual(ledger.cleared_balance('nowhere'), 0)

    def test_voiding_and_restoring_moves_the_balance(self):
        ledger, ids = shop()
        ledger.set_status(ids['rent'], 'void')
        self.assertEqual(ledger.balance('checking'), CHECKING + 90000)
        ledger.set_status(ids['rent'], 'pending')
        self.assertEqual(ledger.balance('checking'), CHECKING)
        self.assertEqual(ledger.cleared_balance('checking'), CHECKING + 2500 - 800 + 90000)


class MonthlyReportTest(unittest.TestCase):
    def test_march(self):
        got = report.monthly(shop()[0], 2024, 3)
        self.assertEqual(got['month'], '2024-03')
        self.assertEqual(got['income'], 250000 + 800)
        self.assertEqual(got['spending'], 4599 + 2500 + 90000)
        self.assertEqual(got['net'], 250000 + 800 - (4599 + 2500 + 90000))
        self.assertEqual(got['by_category'], {'groceries': -4599 - 2500 + 800, 'rent': -90000, 'salary': 250000})
        self.assertEqual(got['entries'], 5)
        self.assertEqual(got['pending'], -2500 + 800)
        self.assertEqual(got['closing'], {'checking': CHECKING + 3000, 'savings': SAVINGS})

    def test_pending_of_other_months_and_void_pending(self):
        ledger, ids = shop()
        self.assertEqual(report.monthly(ledger, 2024, 4)['pending'], 0)
        self.assertEqual(report.monthly(ledger, 2024, 2)['pending'], 0)
        ledger.set_status(ids['april'], 'pending')
        self.assertEqual(report.monthly(ledger, 2024, 4)['pending'], -3000)
        ledger.set_status(ids['card'], 'void')
        self.assertEqual(report.monthly(ledger, 2024, 3)['pending'], 800)

    def test_a_category_with_only_void_entries_is_not_listed(self):
        got = report.monthly(shop()[0], 2024, 3)
        self.assertNotIn('interest', got['by_category'])

    def test_closing_is_always_the_ledger_balances(self):
        ledger, ids = shop()
        ledger.set_status(ids['open'], 'void')
        for month, last in ((2, '2024-02-29'), (3, '2024-03-31'), (4, '2024-04-30')):
            with self.subTest(month=month):
                self.assertEqual(report.monthly(ledger, 2024, month)['closing'], ledger.balances(until=last))

    def test_yearly_agrees(self):
        ledger, _ = shop()
        self.assertEqual(report.yearly(ledger, 2024)[2], report.monthly(ledger, 2024, 3))


class BudgetTest(unittest.TestCase):
    def test_spent_leaves_out_void(self):
        ledger, _ = shop()
        self.assertEqual(Budget({}).spent(ledger, 'groceries', 2024, 3), 4599 + 2500 - 800)
        self.assertEqual(Budget({}).spent(ledger, 'interest', 2024, 3), 0)

    def test_remaining_and_over(self):
        ledger, ids = shop()
        budget = Budget({'groceries': 7000, 'rent': 90000})
        self.assertEqual(budget.remaining(ledger, 'groceries', 2024, 3), 7000 - (4599 + 2500 - 800))
        self.assertEqual(budget.over(ledger, 2024, 3), [])
        ledger.set_status(ids['twice'], 'pending')
        self.assertEqual(budget.over(ledger, 2024, 3), [('groceries', 4599 + 2500 - 800 + 12000, 7000)])


if __name__ == '__main__':
    unittest.main()
