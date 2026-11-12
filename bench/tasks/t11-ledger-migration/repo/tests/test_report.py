import unittest

from ledgerbook import Ledger, report

from helpers import march


class MonthlyReportTest(unittest.TestCase):
    def test_march(self):
        got = report.monthly(march(), 2024, 3)
        keys = ('month', 'income', 'spending', 'net', 'by_category', 'entries', 'closing')
        self.assertEqual({key: got[key] for key in keys}, {
            'month': '2024-03',
            'income': 250000 + 1500 + 50000,
            'spending': 4599 + 12000 + 90000 + 50000,
            'net': 250000 + 1500 + 50000 - (4599 + 12000 + 90000 + 50000),
            'by_category': {'groceries': -15099, 'rent': -90000, 'salary': 250000, 'transfer': 0},
            'entries': 7,
            'closing': {'checking': 194901, 'savings': 550000},
        })

    def test_closing_matches_the_ledger(self):
        ledger = march()
        for month, last in ((2, '2024-02-29'), (3, '2024-03-31'), (4, '2024-04-30')):
            with self.subTest(month=month):
                self.assertEqual(report.monthly(ledger, 2024, month)['closing'], ledger.balances(until=last))

    def test_empty_month(self):
        got = report.monthly(Ledger(), 2024, 5)
        self.assertEqual((got['income'], got['spending'], got['entries'], got['closing']), (0, 0, 0, {}))

    def test_render(self):
        text = report.render(report.monthly(march(), 2024, 3))
        self.assertIn('Report for 2024-03 (7 entries)', text)
        self.assertIn('3,015.00', text)
        self.assertIn('Closing balances', text)

    def test_yearly_has_twelve_months(self):
        self.assertEqual([r['month'] for r in report.yearly(march(), 2024)][:3], ['2024-01', '2024-02', '2024-03'])
