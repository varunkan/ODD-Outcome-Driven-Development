import unittest

from ledgerbook.budget import Budget

from helpers import march


class BudgetTest(unittest.TestCase):
    def test_spent_counts_refunds_down(self):
        self.assertEqual(Budget({}).spent(march(), 'groceries', 2024, 3), 4599 + 12000 - 1500)

    def test_remaining_and_over(self):
        budget = Budget({'groceries': 10000, 'rent': 90000})
        ledger = march()
        self.assertEqual(budget.remaining(ledger, 'groceries', 2024, 3), 10000 - 15099)
        self.assertEqual(budget.over(ledger, 2024, 3), [('groceries', 15099, 10000)])
        self.assertEqual(budget.over(ledger, 2024, 4), [])

    def test_bad_limit(self):
        with self.assertRaises(ValueError):
            Budget({'groceries': -1})
