"""The runner: takes queued jobs one at a time and runs their handlers."""

import logging

from .handlers import DEFAULT_HANDLERS

log = logging.getLogger('jobrun')


class Context:
    """What a handler gets besides the job: the providers it may call."""

    def __init__(self, job, services):
        self.job = job
        self.services = services
        self.ledger = services.get('ledger')
        self.mailer = services.get('mailer')


class Runner:
    """Runs the jobs of one queue. `services` maps names ('ledger', 'mailer') to provider objects."""

    def __init__(self, queue, services=None, handlers=None):
        self.queue = queue
        self.services = dict(services or {})
        self.handlers = dict(DEFAULT_HANDLERS if handlers is None else handlers)

    def register(self, kind, handler):
        if not callable(handler):
            raise TypeError('a handler is callable')
        self.handlers[kind] = handler

    def run_one(self, job_id):
        """Run one queued job to its end. Returns its final state, 'done' or 'failed'."""
        job = self.queue.get(job_id)
        handler = self.handlers.get(job.kind)
        if handler is None:
            self.queue.mark_failed(job_id, 'no handler for kind %r' % job.kind)
            return 'failed'
        self.queue.mark_started(job_id)
        try:
            output = handler(job, Context(job, self.services))
        except Exception as exc:
            log.warning('job %s failed: %s', job_id, exc)
            self.queue.mark_failed(job_id, '%s: %s' % (type(exc).__name__, exc))
            return 'failed'
        self.queue.mark_done(job_id, output)
        return 'done'

    def run_pending(self):
        """Run every queued job, in submission order. Returns {'done': n, 'failed': n}."""
        summary = {'done': 0, 'failed': 0}
        for job in self.queue.queued():
            summary[self.run_one(job.id)] += 1
        return summary
