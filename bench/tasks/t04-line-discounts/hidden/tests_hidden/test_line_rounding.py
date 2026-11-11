import unittest

from checkout import LineItem, Order, line_total_cents, order_total_cents


def line(unit_price_cents, quantity=1, discount_percent=0):
    return LineItem('item', unit_price_cents, quantity=quantity, discount_percent=discount_percent)


def order_of(*specs):
    order = Order()
    for unit_price_cents, quantity, discount_percent in specs:
        order.add('item', unit_price_cents, quantity=quantity, discount_percent=discount_percent)
    return order


class ReportedOrderTest(unittest.TestCase):
    def test_one_line_at_fifteen_percent_off(self):
        order = Order()
        added = order.add('Notebook', 995, quantity=1, discount_percent=15)
        self.assertEqual(line_total_cents(added), 846)
        self.assertEqual(order_total_cents(order), 846)


class HalfUpTest(unittest.TestCase):
    def test_exactly_half_a_cent_goes_up(self):
        cases = [
            # unit price, quantity, discount, expected   (amount before rounding)
            (70, 1, 5, 67),       # 66.5
            (30, 1, 5, 29),       # 28.5
            (10, 1, 15, 9),       # 8.5
            (150, 1, 1, 149),     # 148.5
            (5, 1, 50, 3),        # 2.5
            (1, 1, 50, 1),        # 0.5
            (45, 1, 30, 32),      # 31.5
            (25, 1, 90, 3),       # 2.5
            (50, 1, 55, 23),      # 22.5
        ]
        for unit_price_cents, quantity, discount_percent, expected in cases:
            with self.subTest(unit_price_cents=unit_price_cents, discount_percent=discount_percent):
                self.assertEqual(line_total_cents(line(unit_price_cents, quantity, discount_percent)), expected)

    def test_less_than_half_goes_down(self):
        self.assertEqual(line_total_cents(line(999, 1, 15)), 849)    # 849.15
        self.assertEqual(line_total_cents(line(16, 1, 10)), 14)      # 14.4
        self.assertEqual(line_total_cents(line(101, 1, 51)), 49)     # 49.49
        self.assertEqual(line_total_cents(line(51, 1, 1)), 50)       # 50.49
        self.assertEqual(line_total_cents(line(51, 1, 49)), 26)      # 26.01

    def test_more_than_half_goes_up(self):
        self.assertEqual(line_total_cents(line(33, 1, 10)), 30)      # 29.7
        self.assertEqual(line_total_cents(line(149, 1, 49)), 76)     # 75.99
        self.assertEqual(line_total_cents(line(49, 1, 49)), 25)      # 24.99
        self.assertEqual(line_total_cents(line(67, 1, 3)), 65)       # 64.99

    def test_every_whole_percent_on_small_amounts(self):
        wrong = []
        for unit_price_cents in range(1, 151):
            for discount_percent in range(0, 101):
                exact_hundredths = unit_price_cents * (100 - discount_percent)
                expected = (exact_hundredths + 50) // 100
                got = line_total_cents(line(unit_price_cents, 1, discount_percent))
                if got != expected:
                    wrong.append((unit_price_cents, discount_percent, got, expected))
        self.assertEqual(wrong[:5], [], '%d amounts are not rounded half up' % len(wrong))


class OncePerLineTest(unittest.TestCase):
    def test_the_line_is_rounded_not_each_unit(self):
        self.assertEqual(line_total_cents(line(33, 3, 50)), 50)      # 99 less 50% = 49.5
        self.assertEqual(line_total_cents(line(15, 7, 10)), 95)      # 105 less 10% = 94.5
        self.assertEqual(line_total_cents(line(99, 4, 15)), 337)     # 396 less 15% = 336.6

    def test_a_large_line(self):
        self.assertEqual(line_total_cents(line(1234567, 250, 3)), 299382498)    # 299382497.5


class OrderTotalTest(unittest.TestCase):
    def test_lines_that_each_round_up(self):
        self.assertEqual(order_total_cents(order_of((70, 1, 5), (70, 1, 5))), 134)     # 67 + 67, not 133

    def test_lines_that_each_round_down(self):
        self.assertEqual(order_total_cents(order_of((16, 1, 10), (16, 1, 10), (16, 1, 10))), 42)   # 14 x 3, not 43

    def test_mixed_order_adds_up(self):
        order = order_of((995, 1, 15), (70, 1, 5), (250, 2, 0), (33, 3, 50), (16, 1, 10))
        self.assertEqual([line_total_cents(item) for item in order.lines], [846, 67, 500, 50, 14])
        self.assertEqual(order_total_cents(order), 1477)
        self.assertEqual(order_total_cents(order), sum(line_total_cents(item) for item in order.lines))

    def test_no_discount_full_discount_and_empty_order(self):
        self.assertEqual(line_total_cents(line(250, 2, 0)), 500)
        self.assertEqual(line_total_cents(line(899, 1, 100)), 0)
        self.assertEqual(order_total_cents(order_of((250, 2, 0), (899, 1, 100))), 500)
        self.assertEqual(order_total_cents(Order()), 0)


class WholeCentsTest(unittest.TestCase):
    def test_amounts_are_int(self):
        order = order_of((995, 1, 15), (70, 1, 5))
        for item in order.lines:
            self.assertIs(type(line_total_cents(item)), int)
        self.assertIs(type(order_total_cents(order)), int)
        self.assertIs(type(order_total_cents(Order())), int)


if __name__ == '__main__':
    unittest.main()
