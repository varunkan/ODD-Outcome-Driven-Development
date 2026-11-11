import unittest

from checkout import (
    LineItem,
    Order,
    line_total_cents,
    order_discount_cents,
    order_subtotal_cents,
    order_total_cents,
)


class LineTotalTest(unittest.TestCase):
    def test_line_without_discount(self):
        self.assertEqual(line_total_cents(LineItem('Tea', 250, quantity=2)), 500)

    def test_line_with_discount(self):
        self.assertEqual(line_total_cents(LineItem('Kettle', 2000, discount_percent=10)), 1800)
        self.assertEqual(line_total_cents(LineItem('Mug', 600, quantity=3, discount_percent=50)), 900)


class OrderTotalTest(unittest.TestCase):
    def test_order_amounts(self):
        order = Order()
        order.add('Tea', 250, quantity=2)
        order.add('Kettle', 2000, discount_percent=10)
        order.add('Mug', 600, quantity=3, discount_percent=50)
        self.assertEqual(order_subtotal_cents(order), 4300)
        self.assertEqual(order_total_cents(order), 3200)
        self.assertEqual(order_discount_cents(order), 1100)

    def test_bad_values_are_rejected(self):
        with self.assertRaises(ValueError):
            LineItem('Tea', 250, quantity=0)
        with self.assertRaises(ValueError):
            LineItem('Tea', 250, discount_percent=101)


if __name__ == '__main__':
    unittest.main()
