import unittest

from invoicing import Book, Line
from invoicing.export import rows, to_csv


class ExportMatchesDocumentsTest(unittest.TestCase):
    def book(self):
        book = Book()
        book.issue_invoice('Cafe Rosa', '2024-05-02', [
            Line('Napkins', 1, 50, '5'),            # 2.5 -> 3
            Line('Paper bags', 1, 50, '5'),         # 2.5 -> 3
            Line('Oat milk 1l', 1, 130, '5'),       # 6.5 -> 7
            Line('Tea, loose', 1, 1999, '20'),      # 399.8 -> 400
            Line('Tea, green', 1, 1999, '20'),      # 399.8 -> 400
        ])
        book.issue_invoice('Deli Marco', '2024-05-03', [Line('Stirrers', 3, 30, '5')])
        book.refund('INV-0001', '2024-05-09', {0: 1, 1: 1, 3: 1})
        book.refund('INV-0002', '2024-05-10', {0: 1})
        return book

    def test_every_row_is_the_document_figure(self):
        book = self.book()
        for row in rows(book.documents()):
            with self.subTest(number=row['number'], rate=row['rate']):
                figures = book.get(row['number']).tax_by_rate()[row['rate']]
                self.assertEqual((row['net'], row['tax'], row['gross']),
                                 (figures['net'], figures['tax'], figures['gross']))

    def test_rows(self):
        got = [(row['number'], row['rate'], row['net'], row['tax'], row['gross']) for row in rows(self.book().documents())]
        self.assertEqual(got, [
            ('INV-0001', '20', 3998, 800, 4798),
            ('INV-0001', '5', 230, 13, 243),
            ('INV-0002', '5', 90, 5, 95),
            ('CRN-0001', '20', -1999, -400, -2399),
            ('CRN-0001', '5', -100, -6, -106),
            ('CRN-0002', '5', -30, -2, -32),
        ])

    def test_csv_and_total(self):
        lines = to_csv(self.book().documents()).splitlines()
        self.assertEqual(lines[2], 'INV-0001,invoice,2024-05-02,Cafe Rosa,5,2.30,0.13,2.43')
        self.assertEqual(lines[3], 'INV-0002,invoice,2024-05-03,Deli Marco,5,0.90,0.05,0.95')
        self.assertEqual(lines[-1], 'TOTAL,,,,,21.89,4.10,25.99')
        self.assertEqual(len(lines), 8)


if __name__ == '__main__':
    unittest.main()
