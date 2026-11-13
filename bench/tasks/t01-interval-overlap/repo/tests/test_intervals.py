import unittest

from scheduler.intervals import Interval, format_time, gaps, merge, overlaps, parse_time, total_minutes


class IntervalTests(unittest.TestCase):

    def test_times_convert_both_ways(self):
        self.assertEqual(parse_time('09:30'), 570)
        self.assertEqual(format_time(570), '09:30')
        self.assertEqual(parse_time('24:00'), 1440)
        for bad in ('9.30', '25:00', '12:60', ''):
            with self.assertRaises(ValueError):
                parse_time(bad)
        self.assertEqual(Interval(540, 600).minutes, 60)
        with self.assertRaises(ValueError):
            Interval(600, 600)

    def test_overlapping_and_separate_intervals(self):
        morning = Interval(540, 600)
        self.assertTrue(overlaps(morning, Interval(570, 630)))
        self.assertTrue(overlaps(Interval(570, 630), morning))
        self.assertFalse(overlaps(morning, Interval(660, 720)))
        self.assertFalse(overlaps(Interval(660, 720), morning))

    def test_merge_joins_overlapping_and_back_to_back_intervals(self):
        spans = [Interval(600, 660), Interval(540, 600), Interval(710, 730), Interval(700, 720)]
        self.assertEqual(merge(spans), [Interval(540, 660), Interval(700, 730)])
        self.assertEqual(total_minutes(spans), 150)
        self.assertEqual(gaps(spans, Interval(480, 780)),
                         [Interval(480, 540), Interval(660, 700), Interval(730, 780)])


if __name__ == '__main__':
    unittest.main()
