import unittest

import tinycsv


class QuotedDelimiterTest(unittest.TestCase):
    def test_reported_line_with_a_comma_inside_quotes(self):
        self.assertEqual(tinycsv.parse_line('1001,"Bolt, 5 mm",0.12'), ['1001', 'Bolt, 5 mm', '0.12'])

    def test_quoted_field_first_last_and_alone(self):
        self.assertEqual(tinycsv.parse_line('"a,b",c'), ['a,b', 'c'])
        self.assertEqual(tinycsv.parse_line('a,"b,c"'), ['a', 'b,c'])
        self.assertEqual(tinycsv.parse_line('"a,b,c,d"'), ['a,b,c,d'])

    def test_two_quoted_fields_next_to_each_other(self):
        self.assertEqual(tinycsv.parse_line('"a,b","c,d"\n'), ['a,b', 'c,d'])

    def test_other_delimiter_inside_quotes(self):
        self.assertEqual(tinycsv.parse_line('"x;y";z', delimiter=';'), ['x;y', 'z'])
        self.assertEqual(tinycsv.parse_line('"1,5";"a;b"', delimiter=';'), ['1,5', 'a;b'])


class DoubledQuoteTest(unittest.TestCase):
    def test_reported_line_with_doubled_quotes(self):
        self.assertEqual(
            tinycsv.parse_line('1002,"Screen, 24"" wide",89.00'),
            ['1002', 'Screen, 24" wide', '89.00'],
        )

    def test_doubled_quotes_without_a_delimiter(self):
        self.assertEqual(tinycsv.parse_line('1,"say ""hi""",x'), ['1', 'say "hi"', 'x'])

    def test_field_that_is_only_a_quote_character(self):
        self.assertEqual(tinycsv.parse_line('""""'), ['"'])
        self.assertEqual(tinycsv.parse_line('a,"""",b'), ['a', '"', 'b'])

    def test_quote_at_the_start_and_end_of_the_value(self):
        self.assertEqual(tinycsv.parse_line('"""quoted"", then more"'), ['"quoted", then more'])


class NeighbourTest(unittest.TestCase):
    def test_empty_quoted_field_is_an_empty_string(self):
        self.assertEqual(tinycsv.parse_line('a,"",b'), ['a', '', 'b'])

    def test_unquoted_fields_are_unchanged(self):
        self.assertEqual(tinycsv.parse_line('a,b,,d'), ['a', 'b', '', 'd'])
        self.assertEqual(tinycsv.parse_line('1,5;2', delimiter=';'), ['1,5', '2'])

    def test_spaces_inside_quotes_are_kept(self):
        self.assertEqual(tinycsv.parse_line('" padded ",x'), [' padded ', 'x'])


class WholeTextTest(unittest.TestCase):
    def test_read_rows(self):
        text = 'code,name,price\n1001,"Bolt, 5 mm",0.12\n1002,"Screen, 24"" wide",89.00\n'
        self.assertEqual(
            tinycsv.read_rows(text),
            [
                ['code', 'name', 'price'],
                ['1001', 'Bolt, 5 mm', '0.12'],
                ['1002', 'Screen, 24" wide', '89.00'],
            ],
        )

    def test_read_dicts(self):
        text = '"name, long",price\n"Bolt, 5 mm",0.12\n"Screen, 24"" wide",89.00\n'
        self.assertEqual(
            tinycsv.read_dicts(text),
            [
                {'name, long': 'Bolt, 5 mm', 'price': '0.12'},
                {'name, long': 'Screen, 24" wide', 'price': '89.00'},
            ],
        )

    def test_read_dicts_with_another_delimiter(self):
        text = 'name;price\n"Nut; brass";0,30\n'
        self.assertEqual(tinycsv.read_dicts(text, delimiter=';'), [{'name': 'Nut; brass', 'price': '0,30'}])


class RoundTripTest(unittest.TestCase):
    def test_what_format_line_writes_is_read_back(self):
        rows = [
            ['plain', 'Bolt, 5 mm', 'say "hi"', ''],
            ['"', ',', '","', 'a "b", c'],
            ['1001', 'Screen, 24" wide', '89.00'],
        ]
        for fields in rows:
            self.assertEqual(tinycsv.parse_line(tinycsv.format_line(fields)), fields)


if __name__ == '__main__':
    unittest.main()
