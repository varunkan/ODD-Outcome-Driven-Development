import unittest

from invoicing import Book, Line


def figures(note):
    return [(line.quantity, line.net, line.tax) for line in note.lines]


class CreditNoteRoundingTest(unittest.TestCase):
    def test_whole_invoice_comes_back_to_zero(self):
        book = Book()
        invoice = book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Oat milk 1l', 1, 130, '5'),
                                                                  Line('Napkins', 1, 50, '5')])
        note = book.refund(invoice.number, '2024-05-09')
        self.assertEqual(figures(note), [(-1, -130, -7), (-1, -50, -3)])
        self.assertEqual(invoice.total + note.total, 0)

    def test_negative_halves_round_away_from_zero(self):
        book = Book()
        book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Sugar sticks', 3, 50, '5'),     # 7.5 -> 8
                                                        Line('Stirrers', 5, 130, '5')])       # 32.5 -> 33
        note = book.refund('INV-0001', '2024-05-09', {0: 1, 1: 1})
        self.assertEqual(figures(note), [(-1, -50, -3), (-1, -130, -7)])

    def test_partial_refunds_round_to_the_nearest_cent(self):
        book = Book()
        book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Tea, loose', 4, 1999, '20')])   # 1599.2 -> 1599
        note = book.refund('INV-0001', '2024-05-09', {0: 1})                                 # -399.8 -> -400
        self.assertEqual(figures(note), [(-1, -1999, -400)])

    def test_last_units_give_back_what_is_left(self):
        book = Book()
        invoice = book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Stirrers', 3, 30, '5')])   # 4.5 -> 5
        self.assertEqual(invoice.tax, 5)
        first = book.refund('INV-0001', '2024-05-09', {0: 1})        # -1.5 -> -2
        second = book.refund('INV-0001', '2024-05-10', {0: 1})       # -1.5 -> -2
        last = book.refund('INV-0001', '2024-05-11', {0: 1})         # what is left: -1
        self.assertEqual([figures(n) for n in (first, second, last)],
                         [[(-1, -30, -2)], [(-1, -30, -2)], [(-1, -30, -1)]])
        self.assertEqual(invoice.tax + first.tax + second.tax + last.tax, 0)

    def test_last_units_when_the_parts_fall_short(self):
        book = Book()
        book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Tea, loose', 4, 1999, '20')])   # 1599.2 -> 1599
        notes = [book.refund('INV-0001', '2024-05-09', {0: 1}) for _ in range(3)]            # -400 each
        notes.append(book.refund('INV-0001', '2024-05-12'))                                  # what is left
        self.assertEqual([note.tax for note in notes], [-400, -400, -400, -399])
        self.assertEqual(sum(note.net for note in notes), -4 * 1999)

    def test_last_units_together_with_other_lines(self):
        book = Book()
        invoice = book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Stirrers', 3, 30, '5'),
                                                                  Line('Sugar sticks', 3, 50, '5'),
                                                                  Line('Coffee beans 1kg', 2, 2500, '20')])
        first = book.refund('INV-0001', '2024-05-09', {0: 2, 1: 1})
        self.assertEqual(figures(first), [(-2, -60, -3), (-1, -50, -3)])
        rest = book.refund('INV-0001', '2024-05-10')
        self.assertEqual(figures(rest), [(-1, -30, -2), (-2, -100, -5), (-2, -5000, -1000)])
        self.assertEqual(invoice.total + first.total + rest.total, 0)

    def test_saved_credit_notes_count_after_reloading(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'book.json')
            book = Book(path)
            book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Stirrers', 3, 30, '5')])
            book.refund('INV-0001', '2024-05-09', {0: 1})
            book.refund('INV-0001', '2024-05-10', {0: 1})
            last = Book(path).refund('INV-0001', '2024-05-11')
        self.assertEqual(figures(last), [(-1, -30, -1)])


if __name__ == '__main__':
    unittest.main()
