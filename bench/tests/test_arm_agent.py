"""An arm-supplied agent (arms/<arm>/agent.sh) and the odd-040, odd-race, odd-cascade and odd-spec arms, proven with a
fake `claude` on PATH. No model is called: run.py runs as for a real model (--model haiku), and the `claude` it and
the arms start is the script below, which writes stream-json and a result object like the CLI.

The fake decides what to do from the prompt it is given: odd's race prompt ("You are one attempt"), odd's proof
prompt ("You write the PROOF") or, otherwise, the arm's own first session. FAKE_CLAUDE picks a behaviour for the run.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_bench import BENCH, build_fixture, module, read, run_py, write  # noqa: E402

COST = {'haiku': 0.01, 'sonnet': 0.1}

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, subprocess, sys, time
argv = sys.argv[1:]
if argv[:1] == ['--version']:
    print('9.9.9 (fake claude)')
    sys.exit(0)
prompt, model = argv[argv.index('-p') + 1], argv[argv.index('--model') + 1]
flags = argv[:argv.index('-p')] + argv[argv.index('-p') + 2:]
flags = flags[:flags.index('--model')] + flags[flags.index('--model') + 2:]
role = ('attempt' if 'You are one attempt' in prompt else 'proof' if 'You write the PROOF' in prompt else
        'plain' if 'odd new' not in prompt else 'outcome')
mode = os.environ.get('FAKE_CLAUDE', 'good')
with open(os.path.join(os.environ['FAKE_LOG_DIR'], 'claude-%d-%d.json' % (time.time() * 1e6, os.getpid())), 'w') as f:
    json.dump({'flags': flags, 'role': role, 'model': model, 'env': sorted(os.environ)}, f)
odd = 'python3 .odd/odd.py'
def sh(cmd):
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
PROOF = ('import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n'
         '    def test_sum(self):\n        self.assertEqual(add(2, 3), 5)\n        self.assertEqual(add(4, 1), 5)\n')
tool = {'type': 'tool_use', 'id': 't1', 'name': 'Bash', 'input': {'command': 'ls'}}
text = 'Done.'
if role == 'outcome':
    if mode == 'park':
        text = 'The ticket contradicts itself.\nRESULT: NOT DONE: the list cannot be empty and non-empty'
    else:
        sh(odd + " new add-sum 'add(2, 3) returns 5, the sum' --proof 'python3 -m unittest tests.test_sum' --in calc.py")
        if 'odd seal' in prompt:  # the arm asks this session for the proof too
            open('tests/test_sum.py', 'w').write(PROOF)
            sh(odd + ' seal add-sum --base main')
        text = 'Outcome stated.\nRESULT: DONE'
elif role == 'proof':
    open('tests/test_sum.py', 'w').write(PROOF)
elif role in ('attempt', 'plain'):
    if mode == 'crash' and role == 'attempt':
        print('API Error: 529 overloaded', file=sys.stderr)
        sys.exit(1)
    if mode == 'peek' and role == 'attempt':
        tool['input'] = {'command': 'cat ../tests_hidden/test_add.py'}
    wrong = mode == 'weak' and model == 'haiku'
    open('calc.py', 'w').write('def add(a, b):\n    return %s\n' % ('a * b' if wrong else 'a + b'))
    text = 'Fixed.\nRESULT: DONE' if role == 'plain' else 'Fixed.'
name = 'claude-%s-fake' % model
cost = {'haiku': 0.01, 'sonnet': 0.1}[model] * {'outcome': 1, 'proof': 2, 'attempt': 3, 'plain': 1}[role]
for event in ({'type': 'system', 'subtype': 'init', 'model': name},
              {'type': 'assistant', 'message': {'id': 'm-%d' % os.getpid(), 'model': name, 'content': [tool],
                                                'usage': {'input_tokens': 5, 'output_tokens': 7}}},
              {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': text, 'total_cost_usd': cost,
               'num_turns': 2, 'duration_ms': 100, 'usage': {'input_tokens': 5, 'output_tokens': 7},
               'modelUsage': {name: {'inputTokens': 5, 'outputTokens': 7, 'cacheReadInputTokens': 1,
                                     'cacheCreationInputTokens': 2}}}):
    print(json.dumps(event), flush=True)
'''

NEW_ARMS = ('odd-040', 'odd-race', 'odd-cascade', 'odd-spec')


class ArmAgentTest(unittest.TestCase):
    """Each arm run through run.py on the tiny task, as for a real model, with the fake claude on PATH."""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, self.work, True)
        self.root = build_fixture(os.path.join(self.work, 'fixture'))
        for arm in ('plain', 'odd') + NEW_ARMS:
            shutil.copytree(os.path.join(BENCH, 'arms', arm), os.path.join(self.root, 'arms', arm))
        self.bin = os.path.join(self.work, 'bin')
        write(os.path.join(self.bin, 'claude'), FAKE_CLAUDE)
        os.chmod(os.path.join(self.bin, 'claude'), 0o755)
        self.out = os.path.join(self.work, 'out')

    def run_arms(self, arms, mode='good', task='tiny-add', jobs=1):
        done = run_py(self.work, ['--root', self.root, '--tasks', task, '--arms'] + list(arms) +
                      ['--model', 'haiku', '--allow-dirty', '--jobs', str(jobs), '--out', self.out,
                       '--pass-env', 'FAKE_LOG_DIR', 'FAKE_CLAUDE'],
                      FAKE_CLAUDE=mode, PATH=self.bin + os.pathsep + os.environ['PATH'])
        recs = {}
        for arm in arms:
            path = os.path.join(self.out, '%s.%s.1.json' % (task, arm))
            self.assertTrue(os.path.exists(path), done.stdout + done.stderr)
            recs[arm] = read(path)
        return done, recs

    def calls(self):
        return [read(p) for p in sorted(glob.glob(os.path.join(self.work, 'seen', 'claude-*.json')))]

    def test_race_runs_every_session_with_the_plain_arms_flags_and_sums_their_costs(self):
        done, recs = self.run_arms(['plain', 'odd-race'])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        plain, race = recs['plain'], recs['odd-race']
        calls = self.calls()
        self.assertEqual(sorted(c['role'] for c in calls), ['attempt'] * 3 + ['outcome', 'plain'])
        flags = {json.dumps(c['flags']) for c in calls}
        self.assertEqual(len(flags), 1, 'every claude session, plain or the arm\'s, gets the same flags')
        self.assertIn('--max-turns', calls[0]['flags'])
        self.assertEqual({c['model'] for c in calls}, {'haiku'})
        envs = {json.dumps(sorted(n for n in c['env'] if n != 'ODD_ATTEMPT')) for c in calls}
        self.assertEqual(len(envs), 1, 'every claude session gets the plain arm\'s environment: %s' % envs)
        self.assertFalse([n for n in calls[0]['env'] if n.startswith(('ARM_', 'BENCH_'))])
        self.assertEqual((race['passed'], race['claim'], race['error']), (True, 'DONE', None), race['final'])
        self.assertAlmostEqual(race['cost_usd'], 0.01 + 3 * 0.03)
        self.assertEqual(race['num_turns'], 8)
        self.assertEqual(race['output_tokens'], 4 * 7)
        self.assertEqual(race['models'], ['claude-haiku-fake'])
        self.assertEqual(len(race['sessions']), 4)
        self.assertEqual(race['arm_check'], 0, 'the pinned odd gate passes on what the arm left')
        merged = read(os.path.join(self.out, race['transcript'])).splitlines()
        self.assertEqual(sum(json.loads(x).get('type') == 'result' for x in merged if x.startswith('{')), 5,
                         'four sessions\' results and the arm\'s own')
        self.assertFalse(race['contaminated'], race['contaminated_by'])
        self.assertAlmostEqual(plain['cost_usd'], 0.01)
        self.assertEqual((plain['passed'], plain['claim']), (True, 'DONE'))
        self.assertNotIn('sessions', plain)

    def test_cascade_escalates_to_the_strong_model_when_the_cheap_attempt_is_not_verified(self):
        done, recs = self.run_arms(['odd-cascade'], mode='weak')
        r = recs['odd-cascade']
        self.assertEqual((r['passed'], r['claim'], r['error']), (True, 'DONE', None), r['final'])
        roles = [(c['role'], c['model']) for c in self.calls()]
        self.assertEqual(sorted(roles), [('attempt', 'haiku'), ('attempt', 'sonnet'), ('outcome', 'haiku')])
        self.assertAlmostEqual(r['cost_usd'], 0.01 + 0.03 + 0.3)
        self.assertEqual(r['models'], ['claude-haiku-fake', 'claude-sonnet-fake'])

    def test_spec_has_the_strong_model_write_the_proof_and_one_cheap_attempt_write_the_code(self):
        done, recs = self.run_arms(['odd-spec'])
        r = recs['odd-spec']
        self.assertEqual((r['passed'], r['claim'], r['error']), (True, 'DONE', None), r['final'])
        roles = sorted((c['role'], c['model']) for c in self.calls())
        self.assertEqual(roles, [('attempt', 'haiku'), ('outcome', 'haiku'), ('proof', 'sonnet')])
        self.assertAlmostEqual(r['cost_usd'], 0.01 + 0.2 + 0.03)

    def test_an_arm_sessions_peek_is_seen_by_the_contamination_audit(self):
        done, recs = self.run_arms(['odd-race'], mode='peek')
        r = recs['odd-race']
        self.assertTrue(r['contaminated'])
        self.assertEqual(r['contaminated_by'], 'tests_hidden')

    def test_a_claude_session_crashing_mid_arm_is_an_infrastructure_error(self):
        done, recs = self.run_arms(['odd-race'], mode='crash')
        r = recs['odd-race']
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIsNone(r['passed'])
        self.assertIn('claude session', r['error'])
        self.assertIn('no result object', r['error'])

    def test_the_first_sessions_not_done_is_the_arms_claim_and_no_attempt_runs(self):
        done, recs = self.run_arms(['odd-race'], mode='park')
        r = recs['odd-race']
        self.assertEqual((r['claim'], r['claim_reason']), ('NOT DONE', 'the list cannot be empty and non-empty'))
        self.assertEqual([c['role'] for c in self.calls()], ['outcome'])
        self.assertAlmostEqual(r['cost_usd'], 0.01)

    def test_odd_040_is_the_odd_arm_one_session_under_its_own_name(self):
        done, recs = self.run_arms(['odd-040'])
        r = recs['odd-040']
        self.assertEqual((r['passed'], r['claim']), (True, 'DONE'))
        self.assertEqual([c['role'] for c in self.calls()], ['plain'])
        self.assertNotIn('sessions', r)
        self.assertEqual(r['arm_notes'], {'odd_py': 'same'})

    def test_a_fake_agent_replaces_an_arm_supplied_agent_too(self):
        fake = '%s -c %s' % (sys.executable, "'import json; print(json.dumps({\"result\": \"RESULT: NOT DONE: x\"}))'")
        done = run_py(self.work, ['--root', self.root, '--tasks', 'tiny-add', '--arms', 'odd-race', '--out',
                                  self.out, '--dry-run'], fake=fake, PATH=self.bin + os.pathsep + os.environ['PATH'])
        r = read(os.path.join(self.out, 'tiny-add.odd-race.1.json'))
        self.assertEqual((r['claim'], r['error']), ('NOT DONE', None), done.stderr)
        self.assertEqual(self.calls(), [], 'no claude was started')


class ArmFilesTest(unittest.TestCase):
    def test_every_new_arm_has_its_files_and_states_what_it_does(self):
        for arm in NEW_ARMS:
            d = os.path.join(BENCH, 'arms', arm)
            for name in ('setup.sh', 'prompt.md', 'VERSION', 'NOTES.md'):
                self.assertTrue(os.path.isfile(os.path.join(d, name)), (arm, name))
            self.assertEqual(len(read(os.path.join(d, 'VERSION')).splitlines()), 1)
            self.assertIn('\n## To state with the results\n', read(os.path.join(d, 'NOTES.md')))
            self.assertEqual(os.path.isfile(os.path.join(d, 'agent.sh')), arm != 'odd-040', arm)
            prompt = read(os.path.join(d, 'prompt.md'))
            self.assertEqual(prompt.count('{ticket}'), 1)
            self.assertNotIn('RESULT:', prompt, 'the common ending is run.py\'s')

    def test_the_sum_over_sessions_counts_a_session_without_a_result_as_cost_missing(self):
        helper = module('arm_agent')
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder, True)
        write(os.path.join(folder, '1-a.jsonl'), json.dumps({'type': 'result', 'total_cost_usd': 0.5, 'num_turns': 3,
                                                             'usage': {'output_tokens': 4}}) + '\n')
        write(os.path.join(folder, '2-b.jsonl'), json.dumps({'type': 'assistant', 'message': {
            'id': 'x', 'model': 'm', 'usage': {'output_tokens': 6}}}) + '\n')
        s = helper.total(folder)
        self.assertIsNone(s['total_cost_usd'])
        self.assertEqual((s['usage']['output_tokens'], s['num_turns'], s['models']), (10, 4, ['m']))
        self.assertEqual([x['cost_usd'] for x in s['sessions']], [0.5, None])


if __name__ == '__main__':
    unittest.main()
