"""The job queue: the state of every job, rebuilt from the journal when it is opened."""

import copy
import time
from collections import OrderedDict

from .errors import BadTransition, DuplicateJob, UnknownJob
from .journal import Journal

STATES = ('queued', 'running', 'done', 'failed')


class Job:
    """One job. `state` is one of STATES; `output` is what the handler returned; `error` why it failed."""

    def __init__(self, job_id, kind, payload):
        self.id = job_id
        self.kind = kind
        self.payload = payload
        self.state = 'queued'
        self.output = None
        self.error = None

    def __repr__(self):
        return 'Job(%r, %r, state=%r)' % (self.id, self.kind, self.state)


class JobQueue:
    """Jobs in submission order. Opening a queue replays its journal; a job the journal shows as started but never
    finished was cut off by a crash, so it is put back in the queue and will run again."""

    def __init__(self, path, clock=time.time):
        self._journal = Journal(path)
        self._clock = clock
        self._jobs = OrderedDict()
        for record in self._journal.records():
            self._apply(record)
        for job in self._jobs.values():
            if job.state == 'running':
                job.state = 'queued'

    @property
    def path(self):
        return self._journal.path

    # -- reading -------------------------------------------------------------------------------------------------

    def get(self, job_id):
        return copy.deepcopy(self._job(job_id))

    def state(self, job_id):
        return self._job(job_id).state

    def queued(self):
        return [copy.deepcopy(job) for job in self._jobs.values() if job.state == 'queued']

    def jobs(self):
        return [copy.deepcopy(job) for job in self._jobs.values()]

    def counts(self):
        out = dict.fromkeys(STATES, 0)
        for job in self._jobs.values():
            out[job.state] += 1
        return out

    def __contains__(self, job_id):
        return job_id in self._jobs

    def __len__(self):
        return len(self._jobs)

    # -- writing -------------------------------------------------------------------------------------------------

    def submit(self, job_id, kind, payload=None):
        if not isinstance(job_id, str) or not job_id.strip():
            raise ValueError('a job id is a non-empty string')
        if not isinstance(kind, str) or not kind:
            raise ValueError('a job kind is a non-empty string')
        if job_id in self._jobs:
            raise DuplicateJob('job %r was already submitted' % job_id)
        payload = dict(payload or {})
        self._write({'job': job_id, 'event': 'submitted', 'kind': kind, 'payload': payload})
        return self.get(job_id)

    def mark_started(self, job_id):
        self._move(job_id, 'queued', {'event': 'started'})

    def mark_done(self, job_id, output=None):
        self._move(job_id, 'running', {'event': 'done', 'output': output})

    def mark_failed(self, job_id, error):
        self._move(job_id, ('queued', 'running'), {'event': 'failed', 'error': str(error)})

    # -- inside --------------------------------------------------------------------------------------------------

    def _job(self, job_id):
        try:
            return self._jobs[job_id]
        except KeyError:
            raise UnknownJob(job_id) from None

    def _move(self, job_id, allowed, record):
        job = self._job(job_id)
        allowed = (allowed,) if isinstance(allowed, str) else allowed
        if job.state not in allowed:
            raise BadTransition('job %r is %s, cannot record %s' % (job_id, job.state, record['event']))
        record = dict(record, job=job_id)
        self._write(record)

    def _write(self, record):
        record = dict(record, at=self._clock())
        self._journal.append(record)
        self._apply(record)

    def _apply(self, record):
        event, job_id = record['event'], record['job']
        if event == 'submitted':
            self._jobs[job_id] = Job(job_id, record.get('kind'), record.get('payload') or {})
            return
        job = self._jobs.get(job_id)
        if job is None:  # an event for a job whose submission line was lost: nothing to attach it to
            return
        if event == 'started':
            job.state = 'running'
        elif event == 'done':
            job.state, job.output, job.error = 'done', record.get('output'), None
        elif event == 'failed':
            job.state, job.error = 'failed', record.get('error')
