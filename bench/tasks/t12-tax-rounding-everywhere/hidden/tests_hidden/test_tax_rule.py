import unittest

from invoicing import Book, Line


def taxes(lines):
    invoice = Book().issue_invoice('Cafe Rosa', '2024-05-02', lines)
    return [line.tax for line in invoice.lines], invoice


class InvoiceRoundingTest(unittest.TestCase):
    def test_reported_case(self):
        invoice = Book().issue_invoice('Cafe Rosa', '2024-05-02', [Line('Oat milk 1l', 1, 130, '5')])
        self.assertEqual(invoice.tax, 7)
        self.assertEqual(invoice.total, 137)

    def test_exact_halves_round_up(self):
        got, _ = taxes([
            Line('a', 1, 50, '5'),        # 2.5
            Line('b', 1, 10, '5'),        # 0.5
            Line('c', 3, 30, '5'),        # 4.5
            Line('d', 1, 60, '7.5'),      # 4.5
            Line('e', 1, 4, '12.5'),      # 0.5
            Line('f', 1, 200, '7.25'),    # 14.5
            Line('g', 1, 1, '50'),        # 0.5
            Line('h', 2, 90, '17.5'),     # 31.5
        ])
        self.assertEqual(got, [3, 1, 5, 5, 1, 15, 1, 32])

    def test_everything_else_rounds_to_the_nearest_cent(self):
        got, _ = taxes([
            Line('a', 1, 128, '5'),       # 6.4
            Line('b', 1, 132, '5'),       # 6.6
            Line('c', 1, 1999, '20'),     # 399.8
            Line('d', 3, 333, '7.5'),     # 74.925
            Line('e', 1, 129, '5'),       # 6.45
            Line('f', 1, 4, '10'),        # 0.4
            Line('g', 1, 99, '0'),
            Line('h', 7, 1000, '20'),
        ])
        self.assertEqual(got, [6, 7, 400, 75, 6, 0, 0, 1400])

    def test_document_tax_is_the_sum_of_line_tax(self):
        got, invoice = taxes([Line('a', 1, 50, '5'), Line('b', 1, 50, '5'), Line('c', 1, 130, '5'),
                              Line('d', 1, 2500, '20')])
        self.assertEqual(got, [3, 3, 7, 500])
        self.assertEqual(invoice.tax, 513)
        self.assertEqual(invoice.total, 50 + 50 + 130 + 2500 + 513)
        self.assertEqual(invoice.tax_by_rate()['5'], {'net': 230, 'tax': 13, 'gross': 243})


if __name__ == '__main__':
    unittest.main()
