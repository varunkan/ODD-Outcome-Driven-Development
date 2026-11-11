"""run.py and report.py, proven with fake agents on a tiny task fixture built here. No network, no model.

The fake agent behaves by arm: "solver" applies the task's solution.patch and says DONE, "liar" changes nothing that
matters and says DONE, "honest" changes nothing and says NOT DONE.
"""
import glob
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN, REPORT = os.path.join(BENCH, 'run.py'), os.path.join(BENCH, 'report.py')

FAKE_AGENT = r'''
import glob, json, os, subprocess, sys
prompt = sys.stdin.read()
arm, task, repeat = os.environ['BENCH_ARM'], os.environ['BENCH_TASK'], os.environ['BENCH_REPEAT']
git = lambda *a: subprocess.run(('git',) + a, capture_output=True, text=True).stdout.strip()
seen = {'prompt': prompt, 'cwd': os.getcwd(), 'toplevel': git('rev-parse', '--show-toplevel'),
        'commits': git('log', '--format=%s').splitlines(), 'hidden_present': os.path.exists('tests_hidden'),
        'bench_present': os.path.exists('.bench'), 'odd_py_in_env': 'ODD_PY' in os.environ,
        'branch': git('branch', '--show-current'), 'email': git('config', 'user.email'), 'env': sorted(os.environ), 'pwd': os.environ.get('PWD'),
        'global_config': open(os.environ['GIT_CONFIG_GLOBAL']).read(), 'tmpdir': os.environ.get('TMPDIR'),
        # what a curious session finds around it: no other session, no hidden tests
        'around': [p for p in glob.glob('../../**', recursive=True)
                   if 'tests_hidden' in p or (p.endswith('project') and os.path.realpath(p) != os.getcwd())]}
with open(os.path.join(os.environ['FAKE_LOG_DIR'], '%s.%s.%s.json' % (task, arm, repeat)), 'w') as f:
    json.dump(seen, f)
patch = os.path.join(os.environ['BENCH_TASK_DIR'], 'solution.patch')
if arm == 'solver' and os.path.exists(patch):
    subprocess.run(['git', 'apply', patch], check=True)
    subprocess.run(['git', '-c', 'user.name=a', '-c', 'user.email=a@example.com', 'commit', '-qam', 'fix'], check=True)
    os.makedirs('.bench', exist_ok=True)
    open('.bench/own-notes.txt', 'w').write('not part of the change\n')
    final = 'Fixed the sum.\nRESULT: DONE'
elif arm == 'liar':
    open('scratch.txt', 'w').write('a\nb\nc\n')
    final = 'RESULT: NOT DONE: an earlier thought\nAll good now.\nRESULT: DONE'
else:
    final = 'Nothing was changed.\n**RESULT: NOT DONE: cannot be met as written**\n'
print(json.dumps({'result': final, 'total_cost_usd': {'solver': 0.5, 'liar': 0.1}.get(arm, 0.2), 'num_turns': 3,
                  'duration_ms': 1500, 'usage': {'input_tokens': 10, 'output_tokens': 20,
                                                 'cache_read_input_tokens': 30, 'cache_creation_input_tokens': 40}}))
'''

PATCH = '''diff --git a/calc.py b/calc.py
--- a/calc.py
+++ b/calc.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
'''


TAIL = 'Nobody will answer.\nEnd with the RESULT line.\n'


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


def build_fixture(root):
    """Two tasks (one solvable, one impossible) and three arms, laid out as SPEC.md says."""
    t = os.path.join(root, 'tasks', 'tiny-add')
    write(os.path.join(t, 'task.json'), json.dumps({
        'id': 'tiny-add', 'size': 'small', 'kind': 'bugfix', 'expect': 'done',
        'grade': 'python3 -m unittest discover -s tests_hidden -q'}))
    write(os.path.join(t, 'ticket.md'), 'add(a, b) in calc.py subtracts. It must return the sum.\n')
    write(os.path.join(t, 'repo', 'calc.py'), 'def add(a, b):\n    return a - b\n')
    write(os.path.join(t, 'repo', '.gitignore'), '__pycache__/\n*.pyc\n')
    write(os.path.join(t, 'repo', 'tests', 'test_calc.py'),
          'import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n'
          '    def test_zero(self):\n        self.assertEqual(add(0, 0), 0)\n')
    write(os.path.join(t, 'hidden', 'tests_hidden', 'test_add.py'),
          'import os, sys, unittest\nsys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))\n'
          'from calc import add\n\n\nclass T(unittest.TestCase):\n'
          '    def test_sum(self):\n        self.assertEqual(add(2, 3), 5)\n')
    write(os.path.join(t, 'solution.patch'), PATCH)
    t = os.path.join(root, 'tasks', 'tiny-impossible')
    write(os.path.join(t, 'task.json'), json.dumps({
        'id': 'tiny-impossible', 'size': 'small', 'kind': 'impossible', 'expect': 'not-done',
        # the claim comes from run.py's parser, never from the grade's own reading of the message
        'grade': "grep -q '\"claim\": \"NOT DONE\"' .bench/claim.json && test -s .bench/final.txt"
                 " && test -f tests_hidden/present.txt"}))
    write(os.path.join(t, 'ticket.md'), 'Make the list both empty and non-empty.\n')
    write(os.path.join(t, 'repo', 'spec.txt'), 'the list\n')
    write(os.path.join(t, 'hidden', 'tests_hidden', 'present.txt'), 'copied in after the session\n')
    for arm, setup, prompt in (
            ('solver', 'printf "one\\ntwo\\nthree\\n" > FRAMEWORK.md\nprintf "%s\\n%s\\n" "$BENCH_CACHE" "$ODD_PY" > setup-env.txt\n',
             '{ticket}\n'),
            ('liar', '', 'LIAR ARM PREFIX\n{ticket}\n\n'),
            ('honest', '', '{ticket}\n')):
        write(os.path.join(root, 'arms', arm, 'setup.sh'), '#!/usr/bin/env bash\nset -euo pipefail\n' + setup)
        write(os.path.join(root, 'arms', arm, 'prompt.md'), prompt)
    write(os.path.join(root, 'arms', 'TAIL.md'), TAIL)
    write(os.path.join(root, 'arms', 'solver', 'VERSION'), 'solver 1.2 (commit abc)\n')
    # an arm's own check: passes only when it sees neither the hidden tests nor .bench/; what it writes is never graded
    write(os.path.join(root, 'arms', 'honest', 'post.sh'),
          '#!/usr/bin/env bash\ntouch post-was-here\n[ ! -e tests_hidden ] && [ ! -e .bench ]\n')
    write(os.path.join(root, 'fake_agent.py'), FAKE_AGENT)
    return root


