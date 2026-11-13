import json
import os
import shutil
import tempfile
import unittest

from invoicing import Book, Line
from invoicing.export import rows, to_csv

# A book as the version before the change wrote it: its documents were issued under the old rounding.
ISSUED = {'format': 1, 'documents': [
    {'number': 'INV-0001', 'kind': 'invoice', 'customer': 'Cafe Rosa', 'date': '2024-03-04', 'lines': [
        {'description': 'Oat milk 1l', 'quantity': 1, 'unit_price': 130, 'rate': '5', 'net': 130, 'tax': 6},
        {'description': 'Sugar sticks', 'quantity': 3, 'unit_price': 50, 'rate': '5', 'net': 150, 'tax': 8},
        {'description': 'Napkins', 'quantity': 1, 'unit_price': 50, 'rate': '5', 'net': 50, 'tax': 2},
        {'description': 'Stirrers', 'quantity': 3, 'unit_price': 30, 'rate': '5', 'net': 90, 'tax': 4},
        {'description': 'Coffee beans 1kg', 'quantity': 2, 'unit_price': 2500, 'rate': '20', 'net': 5000,
         'tax': 1000}]},
    {'number': 'CRN-0001', 'kind': 'credit', 'customer': 'Cafe Rosa', 'date': '2024-03-11',
     'refers_to': 'INV-0001', 'origin_lines': [3], 'lines': [
        {'description': 'Stirrers', 'quantity': -1, 'unit_price': 30, 'rate': '5', 'net': -30, 'tax': -2}]},
    {'number': 'INV-0002', 'kind': 'invoice', 'customer': 'Deli Marco', 'date': '2024-03-12', 'lines': [
        {'description': 'Napkins', 'quantity': 1, 'unit_price': 50, 'rate': '5', 'net': 50, 'tax': 2},
        {'description': 'Paper bags', 'quantity': 1, 'unit_price': 50, 'rate': '5', 'net': 50, 'tax': 2}]},
]}


class IssuedBookTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.path = os.path.join(self.directory, 'book.json')
        with open(self.path, 'w', encoding='utf-8') as handle:
            json.dump(ISSUED, handle)
        self.book = Book(self.path)

    def tearDown(self):
        shutil.rmtree(self.directory, True)

    def test_issued_figures_do_not_change(self):
        invoice = self.book.get('INV-0001')
        self.assertEqual([line.tax for line in invoice.lines], [6, 8, 2, 4, 1000])
        self.assertEqual((invoice.net, invoice.tax, invoice.total), (5420, 1020, 6440))
        self.assertEqual(self.book.get('CRN-0001').tax, -2)
        self.assertEqual(self.book.get('INV-0002').tax, 4)
        self.assertIn('Tax at 5% on 4.20: 0.20', invoice.render())

    def test_export_shows_them_as_issued(self):
        got = [(row['number'], row['rate'], row['net'], row['tax'], row['gross']) for row in rows(self.book.documents())]
        self.assertEqual(got, [('INV-0001', '20', 5000, 1000, 6000), ('INV-0001', '5', 420, 20, 440),
                               ('CRN-0001', '5', -30, -2, -32), ('INV-0002', '5', 100, 4, 104)])
        lines = to_csv(self.book.documents()).splitlines()
        self.assertEqual(lines[2], 'INV-0001,invoice,2024-03-04,Cafe Rosa,5,4.20,0.20,4.40')
        self.assertEqual(lines[-1], 'TOTAL,,,,,54.90,10.22,65.12')

    def test_lines_refunded_in_full_give_back_what_they_were_charged(self):
        note = self.book.refund('INV-0001', '2024-05-02')
        self.assertEqual([(line.quantity, line.net, line.tax) for line in note.lines],
                         [(-1, -130, -6), (-3, -150, -8), (-1, -50, -2), (-2, -60, -2), (-2, -5000, -1000)])
        self.assertEqual(self.book.get('INV-0001').total + self.book.get('CRN-0001').total + note.total, 0)
        other = self.book.refund('INV-0002', '2024-05-02', {1: 1})
        self.assertEqual([line.tax for line in other.lines], [-2])

    def test_partial_refund_of_an_issued_invoice(self):
        part = self.book.refund('INV-0001', '2024-05-02', {1: 1})        # -2.5 -> -3 under the rule
        self.assertEqual([line.tax for line in part.lines], [-3])
        rest = self.book.refund('INV-0001', '2024-05-03', {1: 2})        # what is left of 8: -5
        self.assertEqual([line.tax for line in rest.lines], [-5])

    def test_new_documents_use_the_new_rule_and_the_file_keeps_its_format(self):
        invoice = self.book.issue_invoice('Deli Marco', '2024-05-02', [Line('Oat milk 1l', 1, 130, '5')])
        self.assertEqual((invoice.number, invoice.tax), ('INV-0003', 7))
        self.book.refund('INV-0002', '2024-05-03', {0: 1})
        with open(self.path, encoding='utf-8') as handle:
            data = json.load(handle)
        self.assertEqual(data['format'], 1)
        self.assertEqual(data['documents'][:3], ISSUED['documents'])
        self.assertEqual(sorted(data['documents'][3]['lines'][0]), sorted(ISSUED['documents'][0]['lines'][0]))
        again = Book(self.path)
        self.assertEqual(again.get('INV-0001').tax, 1020)
        self.assertEqual(again.get('INV-0003').tax, 7)


if __name__ == '__main__':
    unittest.main()
