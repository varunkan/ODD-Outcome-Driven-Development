"""Acceptance tests for the back-to-back booking report. Copied into the repository after the session ends."""
import unittest

from scheduler.bookings import BookingConflict, Schedule
from scheduler.intervals import Interval, overlaps


def titles(bookings):
    return sorted(booking.title for booking in bookings)


def blocks(schedule):
    return [tuple(block) for block in schedule.busy_blocks()]


class OverlapsTests(unittest.TestCase):

    def test_touching_intervals_do_not_overlap_in_either_order(self):
        early, late = Interval(540, 600), Interval(600, 660)
        self.assertFalse(overlaps(early, late))
        self.assertFalse(overlaps(late, early))

    def test_one_shared_minute_is_an_overlap_in_either_order(self):
        early, late = Interval(540, 601), Interval(600, 660)
        self.assertTrue(overlaps(early, late))
        self.assertTrue(overlaps(late, early))

    def test_containment_and_identical_intervals_overlap(self):
        outer, inner = Interval(540, 720), Interval(600, 660)
        self.assertTrue(overlaps(outer, inner))
        self.assertTrue(overlaps(inner, outer))
        self.assertTrue(overlaps(inner, Interval(600, 660)))
        self.assertTrue(overlaps(Interval(600, 601), Interval(600, 601)))

    def test_intervals_with_a_gap_do_not_overlap(self):
        self.assertFalse(overlaps(Interval(540, 600), Interval(601, 660)))
        self.assertFalse(overlaps(Interval(601, 660), Interval(540, 600)))


class BookingTests(unittest.TestCase):

    def setUp(self):
        self.room = Schedule(opens='08:00', closes='18:00')
        self.room.book('Standup', '09:00', '10:00')

    def test_booking_that_starts_when_another_ends_is_accepted(self):
        self.room.book('Design review', '10:00', '11:00')
        self.assertEqual(titles(self.room.conflicts('08:00', '18:00')), ['Design review', 'Standup'])

    def test_booking_that_ends_when_another_starts_is_accepted(self):
        self.room.book('Prep', '08:00', '09:00')
        self.assertEqual(titles(self.room.conflicts('08:00', '18:00')), ['Prep', 'Standup'])

    def test_booking_that_touches_bookings_on_both_sides_is_accepted(self):
        self.room.book('Retro', '11:00', '12:00')
        self.room.book('Design review', '10:00', '11:00')
        self.assertEqual(titles(self.room.conflicts('08:00', '18:00')), ['Design review', 'Retro', 'Standup'])

    def test_one_minute_of_overlap_is_refused_at_either_end(self):
        with self.assertRaises(BookingConflict):
            self.room.book('Runs into the start', '08:00', '09:01')
        with self.assertRaises(BookingConflict):
            self.room.book('Starts before the end', '09:59', '11:00')
        self.assertEqual(titles(self.room.conflicts('08:00', '18:00')), ['Standup'])

    def test_same_inside_and_around_are_refused(self):
        for start, end in (('09:00', '10:00'), ('09:15', '09:45'), ('08:30', '10:30')):
            with self.assertRaises(BookingConflict):
                self.room.book('Clash', start, end)
        self.assertEqual(titles(self.room.conflicts('08:00', '18:00')), ['Standup'])


class ConflictsTests(unittest.TestCase):

    def setUp(self):
        self.room = Schedule(opens='08:00', closes='18:00')
        self.room.book('Standup', '09:00', '10:00')
        self.room.book('Retro', '11:00', '12:00')

    def test_bookings_that_only_touch_are_not_listed(self):
        self.assertEqual(list(self.room.conflicts('10:00', '11:00')), [])
        self.assertEqual(list(self.room.conflicts('08:00', '09:00')), [])
        self.assertEqual(list(self.room.conflicts('12:00', '13:00')), [])

    def test_bookings_that_really_overlap_are_listed(self):
        self.assertEqual(titles(self.room.conflicts('09:59', '11:01')), ['Retro', 'Standup'])
        self.assertEqual(titles(self.room.conflicts('09:30', '11:00')), ['Standup'])
        self.assertEqual(titles(self.room.conflicts('10:00', '11:01')), ['Retro'])


class SuggestedSlotTests(unittest.TestCase):

    def test_suggested_slot_next_to_a_booking_can_be_booked(self):
        room = Schedule(opens='08:00', closes='18:00')
        room.book('Standup', '09:00', '10:00')
        self.assertEqual(tuple(room.first_free(60)), ('08:00', '09:00'))
        room.book('Prep', *room.first_free(60))
        room.book('Design review', *room.first_free(60))
        self.assertEqual(titles(room.conflicts('08:00', '18:00')), ['Design review', 'Prep', 'Standup'])
        self.assertEqual(blocks(room), [('08:00', '11:00')])

    def test_day_can_be_filled_with_suggested_slots(self):
        room = Schedule(opens='09:00', closes='12:00')
        for number in range(3):
            slot = room.first_free(60)
            self.assertIsNotNone(slot)
            room.book('Session %d' % number, *slot)
        self.assertIsNone(room.first_free(60))
        self.assertIsNone(room.first_free(1))
        self.assertEqual(blocks(room), [('09:00', '12:00')])


class BusyBlocksTests(unittest.TestCase):

    def test_back_to_back_bookings_show_as_one_block(self):
        room = Schedule(opens='08:00', closes='18:00')
        room.book('Standup', '09:00', '10:00')
        room.book('Design review', '10:00', '11:00')
        self.assertEqual(blocks(room), [('09:00', '11:00')])

    def test_bookings_with_a_gap_stay_separate_blocks(self):
        room = Schedule(opens='08:00', closes='18:00')
        room.book('Design review', '10:00', '11:00')
        room.book('Standup', '09:00', '10:00')
        room.book('Lunch talk', '13:00', '14:00')
        self.assertEqual(blocks(room), [('09:00', '11:00'), ('13:00', '14:00')])


if __name__ == '__main__':
    unittest.main()
