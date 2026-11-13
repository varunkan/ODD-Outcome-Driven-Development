import unittest

from ledgerbook.money import format_amount, parse_amount


class MoneyTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_amount('12.50'), 1250)
        self.assertEqual(parse_amount('-3'), -300)
        self.assertEqual(parse_amount('1,234.5'), 123450)
        self.assertEqual(parse_amount(' +0.07 '), 7)

    def test_parse_refuses(self):
        for text in ('', '12.345', '1,23', 'ten', '1.2.3'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_amount(text)

    def test_format(self):
        self.assertEqual(format_amount(1250), '12.50')
        self.assertEqual(format_amount(-5), '-0.05')
        self.assertEqual(format_amount(123450, thousands=True), '1,234.50')
