import unittest

import tinycsv


class ParseLineTest(unittest.TestCase):
    def test_plain_fields(self):
        self.assertEqual(tinycsv.parse_line('1001,Washer,0.04'), ['1001', 'Washer', '0.04'])
        self.assertEqual(tinycsv.parse_line('a,,c\n'), ['a', '', 'c'])
        self.assertEqual(tinycsv.parse_line('a, b'), ['a', ' b'])

    def test_quotes_around_a_simple_field_are_removed(self):
        self.assertEqual(tinycsv.parse_line('"Washer",0.04'), ['Washer', '0.04'])


class ReadTextTest(unittest.TestCase):
    def test_read_rows_skips_blank_lines(self):
        self.assertEqual(tinycsv.read_rows('a,b\n\nc,d\n'), [['a', 'b'], ['c', 'd']])

    def test_read_dicts_uses_the_header_and_pads_short_rows(self):
        text = 'code;name;price\n1001;Washer;0.04\n1002;Nut\n'
        self.assertEqual(
            tinycsv.read_dicts(text, delimiter=';'),
            [
                {'code': '1001', 'name': 'Washer', 'price': '0.04'},
                {'code': '1002', 'name': 'Nut', 'price': ''},
            ],
        )


if __name__ == '__main__':
    unittest.main()
