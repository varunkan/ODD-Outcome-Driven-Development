import unittest

from invoicing import Book, Line
from invoicing.export import between, rows, to_csv


class ExportTest(unittest.TestCase):
    def test_csv(self):
        book = Book()
        book.issue_invoice('Cafe Rosa', '2024-05-02', [
            Line('Oat milk 1l', 10, 200, '5'),
            Line('Coffee beans 1kg', 4, 2500, '20'),
        ])
        book.refund('INV-0001', '2024-05-09', {1: 2})
        self.assertEqual(to_csv(book.documents()).splitlines(), [
            'number,kind,date,customer,rate,net,tax,gross',
            'INV-0001,invoice,2024-05-02,Cafe Rosa,20,100.00,20.00,120.00',
            'INV-0001,invoice,2024-05-02,Cafe Rosa,5,20.00,1.00,21.00',
            'CRN-0001,credit,2024-05-09,Cafe Rosa,20,-50.00,-10.00,-60.00',
            'TOTAL,,,,,70.00,11.00,81.00',
        ])

    def test_rows_in_cents(self):
        book = Book()
        book.issue_invoice('A', '2024-05-02', [Line('x', 3, 1000, '20')])
        self.assertEqual(rows(book.documents()), [{'number': 'INV-0001', 'kind': 'invoice', 'date': '2024-05-02',
                                                   'customer': 'A', 'rate': '20', 'net': 3000, 'tax': 600,
                                                   'gross': 3600}])

    def test_between(self):
        book = Book()
        for day in ('2024-03-31', '2024-04-01', '2024-06-30', '2024-07-01'):
            book.issue_invoice('A', day, [Line('x', 1, 1000, '20')])
        self.assertEqual([d.date for d in between(book.documents(), '2024-04-01', '2024-06-30')],
                         ['2024-04-01', '2024-06-30'])
