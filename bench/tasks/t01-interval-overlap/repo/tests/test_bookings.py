import unittest

from scheduler.bookings import BookingConflict, Schedule


class ScheduleTests(unittest.TestCase):

    def setUp(self):
        self.room = Schedule()
        self.room.book('Standup', '09:00', '10:00')
        self.room.book('Lunch talk', '13:00', '14:00')

    def test_bookings_are_listed_in_time_order_and_can_be_cancelled(self):
        planning = self.room.book('Planning', '11:00', '12:00')
        self.assertEqual((planning.start, planning.end), ('11:00', '12:00'))
        self.assertEqual([made.title for made in self.room.bookings()], ['Standup', 'Planning', 'Lunch talk'])
        self.assertEqual(self.room.cancel('Planning'), 1)
        self.assertEqual(self.room.cancel('Planning'), 0)
        self.assertEqual([made.title for made in self.room.bookings()], ['Standup', 'Lunch talk'])

    def test_overlapping_booking_is_refused(self):
        with self.assertRaises(BookingConflict) as caught:
            self.room.book('Interview', '09:30', '10:30')
        self.assertEqual([made.title for made in caught.exception.clashes], ['Standup'])
        self.assertEqual(len(self.room.bookings()), 2)
        self.assertEqual([made.title for made in self.room.conflicts('12:30', '15:00')], ['Lunch talk'])
        with self.assertRaises(ValueError):
            self.room.book('Night shift', '17:00', '19:00')

    def test_free_time(self):
        self.assertEqual(self.room.free_slots(), [('08:00', '09:00'), ('10:00', '13:00'), ('14:00', '18:00')])
        self.assertEqual(self.room.free_slots(minimum=120), [('10:00', '13:00'), ('14:00', '18:00')])
        self.assertEqual(self.room.first_free(120), ('10:00', '12:00'))
        self.assertEqual(self.room.first_free(30, after='10:15'), ('10:15', '10:45'))
        self.assertIsNone(self.room.first_free(300))


if __name__ == '__main__':
    unittest.main()
