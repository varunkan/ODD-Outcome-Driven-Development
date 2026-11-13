import json
import os
import shutil
import tempfile
import unittest

from jobrun import Crash, JobQueue, Ledger, Mailer, ProviderUnavailable, Runner


class Sleeps:
    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='jobrun-t-')
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, 'journal.jsonl')
        self.ledger, self.mailer = Ledger(), Mailer()
        self.sleep = Sleeps()

    def open(self, **kw):
        """A till starting up: a fresh queue on the journal, a fresh runner, the same providers."""
        kw.setdefault('sleep', self.sleep)
        self.queue = JobQueue(self.path)
        self.runner = Runner(self.queue, services={'ledger': self.ledger, 'mailer': self.mailer}, **kw)
        return self.queue, self.runner

    def crash_then_restart(self, **kw):
        with self.assertRaises(Crash):
            self.runner.run_pending()
        self.open(**kw)
        return self.runner.run_pending()

    def charges(self):
        return [(e['type'], e['account'], e['amount']) for e in self.ledger.entries]


INVOICE = {'invoice': 'INV-1', 'account': 'acme', 'amount': 1200}
RECEIPT = {'invoice': 'INV-3', 'account': 'acme', 'amount': 1050, 'email': 'ap@acme.example.com'}
SPLIT = {'invoice': 'INV-2', 'parts': [{'account': 'acme', 'amount': 700}, {'account': 'globex', 'amount': 300}]}


