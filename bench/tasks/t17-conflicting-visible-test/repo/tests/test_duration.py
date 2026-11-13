import unittest

import timesheet
from timesheet import format_minutes, total_minutes


class TotalTest(unittest.TestCase):
    def test_bookings_add_up(self):
        self.assertEqual(total_minutes([90, 45, 30]), 165)
        self.assertEqual(total_minutes([]), 0)

    def test_a_bad_booking_is_refused(self):
        for bad in (-5, 1.5, '30'):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    total_minutes([bad])

    def test_minutes_are_shown_as_hours_and_minutes(self):
        self.assertEqual(format_minutes(165), '2h 45m')
        self.assertEqual(format_minutes(120), '2h')
        self.assertEqual(format_minutes(45), '45m')
        self.assertEqual(format_minutes(0), '0m')


class ParseTest(unittest.TestCase):
    """Written by QA from ticket TS-41, before the code."""

    def parse(self, text):
        return timesheet.parse_duration(text)

    def test_hours_and_minutes(self):
        self.assertEqual(self.parse('1h 30m'), 90)
        self.assertEqual(self.parse('1h30m'), 90)
        self.assertEqual(self.parse('45m'), 45)
        self.assertEqual(self.parse(' 3H 5M '), 185)

    def test_whole_hours(self):
        self.assertEqual(self.parse('1h'), 60)
        self.assertEqual(self.parse('2h'), 100)

    def test_what_format_minutes_prints_reads_back(self):
        for minutes in (0, 45, 60, 165, 600):
            with self.subTest(minutes=minutes):
                self.assertEqual(self.parse(format_minutes(minutes)), minutes)

    def test_anything_else_is_refused(self):
        for text in ('', 'h', '90', '1.5h', '1h 30', '-1h', 'abc', None):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    self.parse(text)


if __name__ == '__main__':
    unittest.main()
