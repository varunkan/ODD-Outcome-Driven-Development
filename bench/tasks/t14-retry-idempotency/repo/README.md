# jobrun

The job runner behind our tills. A till submits jobs (charge an invoice, mail a receipt, refund) to a queue whose
only storage is a journal file; a runner works through the queue and calls the payment and mail providers. Python 3
standard library only.

```python
from jobrun import JobQueue, Runner, Ledger, Mailer

queue = JobQueue('/var/lib/till/journal.jsonl')
queue.submit('job-0001', 'charge_invoice', {'invoice': 'INV-1', 'account': 'acme', 'amount': 1200})
runner = Runner(queue, services={'ledger': Ledger(), 'mailer': Mailer()})
runner.run_pending()          # {'done': 1, 'failed': 0}
queue.state('job-0001')       # 'done'
```

## What is in it

- `jobrun/journal.py`: the journal, one JSON object per line. Its format is described at the top of the file; every
  till has journals on disk in it.
- `jobrun/queue.py`: `JobQueue(path)`. Rebuilds each job's state (`queued`, `running`, `done`, `failed`) from the
  journal when opened. A job that was started and never finished was cut off by a crash and is queued again.
- `jobrun/runner.py`: `Runner(queue, services, handlers=None)`, with `run_one(job_id)` and `run_pending()`.
- `jobrun/handlers.py`: the job kinds and their payloads: `charge_invoice`, `split_charge`, `refund`,
  `send_receipt`, `notify`.
- `jobrun/fakes.py`: in-memory `Ledger` (payments) and `Mailer` that behave like the real providers, including
  idempotency keys and injected failures (`fail_next`, `Crash`).
- `jobrun/errors.py`: `TransientError` (worth trying again, e.g. `ProviderUnavailable`) and `PermanentError`.
- `python3 -m jobrun report <journal>`: a summary for the night shift.

## Providers

Both real providers accept an idempotency key on every call (`key=`) and keep keys for 30 days: a second call with
the same key and the same request does nothing and returns the first answer; the same key with a different request
is refused with `IdempotencyConflict`. The fakes do the same.

## Tests

```
python3 -m unittest discover -s tests
```
