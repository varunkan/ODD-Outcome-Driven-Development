import unittest

from jobrun import Crash, IdempotencyConflict, Ledger, Mailer, ProviderUnavailable


class LedgerTest(unittest.TestCase):
    def test_charge_and_refund(self):
        ledger = Ledger()
        ledger.charge('acme', 1200)
        ledger.refund('acme', 200)
        self.assertEqual(ledger.balance('acme'), 1000)
        self.assertEqual([e['type'] for e in ledger.entries], ['charge', 'refund'])

    def test_without_a_key_every_call_charges(self):
        ledger = Ledger()
        ledger.charge('acme', 100)
        ledger.charge('acme', 100)
        self.assertEqual(ledger.balance('acme'), 200)

    def test_same_key_same_request_charges_once(self):
        ledger = Ledger()
        first = ledger.charge('acme', 100, key='k1')
        second = ledger.charge('acme', 100, key='k1')
        self.assertEqual(first, second)
        self.assertEqual(len(ledger.entries), 1)
        self.assertEqual(ledger.calls, 2)

    def test_same_key_other_request_conflicts(self):
        ledger = Ledger()
        ledger.charge('acme', 100, key='k1')
        with self.assertRaises(IdempotencyConflict):
            ledger.charge('acme', 150, key='k1')
        with self.assertRaises(IdempotencyConflict):
            ledger.refund('acme', 100, key='k1')

    def test_fail_next_before_the_work(self):
        ledger = Ledger()
        ledger.fail_next(ProviderUnavailable('down'))
        with self.assertRaises(ProviderUnavailable):
            ledger.charge('acme', 100)
        self.assertEqual(ledger.entries, [])
        ledger.charge('acme', 100)
        self.assertEqual(len(ledger.entries), 1)

    def test_fail_next_after_the_work(self):
        ledger = Ledger()
        ledger.fail_next(ProviderUnavailable('timeout'), after=True)
        with self.assertRaises(ProviderUnavailable):
            ledger.charge('acme', 100)
        self.assertEqual(len(ledger.entries), 1)

    def test_crash_is_not_an_exception(self):
        self.assertFalse(issubclass(Crash, Exception))


class MailerTest(unittest.TestCase):
    def test_send_and_key(self):
        mailer = Mailer()
        mailer.send('x@example.com', 'hi', 'body', key='m1')
        mailer.send('x@example.com', 'hi', 'body', key='m1')
        mailer.send('x@example.com', 'hi', 'body')
        self.assertEqual(len(mailer.outbox), 2)

    def test_fail_several_times(self):
        mailer = Mailer()
        mailer.fail_next(ProviderUnavailable('down'), times=2)
        for _ in range(2):
            with self.assertRaises(ProviderUnavailable):
                mailer.send('x@example.com', 'hi', 'body')
        mailer.send('x@example.com', 'hi', 'body')
        self.assertEqual(mailer.calls, 3)
        self.assertEqual(len(mailer.outbox), 1)
