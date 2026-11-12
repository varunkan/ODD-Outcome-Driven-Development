# Retry jobs that fail for a passing reason, and never charge a customer twice

Today a job that meets a provider outage (`ProviderUnavailable`, or any other `TransientError`) is marked `failed`
and the night shift resubmits it by hand. Please make `jobrun.Runner` try such jobs again by itself.

The part we care about most: a job must never do its side effect twice for one job id. Last month a till lost power
while running a `send_receipt` job; after the restart the queue ran it again and the customer was charged twice. We
also see the payment provider time out after it has already taken the money, and a plain retry of that would charge
twice too. Both providers accept an idempotency key on every call (see the README; `jobrun.fakes` behaves the same),
which is what we have never used.

What we need:

1. **Retries.** `Runner(queue, services=None, handlers=None, max_attempts=3, backoff=1.0, sleep=time.sleep)`. When a
   handler raises a `TransientError`, the runner waits and starts the job again, until it succeeds or it has been
   started `max_attempts` times; then the job is `failed`. The wait before the second start is `backoff` seconds and
   doubles before each start after that (1.0, 2.0, 4.0, ... with the default), and it is made by calling
   `sleep(seconds)`. Any other exception fails the job at once, with no retry and no wait. `run_one` and
   `run_pending` keep their return values: a job that succeeds on a later attempt counts as `done`.
2. **Attempts.** `queue.attempts(job_id)` returns how many times the job has been started. Every start counts,
   including one cut off by a crash, and the count survives reopening the queue: a job that has already been started
   `max_attempts` times is not started again after a restart, it is marked `failed`.
3. **Once per job id.** For one job id, each side effect the job's handler makes (each charge, each refund, each
   mail) happens exactly once once the job is `done`, however many attempts and restarts it took, and whichever point
   it failed or crashed at: before a provider call, after the provider did the work but before the answer arrived,
   or after a call returned but before the journal recorded the job as finished. This holds for every job kind in
   `jobrun.handlers`, including `split_charge`, which charges several accounts in one job, and `send_receipt`, which
   charges and then mails. Two different jobs are two different side effects, even when their payloads are alike
   (a `refund` for an invoice is not the same thing as the `charge_invoice` for it, and two `notify` jobs with the
   same text are two mails).
4. **Old journals.** Every till has journal files written by the current version, in the format described at the
   top of `jobrun/journal.py`. They must open and run as they do today; a job they show as started and never
   finished counts those starts as attempts.

To reproduce a crash in a test, the fakes have `fail_next(Crash(), after=True)` (the provider does the work, then
the process "dies") and `fail_next(Crash())` (it dies before the work). After a `Crash`, open a new
`JobQueue` on the same journal file and a new `Runner` with the same `Ledger` and `Mailer`, and call
`run_pending()` again, as a restarted till does.

The rest of the interface stays as it is: `JobQueue(path)`, `submit`, `state`, `get`, `queued`, `Runner.register`,
the job kinds and their payloads, and the fakes' `entries`, `outbox`, `calls`, `balance` and `fail_next`.
