"""In-memory stand-ins for the payment provider and the mail provider, for tests and local runs.

They behave like the real providers in the ways that matter here:

- Every call may carry an idempotency key (`key=`). The first call with a key does the work and remembers its
  answer; a later call with the same key and the same request does nothing and returns the remembered answer; the
  same key with a different request raises IdempotencyConflict. A call without a key always does the work.
- `fail_next(exc)` makes the next call raise `exc` without doing anything. `fail_next(exc, after=True)` makes the
  next call do its work and then raise `exc`, as when the provider took the request but the answer never arrived.
  Pass `Crash()` to stand for the process dying at that point.

What actually happened is in `Ledger.entries` and `Mailer.outbox`; `calls` counts every call, failed ones included.
"""

from .errors import IdempotencyConflict


class Crash(BaseException):
    """Stands for the process dying. It is a BaseException so that nothing in jobrun catches it."""


class _Fault:
    def __init__(self, exc, after):
        self.exc = exc
        self.after = after


class _Provider:
    def __init__(self):
        self.calls = 0
        self._faults = []
        self._answers = {}
        self._next_id = 0

    def fail_next(self, exc, after=False, times=1):
        for _ in range(times):
            self._faults.append(_Fault(exc, after))

    def _call(self, request, key, work):
        self.calls += 1
        fault = self._faults.pop(0) if self._faults else None
        if fault is not None and not fault.after:
            raise fault.exc
        if key is not None and key in self._answers:
            first_request, answer = self._answers[key]
            if first_request != request:
                raise IdempotencyConflict('key %r was first used for %r, now for %r' % (key, first_request, request))
        else:
            answer = work()
            if key is not None:
                self._answers[key] = (request, answer)
        if fault is not None:
            raise fault.exc
        return dict(answer)

    def _new_id(self, prefix):
        self._next_id += 1
        return '%s-%d' % (prefix, self._next_id)


class Ledger(_Provider):
    """The payment provider. Amounts are whole cents."""

    def __init__(self):
        super().__init__()
        self.entries = []

    def charge(self, account, amount, key=None):
        return self._call(('charge', account, amount), key, lambda: self._book('charge', account, amount))

    def refund(self, account, amount, key=None):
        return self._call(('refund', account, amount), key, lambda: self._book('refund', account, -amount))

    def balance(self, account):
        return sum(entry['amount'] for entry in self.entries if entry['account'] == account)

    def _book(self, what, account, amount):
        entry = {'id': self._new_id(what[:2]), 'type': what, 'account': account, 'amount': amount}
        self.entries.append(entry)
        return entry


class Mailer(_Provider):
    """The mail provider."""

    def __init__(self):
        super().__init__()
        self.outbox = []

    def send(self, to, subject, body, key=None):
        return self._call(('send', to, subject, body), key, lambda: self._post(to, subject, body))

    def _post(self, to, subject, body):
        message = {'id': self._new_id('m'), 'to': to, 'subject': subject, 'body': body}
        self.outbox.append(message)
        return message
