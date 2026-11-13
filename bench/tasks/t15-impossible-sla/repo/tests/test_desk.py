import datetime as dt
import unittest

from helpdesk import DEFAULT_DESK, Desk
from helpdesk.holidays import HOLIDAYS, parse_holidays


def at(text):
    return dt.datetime.strptime(text, '%Y-%m-%d %H:%M')


class OpeningHoursTest(unittest.TestCase):
    def test_open_on_weekdays_from_eight_to_six(self):
        self.assertTrue(DEFAULT_DESK.is_open(at('2026-03-09 08:00')))
        self.assertTrue(DEFAULT_DESK.is_open(at('2026-03-09 17:59')))
        self.assertFalse(DEFAULT_DESK.is_open(at('2026-03-09 18:00')))
        self.assertFalse(DEFAULT_DESK.is_open(at('2026-03-09 07:59')))

    def test_closed_at_weekends_and_on_holidays(self):
        self.assertFalse(DEFAULT_DESK.is_open(at('2026-03-14 10:00')))   # Saturday
        self.assertFalse(DEFAULT_DESK.is_open(at('2026-04-03 10:00')))   # Good Friday
        self.assertIn(dt.date(2026, 12, 25), HOLIDAYS)

    def test_next_open(self):
        self.assertEqual(DEFAULT_DESK.next_open(at('2026-03-09 10:15')), at('2026-03-09 10:15'))
        self.assertEqual(DEFAULT_DESK.next_open(at('2026-03-09 06:00')), at('2026-03-09 08:00'))
        self.assertEqual(DEFAULT_DESK.next_open(at('2026-03-13 18:30')), at('2026-03-16 08:00'))
        self.assertEqual(DEFAULT_DESK.next_open(at('2026-04-02 19:00')), at('2026-04-07 08:00'))  # Easter

    def test_previous_close(self):
        self.assertEqual(DEFAULT_DESK.previous_close(at('2026-03-14 12:00')), at('2026-03-13 18:00'))
        self.assertEqual(DEFAULT_DESK.previous_close(at('2026-03-10 07:00')), at('2026-03-09 18:00'))

    def test_desk_minutes_skip_closed_time(self):
        self.assertEqual(DEFAULT_DESK.add_working_minutes(at('2026-03-09 09:00'), 120), at('2026-03-09 11:00'))
        self.assertEqual(DEFAULT_DESK.add_working_minutes(at('2026-03-13 17:30'), 60), at('2026-03-16 08:30'))
        self.assertEqual(DEFAULT_DESK.add_working_minutes(at('2026-03-14 11:00'), 0), at('2026-03-16 08:00'))
        self.assertEqual(DEFAULT_DESK.working_minutes_between(at('2026-03-13 17:00'), at('2026-03-16 09:00')), 120)
        self.assertEqual(DEFAULT_DESK.working_minutes_between(at('2026-03-16 09:00'), at('2026-03-13 17:00')), 0)

    def test_a_desk_of_other_hours(self):
        desk = Desk(opens=dt.time(9, 0), closes=dt.time(12, 0), workdays=[5])
        self.assertTrue(desk.is_open(at('2026-03-14 09:30')))
        self.assertEqual(desk.add_working_minutes(at('2026-03-14 11:00'), 90), at('2026-03-21 09:30'))
        with self.assertRaises(ValueError):
            Desk(opens=dt.time(18, 0), closes=dt.time(8, 0))

    def test_holiday_list_is_read_line_by_line(self):
        self.assertEqual(parse_holidays('2026-01-01 New Year\n# a comment\n\n2026-12-25'),
                         {dt.date(2026, 1, 1), dt.date(2026, 12, 25)})
        with self.assertRaises(ValueError) as caught:
            parse_holidays('2026-01-01\nChristmas')
        self.assertIn('line 2', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
