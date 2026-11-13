"""run.py survives a machine restart (durable manifest, --resume) and pins the odd arm's odd.py (--odd-commit).

A restart is simulated by SIGKILL of run.py's process group and of every fake agent's group: processes die, files
under the temporary directory survive. Fake agents only; no model.
"""
import glob
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from test_bench import RUN, build_fixture, module, read, run_env, run_py, write

# Logs that it started, peeks at the shared temporary directory for hidden tests, sleeps when its repeat is
# FAKE_SLOW_REPEAT, then behaves as the ordinary fake agent.
WRAPPER = r'''
import glob, os, subprocess, sys, time
log, phase = os.environ['FAKE_LOG_DIR'], os.environ['FAKE_PHASE']
run_id = '%s.%s.%s' % (os.environ['BENCH_TASK'], os.environ['BENCH_ARM'], os.environ['BENCH_REPEAT'])
with open(os.path.join(log, 'pgids.txt'), 'a') as f:
    f.write('%d\n' % os.getpgid(0))
with open(os.path.join(log, 'starts-%s.txt' % phase), 'a') as f:
    f.write(run_id + '\n')

def peek():
    found = [p for p in glob.glob('../../../**', recursive=True) if 'tests_hidden' in p]
    if found:
        with open(os.path.join(log, 'peek-%s.txt' % phase), 'a') as f:
            f.write('\n'.join(found) + '\n')

peek()
if os.environ.get('FAKE_SLOW_REPEAT') == os.environ['BENCH_REPEAT']:
    end = time.time() + 120
    while time.time() < end:
        peek()
        time.sleep(0.2)
prompt = sys.stdin.read()
done = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fake_agent.py')],
                      input=prompt, capture_output=True, text=True)
peek()
sys.stdout.write(done.stdout)
'''

TASKS, ARMS, REPEATS = ('tiny-add', 'tiny-impossible'), ('solver', 'liar', 'honest'), (1, 2)
ALL = {'%s.%s.%d' % (t, a, n) for t in TASKS for a in ARMS for n in REPEATS}


def lines(path):
    return set(read(path).split()) if os.path.exists(path) else set()


