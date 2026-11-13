import unittest

from apigate.gateway import Gateway, Request
from apigate.keys import KeyStore, UnknownKey


class KeyStoreTests(unittest.TestCase):

    def test_keys_are_added_looked_up_and_revoked(self):
        keys = KeyStore()
        keys.add('k-ann-2', 'ann', 'pro')
        keys.add('k-ann-1', 'ann', 'free')
        keys.add('k-bob', 'bob', 'free')
        self.assertEqual(keys.lookup('k-ann-2').plan.name, 'pro')
        self.assertEqual(keys.keys_of('ann'), ['k-ann-1', 'k-ann-2'])
        self.assertEqual(len(keys), 3)
        keys.revoke('k-bob')
        self.assertFalse(keys.lookup('k-bob').active)
        with self.assertRaises(UnknownKey):
            keys.lookup('k-nobody')
        with self.assertRaises(ValueError):
            keys.add('k-bob', 'bob', 'free')


class GatewayTests(unittest.TestCase):

    def setUp(self):
        self.keys = KeyStore()
        self.keys.add('k-ann', 'ann', 'free')
        self.gateway = Gateway(self.keys, lambda request: 'you asked for ' + request.path)

    def test_a_known_key_reaches_the_handler(self):
        response = self.gateway.handle(Request('k-ann', '/orders'))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, 'you asked for /orders')
        self.assertTrue(response.ok)

    def test_unknown_and_revoked_keys_are_turned_away(self):
        self.assertEqual(self.gateway.handle(Request('k-nobody', '/orders')).status, 401)
        self.keys.revoke('k-ann')
        response = self.gateway.handle(Request('k-ann', '/orders'))
        self.assertEqual((response.status, response.body), (403, 'api key revoked'))
        self.assertFalse(response.ok)
        self.assertEqual(self.gateway.stats(), {401: 1, 403: 1})


if __name__ == '__main__':
    unittest.main()