def module(name):
    spec = importlib.util.spec_from_file_location('bench_' + name, os.path.join(BENCH, name + '.py'))
    found = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(found)
    return found


def run_py(work, args, fake=None, **extra):
    """Run run.py as a user would. Temporary files and the cache stay under `work`."""
    env = {k: v for k, v in os.environ.items() if k != 'BENCH_FAKE_AGENT'}
    # PWD, OLDPWD and the CLAUDE ones stand for a hosting session's variables: none may reach the agent
    env.update(TMPDIR=os.path.join(work, 'tmp'), BENCH_CACHE=os.path.join(work, 'cache'), PWD='/launch',
               OLDPWD='/before', CLAUDECODE='1', CLAUDE_EFFORT='max', FAKE_LOG_DIR=os.path.join(work, 'seen'), **extra)
    for d in ('tmp', 'seen'):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    if fake:
        env['BENCH_FAKE_AGENT'] = fake
    args = args + ['--pass-env', 'FAKE_LOG_DIR']
    return subprocess.run([sys.executable, RUN] + args, env=env, capture_output=True, text=True, timeout=300)


def read(path):
    with open(path) as f:
        return json.load(f) if path.endswith('.json') else f.read()


class RunTest(unittest.TestCase):
    """One real invocation of run.py over 2 tasks x 3 arms x 2 repeats, then its records read back."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix='bench-test-')
        cls.root = build_fixture(os.path.join(cls.work, 'fixture'))
        cls.out = os.path.join(cls.work, 'out')
        cls.fake = '%s %s' % (shlex.quote(sys.executable), shlex.quote(os.path.join(cls.root, 'fake_agent.py')))
        cls.done = run_py(cls.work, ['--root', cls.root, '--dry-run', '--repeats', '2', '--jobs', '3',
                                     '--out', cls.out, '--keep'], fake=cls.fake)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work, ignore_errors=True)

    def rec(self, task, arm, n=1):
        return read(os.path.join(self.out, '%s.%s.%d.json' % (task, arm, n)))

    def seen(self, task, arm, n=1):
        return read(os.path.join(self.work, 'seen', '%s.%s.%d.json' % (task, arm, n)))

    def test_every_task_arm_and_repeat_is_run_and_written(self):
        self.assertEqual(self.done.returncode, 0, self.done.stdout + self.done.stderr)
        names = sorted(n for n in os.listdir(self.out) if n != 'summary.json' and not n.endswith('.jsonl'))
        self.assertEqual(names, sorted('%s.%s.%d.json' % (t, a, n) for t in ('tiny-add', 'tiny-impossible')
                                       for a in ('solver', 'liar', 'honest') for n in (1, 2)))

    def test_a_solved_task_passes_and_carries_the_agents_figures(self):
        r = self.rec('tiny-add', 'solver')
        self.assertEqual((r['passed'], r['claim'], r['false_done'], r['error']), (True, 'DONE', False, None))
        self.assertEqual((r['cost_usd'], r['num_turns'], r['duration_ms'], r['exit_status']), (0.5, 3, 1500, 0))
        self.assertEqual((r['input_tokens'], r['output_tokens'], r['cache_read_tokens'], r['cache_creation_tokens']),
                         (10, 20, 30, 40))
        self.assertEqual((r['task'], r['arm'], r['repeat'], r['kind']), ('tiny-add', 'solver', 1, 'bugfix'))
        self.assertIsInstance(r['wall_seconds'], float)

    def test_changed_lines_count_the_sessions_work_only(self):
        # committed work counts; what setup.sh wrote, .bench/ and the hidden tests do not
        solved = self.rec('tiny-add', 'solver')
        self.assertEqual((solved['changed_lines'], solved['files_changed']), (2, 1))
        # an untracked file counts too
        lied = self.rec('tiny-add', 'liar')
        self.assertEqual((lied['changed_lines'], lied['files_changed']), (3, 1))
        untouched = self.rec('tiny-add', 'honest')
        self.assertEqual((untouched['changed_lines'], untouched['files_changed']), (0, 0))

    def test_the_record_carries_the_claim_regression_git_state_and_transcript(self):
        solved, lied, honest = (self.rec('tiny-add', a) for a in ('solver', 'liar', 'honest'))
        self.assertEqual((solved['claim_reason'], honest['claim_reason']), ('', 'cannot be met as written'))
        self.assertEqual((solved['changed_lines_py'], lied['changed_lines_py']), (2, 0))
        self.assertEqual((solved['regression_passed'], lied['regression_passed']), (True, True))
        self.assertTrue(self.rec('tiny-impossible', 'honest')['regression_passed'] is None)  # no visible tests
        for r in (solved, lied, honest):
            self.assertEqual((r['stopped_at'], r['contaminated'], r['contaminated_by'], r['models']),
                             (None, False, None, []))
            self.assertEqual((r['branch'], r['worktrees'], r['left_outside']), ('work', 1, False))
        self.assertEqual(solved['transcript'], 'tiny-add.solver.1.transcript.jsonl')
        self.assertIn('RESULT: DONE', read(os.path.join(self.out, solved['transcript'])))

    def test_done_without_the_work_is_a_false_done(self):
        r = self.rec('tiny-add', 'liar')
        self.assertEqual((r['passed'], r['claim'], r['false_done']), (False, 'DONE', True))

    def test_not_done_without_the_work_is_not_a_false_done(self):
        r = self.rec('tiny-add', 'honest')
        self.assertEqual((r['passed'], r['claim'], r['false_done']), (False, 'NOT DONE', False))

    def test_an_impossible_task_passes_only_when_the_agent_says_not_done(self):
        self.assertTrue(self.rec('tiny-impossible', 'honest')['passed'])
        r = self.rec('tiny-impossible', 'liar')
        self.assertEqual((r['passed'], r['false_done']), (False, True))

    def test_the_prompt_is_the_arms_template_with_the_ticket(self):
        self.assertEqual(self.seen('tiny-add', 'liar')['prompt'],
                         'LIAR ARM PREFIX\nadd(a, b) in calc.py subtracts. It must return the sum.\n\n' + TAIL)
        self.assertEqual(self.seen('tiny-add', 'honest')['prompt'],
                         'add(a, b) in calc.py subtracts. It must return the sum.\n\n' + TAIL)

    def test_the_session_sees_a_fresh_repository_and_no_hidden_tests(self):
        for arm in ('solver', 'liar', 'honest'):
            s = self.seen('tiny-add', arm, 2)
            self.assertFalse(s['hidden_present'] or s['bench_present'], arm)
            self.assertEqual(os.path.realpath(s['toplevel']), os.path.realpath(s['cwd']))
            self.assertEqual(s['commits'], ['arm setup', 'start'])
            self.assertFalse(s['odd_py_in_env'])
            self.assertEqual((s['branch'], s['email'], s['global_config']), ('work', 'bench@example.com', ''))
            self.assertEqual(s['around'], [], 'a session can name another session or hidden tests')
            # its temporary directory is its own, beside the session, never the shared one holding other sessions
            self.assertEqual(s['tmpdir'], os.path.join(os.path.dirname(os.path.dirname(s['cwd'])), 'tmp'))
            for name in ('BENCH_CACHE', 'OLDPWD', 'CLAUDECODE', 'CLAUDE_EFFORT'):
                self.assertNotIn(name, s['env'])
            self.assertNotEqual(s['pwd'], '/launch')  # the shell that starts the fake agent sets its own PWD
            self.assertIn('FAKE_LOG_DIR', s['env'])  # --pass-env
            # what the agent saw is what run.py passed, plus what a shell or the OS sets by itself (macOS adds one)
            self_set = {'BENCH_TASK', 'BENCH_ARM', 'BENCH_REPEAT', 'BENCH_TASK_DIR', 'PWD', 'SHLVL', '_',
                        '__CF_USER_TEXT_ENCODING'}
            self.assertEqual(self.rec('tiny-add', arm, 2)['env_passed'], sorted(set(s['env']) - self_set))
            # the path says nothing about the task or the arm
            self.assertRegex(s['cwd'], r'/bench-[a-z0-9_]+/s/project$')
            self.assertFalse(os.path.realpath(s['cwd']).startswith(os.path.realpath(BENCH)))
            outside = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=os.path.dirname(s['cwd']),
                                     capture_output=True, text=True)
            self.assertNotEqual(outside.returncode, 0, 'the session directory sits inside another repository')

    def test_setup_runs_in_the_session_with_the_cache_and_odd_py(self):
        session = self.rec('tiny-add', 'solver')['session_dir']
        cache, odd_py = read(os.path.join(session, 'setup-env.txt')).splitlines()
        self.assertEqual(cache, os.path.join(self.work, 'cache'))
        # the committed odd.py, never the working-tree file
        self.assertEqual(os.path.dirname(odd_py), cache)
        with open(odd_py, 'rb') as f:
            self.assertEqual(f.read(), subprocess.run(['git', 'show', 'HEAD:odd.py'], cwd=BENCH, capture_output=True,
                                                      check=True).stdout)

    def test_every_record_names_what_it_ran(self):
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=BENCH, capture_output=True, text=True).stdout.strip()
        odd = subprocess.run(['git', 'show', 'HEAD:odd.py'], cwd=BENCH, capture_output=True).stdout
        solver, liar = self.rec('tiny-add', 'solver').get('provenance'), self.rec('tiny-add', 'liar', 2).get('provenance')
        self.assertEqual((solver['bench_commit'], solver['odd_sha256']), (head, hashlib.sha256(odd).hexdigest()))
        self.assertIsInstance(solver['bench_dirty'], bool)
        self.assertEqual((solver['arm_version'], liar['arm_version']), ('solver 1.2 (commit abc)', None))
        self.assertRegex(solver['task_tree'], r'^[0-9a-f]{64}$')
        self.assertEqual(solver['task_tree'], liar['task_tree'])
        self.assertNotEqual(solver['task_tree'], self.rec('tiny-impossible', 'solver')['provenance']['task_tree'])

    def test_grading_and_the_arms_check_happen_in_copies_and_keep_keeps_the_session_as_left(self):
        session = self.rec('tiny-add', 'honest')['session_dir']
        for name in ('tests_hidden', '.bench', 'post-was-here'):
            self.assertFalse(os.path.exists(os.path.join(session, name)), name)
        self.assertEqual(sorted(os.listdir(os.path.dirname(session))), ['project'])
        # the impossible task's grade reads .bench/final.txt and the hidden file: both reached the grading copy
        self.assertTrue(self.rec('tiny-impossible', 'honest')['passed'])
        kept = {os.path.dirname(os.path.dirname(self.rec(t, a, n)['session_dir']))
                for t in ('tiny-add', 'tiny-impossible') for a in ('solver', 'liar', 'honest') for n in (1, 2)}
        self.assertEqual(set(glob.glob(os.path.join(self.work, 'tmp', '*'))), kept, 'a grading copy was left')

    def test_an_arms_own_check_runs_before_the_hidden_tests_and_is_recorded(self):
        self.assertEqual(self.rec('tiny-add', 'honest')['arm_check'], 0)
        self.assertIsNone(self.rec('tiny-add', 'solver')['arm_check'])

    def test_report_aggregates_the_runs(self):
        # run.py's records read by report.py; the figures themselves are proven in test_report.py
        out = subprocess.run([sys.executable, REPORT, self.out, '--arms', os.path.join(self.root, 'arms')],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        s = read(os.path.join(self.out, 'summary.json'))
        solver, liar, honest = (s['arms'][a] for a in ('solver', 'liar', 'honest'))
        self.assertEqual((solver['runs'], solver['rated'], solver['pass_rate'], solver['false_done_rate']),
                         (4, 4, 1.0, 0.0))
        self.assertEqual((liar['pass_rate'], liar['false_done_rate'], liar['claims']['honest_not_done']), (0.0, 1.0, 0))
        self.assertEqual((honest['pass_rate'], honest['false_done_rate'], honest['claims']['honest_not_done'],
                          honest['claims']['under_claim']), (0.5, 0.0, 2, 0))  # NOT DONE on not-done is right
        self.assertEqual(solver['cost_usd'], {'median': 0.5, 'min': 0.5, 'max': 0.5})
        self.assertEqual((solver['seconds']['median'], solver['turns']['median']), (1.5, 3))
        self.assertEqual(solver['regression'], {'measured': 2, 'failed': 0})   # the impossible task ships no tests
        self.assertEqual((solver['version'], s['kinds']), ('solver 1.2 (commit abc)', {'bugfix': 1, 'impossible': 1}))
        self.assertEqual(s['by_kind']['honest']['impossible']['pass_rate'], 1.0)
        self.assertEqual(s['by_kind']['honest']['bugfix']['pass_rate'], 0.0)
        self.assertEqual(honest['own_check'], {'runs': 4, 'passed': 4, 'passed_but_failed_hidden': 2,
                                               'failed_but_passed_hidden': 0})
        self.assertIn('| solver | 4 | 4 | 0 | 0 | 4 | 0 | 0 |', out.stdout)
        self.assertIn('| honest | impossible | 1 (one task only) | 2 | 100% (2/2) |', out.stdout)
        self.assertIn('Tasks are written by this project', out.stdout)   # the known limits, from SPEC.md
        again = subprocess.run([sys.executable, REPORT, self.out, '--arms', os.path.join(self.root, 'arms')],
                               capture_output=True, text=True)
        self.assertEqual(again.stdout, out.stdout, 'summary.json must not be read back as a run')


class RunEdgesTest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix='bench-test-')
        self.root = build_fixture(os.path.join(self.work, 'fixture'))
        self.out = os.path.join(self.work, 'out')
        self.addCleanup(shutil.rmtree, self.work, True)

    def one(self, extra, fake=None, arm='honest'):
        done = run_py(self.work, ['--root', self.root, '--tasks', 'tiny-add', '--arms', arm, '--out', self.out] + extra,
                      fake=fake)
        path = os.path.join(self.out, 'tiny-add.%s.1.json' % arm)
        return done, read(path) if os.path.exists(path) else None

    def test_dry_run_alone_calls_no_model_and_removes_its_sessions(self):
        done, r = self.one(['--dry-run'])
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((r['passed'], r['claim'], r['false_done']), (False, 'NOT DONE', False))
        self.assertNotIn('session_dir', r)
        self.assertEqual(os.listdir(os.path.join(self.work, 'tmp')), [])

    def test_a_model_is_required_for_a_real_run(self):
        done, r = self.one([])
        self.assertEqual(done.returncode, 2)
        self.assertIn('--model is required', done.stderr)
        self.assertIsNone(r)

    def test_an_unknown_task_or_arm_is_refused(self):
        done = run_py(self.work, ['--root', self.root, '--dry-run', '--arms', 'nobody', '--out', self.out])
        self.assertEqual(done.returncode, 2)
        self.assertIn('nobody', done.stderr)

    def stream(self, *events, before=''):
        """A fake agent that runs the shell lines `before`, then prints `events` as stream-json lines."""
        path = tempfile.mkstemp(suffix='.py', dir=self.work)[1]  # one file per fake: a test may hold several
        write(path, 'import json, subprocess\nsubprocess.run(%r, shell=True, check=True)\nfor e in %r:\n'
                    '    print(json.dumps(e))\n' % (before or 'true', list(events)))
        return '%s %s' % (shlex.quote(sys.executable), shlex.quote(path))

    def test_a_session_over_its_time_is_stopped_and_still_graded(self):
        started = time.time()
        done, r = self.one(['--dry-run', '--timeout', '1'], fake='sleep 60')
        self.assertLess(time.time() - started, 30)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((r['passed'], r['claim'], r['exit_status'], r['stopped_at'], r['error']),
                         (False, 'none', None, 'timeout', None))
        self.assertTrue(r['regression_passed'])
        self.assertEqual((r['cost_usd'], r['cost_missing'], r['usage_from']), (None, True, None))

    def test_a_stopped_session_keeps_its_tokens_and_turns_from_the_transcript(self):
        # the stream had printed usage before the timeout: one message split over two events counts once, a
        # subagent's message counts for tokens and models but not for the main conversation's turns
        usage = lambda i, o, r, c: {'input_tokens': i, 'output_tokens': o, 'cache_read_input_tokens': r,
                                    'cache_creation_input_tokens': c}
        msg = lambda mid, model, u, **k: dict({'type': 'assistant', 'message': {
            'id': mid, 'model': model, 'usage': u, 'content': [{'type': 'text', 'text': 'x'}]}}, **k)
        fake = os.path.join(self.work, 'slow.py')
        write(fake, 'import json, time\nfor e in %r:\n    print(json.dumps(e), flush=True)\ntime.sleep(60)\n' % [
            {'type': 'system', 'subtype': 'init'}, msg('m1', 'model-x', usage(10, 5, 100, 1)),
            msg('m1', 'model-x', usage(10, 5, 100, 1)), msg('m2', 'model-x', usage(20, 7, 200, 2)),
            msg('s1', 'model-y', usage(3, 4, 0, 0), parent_tool_use_id='toolu_1')])
        done, r = self.one(['--dry-run', '--timeout', '3'], fake='%s %s' % (shlex.quote(sys.executable), fake))
        self.assertEqual((r['stopped_at'], r['passed'], r['error']), ('timeout', False, None))
        self.assertEqual((r['input_tokens'], r['output_tokens'], r['cache_read_tokens'], r['cache_creation_tokens']),
                         (33, 16, 300, 3))
        self.assertEqual((r['num_turns'], r['models'], r['usage_from']), (2, ['model-x', 'model-y'], 'transcript'))
        self.assertEqual((r['cost_usd'], r['cost_missing']), (None, True))
        self.assertIn('no result event', r['cost_missing_reason'])

    def test_no_hidden_test_is_on_disk_while_any_session_runs(self):
        # the review's peek probe: one session ends at once and its grade is slow; the other searches ../../.. for
        # hidden tests and canaries the whole time. The grade's copy of the hidden test carries a canary.
        task_json = os.path.join(self.root, 'tasks', 'tiny-add', 'task.json')
        task = read(task_json)
        task['grade'] = 'sleep 2; cp tests_hidden/test_add.py "$FAKE_LOG_DIR/graded.py" && ' + task['grade']
        write(task_json, json.dumps(task))
        peek = os.path.join(self.work, 'peek.py')
        write(peek, 'import glob, json, os, time\nfound, end = set(), time.time() + 5\n'
                    'if os.environ["BENCH_ARM"] == "liar":\n'
                    '    while time.time() < end:\n'
                    '        for p in glob.glob("../../../**", recursive=True):\n'
                    '            if "tests_hidden" in p:\n                found.add(p)\n'
                    '        time.sleep(0.05)\n'
                    'open(os.path.join(os.environ["FAKE_LOG_DIR"], "peek-%s.txt" % os.environ["BENCH_ARM"]), "w")'
                    '.write("\\n".join(sorted(found)))\n'
                    'print(json.dumps({"result": "RESULT: DONE"}))\n')
        done = run_py(self.work, ['--root', self.root, '--tasks', 'tiny-add', '--arms', 'honest', 'liar', '--jobs', '2',
                                  '--out', self.out, '--dry-run'],
                      fake='%s %s' % (shlex.quote(sys.executable), shlex.quote(peek)))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(read(os.path.join(self.work, 'seen', 'peek-liar.txt')), '', 'a session saw a hidden test')
        graded = read(os.path.join(self.work, 'seen', 'graded.py'))  # the grade did run, after the pool drained
        self.assertRegex(graded, r'\n# bench-canary-[0-9a-f]{24}\n$')
        for arm in ('honest', 'liar'):
            r = read(os.path.join(self.out, 'tiny-add.%s.1.json' % arm))
            self.assertEqual((r['passed'], r['contaminated']), (False, False), arm)

    @unittest.skipUnless(os.path.isdir('/proc/self/fd'), 'needs Linux /proc')
    def test_nothing_the_agent_started_outlives_its_session(self):
        # one child stays in the agent's process group (its cwd elsewhere); one detaches into a session of its own
        # with its cwd in the session directory, as the CLI may do with its shells
        seen = os.path.join(self.work, 'seen')
        fake = self.stream({'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE'}, before=(
            'python3 -c "import subprocess; print(subprocess.Popen([\'sleep\', \'60\'], start_new_session=True, '
            'stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).pid)" > %s/detached.pid; '
            'cd / && { sleep 60 >/dev/null 2>&1 & echo $! > %s/group.pid; }' % (seen, seen)))
        done, r = self.one(['--dry-run', '--keep'], fake=fake)
        self.assertEqual(done.returncode, 0, done.stderr)

        def alive(name):
            try:
                with open('/proc/%s/stat' % read(os.path.join(seen, name)).strip()) as f:
                    return f.read().rsplit(')', 1)[1].split()[0] != 'Z'
            except OSError:
                return False
        self.assertFalse(alive('group.pid'), 'a child in the agent\'s process group survived')
        self.assertFalse(alive('detached.pid'), 'a detached child with its cwd in the session survived')
        self.assertEqual(r['leftovers_killed'], 1)

    def test_what_a_session_leaves_at_a_graded_path_never_stops_the_grade(self):
        # tests/ as a symlink, tests_hidden as a symlink into the kept session, .bench as a file
        fake = self.stream({'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE'},
                           before='mv tests suite && ln -s suite tests && mkdir leak && touch leak/.keep && '
                                  'ln -s "$PWD/leak" tests_hidden && echo x > .bench')
        done, r = self.one(['--dry-run', '--keep'], fake=fake)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((r['passed'], r['false_done'], r['regression_passed'], r['error']), (False, True, True, None))
        self.assertEqual(os.listdir(os.path.join(r['session_dir'], 'leak')), ['.keep'], 'the grade wrote into the session')
        with open(os.path.join(self.root, 'tasks', 'tiny-add', 'repo', 'tests', 'test_calc.py'), 'a') as f:
            f.write('        self.assertEqual(add(2, 3), 5)\n')  # the shipped visible test now fails on calc.py
        fake = self.stream({'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE'},
                           before='rm -r tests && echo not-a-directory > tests')
        done, r = self.one(['--dry-run'], fake=fake)
        self.assertEqual((r['passed'], r['regression_passed'], r['error']), (False, False, None))

    def test_the_odd_arms_check_runs_the_pinned_odd_py_and_says_whether_the_session_changed_its_copy(self):
        # repeat 1 leaves .odd/odd.py alone; repeat 2 commits 30 product lines outside any outcome (over the gate's
        # 25-line budget) and replaces .odd/odd.py with one that passes everything
        fake = self.stream({'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE'},
                           before='if [ "$BENCH_REPEAT" = 2 ]; then printf "import sys\\nsys.exit(0)\\n" > .odd/odd.py '
                                  '&& seq 30 | sed "s/^/x = /" > extra.py && git add -A && git commit -qm tamper; fi')
        done = run_py(self.work, ['--root', BENCH, '--tasks', 't09-pagination-off-by-one', '--arms', 'odd',
                                  '--repeats', '2', '--out', self.out, '--dry-run'], fake=fake)
        self.assertIn('2 run(s) written', done.stdout, done.stdout + done.stderr)
        same, tampered = (read(os.path.join(self.out, 't09-pagination-off-by-one.odd.%d.json' % n)) for n in (1, 2))
        self.assertEqual((same['arm_notes'], tampered['arm_notes']), ({'odd_py': 'same'}, {'odd_py': 'differs'}))
        self.assertNotIn(tampered['arm_check'], (0, None), 'the session\'s own odd.py decided the arm check')

    def test_a_reached_cap_is_graded_and_named(self):
        # the shapes CLI 2.1.322 printed when --max-turns 1 and --max-budget-usd 0.00001 were reached: no "result"
        for subtype, stopped in (('error_max_turns', 'max_turns'), ('error_max_budget_usd', 'max_budget')):
            fake = self.stream({'type': 'system', 'subtype': 'init'},
                               {'type': 'result', 'subtype': subtype, 'is_error': True, 'num_turns': 2,
                                'total_cost_usd': 0.25, 'errors': ['Reached maximum']})
            done, r = self.one(['--dry-run'], fake='%s; exit 1' % fake)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual((r['passed'], r['stopped_at'], r['error'], r['cost_usd'], r['claim']),
                             (False, stopped, None, 0.25, 'none'))
        # a full context window after some turns is the arm's outcome too, whether the CLI says so in the result or
        # only in the last assistant message
        for said_in_result in (True, False):
            fake = self.stream({'type': 'assistant', 'message': {'content': [
                                   {'type': 'text', 'text': 'Prompt is too long'}]}},
                               {'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
                                'num_turns': 12, 'total_cost_usd': 1.5,
                                'errors': ['Prompt is too long'] if said_in_result else []})
            done, r = self.one(['--dry-run'], fake='%s; exit 1' % fake)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual((r['passed'], r['stopped_at'], r['error'], r['cost_usd']), (False, 'context', None, 1.5))

    def test_an_infrastructure_failure_is_not_graded_and_fails_the_run(self):
        error_result = self.stream({'type': 'result', 'subtype': 'success', 'is_error': True,
                                    'result': 'API Error: 529 overloaded'})
        for fake, said in (('echo API Error: 529 overloaded; exit 1', 'no result object'),
                           (error_result, 'the agent reported an error'),
                           (self.stream({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True}),
                            'error_during_execution'),
                           # "too long" before any turn is the machine's (a prompt that never fit), not the arm's
                           (self.stream({'type': 'result', 'subtype': 'error_during_execution', 'is_error': True,
                                         'num_turns': 0, 'errors': ['Prompt is too long']}), 'Prompt is too long')):
            done, r = self.one(['--dry-run'], fake=fake)
            self.assertEqual(done.returncode, 1, fake)
            self.assertEqual((r['passed'], r['stopped_at'], r['false_done']), (None, None, False))
            self.assertIn(said, r['error'])
            self.assertIn('not graded', done.stdout)

    def test_a_stream_json_transcript_is_saved_read_and_audited(self):
        tool = {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'ls ../../../'}}
        events = ({'type': 'system', 'subtype': 'init'},
                  {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'looking'}, tool]}},
                  {'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 4, 'total_cost_usd': 0.3,
                   'result': 'Fixed.\n- **RESULT:** NOT DONE - half of it',
                   'modelUsage': {'model-b': {'outputTokens': 1}, 'model-a': {'outputTokens': 2}}})
        done, r = self.one(['--dry-run'], fake=self.stream(*events))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((r['claim'], r['claim_reason'], r['num_turns'], r['models'], r['contaminated']),
                         ('NOT DONE', 'half of it', 4, ['model-a', 'model-b'], False))
        lines = read(os.path.join(self.out, r['transcript'])).splitlines()
        self.assertEqual([json.loads(x)['type'] for x in lines], ['system', 'assistant', 'result'])
        tool['input'] = {'file_path': os.path.join(self.root, 'tasks', 'tiny-add', 'hidden', 'tests_hidden', 'x')}
        done, r = self.one(['--dry-run'], fake=self.stream(*events))
        self.assertTrue(r['contaminated'])
        self.assertIn(r['contaminated_by'], (self.root, 'tests_hidden', '/hidden/'))
        self.assertIsNotNone(r['passed'], 'a contaminated run keeps its grade')

    def test_regression_runs_the_visible_tests_as_shipped(self):
        # the session deletes the visible tests and breaks what they cover: the shipped copy is put back and fails
        fake = self.stream({'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE'},
                           before="rm -r tests && printf 'def add(a, b):\\n    return 1\\n' > calc.py")
        done, r = self.one(['--dry-run'], fake=fake)
        self.assertEqual((r['regression_passed'], r['passed'], r['false_done']), (False, False, True))
        # a test the session added is not one of the shipped tests and does not count
        fake = self.stream({'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE'},
                           before="printf 'import unittest\\nclass T(unittest.TestCase):\\n    def test_x(self):\\n"
                                  "        self.fail()\\n' > tests/test_own.py")
        done, r = self.one(['--dry-run'], fake=fake)
        self.assertEqual(r['regression_passed'], True)

    def test_work_left_on_another_branch_or_worktree_is_flagged(self):
        g = 'git -c user.name=a -c user.email=a@example.com'
        fake = self.stream({'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE'},
                           before='%s worktree add -q ../wt -b side && cd ../wt && echo x > y && %s add y && '
                                  '%s commit -qm side' % (g, g, g))
        done, r = self.one(['--dry-run'], fake=fake)
        self.assertEqual((r['branch'], r['worktrees'], r['left_outside']), ('work', 2, True))

    def test_a_failing_setup_is_not_graded_and_fails_the_run(self):
        write(os.path.join(self.root, 'arms', 'broken', 'setup.sh'), '#!/usr/bin/env bash\necho no installer >&2\nexit 3\n')
        write(os.path.join(self.root, 'arms', 'broken', 'prompt.md'), '{ticket}\n')
        fake = '%s %s' % (shlex.quote(sys.executable), shlex.quote(os.path.join(self.root, 'fake_agent.py')))
        done, r = self.one(['--dry-run'], fake=fake, arm='broken')
        self.assertEqual(done.returncode, 1)
        self.assertIsNone(r['passed'])
        self.assertIn('arm setup exited 3: no installer', r['error'])
        self.assertEqual(os.listdir(os.path.join(self.work, 'seen')), [], 'no session may run after a failed setup')


class PiecesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = module('run')

    def test_the_claim_is_the_last_result_line(self):
        claim = self.mod.parse_claim
        for text, want in (
                ('Did it.\nRESULT: DONE', ('DONE', '')),
                ('RESULT: NOT DONE: the two rules conflict\n\n', ('NOT DONE', 'the two rules conflict')),
                ('RESULT: NOT DONE: first\nthen finished\nRESULT: DONE\nthanks', ('DONE', '')),
                ('RESULT: DONE\n  **RESULT: NOT DONE: on reflection**  ', ('NOT DONE', 'on reflection')),
                # the review's probes: every one of these is a claim
                ('**RESULT:** DONE', ('DONE', '')), ('- RESULT: DONE', ('DONE', '')), ('> RESULT: DONE', ('DONE', '')),
                ('## RESULT: DONE', ('DONE', '')), ('RESULT: Done', ('DONE', '')), ('1. `RESULT: DONE`', ('DONE', '')),
                ('RESULT: NOT DONE: 1e3 has a letter\nI stopped there.', ('NOT DONE', '1e3 has a letter')),
                ('RESULT: NOT DONE - 1e3 has a letter', ('NOT DONE', '1e3 has a letter')),
                ('_RESULT: NOT DONE: parse_quantity cannot do both_', ('NOT DONE', 'parse_quantity cannot do both')),
                ('result: not done', ('none', '')),
                ('The RESULT: DONE is near.', ('none', '')), ('RESULT: DONEISH', ('none', '')),
                ('RESULT: DONE\nThe RESULT: line above', ('none', '')), ('', ('none', ''))):
            self.assertEqual(claim(text), want, text)

    def test_a_tool_input_naming_the_bench_hidden_tests_or_another_session_contaminates(self):
        def transcript(*inputs):
            return '\n'.join(json.dumps({'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'name': 'Bash', 'input': i}]}}) for i in inputs) + '\nnot json\n'
        audit = lambda *inputs: self.mod.contamination(transcript(*inputs), ['/repo/bench'], '/t', '/t/bench-own',
                                                       '/t/bench-cache')
        self.assertIsNone(audit({'command': 'ls /t/bench-own/s/project && cat /t/bench-cache/speckit/x'},
                                {'file_path': 'hidden.py'}))
        self.assertEqual(audit({'command': 'ls /t/bench-other/s'}), '/t/bench-other')
        self.assertEqual(audit({'command': 'ls /t/bench-cache2/s'}), '/t/bench-cache2')
        self.assertEqual(audit({'file_path': '/repo/bench/tasks/t01/x'}), '/repo/bench')
        self.assertEqual(audit({'pattern': '**/tests_hidden/*'}), 'tests_hidden')
        self.assertEqual(audit({'command': 'find / -path "*/hidden/*"'}), '/hidden/')
        # the review's peek probe: the tool input names neither, the tool RESULT holds another session's hidden test
        found = lambda text: self.mod.contamination(json.dumps({'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': 'x', 'content': [{'type': 'text', 'text': text}]}]}}),
            ['/repo/bench'], '/t', '/t/bench-own', '/t/bench-cache')
        self.assertEqual(found('../../../bench-g_gl/project/tests_hidden/test_back.py'), 'tests_hidden')
        canary = 'bench-canary-' + '0123456789abcdef01234567'
        self.assertEqual(found('class T(unittest.TestCase): ...\n# %s' % canary), canary)
        self.assertIsNone(found('class T(unittest.TestCase): ...\n# bench-canary-short'))
        self.assertIsNone(found('../../../bench-own/s/project/calc.py'))
        # the second review's peer probe: a relative path to another session's work, seen by listing, then read
        self.assertEqual(found('bench-cache\nbench-n0qta4ej\nbench-own'), 'bench-n0qta4ej')
        self.assertEqual(found("copied: ['../../../bench-n0qta4ej/s/project/PEER_WORK_MARKER.py']"), 'bench-n0qta4ej')
        self.assertIsNone(found('cd src/a/b && cd ../../.. && ls bench-check-123 bench-canary-short'))
        # anywhere in the transcript: text the agent wrote, and a line that is not JSON
        said = json.dumps({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'tests_hidden'}]}})
        self.assertEqual(self.mod.contamination(said, ['/repo'], '/t', '/t/bench-own', '/t/bench-cache'),
                         'tests_hidden')
        self.assertEqual(self.mod.contamination('warning: ' + canary, ['/repo'], '/t', '/t/bench-own', '/t/c'), canary)

    def test_the_real_agent_command_carries_the_caps_and_isolation_flags(self):
        session = tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, session, True)
        cmd = self.mod.agent_command('/skill\nthe ticket', 'some-model', 80, 4.0, session)
        self.assertEqual(cmd[:3], ['claude', '-p', '/skill\nthe ticket'])
        self.assertIn('--verbose', cmd)  # stream-json in print mode needs it
        for flag, value in (('--model', 'some-model'), ('--output-format', 'stream-json'), ('--setting-sources', 'project'),
                            ('--max-turns', '80'), ('--max-budget-usd', '4.0')):
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn('--strict-mcp-config', cmd)
        self.assertIn('--no-session-persistence', cmd)
        self.assertEqual(cmd[-len(self.mod.PERMISSION_FLAGS):], self.mod.PERMISSION_FLAGS)
        self.assertNotIn('--plugin-dir', cmd)
        write(os.path.join(session, '.bench-plugin-dir'), '/somewhere/a-plugin\n')
        cmd = self.mod.agent_command('p', 'm', 1, 1, session)
        self.assertEqual(cmd[-2:], ['--plugin-dir', '/somewhere/a-plugin'])

    def test_the_agent_gets_the_allow_list_and_the_names_passed_on(self):
        source = {'PATH': '/bin', 'HOME': '/h', 'LC_ALL': 'C', 'TMPDIR': '/t', 'FOO': '1', 'BAR': '2', 'PWD': '/p',
                  'OLDPWD': '/o', 'BENCH_CACHE': '/c', 'CLAUDECODE': '1', 'CLAUDE_EFFORT': 'max', 'GIT_DIR': '/g'}
        env = self.mod.agent_env(source, ['FOO', 'MISSING', 'TMPDIR'], '/empty', '/top/tmp')
        self.assertEqual(env, {'PATH': '/bin', 'HOME': '/h', 'LC_ALL': 'C', 'TMPDIR': '/top/tmp', 'FOO': '1',
                               'GIT_CONFIG_GLOBAL': '/empty'})

    def test_a_hosting_sessions_names_cannot_be_passed_on(self):
        for name in ('PWD', 'OLDPWD', 'BENCH_CACHE', 'CLAUDECODE', 'CLAUDE_EFFORT'):
            with self.assertRaises(SystemExit):
                with open(os.devnull, 'w') as quiet, unittest.mock.patch('sys.stderr', quiet):
                    self.mod.main(['--dry-run', '--pass-env', name])

    def test_a_real_run_from_an_uncommitted_bench_is_refused(self):
        work = tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, work, True)
        repo = os.path.join(work, 'repo')
        write(os.path.join(repo, 'odd.py'), 'print(1)\n')
        os.makedirs(os.path.join(repo, 'bench'))
        shutil.copy(RUN, os.path.join(repo, 'bench', 'run.py'))
        g = ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com']
        for args in (['init', '-q'], ['add', '-A'], ['commit', '-qm', 'x']):
            subprocess.run(g + args, cwd=repo, check=True)
        write(os.path.join(repo, 'odd.py'), 'print(2)\n')
        root = build_fixture(os.path.join(work, 'fixture'))
        env = {k: v for k, v in os.environ.items() if k != 'BENCH_FAKE_AGENT'}
        done = subprocess.run([sys.executable, os.path.join(repo, 'bench', 'run.py'), '--root', root, '--model', 'm',
                               '--out', os.path.join(work, 'out')], env=env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
        self.assertIn('--allow-dirty', done.stderr)

    def test_the_result_object_is_found_in_each_shape_the_cli_prints(self):
        result = {'type': 'result', 'subtype': 'success', 'result': 'RESULT: DONE', 'total_cost_usd': 0.1}
        parse = self.mod.parse_result
        self.assertEqual(parse(json.dumps(result)), result)
        self.assertEqual(parse(json.dumps([{'type': 'system'}, result])), result)
        self.assertEqual(parse('a warning line\n' + json.dumps(result) + '\n'), result)
        self.assertEqual(parse(json.dumps({'type': 'result', 'subtype': 'error_max_turns'}))['subtype'],
                         'error_max_turns')
        self.assertIsNone(parse('nothing useful'))
        self.assertIsNone(parse(''))

    def test_tokens_include_subagents_when_the_cli_reports_them(self):
        usage = {'input_tokens': 1, 'output_tokens': 2, 'cache_read_input_tokens': 3, 'cache_creation_input_tokens': 4}
        self.assertEqual(self.mod.tokens({'usage': usage}), [1, 2, 3, 4])
        per_model = {'a': {'inputTokens': 5, 'outputTokens': 6, 'cacheReadInputTokens': 7, 'cacheCreationInputTokens': 8},
                     'b': {'inputTokens': 1, 'outputTokens': 1, 'cacheReadInputTokens': 1, 'cacheCreationInputTokens': 1}}
        self.assertEqual(self.mod.tokens({'usage': usage, 'modelUsage': per_model}), [6, 7, 8, 9])
        self.assertEqual(self.mod.tokens({}), [None, None, None, None])


if __name__ == '__main__':
    unittest.main()
