import unittest

from checkout import Order, format_cents, render_receipt


class ReceiptTest(unittest.TestCase):
    def test_format_cents(self):
        self.assertEqual(format_cents(1234), '12.34')
        self.assertEqual(format_cents(5), '0.05')
        self.assertEqual(format_cents(-250), '-2.50')

    def test_receipt_rows(self):
        order = Order()
        order.add('Tea', 250, quantity=2)
        order.add('Kettle', 2000, discount_percent=10)
        rows = render_receipt(order).split('\n')
        self.assertEqual(len(rows), 4)
        self.assertTrue(rows[0].startswith('2 x Tea') and rows[0].endswith(' 5.00'))
        self.assertTrue(rows[1].startswith('1 x Kettle (-10%)') and rows[1].endswith(' 18.00'))
        self.assertTrue(rows[2].startswith('You saved') and rows[2].endswith(' 2.00'))
        self.assertTrue(rows[3].startswith('TOTAL') and rows[3].endswith(' 23.00'))


if __name__ == '__main__':
    unittest.main()
