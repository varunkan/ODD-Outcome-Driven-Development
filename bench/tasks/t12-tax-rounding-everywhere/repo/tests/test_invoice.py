import os
import tempfile
import unittest

from invoicing import Book, Line


class InvoiceTest(unittest.TestCase):
    def test_figures(self):
        invoice = Book().issue_invoice('Cafe Rosa', '2024-05-02', [
            Line('Coffee beans 1kg', 4, 2500, '20'),
            Line('Oat milk 1l', 10, 130, '5'),
        ])
        self.assertEqual(invoice.number, 'INV-0001')
        self.assertEqual([line.tax for line in invoice.lines], [2000, 65])
        self.assertEqual((invoice.net, invoice.tax, invoice.total), (11300, 2065, 13365))

    def test_tax_is_rounded_to_the_nearest_cent_per_line(self):
        invoice = Book().issue_invoice('Cafe Rosa', '2024-05-02', [
            Line('Sugar sticks', 1, 128, '5'),      # 6.4 cents
            Line('Napkins', 1, 132, '5'),           # 6.6 cents
            Line('Tea, loose', 1, 1999, '20'),      # 399.8 cents
            Line('Cake slice', 3, 333, '7.5'),      # 74.925 cents
            Line('Water', 1, 99, '0'),
        ])
        self.assertEqual([line.tax for line in invoice.lines], [6, 7, 400, 75, 0])
        self.assertEqual(invoice.tax, 6 + 7 + 400 + 75)

    def test_tax_by_rate(self):
        invoice = Book().issue_invoice('Cafe Rosa', '2024-05-02', [
            Line('Oat milk 1l', 10, 130, '5'),
            Line('Coffee beans 1kg', 4, 2500, '20'),
            Line('Soy milk 1l', 2, 140, '5'),
        ])
        self.assertEqual(invoice.tax_by_rate(), {
            '20': {'net': 10000, 'tax': 2000, 'gross': 12000},
            '5': {'net': 1580, 'tax': 65 + 14, 'gross': 1580 + 79},
        })
        self.assertEqual(list(invoice.tax_by_rate()), ['20', '5'])

    def test_numbers_count_up(self):
        book = Book()
        numbers = [book.issue_invoice('A', '2024-05-0%d' % day, [Line('x', 1, 100, '20')]).number
                   for day in (1, 2, 3)]
        self.assertEqual(numbers, ['INV-0001', 'INV-0002', 'INV-0003'])

    def test_bad_lines_are_refused(self):
        book = Book()
        for args in (('x', 1, 100, 20), ('x', 1, 100, '20%'), ('x', 0, 100, '20'), ('x', 1, -100, '20'),
                     ('', 1, 100, '20'), ('x', 1.5, 100, '20')):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    book.issue_invoice('A', '2024-05-01', [Line(*args)])
        with self.assertRaises(ValueError):
            book.issue_invoice('A', '2024-05-01', [Line('x', -1, 100, '20')])
        self.assertEqual(book.documents(), [])

    def test_saved_and_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'book.json')
            book = Book(path)
            book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Oat milk 1l', 10, 130, '5')])
            again = Book(path)
            invoice = again.get('INV-0001')
            self.assertEqual((invoice.customer, invoice.net, invoice.tax), ('Cafe Rosa', 1300, 65))
            self.assertEqual(again.issue_invoice('B', '2024-05-03', [Line('x', 1, 100, '20')]).number, 'INV-0002')

    def test_render(self):
        invoice = Book().issue_invoice('Cafe Rosa', '2024-05-02', [Line('Oat milk 1l', 10, 130, '5')])
        text = invoice.render()
        self.assertIn('INVOICE INV-0001', text)
        self.assertIn('Tax at 5% on 13.00: 0.65', text)
        self.assertIn('Total        13.65', text)