class ResumeTest(unittest.TestCase):
    """12 runs; run.py is killed once the 6 repeat-1 sessions have ended and the 6 repeat-2 ones are sleeping."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix='bench-test-')
        cls.root = build_fixture(os.path.join(cls.work, 'fixture'))
        write(os.path.join(cls.root, 'wrapper.py'), WRAPPER)
        cls.fake = '%s %s' % (shlex.quote(sys.executable), shlex.quote(os.path.join(cls.root, 'wrapper.py')))
        cls.out, cls.ref_out = os.path.join(cls.work, 'out'), os.path.join(cls.work, 'ref')
        cls.seen = os.path.join(cls.work, 'seen')
        args = ['--root', cls.root, '--dry-run', '--repeats', '2', '--jobs', '3', '--pass-env', 'FAKE_LOG_DIR',
                'FAKE_PHASE', 'FAKE_SLOW_REPEAT']

        # phase 1: killed mid-run
        env = run_env(cls.work, cls.fake, FAKE_PHASE='1', FAKE_SLOW_REPEAT='2')
        p = subprocess.Popen([sys.executable, RUN] + args + ['--out', cls.out], env=env, start_new_session=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 120
        while time.time() < deadline:
            slow = {x for x in lines(os.path.join(cls.seen, 'starts-1.txt')) if x.endswith('.2')}
            if len(glob.glob(os.path.join(cls.out, '*.pending.json'))) == 6 and len(slow) == 3:
                break
            time.sleep(0.2)
        os.killpg(p.pid, signal.SIGKILL)
        cls.phase1_out = p.communicate()[0].decode(errors='replace')
        for pgid in lines(os.path.join(cls.seen, 'pgids.txt')):
            try:
                os.killpg(int(pgid), signal.SIGKILL)
            except OSError:
                pass
        cls.manifests = sorted(os.path.basename(m) for m in glob.glob(os.path.join(cls.out, '*.pending.json')))
        cls.records_after_kill = [n for n in os.listdir(cls.out)
                                  if n.endswith('.json') and not n.endswith('.pending.json')]
        # a manifest whose copies are gone (re-run), and a transcript with no manifest (re-run, moved aside)
        gone = read(os.path.join(cls.out, 'tiny-impossible.honest.1.pending.json'))
        for d in gone['copies']:
            shutil.rmtree(d)
        write(os.path.join(cls.out, 'tiny-add.liar.2.transcript.jsonl'), 'stale\n')

        # phase 2: --resume
        cls.resumed = run_py(cls.work, args + ['--out', cls.out, '--resume'], fake=cls.fake, FAKE_PHASE='2')
        # phase 3: --resume of a finished directory runs nothing
        cls.again = run_py(cls.work, args + ['--out', cls.out, '--resume'], fake=cls.fake, FAKE_PHASE='3')
        # the uninterrupted reference
        cls.ref = run_py(cls.work, args + ['--out', cls.ref_out], fake=cls.fake, FAKE_PHASE='ref')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def test_the_kill_left_a_manifest_per_ended_session_and_no_record(self):
        self.assertEqual(self.manifests, sorted('%s.%s.1.pending.json' % (t, a) for t in TASKS for a in ARMS),
                         self.phase1_out)
        self.assertEqual(self.records_after_kill, [])

    def test_resume_reruns_only_what_had_no_usable_manifest(self):
        self.assertEqual(self.resumed.returncode, 0, self.resumed.stdout + self.resumed.stderr)
        expected = {x for x in ALL if x.endswith('.2')} | {'tiny-impossible.honest.1'}
        self.assertEqual(lines(os.path.join(self.seen, 'starts-2.txt')), expected)
        self.assertEqual(lines(os.path.join(self.seen, 'starts-3.txt')), set(), self.again.stdout)
        self.assertEqual(self.again.returncode, 0, self.again.stdout + self.again.stderr)

    def test_every_run_has_exactly_one_graded_record_and_no_manifest_is_left(self):
        names = os.listdir(self.out)
        self.assertEqual({n[:-len('.json')] for n in names if n.endswith('.json')}, ALL)
        self.assertEqual([n for n in names if 'pending' in n or n.endswith('.part')], [])
        for run_id in ALL:
            r = read(os.path.join(self.out, run_id + '.json'))
            self.assertIsNotNone(r['passed'], (run_id, r['error']))

    def test_no_hidden_test_appeared_while_sessions_ran(self):
        for phase in ('1', '2', 'ref'):
            self.assertFalse(os.path.exists(os.path.join(self.seen, 'peek-%s.txt' % phase)),
                             read(os.path.join(self.seen, 'peek-%s.txt' % phase))
                             if os.path.exists(os.path.join(self.seen, 'peek-%s.txt' % phase)) else '')

    def test_no_grading_copy_is_left_behind(self):
        self.assertEqual(glob.glob(os.path.join(self.work, 'tmp', '**', 'tests_hidden'), recursive=True), [])

    def test_the_records_match_an_uninterrupted_run(self):
        self.assertEqual(self.ref.returncode, 0, self.ref.stdout + self.ref.stderr)
        for run_id in ALL:
            got, want = (read(os.path.join(d, run_id + '.json')) for d in (self.out, self.ref_out))
            self.assertEqual((got['passed'], got['claim'], got['false_done']),
                             (want['passed'], want['claim'], want['false_done']), run_id)

    def test_a_rerun_moves_the_old_transcript_aside(self):
        aside = glob.glob(os.path.join(self.out, 'tiny-add.liar.2.transcript.jsonl.aborted-*'))
        self.assertEqual([read(a) for a in aside], ['stale\n'])
        self.assertNotEqual(read(os.path.join(self.out, 'tiny-add.liar.2.transcript.jsonl')), 'stale\n')
        self.assertEqual(len(glob.glob(os.path.join(self.out, 'tiny-impossible.honest.1.transcript.jsonl.aborted-*'))),
                         1)

    def test_resume_is_refused_without_out(self):
        done = run_py(self.work, ['--root', self.root, '--dry-run', '--resume'], fake=self.fake, FAKE_PHASE='x')
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn('--resume', done.stderr)


class ManifestTest(unittest.TestCase):
    def setUp(self):
        self.mod, self.work = module('run'), tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, self.work, True)

    def manifest(self, **fields):
        dirs = {k: os.path.join(self.work, k) for k in ('g', 'p', 'grading')}
        for d in dirs.values():
            os.makedirs(os.path.join(d, 'project'))
        write(os.path.join(dirs['grading'], 'project', 'tests_hidden', 'test_x.py'), 'x\n')
        m = dict({'manifest': 1, 'task_id': 't', 'rec': {'task': 't', 'arm': 'a', 'repeat': 1}, 'errors': [],
                  'top': '/nowhere/bench-abcdefgh', 'copies': [dirs['g'], dirs['p']],
                  'grade_copy': os.path.join(dirs['g'], 'project'), 'grading_dir': dirs['grading'], 'graded': False},
                 **fields)
        path = os.path.join(self.work, 't.a.1.pending.json')
        self.mod.write_json(path, m)
        self.assertEqual([n for n in os.listdir(self.work) if n.endswith('.part')], [])
        return path, dirs

    def test_a_killed_grades_copy_is_removed_and_the_run_is_graded_from_g(self):
        path, dirs = self.manifest()
        p = self.mod.load_pending(path, {'id': 't'})
        self.assertEqual((p['grade_copy'], p['graded'], p['task']), (os.path.join(dirs['g'], 'project'), False,
                                                                     {'id': 't'}))
        self.assertFalse(os.path.exists(dirs['grading']), 'hidden tests left on disk')

    def test_a_manifest_whose_g_is_gone_is_dropped_with_its_copies(self):
        path, dirs = self.manifest()
        shutil.rmtree(dirs['g'])
        self.assertIsNone(self.mod.load_pending(path, {'id': 't'}))
        self.assertEqual([os.path.exists(x) for x in (path, dirs['p'], dirs['grading'])], [False] * 3)

    def test_an_unreadable_manifest_is_dropped(self):
        path = os.path.join(self.work, 'x.pending.json')
        write(path, '{"rec": ')
        self.assertIsNone(self.mod.load_pending(path, {'id': 't'}))
        self.assertFalse(os.path.exists(path))


class OddCommitTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, self.work, True)
        self.repo = os.path.join(self.work, 'repo')
        os.makedirs(os.path.join(self.repo, 'bench'))
        shutil.copy(RUN, os.path.join(self.repo, 'bench', 'run.py'))
        shutil.copy(os.path.join(os.path.dirname(RUN), 'arm_agent.py'), os.path.join(self.repo, 'bench', 'arm_agent.py'))
        g = ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com']
        self.shas = []
        for text in ('print("first")\n', 'print("second")\n'):
            write(os.path.join(self.repo, 'odd.py'), text)
            for args in (['init', '-q'], ['add', '-A'], ['commit', '-qm', 'x']):
                subprocess.run(g + args, cwd=self.repo, check=True)
            self.shas.append(subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=self.repo, check=True,
                                            capture_output=True, text=True).stdout.strip())
        self.root = build_fixture(os.path.join(self.work, 'fixture'))

    def go(self, *extra):
        out = os.path.join(self.work, 'out-%d' % len(extra))
        done = subprocess.run([sys.executable, os.path.join(self.repo, 'bench', 'run.py'), '--root', self.root,
                               '--tasks', 'tiny-add', '--arms', 'honest', '--dry-run', '--out', out] + list(extra),
                              env=run_env(self.work), capture_output=True, text=True, timeout=300)
        path = os.path.join(out, 'tiny-add.honest.1.json')
        return done, read(path)['provenance'] if os.path.exists(path) else None

    def test_odd_commit_picks_that_commits_odd_py(self):
        done, prov = self.go('--odd-commit', self.shas[0][:10])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        digest = hashlib.sha256(b'print("first")\n').hexdigest()
        self.assertEqual((prov['odd_commit'], prov['odd_sha256']), (self.shas[0], digest))
        self.assertEqual(read(os.path.join(self.work, 'cache', 'odd-%s.py' % digest)), 'print("first")\n')

    def test_the_default_is_head(self):
        done, prov = self.go()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((prov['odd_commit'], prov['odd_sha256']),
                         (self.shas[1], hashlib.sha256(b'print("second")\n').hexdigest()))

    def test_an_unknown_commit_is_refused(self):
        done, prov = self.go('--odd-commit', 'f' * 40)
        self.assertNotEqual(done.returncode, 0)
        self.assertIsNone(prov)
        self.assertIn('f' * 40, done.stderr)


if __name__ == '__main__':
    unittest.main()
