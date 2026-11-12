from jobrun import BadTransition, DuplicateJob, JobQueue, UnknownJob

from helpers import Clock, TempDirTest


class QueueTest(TempDirTest):
    def test_submitted_jobs_are_queued_in_order(self):
        queue = JobQueue(self.path(), clock=Clock())
        queue.submit('b', 'notify', {'email': 'x@example.com', 'subject': 'hi'})
        queue.submit('a', 'notify', {'email': 'y@example.com', 'subject': 'hi'})
        self.assertEqual([job.id for job in queue.queued()], ['b', 'a'])
        self.assertEqual(queue.state('a'), 'queued')
        self.assertEqual(queue.counts(), {'queued': 2, 'running': 0, 'done': 0, 'failed': 0})

    def test_ids_are_never_reused(self):
        queue = JobQueue(self.path())
        queue.submit('a', 'notify')
        with self.assertRaises(DuplicateJob):
            queue.submit('a', 'refund')

    def test_bad_ids_are_refused(self):
        queue = JobQueue(self.path())
        for bad in ('', '   ', None, 7):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                queue.submit(bad, 'notify')

    def test_unknown_job(self):
        with self.assertRaises(UnknownJob):
            JobQueue(self.path()).state('nope')

    def test_life_of_a_job(self):
        queue = JobQueue(self.path())
        queue.submit('a', 'notify')
        queue.mark_started('a')
        self.assertEqual(queue.state('a'), 'running')
        queue.mark_done('a', {'message': 'm-1'})
        self.assertEqual(queue.state('a'), 'done')
        self.assertEqual(queue.get('a').output, {'message': 'm-1'})

    def test_finished_jobs_cannot_start_again(self):
        queue = JobQueue(self.path())
        queue.submit('a', 'notify')
        queue.mark_started('a')
        queue.mark_failed('a', 'boom')
        with self.assertRaises(BadTransition):
            queue.mark_started('a')
        self.assertEqual(queue.get('a').error, 'boom')

    def test_state_survives_reopening(self):
        queue = JobQueue(self.path())
        queue.submit('a', 'notify')
        queue.submit('b', 'notify')
        queue.mark_started('a')
        queue.mark_done('a')
        again = JobQueue(self.path())
        self.assertEqual(again.state('a'), 'done')
        self.assertEqual(again.state('b'), 'queued')

    def test_a_job_cut_off_by_a_crash_is_queued_again(self):
        queue = JobQueue(self.path())
        queue.submit('a', 'notify')
        queue.mark_started('a')
        again = JobQueue(self.path())
        self.assertEqual(again.state('a'), 'queued')
        self.assertEqual([job.id for job in again.queued()], ['a'])

    def test_copies_are_handed_out(self):
        queue = JobQueue(self.path())
        queue.submit('a', 'notify', {'email': 'x@example.com'})
        queue.get('a').payload['email'] = 'changed'
        self.assertEqual(queue.get('a').payload['email'], 'x@example.com')
