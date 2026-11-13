import unittest

import tinycsv


class WriterTest(unittest.TestCase):
    def test_format_line_quotes_only_where_needed(self):
        self.assertEqual(tinycsv.format_line(['1001', 'Washer', 0.04]), '1001,Washer,0.04')
        self.assertEqual(tinycsv.format_line(['Bolt, 5 mm', 'x']), '"Bolt, 5 mm",x')
        self.assertEqual(tinycsv.format_line(['24" wide']), '"24"" wide"')

    def test_write_rows(self):
        self.assertEqual(tinycsv.write_rows([['a', 'b'], ['c', 'd']]), 'a,b\nc,d\n')
        self.assertEqual(tinycsv.write_rows([]), '')


if __name__ == '__main__':
    unittest.main()
