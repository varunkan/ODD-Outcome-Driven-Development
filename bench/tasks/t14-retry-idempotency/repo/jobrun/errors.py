"""The exceptions jobrun raises, and the ones its providers raise."""


class JobError(Exception):
    """Base class for every error jobrun defines."""


class UnknownJob(JobError, KeyError):
    """No job with that id was ever submitted."""

    def __str__(self):
        return 'no job %r' % (self.args[0] if self.args else None)


class DuplicateJob(JobError, ValueError):
    """A job with that id was already submitted. Ids are never reused."""


class BadTransition(JobError):
    """A job was moved to a state it cannot reach from the one it is in."""


class TransientError(JobError):
    """A failure that may go away when the same call is made again later (timeouts, maintenance windows)."""


class ProviderUnavailable(TransientError):
    """The provider did not answer, or answered that it is unavailable."""


class PermanentError(JobError):
    """A failure that the same call, made again, will meet again."""


class IdempotencyConflict(PermanentError):
    """An idempotency key was sent again with a different request than the first time."""