class RetryTest(Base):
    def test_transient_failure_is_retried_and_succeeds(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(ProviderUnavailable('maintenance'), times=2)
        self.assertEqual(runner.run_pending(), {'done': 1, 'failed': 0})
        self.assertEqual(queue.state('j1'), 'done')
        self.assertEqual(self.charges(), [('charge', 'acme', 1200)])
        self.assertEqual(queue.attempts('j1'), 3)
        self.assertEqual(self.sleep.calls, [1.0, 2.0])

    def test_backoff_doubles_from_the_given_value(self):
        queue, runner = self.open(max_attempts=4, backoff=0.5)
        queue.submit('j1', 'notify', {'email': 'x@example.com', 'subject': 's', 'body': 'b'})
        self.mailer.fail_next(ProviderUnavailable('down'), times=3)
        self.assertEqual(runner.run_one('j1'), 'done')
        self.assertEqual(self.sleep.calls, [0.5, 1.0, 2.0])
        self.assertEqual(len(self.mailer.outbox), 1)

    def test_gives_up_after_max_attempts(self):
        queue, runner = self.open(max_attempts=3)
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(ProviderUnavailable('down'), times=5)
        self.assertEqual(runner.run_pending(), {'done': 0, 'failed': 1})
        self.assertEqual(queue.state('j1'), 'failed')
        self.assertEqual(self.ledger.calls, 3)
        self.assertEqual(queue.attempts('j1'), 3)
        self.assertEqual(self.ledger.entries, [])

    def test_other_errors_are_not_retried(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', dict(INVOICE, amount=0))
        self.assertEqual(runner.run_pending(), {'done': 0, 'failed': 1})
        self.assertEqual(queue.attempts('j1'), 1)
        self.assertEqual(self.sleep.calls, [])

    def test_one_job_failing_does_not_stop_the_next(self):
        queue, runner = self.open(max_attempts=2)
        queue.submit('j1', 'charge_invoice', INVOICE)
        queue.submit('j2', 'charge_invoice', dict(INVOICE, invoice='INV-9', account='globex'))
        self.ledger.fail_next(ProviderUnavailable('down'), times=2)
        self.assertEqual(runner.run_pending(), {'done': 1, 'failed': 1})
        self.assertEqual(self.charges(), [('charge', 'globex', 1200)])


class TimeoutAfterTheWorkTest(Base):
    def test_charge_taken_but_answer_lost_is_not_charged_again(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(ProviderUnavailable('timeout'), after=True)
        self.assertEqual(runner.run_pending(), {'done': 1, 'failed': 0})
        self.assertEqual(self.charges(), [('charge', 'acme', 1200)])
        self.assertEqual(queue.attempts('j1'), 2)

    def test_receipt_mail_fails_then_retry_does_not_charge_again(self):
        queue, runner = self.open()
        queue.submit('j1', 'send_receipt', RECEIPT)
        self.mailer.fail_next(ProviderUnavailable('down'))
        self.assertEqual(runner.run_pending(), {'done': 1, 'failed': 0})
        self.assertEqual(self.charges(), [('charge', 'acme', 1050)])
        self.assertEqual(len(self.mailer.outbox), 1)

    def test_receipt_mail_sent_but_answer_lost_is_not_sent_again(self):
        queue, runner = self.open()
        queue.submit('j1', 'send_receipt', RECEIPT)
        self.mailer.fail_next(ProviderUnavailable('timeout'), after=True)
        runner.run_pending()
        self.assertEqual(self.charges(), [('charge', 'acme', 1050)])
        self.assertEqual(len(self.mailer.outbox), 1)

    def test_split_charge_first_part_times_out_after_the_work(self):
        queue, runner = self.open()
        queue.submit('j1', 'split_charge', SPLIT)
        self.ledger.fail_next(ProviderUnavailable('timeout'), after=True)  # acme charged, the answer lost
        self.assertEqual(runner.run_pending(), {'done': 1, 'failed': 0})
        self.assertEqual(self.charges(), [('charge', 'acme', 700), ('charge', 'globex', 300)])
        self.assertEqual(queue.state('j1'), 'done')

    def test_split_charge_retry_after_second_part_fails(self):
        ledger = GlobexDownOnce()
        self.ledger = ledger
        queue, runner = self.open()
        queue.submit('j1', 'split_charge', SPLIT)
        self.assertEqual(runner.run_pending(), {'done': 1, 'failed': 0})
        self.assertEqual(self.charges(), [('charge', 'acme', 700), ('charge', 'globex', 300)])
        self.assertEqual(queue.attempts('j1'), 2)


class GlobexDownOnce(Ledger):
    """The first charge to globex is refused before any work; everything else goes through."""

    def __init__(self):
        super().__init__()
        self.refused = False

    def charge(self, account, amount, key=None):
        if account == 'globex' and not self.refused:
            self.refused = True
            raise ProviderUnavailable('globex bank down')
        return super().charge(account, amount, key=key)


class CrashTest(Base):
    def test_crash_after_the_charge_was_taken(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(Crash(), after=True)
        self.assertEqual(self.crash_then_restart(), {'done': 1, 'failed': 0})
        self.assertEqual(self.queue.state('j1'), 'done')
        self.assertEqual(self.charges(), [('charge', 'acme', 1200)])

    def test_crash_before_the_charge_still_charges_once_after_restart(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(Crash())
        self.crash_then_restart()
        self.assertEqual(self.queue.state('j1'), 'done')
        self.assertEqual(self.charges(), [('charge', 'acme', 1200)])

    def test_reported_case_power_lost_during_send_receipt(self):
        queue, runner = self.open()
        queue.submit('j1', 'send_receipt', RECEIPT)
        self.mailer.fail_next(Crash())  # the charge returned, the till died before the mail
        self.crash_then_restart()
        self.assertEqual(self.queue.state('j1'), 'done')
        self.assertEqual(self.charges(), [('charge', 'acme', 1050)])
        self.assertEqual(len(self.mailer.outbox), 1)

    def test_crash_after_the_mail_was_sent(self):
        queue, runner = self.open()
        queue.submit('j1', 'send_receipt', RECEIPT)
        self.mailer.fail_next(Crash(), after=True)
        self.crash_then_restart()
        self.assertEqual(self.charges(), [('charge', 'acme', 1050)])
        self.assertEqual(len(self.mailer.outbox), 1)
        self.assertEqual(self.queue.state('j1'), 'done')

    def test_crash_in_the_middle_of_a_split_charge(self):
        queue, runner = self.open()
        queue.submit('j1', 'split_charge', SPLIT)
        self.ledger.fail_next(Crash(), after=True)  # acme charged, then the till died
        self.crash_then_restart()
        self.assertEqual(self.charges(), [('charge', 'acme', 700), ('charge', 'globex', 300)])
        self.assertEqual(self.queue.state('j1'), 'done')

    def test_two_crashes_then_a_timeout(self):
        queue, runner = self.open()
        queue.submit('j1', 'send_receipt', RECEIPT)
        self.ledger.fail_next(Crash(), after=True)
        with self.assertRaises(Crash):
            runner.run_pending()
        queue, runner = self.open(max_attempts=5)
        self.mailer.fail_next(Crash(), after=True)
        with self.assertRaises(Crash):
            runner.run_pending()
        queue, runner = self.open(max_attempts=5)
        self.ledger.fail_next(ProviderUnavailable('timeout'), after=True)
        self.assertEqual(runner.run_pending(), {'done': 1, 'failed': 0})
        self.assertEqual(self.charges(), [('charge', 'acme', 1050)])
        self.assertEqual(len(self.mailer.outbox), 1)
        self.assertEqual(queue.attempts('j1'), 4)

    def test_jobs_finished_before_the_crash_are_not_run_again(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        queue.submit('j2', 'charge_invoice', dict(INVOICE, invoice='INV-2', account='globex'))
        runner.run_one('j1')
        self.ledger.fail_next(Crash(), after=True)
        self.crash_then_restart()
        self.assertEqual(self.charges(), [('charge', 'acme', 1200), ('charge', 'globex', 1200)])


class AttemptsAcrossRestartsTest(Base):
    def test_attempts_survive_reopening(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(Crash())
        with self.assertRaises(Crash):
            runner.run_pending()
        queue, runner = self.open()
        self.assertEqual(queue.attempts('j1'), 1)
        runner.run_pending()
        self.assertEqual(queue.attempts('j1'), 2)
        self.assertEqual(JobQueue(self.path).attempts('j1'), 2)

    def test_a_crashed_start_counts_towards_max_attempts(self):
        queue, runner = self.open(max_attempts=2)
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(Crash())
        with self.assertRaises(Crash):
            runner.run_pending()
        queue, runner = self.open(max_attempts=2)
        self.ledger.fail_next(ProviderUnavailable('down'), times=5)
        self.assertEqual(runner.run_pending(), {'done': 0, 'failed': 1})
        self.assertEqual(self.ledger.calls, 2)
        self.assertEqual(queue.attempts('j1'), 2)

    def test_a_job_out_of_attempts_is_not_started_after_a_restart(self):
        queue, runner = self.open(max_attempts=1)
        queue.submit('j1', 'charge_invoice', INVOICE)
        self.ledger.fail_next(Crash())
        with self.assertRaises(Crash):
            runner.run_pending()
        queue, runner = self.open(max_attempts=1)
        self.assertEqual(runner.run_pending(), {'done': 0, 'failed': 1})
        self.assertEqual(queue.state('j1'), 'failed')
        self.assertEqual(self.ledger.calls, 1)
        self.assertEqual(queue.attempts('j1'), 1)


def write_journal(path, lines):
    with open(path, 'w') as f:
        for line in lines:
            f.write(json.dumps(line, sort_keys=True, separators=(',', ':')) + '\n')


class OldJournalTest(Base):
    OLD = [
        {'job': 'old-1', 'event': 'submitted', 'kind': 'charge_invoice', 'at': 1.0,
         'payload': {'invoice': 'INV-7', 'account': 'acme', 'amount': 500}},
        {'job': 'old-1', 'event': 'started', 'at': 2.0},
        {'job': 'old-1', 'event': 'done', 'at': 3.0, 'output': {'invoice': 'INV-7', 'charge': 'ch-1'}},
        {'job': 'old-2', 'event': 'submitted', 'kind': 'notify', 'at': 4.0,
         'payload': {'email': 'x@example.com', 'subject': 'Hello', 'body': 'b'}},
        {'job': 'old-3', 'event': 'submitted', 'kind': 'charge_invoice', 'at': 5.0,
         'payload': {'invoice': 'INV-8', 'account': 'globex', 'amount': 900}},
        {'job': 'old-3', 'event': 'started', 'at': 6.0},
        {'job': 'old-4', 'event': 'submitted', 'kind': 'refund', 'at': 7.0,
         'payload': {'invoice': 'INV-7', 'account': 'acme', 'amount': 500}},
        {'job': 'old-4', 'event': 'started', 'at': 8.0},
        {'job': 'old-4', 'event': 'started', 'at': 9.0},
    ]

    def test_old_journal_opens_and_runs(self):
        write_journal(self.path, self.OLD)
        queue, runner = self.open(max_attempts=3)
        self.assertEqual(queue.state('old-1'), 'done')
        self.assertEqual(queue.attempts('old-1'), 1)
        self.assertEqual(queue.attempts('old-2'), 0)
        self.assertEqual(queue.attempts('old-3'), 1)
        self.assertEqual(queue.attempts('old-4'), 2)
        self.assertEqual(runner.run_pending(), {'done': 3, 'failed': 0})
        self.assertEqual(self.charges(), [('charge', 'globex', 900), ('refund', 'acme', -500)])
        self.assertEqual(len(self.mailer.outbox), 1)
        self.assertEqual(queue.attempts('old-4'), 3)

    def test_old_journal_job_out_of_attempts(self):
        write_journal(self.path, self.OLD)
        queue, runner = self.open(max_attempts=2)
        runner.run_pending()
        self.assertEqual(queue.state('old-4'), 'failed')
        self.assertEqual(queue.state('old-3'), 'done')
        self.assertEqual(self.charges(), [('charge', 'globex', 900)])


class DifferentJobsTest(Base):
    def test_refund_after_charge_for_the_same_invoice(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        queue.submit('j2', 'refund', INVOICE)
        self.assertEqual(runner.run_pending(), {'done': 2, 'failed': 0})
        self.assertEqual(self.charges(), [('charge', 'acme', 1200), ('refund', 'acme', -1200)])

    def test_two_notify_jobs_with_the_same_text_send_two_mails(self):
        queue, runner = self.open()
        payload = {'email': 'x@example.com', 'subject': 'Open late', 'body': 'Till 10pm today'}
        queue.submit('j1', 'notify', payload)
        queue.submit('j2', 'notify', payload)
        runner.run_pending()
        self.assertEqual(len(self.mailer.outbox), 2)

    def test_two_charge_jobs_on_one_account_are_two_charges(self):
        queue, runner = self.open()
        queue.submit('j1', 'charge_invoice', INVOICE)
        queue.submit('j2', 'charge_invoice', dict(INVOICE, invoice='INV-2'))
        self.ledger.fail_next(ProviderUnavailable('timeout'), after=True)
        runner.run_pending()
        self.assertEqual(self.charges(), [('charge', 'acme', 1200), ('charge', 'acme', 1200)])

    def test_one_journal_two_tills_runs(self):
        queue, runner = self.open()
        queue.submit('j1', 'send_receipt', RECEIPT)
        runner.run_pending()
        queue, runner = self.open()
        queue.submit('j2', 'send_receipt', RECEIPT)
        runner.run_pending()
        self.assertEqual(len(self.ledger.entries), 2)
        self.assertEqual(len(self.mailer.outbox), 2)


if __name__ == '__main__':
    unittest.main()
