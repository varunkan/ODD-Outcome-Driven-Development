"""Acceptance tests for the plan-limit request: the limiter. Copied into the repository after the session ends."""
import unittest

from apigate.limiter import SlidingWindowLimiter


class FakeClock:
    """A clock the test moves by hand. Calling it returns the current time in seconds."""

    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


class AllowTests(unittest.TestCase):

    def setUp(self):
        self.clock = FakeClock(0.0)
        self.limiter = SlidingWindowLimiter(3, 10, clock=self.clock)

    def test_allows_up_to_the_limit_then_refuses(self):
        answers = [self.limiter.allow('ann') for _ in range(5)]
        self.assertEqual(answers, [True, True, True, False, False])

    def test_window_slides_instead_of_starting_again(self):
        for at in (0.0, 4.0, 8.0):
            self.clock.now = at
            self.assertTrue(self.limiter.allow('ann'), 'request at %s' % at)
        self.clock.now = 9.75
        self.assertFalse(self.limiter.allow('ann'))
        self.clock.now = 10.0     # the request counted at 0 leaves at exactly 0 + 10
        self.assertTrue(self.limiter.allow('ann'))
        self.clock.now = 11.0     # 4, 8 and 10 are still inside the window
        self.assertFalse(self.limiter.allow('ann'))
        self.clock.now = 13.5
        self.assertFalse(self.limiter.allow('ann'))
        self.clock.now = 14.0     # the request counted at 4 has left
        self.assertTrue(self.limiter.allow('ann'))
        self.assertFalse(self.limiter.allow('ann'))

    def test_refused_requests_are_not_counted(self):
        limiter = SlidingWindowLimiter(1, 10, clock=self.clock)
        self.assertTrue(limiter.allow('ann'))
        for at in (3.0, 6.0, 9.0):
            self.clock.now = at
            self.assertFalse(limiter.allow('ann'), 'request at %s' % at)
        self.clock.now = 10.0
        self.assertTrue(limiter.allow('ann'))

    def test_keys_never_share_a_count(self):
        for _ in range(3):
            self.assertTrue(self.limiter.allow('ann'))
        self.assertFalse(self.limiter.allow('ann'))
        self.assertTrue(self.limiter.allow('bob'))
        self.assertEqual(self.limiter.remaining('bob'), 2)
        self.assertEqual(self.limiter.remaining('ann'), 0)
        self.assertEqual(self.limiter.remaining('someone new'), 3)

    def test_a_window_shorter_than_a_second(self):
        limiter = SlidingWindowLimiter(1, 0.5, clock=self.clock)
        self.assertTrue(limiter.allow('ann'))
        self.clock.now = 0.25
        self.assertFalse(limiter.allow('ann'))
        self.clock.now = 0.5
        self.assertTrue(limiter.allow('ann'))

    def test_never_more_than_the_limit_in_any_window_over_a_long_run(self):
        limit, window = 4, 10
        limiter = SlidingWindowLimiter(limit, window, clock=self.clock)
        counted = []
        answers = []
        for step in range(400):
            self.clock.now += (step * step) % 7 % 4
            now = self.clock.now
            inside = [at for at in counted if at + window > now]
            expected = len(inside) < limit
            self.assertEqual(limiter.allow('ann'), expected, 'request %d at %s' % (step, now))
            answers.append(expected)
            if expected:
                counted.append(now)
        self.assertIn(True, answers)
        self.assertIn(False, answers)


class RemainingAndRetryAfterTests(unittest.TestCase):

    def setUp(self):
        self.clock = FakeClock(100.0)
        self.limiter = SlidingWindowLimiter(3, 10, clock=self.clock)

    def test_remaining_counts_down_and_asking_costs_nothing(self):
        self.assertEqual(self.limiter.remaining('ann'), 3)
        self.limiter.allow('ann')
        self.limiter.allow('ann')
        for _ in range(5):
            self.assertEqual(self.limiter.remaining('ann'), 1)
        self.assertTrue(self.limiter.allow('ann'))
        self.assertEqual(self.limiter.remaining('ann'), 0)
        self.assertFalse(self.limiter.allow('ann'))
        self.assertEqual(self.limiter.remaining('ann'), 0)

    def test_remaining_grows_back_as_requests_leave_the_window(self):
        for at in (100.0, 103.0, 106.0):
            self.clock.now = at
            self.limiter.allow('ann')
        for at, left in ((109.0, 0), (110.0, 1), (112.5, 1), (113.0, 2), (116.0, 3), (500.0, 3)):
            self.clock.now = at
            self.assertEqual(self.limiter.remaining('ann'), left, 'remaining at %s' % at)

    def test_retry_after_is_zero_while_a_request_would_be_allowed(self):
        self.assertEqual(self.limiter.retry_after('ann'), 0)
        self.limiter.allow('ann')
        self.limiter.allow('ann')
        self.assertEqual(self.limiter.retry_after('ann'), 0)

    def test_retry_after_is_the_time_until_the_oldest_request_leaves(self):
        for at in (100.0, 102.0, 103.0):
            self.clock.now = at
            self.limiter.allow('ann')
        self.assertAlmostEqual(self.limiter.retry_after('ann'), 7.0)
        self.clock.now = 105.5
        self.assertAlmostEqual(self.limiter.retry_after('ann'), 4.5)
        self.assertAlmostEqual(self.limiter.retry_after('ann'), 4.5)
        self.clock.now = 110.0    # the request counted at 100 has left
        self.assertEqual(self.limiter.retry_after('ann'), 0)
        self.assertTrue(self.limiter.allow('ann'))
        self.assertAlmostEqual(self.limiter.retry_after('ann'), 2.0)    # until the one counted at 102 leaves
        self.assertEqual(self.limiter.retry_after('bob'), 0)


class ResetTests(unittest.TestCase):

    def test_reset_forgets_one_key_only(self):
        clock = FakeClock(5.0)
        limiter = SlidingWindowLimiter(2, 60, clock=clock)
        for key in ('ann', 'ann', 'bob', 'bob'):
            self.assertTrue(limiter.allow(key))
        self.assertFalse(limiter.allow('ann'))
        limiter.reset('ann')
        self.assertEqual(limiter.remaining('ann'), 2)
        self.assertEqual(limiter.retry_after('ann'), 0)
        self.assertTrue(limiter.allow('ann'))
        self.assertFalse(limiter.allow('bob'))
        self.assertEqual(limiter.remaining('bob'), 0)

    def test_reset_of_a_key_never_seen_is_harmless(self):
        limiter = SlidingWindowLimiter(2, 60, clock=FakeClock(5.0))
        limiter.reset('nobody')
        self.assertEqual(limiter.remaining('nobody'), 2)


class ArgumentTests(unittest.TestCase):

    def test_limit_must_be_a_whole_number_of_at_least_one(self):
        for limit in (0, -1, 2.5):
            with self.assertRaises(ValueError, msg='limit %r' % (limit,)):
                SlidingWindowLimiter(limit, 10)

    def test_window_must_be_greater_than_zero(self):
        for window in (0, -5):
            with self.assertRaises(ValueError, msg='window %r' % (window,)):
                SlidingWindowLimiter(3, window)

    def test_works_without_a_clock(self):
        limiter = SlidingWindowLimiter(2, 3600)
        self.assertEqual([limiter.allow('ann') for _ in range(3)], [True, True, False])
        self.assertEqual(limiter.remaining('ann'), 0)
        wait = limiter.retry_after('ann')
        self.assertGreater(wait, 0)
        self.assertLessEqual(wait, 3600)


if __name__ == '__main__':
    unittest.main()
