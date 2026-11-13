"""Acceptance tests for the plan-limit request: the gateway. Copied into the repository after the session ends."""
import unittest

from apigate.gateway import Gateway, Request
from apigate.keys import KeyStore
from apigate.plans import PLANS, Plan


class FakeClock:
    """A clock the test moves by hand. Calling it returns the current time in seconds."""

    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now


class GatewayLimitTests(unittest.TestCase):

    def setUp(self):
        self.clock = FakeClock(50.0)
        self.keys = KeyStore()
        self.keys.add('k-ann', 'ann', Plan('trial', 3, 10))
        self.keys.add('k-bob', 'bob', Plan('trial', 3, 10))
        self.served = []
        self.gateway = Gateway(self.keys, self.handler, clock=self.clock)

    def handler(self, request):
        self.served.append(request.key)
        return 'served ' + request.path

    def ask(self, key, at=None):
        if at is not None:
            self.clock.now = at
        return self.gateway.handle(Request(key, '/orders'))

    def test_requests_inside_the_plan_are_served_with_the_rate_headers(self):
        left = []
        for _ in range(3):
            response = self.ask('k-ann')
            self.assertEqual(response.status, 200)
            self.assertEqual(response.body, 'served /orders')
            self.assertEqual(response.headers['X-RateLimit-Limit'], '3')
            left.append(response.headers['X-RateLimit-Remaining'])
        self.assertEqual(left, ['2', '1', '0'])

    def test_a_request_over_the_plan_is_refused_without_calling_the_handler(self):
        for at in (50.0, 51.0, 52.0):
            self.assertEqual(self.ask('k-ann', at).status, 200)
        refused = self.ask('k-ann', 53.5)
        self.assertEqual(refused.status, 429)
        self.assertEqual(refused.body, 'rate limit exceeded')
        self.assertEqual(refused.headers['Retry-After'], '7')     # 6.5 seconds, rounded up
        self.assertEqual(self.ask('k-ann', 54.0).headers['Retry-After'], '6')
        self.assertEqual(self.served, ['k-ann'] * 3)

    def test_the_window_slides_and_refusals_are_not_counted(self):
        for at in (50.0, 51.0, 52.0):
            self.assertEqual(self.ask('k-ann', at).status, 200)
        for at in (55.0, 57.0, 59.0):
            self.assertEqual(self.ask('k-ann', at).status, 429)
        served = self.ask('k-ann', 60.0)      # the request counted at 50 has left the window
        self.assertEqual(served.status, 200)
        self.assertEqual(served.headers['X-RateLimit-Remaining'], '0')
        again = self.ask('k-ann', 60.0)       # 51, 52 and 60 are inside it
        self.assertEqual(again.status, 429)
        self.assertEqual(again.headers['Retry-After'], '1')
        self.assertEqual(self.ask('k-ann', 61.0).status, 200)

    def test_two_keys_on_the_same_plan_do_not_share_a_count(self):
        for _ in range(3):
            self.assertEqual(self.ask('k-ann').status, 200)
        self.assertEqual(self.ask('k-ann').status, 429)
        first = self.ask('k-bob')
        self.assertEqual(first.status, 200)
        self.assertEqual(first.headers['X-RateLimit-Remaining'], '2')

    def test_each_key_is_held_to_its_own_plan(self):
        self.keys.add('k-cat', 'cat', Plan('taster', 1, 30))
        first = self.ask('k-cat')
        self.assertEqual(first.status, 200)
        self.assertEqual(first.headers['X-RateLimit-Limit'], '1')
        self.assertEqual(first.headers['X-RateLimit-Remaining'], '0')
        refused = self.ask('k-cat', 60.0)
        self.assertEqual(refused.status, 429)
        self.assertEqual(refused.headers['Retry-After'], '20')
        self.assertEqual(self.ask('k-ann').status, 200)
        self.assertEqual(self.ask('k-cat', 80.0).status, 200)

    def test_unknown_and_revoked_keys_keep_their_answers(self):
        for _ in range(8):
            self.assertEqual(self.ask('k-nobody').status, 401)
        for _ in range(4):
            self.ask('k-ann')
        self.keys.revoke('k-ann')
        self.assertEqual(self.ask('k-ann').status, 403)
        self.assertEqual(self.served, ['k-ann'] * 3)

    def test_a_plan_without_a_limit_is_never_limited(self):
        self.keys.add('k-ops', 'ops', PLANS['internal'])
        statuses = {self.ask('k-ops').status for _ in range(200)}
        self.assertEqual(statuses, {200})
        self.assertEqual(len(self.served), 200)

    def test_stats_count_refusals_like_any_other_status(self):
        for _ in range(5):
            self.ask('k-ann')
        self.ask('k-nobody')
        self.assertEqual(self.gateway.stats(), {200: 3, 429: 2, 401: 1})


if __name__ == '__main__':
    unittest.main()
