import unittest

from pricebook import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class TTLCacheTest(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.cache = TTLCache(ttl=60, clock=self.clock)

    def test_put_then_get(self):
        self.cache.put('a', 1)
        self.assertEqual(self.cache.get('a'), 1)
        self.assertIn('a', self.cache)
        self.assertIsNone(self.cache.get('b'))
        self.assertEqual(self.cache.get('b', 'fallback'), 'fallback')

    def test_entry_expires_after_ttl(self):
        self.cache.put('a', 1)
        self.clock.now += 59
        self.assertEqual(self.cache.get('a'), 1)
        self.clock.now += 1
        self.assertIsNone(self.cache.get('a'))
        self.assertEqual(len(self.cache), 0)

    def test_discard_and_clear(self):
        self.cache.put('a', 1)
        self.cache.put('b', 2)
        self.cache.discard('a')
        self.cache.discard('never put')
        self.assertNotIn('a', self.cache)
        self.assertEqual(len(self.cache), 1)
        self.cache.clear()
        self.assertEqual(len(self.cache), 0)

    def test_ttl_must_be_positive(self):
        with self.assertRaises(ValueError):
            TTLCache(ttl=0)


if __name__ == '__main__':
    unittest.main()
