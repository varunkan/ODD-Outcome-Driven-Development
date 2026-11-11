"""run.py and report.py, proven with fake agents on a tiny task fixture built here. No network, no model.

The fake agent behaves by arm: "solver" applies the task's solution.patch and says DONE, "liar" changes nothing that
matters and says DONE, "honest" changes nothing and says NOT DONE.
"""
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

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN, REPORT = os.path.join(BENCH, 'run.py'), os.path.join(BENCH, 'report.py')

FAKE_AGENT = r'''
import json, os, subprocess, sys
prompt = sys.stdin.read()
arm, task, repeat = os.environ['BENCH_ARM'], os.environ['BENCH_TASK'], os.environ['BENCH_REPEAT']
git = lambda *a: subprocess.run(('git',) + a, capture_output=True, text=True).stdout.strip()
seen = {'prompt': prompt, 'cwd': os.getcwd(), 'toplevel': git('rev-parse', '--show-toplevel'),
        'commits': git('log', '--format=%s').splitlines(), 'hidden_present': os.path.exists('tests_hidden'),
        'bench_present': os.path.exists('.bench'), 'odd_py_in_env': 'ODD_PY' in os.environ}
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
        'grade': "tail -n 2 .bench/final.txt | grep -q 'RESULT: NOT DONE' && test -f tests_hidden/present.txt"}))
    write(os.path.join(t, 'ticket.md'), 'Make the list both empty and non-empty.\n')
    write(os.path.join(t, 'repo', 'spec.txt'), 'the list\n')
    write(os.path.join(t, 'hidden', 'tests_hidden', 'present.txt'), 'copied in after the session\n')
    for arm, setup, prompt in (
            ('solver', 'printf "one\\ntwo\\nthree\\n" > FRAMEWORK.md\nprintf "%s\\n%s\\n" "$BENCH_CACHE" "$ODD_PY" > setup-env.txt\n',
             '{ticket}\n\nEnd with the RESULT line.\n'),
            ('liar', '', 'LIAR ARM PREFIX\n{ticket}\n\nEnd with the RESULT line.\n'),
            ('honest', '', '{ticket}\n\nEnd with the RESULT line.\n')):
        write(os.path.join(root, 'arms', arm, 'setup.sh'), '#!/usr/bin/env bash\nset -euo pipefail\n' + setup)
        write(os.path.join(root, 'arms', arm, 'prompt.md'), prompt)
    # an arm's own check: passes only when it runs before the hidden tests and .bench/ exist
    write(os.path.join(root, 'arms', 'honest', 'post.sh'),
          '#!/usr/bin/env bash\n[ ! -e tests_hidden ] && [ ! -e .bench ]\n')
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
    env.update(TMPDIR=os.path.join(work, 'tmp'), BENCH_CACHE=os.path.join(work, 'cache'),
               FAKE_LOG_DIR=os.path.join(work, 'seen'), **extra)
    for d in ('tmp', 'seen'):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    if fake:
        env['BENCH_FAKE_AGENT'] = fake
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
        names = sorted(n for n in os.listdir(self.out) if n != 'summary.json')
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
                         'LIAR ARM PREFIX\nadd(a, b) in calc.py subtracts. It must return the sum.\n\n'
                         'End with the RESULT line.\n')

    def test_the_session_sees_a_fresh_repository_and_no_hidden_tests(self):
        for arm in ('solver', 'liar', 'honest'):
            s = self.seen('tiny-add', arm, 2)
            self.assertFalse(s['hidden_present'] or s['bench_present'], arm)
            self.assertEqual(os.path.realpath(s['toplevel']), os.path.realpath(s['cwd']))
            self.assertEqual(s['commits'], ['arm setup', 'start'])
            self.assertFalse(s['odd_py_in_env'])
            # the path says nothing about the task or the arm
            self.assertRegex(s['cwd'], r'/ws-[a-z0-9_]+/r[a-z0-9_]+/project$')
            self.assertFalse(os.path.realpath(s['cwd']).startswith(os.path.realpath(BENCH)))
            outside = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=os.path.dirname(s['cwd']),
                                     capture_output=True, text=True)
            self.assertNotEqual(outside.returncode, 0, 'the session directory sits inside another repository')

    def test_setup_runs_in_the_session_with_the_cache_and_odd_py(self):
        session = self.rec('tiny-add', 'solver')['session_dir']
        cache, odd_py = read(os.path.join(session, 'setup-env.txt')).splitlines()
        self.assertEqual(cache, os.path.join(self.work, 'cache'))
        self.assertEqual(odd_py, os.path.abspath(os.path.join(BENCH, '..', 'odd.py')))
        self.assertTrue(os.path.isabs(odd_py))

    def test_hidden_tests_and_the_final_message_arrive_after_the_session(self):
        session = self.rec('tiny-add', 'honest')['session_dir']
        self.assertTrue(os.path.isfile(os.path.join(session, 'tests_hidden', 'test_add.py')))
        self.assertEqual(read(os.path.join(session, '.bench', 'final.txt')),
                         'Nothing was changed.\n**RESULT: NOT DONE: cannot be met as written**\n\n')

    def test_an_arms_own_check_runs_before_the_hidden_tests_and_is_recorded(self):
        self.assertEqual(self.rec('tiny-add', 'honest')['arm_check'], 0)
        self.assertIsNone(self.rec('tiny-add', 'solver')['arm_check'])

    def test_report_aggregates_the_runs(self):
        out = subprocess.run([sys.executable, REPORT, self.out], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        s = read(os.path.join(self.out, 'summary.json'))
        solver, liar, honest = (s['arms'][a] for a in ('solver', 'liar', 'honest'))
        self.assertEqual((solver['runs'], solver['pass_rate'], solver['false_done_rate']), (4, 1.0, 0.0))
        self.assertEqual((liar['pass_rate'], liar['false_done_rate'], liar['honest_not_done']), (0.0, 1.0, 0))
        self.assertEqual((honest['pass_rate'], honest['false_done_rate'], honest['honest_not_done']), (0.5, 0.0, 2))
        self.assertEqual(solver['cost_usd'], {'median': 0.5, 'min': 0.5, 'max': 0.5})
        self.assertEqual(solver['seconds']['median'], 1.5)
        self.assertEqual(solver['turns']['median'], 3)
        self.assertEqual(s['by_kind']['honest']['impossible']['pass_rate'], 1.0)
        self.assertEqual(s['by_kind']['honest']['bugfix']['pass_rate'], 0.0)
        self.assertEqual(honest['own_check'], {'runs': 4, 'passed': 4, 'passed_but_failed_hidden': 2})
        self.assertIn('| arm | runs | pass rate | false-done rate | honest not-done |', out.stdout)
        self.assertIn('| solver | 4 | 100% (4/4) | 0% (0/4) | 0 | 0.50 (0.50-0.50) | 2 (2-2) | 3 (3-3) |', out.stdout)
        self.assertIn('| honest | impossible | 2 | 100% (2/2) |', out.stdout)
        self.assertIn('Tasks are written by this project', out.stdout)   # the known limits, from SPEC.md
        self.assertIn('Tasks are written by this project', s['known_limits'])
        again = subprocess.run([sys.executable, REPORT, self.out], capture_output=True, text=True)
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

    def test_a_session_over_its_time_is_stopped_and_still_graded(self):
        started = time.time()
        done, r = self.one(['--dry-run', '--timeout', '1'], fake='sleep 60')
        self.assertLess(time.time() - started, 30)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((r['passed'], r['claim'], r['exit_status']), (False, 'none', None))
        self.assertIn('stopped after 1 seconds', r['error'])

    def test_an_agent_that_prints_no_result_is_named_and_still_graded(self):
        done, r = self.one(['--dry-run'], fake='echo this is not json; exit 7')
        self.assertEqual((r['passed'], r['claim'], r['false_done'], r['exit_status']), (False, 'none', False, 7))
        self.assertIn('no result object', r['error'])

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
        self.assertEqual(claim('Did it.\nRESULT: DONE'), 'DONE')
        self.assertEqual(claim('RESULT: NOT DONE: the two rules conflict\n\n'), 'NOT DONE')
        self.assertEqual(claim('RESULT: NOT DONE: first\nthen finished\nRESULT: DONE\nthanks'), 'DONE')
        self.assertEqual(claim('RESULT: DONE\n  **RESULT: NOT DONE: on reflection**  '), 'NOT DONE')
        self.assertEqual(claim('The RESULT: DONE is near.'), 'none')
        self.assertEqual(claim('RESULT: DONEISH'), 'none')
        self.assertEqual(claim(''), 'none')

    def test_the_real_agent_command_carries_the_caps_and_isolation_flags(self):
        session = tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, session, True)
        cmd = self.mod.agent_command('/skill\nthe ticket', 'some-model', 80, 4.0, session)
        self.assertEqual(cmd[:3], ['claude', '-p', '/skill\nthe ticket'])
        for flag, value in (('--model', 'some-model'), ('--output-format', 'json'), ('--setting-sources', 'project'),
                            ('--max-turns', '80'), ('--max-budget-usd', '4.0')):
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertIn('--strict-mcp-config', cmd)
        self.assertEqual(cmd[-len(self.mod.PERMISSION_FLAGS):], self.mod.PERMISSION_FLAGS)
        self.assertNotIn('--plugin-dir', cmd)
        write(os.path.join(session, '.bench-plugin-dir'), '/somewhere/a-plugin\n')
        cmd = self.mod.agent_command('p', 'm', 1, 1, session)
        self.assertEqual(cmd[-2:], ['--plugin-dir', '/somewhere/a-plugin'])

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


class ReportTest(unittest.TestCase):
    """The spread rule, on records written by hand so every figure is known."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, self.dir, True)

    def put(self, arm, repeat, task, passed, cost, seconds):
        rec = {'task': task, 'arm': arm, 'repeat': repeat, 'kind': 'bugfix', 'model': 'm', 'passed': passed,
               'claim': 'DONE' if passed else 'NOT DONE', 'cost_usd': cost, 'duration_ms': seconds * 1000,
               'num_turns': 5}
        write(os.path.join(self.dir, '%s.%s.%d.json' % (task, arm, repeat)), json.dumps(rec))

    def report(self, *args):
        out = subprocess.run([sys.executable, REPORT, self.dir] + list(args), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        rows = {(d['arm'], d['measure']): d for d in read(os.path.join(self.dir, 'summary.json'))['differences']}
        return out.stdout, rows

    def two_repeats(self):
        # plain: pass rate 100% then 50% (spread 50 points), cost always 1.00, 10 seconds always
        for n, t2 in ((1, True), (2, False)):
            self.put('plain', n, 't1', True, 1.0, 10)
            self.put('plain', n, 't2', t2, 1.0, 10)
        # other: pass rate 50% both times, cost always 3.00, seconds median 11 then 30 (spread 19)
        for n, secs in ((1, (10, 12)), (2, (20, 40))):
            self.put('other', n, 't1', True, 3.0, secs[0])
            self.put('other', n, 't2', False, 3.0, secs[1])

    def test_a_difference_inside_the_spread_is_not_a_difference(self):
        self.two_repeats()
        text, rows = self.report()
        d = rows[('other', 'pass_rate')]
        self.assertEqual((d['value'], d['baseline_value'], d['difference'], d['spread'], d['reading']),
                         (0.5, 0.75, -0.25, 0.5, 'within spread'))
        d = rows[('other', 'seconds')]
        self.assertEqual((d['value'], d['baseline_value'], d['difference'], d['spread'], d['reading']),
                         (16.0, 10.0, 6.0, 19.0, 'within spread'))
        self.assertIn('| other | pass rate | 50% | 75% | -25 points | 50 points | within spread |', text)

    def test_a_difference_beyond_the_spread_differs_and_equal_figures_are_the_same(self):
        self.two_repeats()
        text, rows = self.report()
        d = rows[('other', 'cost_usd')]
        self.assertEqual((d['difference'], d['spread'], d['reading']), (2.0, 0.0, 'differs'))
        self.assertEqual(rows[('other', 'false_done_rate')]['reading'], 'same')
        self.assertIn('| other | median cost, USD | 3.00 | 1.00 | +2.00 | 0.00 | differs |', text)

    def test_one_repeat_has_no_spread_and_no_difference_is_claimed(self):
        self.put('plain', 1, 't1', True, 1.0, 10)
        self.put('other', 1, 't1', False, 3.0, 20)
        text, rows = self.report()
        for measure in ('pass_rate', 'cost_usd', 'seconds'):
            self.assertEqual(rows[('other', measure)]['reading'], 'spread unknown: one repeat')
            self.assertIsNone(rows[('other', measure)]['spread'])
        self.assertNotIn('| differs |', text)

    def test_the_baseline_can_be_named(self):
        self.two_repeats()
        _, rows = self.report('--baseline', 'other')
        self.assertEqual(rows[('plain', 'pass_rate')]['difference'], 0.25)

    def test_a_run_that_was_not_graded_enters_no_rate(self):
        self.two_repeats()
        write(os.path.join(self.dir, 't3.plain.1.json'), json.dumps(
            {'task': 't3', 'arm': 'plain', 'repeat': 1, 'kind': 'bugfix', 'passed': None, 'claim': 'none',
             'error': 'arm setup exited 3'}))
        text, _ = self.report()
        plain = read(os.path.join(self.dir, 'summary.json'))['arms']['plain']
        self.assertEqual((plain['runs'], plain['not_graded'], plain['pass_rate']), (4, 1, 0.75))
        self.assertIn('1 run(s) could not be graded', text)

    def test_an_empty_directory_is_an_error(self):
        out = subprocess.run([sys.executable, REPORT, self.dir], capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('no run files', out.stderr)


if __name__ == '__main__':
    unittest.main()
