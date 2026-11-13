import unittest

from stockfile import format_quantity, largest, parse_quantity, parse_row, read_rows, total_by_sku


class QuantityTest(unittest.TestCase):
    def test_whole_numbers_are_read(self):
        self.assertEqual(parse_quantity('12'), 12)
        self.assertEqual(parse_quantity('0'), 0)
        self.assertEqual(parse_quantity(' 1,250 '), 1250)
        self.assertEqual(parse_quantity('+7'), 7)
        self.assertEqual(parse_quantity('-3'), -3)
        self.assertEqual(format_quantity(1250), '1,250')
        self.assertEqual(parse_quantity(format_quantity(2000000)), 2000000)

    def test_text_without_a_number_is_rejected(self):
        for text in ('', '   ', 'abc', 'n/a', '-', None):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_quantity(text)


class FileTest(unittest.TestCase):
    def test_rows_and_totals(self):
        rows = read_rows(['# count of 3 March', 'PAL-7;1,250', 'BOX-2; 40', '', 'PAL-7;250', 'BAG-9;40'])
        self.assertEqual(rows, [('PAL-7', 1250), ('BOX-2', 40), ('PAL-7', 250), ('BAG-9', 40)])
        self.assertEqual(parse_row(' BOX-2 ; 40 '), ('BOX-2', 40))
        self.assertEqual(total_by_sku(rows), {'PAL-7': 1500, 'BOX-2': 40, 'BAG-9': 40})
        self.assertEqual(largest(rows, 2), [('PAL-7', 1500), ('BAG-9', 40)])
        with self.assertRaises(ValueError) as caught:
            read_rows(['PAL-7;10', 'no separator here'])
        self.assertIn('line 2', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
