import io

from jobrun import JobQueue, Ledger, Mailer, Runner
from jobrun.report import main

from helpers import TempDirTest


class RunnerTest(TempDirTest):
    def setUp(self):
        super().setUp()
        self.ledger, self.mailer = Ledger(), Mailer()
        self.queue = JobQueue(self.path())
        self.runner = Runner(self.queue, services={'ledger': self.ledger, 'mailer': self.mailer})

    def test_charge_invoice(self):
        self.queue.submit('j1', 'charge_invoice', {'invoice': 'INV-1', 'account': 'acme', 'amount': 1200})
        self.assertEqual(self.runner.run_pending(), {'done': 1, 'failed': 0})
        self.assertEqual(self.queue.state('j1'), 'done')
        self.assertEqual(self.ledger.balance('acme'), 1200)
        self.assertEqual(self.queue.get('j1').output['invoice'], 'INV-1')

    def test_split_charge(self):
        self.queue.submit('j1', 'split_charge', {'invoice': 'INV-2', 'parts': [
            {'account': 'acme', 'amount': 700}, {'account': 'globex', 'amount': 300}]})
        self.runner.run_pending()
        self.assertEqual((self.ledger.balance('acme'), self.ledger.balance('globex')), (700, 300))

    def test_send_receipt_charges_and_mails(self):
        self.queue.submit('j1', 'send_receipt', {'invoice': 'INV-3', 'account': 'acme', 'amount': 1050,
                                                 'email': 'ap@acme.example.com'})
        self.runner.run_pending()
        self.assertEqual(self.ledger.balance('acme'), 1050)
        self.assertEqual(len(self.mailer.outbox), 1)
        self.assertIn('10.50', self.mailer.outbox[0]['body'])

    def test_refund_and_notify(self):
        self.queue.submit('j1', 'refund', {'invoice': 'INV-4', 'account': 'acme', 'amount': 300})
        self.queue.submit('j2', 'notify', {'email': 'x@example.com', 'subject': 'Refund', 'body': 'Sent.'})
        self.runner.run_pending()
        self.assertEqual(self.ledger.balance('acme'), -300)
        self.assertEqual(self.mailer.outbox[0]['subject'], 'Refund')

    def test_bad_payload_fails_the_job(self):
        self.queue.submit('j1', 'charge_invoice', {'invoice': 'INV-5', 'account': 'acme', 'amount': -5})
        self.assertEqual(self.runner.run_pending(), {'done': 0, 'failed': 1})
        self.assertIn('amount', self.queue.get('j1').error)
        self.assertEqual(self.ledger.entries, [])

    def test_unknown_kind_fails_the_job(self):
        self.queue.submit('j1', 'teleport', {})
        self.runner.run_pending()
        self.assertEqual(self.queue.state('j1'), 'failed')

    def test_jobs_run_in_submission_order_and_only_once(self):
        seen = []
        self.runner.register('probe', lambda job, ctx: seen.append(job.id))
        for job_id in ('c', 'a', 'b'):
            self.queue.submit(job_id, 'probe')
        self.runner.run_pending()
        self.runner.run_pending()
        self.assertEqual(seen, ['c', 'a', 'b'])

    def test_report(self):
        self.queue.submit('j1', 'teleport', {})
        self.queue.submit('j2', 'notify', {'email': 'x@example.com', 'subject': 's'})
        self.runner.run_one('j1')
        out = io.StringIO()
        self.assertEqual(main(['report', self.path()], out=out), 0)
        text = out.getvalue()
        self.assertIn('2 jobs: 1 queued, 0 running, 0 done, 1 failed', text)
        self.assertIn('failed  j1 (teleport)', text)
        self.assertIn('waiting j2 (notify)', text)
