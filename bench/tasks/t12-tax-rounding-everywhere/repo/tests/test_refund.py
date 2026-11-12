import unittest

from invoicing import Book, Line, RefundError


def invoiced():
    book = Book()
    book.issue_invoice('Cafe Rosa', '2024-05-02', [
        Line('Coffee beans 1kg', 4, 2500, '20'),
        Line('Oat milk 1l', 10, 200, '5'),
    ])
    return book


class RefundTest(unittest.TestCase):
    def test_part_of_one_line(self):
        book = invoiced()
        note = book.refund('INV-0001', '2024-05-09', {0: 1})
        self.assertEqual((note.number, note.kind, note.refers_to), ('CRN-0001', 'credit', 'INV-0001'))
        self.assertEqual([(line.quantity, line.net, line.tax) for line in note.lines], [(-1, -2500, -500)])
        self.assertEqual(book.refunded('INV-0001', 0), 1)

    def test_everything_left(self):
        book = invoiced()
        book.refund('INV-0001', '2024-05-09', {1: 4})
        note = book.refund('INV-0001', '2024-05-10')
        self.assertEqual([(line.quantity, line.net, line.tax) for line in note.lines],
                         [(-4, -10000, -2000), (-6, -1200, -60)])
        self.assertEqual(note.number, 'CRN-0002')
        with self.assertRaises(RefundError):
            book.refund('INV-0001', '2024-05-11')

    def test_cannot_refund_more_than_was_sold(self):
        book = invoiced()
        book.refund('INV-0001', '2024-05-09', {0: 3})
        for quantities in ({0: 2}, {2: 1}, {0: 0}, {1: -1}):
            with self.subTest(quantities=quantities):
                with self.assertRaises(RefundError):
                    book.refund('INV-0001', '2024-05-10', quantities)
        self.assertEqual(len(book.documents('credit')), 1)

    def test_only_invoices_are_refunded(self):
        book = invoiced()
        book.refund('INV-0001', '2024-05-09', {0: 1})
        with self.assertRaises(RefundError):
            book.refund('CRN-0001', '2024-05-10')
        with self.assertRaises(KeyError):
            book.refund('INV-0099', '2024-05-10')
