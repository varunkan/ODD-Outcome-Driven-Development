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
peeked = []  # peeklog: what an attempt finds by walking up its tree (earlier sessions' transcripts)
if mode == 'peeklog' and role == 'attempt':
    here = os.getcwd()
    while os.path.dirname(here) != here:
        folder = os.path.join(here, 'transcripts')
        if os.path.isdir(folder):
            peeked += [os.path.join(folder, n) for n in os.listdir(folder) if n.endswith('.jsonl')]
        here = os.path.dirname(here)
with open(os.path.join(os.environ['FAKE_LOG_DIR'], 'claude-%d-%d.json' % (time.time() * 1e6, os.getpid())), 'w') as f:
    json.dump({'flags': flags, 'role': role, 'model': model, 'env': sorted(os.environ), 'peeked': peeked}, f)
odd = 'python3 .odd/odd.py'
def sh(cmd):
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
PROOF = ('import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n'
         '    def test_sum(self):\n        self.assertEqual(add(2, 3), 5)\n        self.assertEqual(add(4, 1), 5)\n')
tool = {'type': 'tool_use', 'id': 't1', 'name': 'Bash', 'input': {'command': 'ls'}}
text, subtype = 'Done.', 'success'
if role == 'outcome':
    if mode == 'capfirst':  # stopped at the turn cap, as the CLI reports it: no result text
        sh(odd + " new add-sum 'add(2, 3) returns 5, the sum' --proof 'python3 -m unittest tests.test_sum' --in calc.py")
        text, subtype = None, 'error_max_turns'
    elif mode == 't17done':  # claims DONE, never names the conflict; odd seal then refuses (no test file changed)
        sh(odd + " new parse-2h-duration 'parse_duration reads typed durations' "
                 "--proof 'python3 -m unittest tests.test_duration' --in timesheet/duration.py")
        text = 'Outcome stated.\nRESULT: DONE'
    elif mode == 'park':
        text = 'The ticket contradicts itself.\nRESULT: NOT DONE: the list cannot be empty and non-empty'
    else:
        sh(odd + " new add-sum 'add(2, 3) returns 5, the sum' --proof 'python3 -m unittest tests.test_sum' --in calc.py")
        if 'odd seal' in prompt:  # the arm asks this session for the proof too
            open('tests/test_sum.py', 'w').write(PROOF.replace('add(2, 3), 5', 'add(2, 3), 6') if mode == 'dispute' else PROOF)
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
    if mode == 'dispute' and role == 'attempt' and 'add(2, 3), 6' in open('tests/test_sum.py').read():
        text = 'The proof is wrong.\nodd-dispute: tests/test_sum.py expects add(2, 3) == 6, the outcome says 5'
        tool['input'] = {'command': 'cat tests/test_sum.py'}
    else:
        open('calc.py', 'w').write('def add(a, b):\n    return %s\n' % ('a * b' if wrong else 'a + b'))
        text = 'Fixed.\nRESULT: DONE' if role == 'plain' else 'Fixed.'
name = 'claude-%s-fake' % model
cost = {'haiku': 0.01, 'sonnet': 0.1}[model] * {'outcome': 1, 'proof': 2, 'attempt': 3, 'plain': 1}[role]
for event in ({'type': 'system', 'subtype': 'init', 'model': name},
              {'type': 'assistant', 'message': {'id': 'm-%d' % os.getpid(), 'model': name, 'content': [tool],
                                                'usage': {'input_tokens': 5, 'output_tokens': 7}}},
              {'type': 'result', 'subtype': subtype, 'is_error': subtype != 'success', 'result': text,
               'total_cost_usd': cost,
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

    def run_arms(self, arms, mode='good', task='tiny-add', jobs=1, extra=()):
        done = run_py(self.work, ['--root', self.root, '--tasks', task, '--arms'] + list(arms) + list(extra) +
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
        def uncapped(flags):  # the caps' values are what is left of the run's (test_..._caps_hold_for_the_whole_run)
            return [f if n == 0 or flags[n - 1] not in ('--max-turns', '--max-budget-usd') else 'N'
                    for n, f in enumerate(flags)]
        flags = {json.dumps(uncapped(c['flags'])) for c in calls}
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

    def test_a_disputed_proof_goes_back_to_its_author_once_and_the_race_runs_again(self):
        done, recs = self.run_arms(['odd-race'], mode='dispute')
        r = recs['odd-race']
        self.assertEqual((r['passed'], r['claim'], r['error']), (True, 'DONE', None), r['final'])
        self.assertIn('odd spec add-sum', r['final'])
        roles = sorted((c['role'], c['model']) for c in self.calls())
        self.assertEqual(roles, [('attempt', 'haiku')] * 6 + [('outcome', 'haiku'), ('proof', 'haiku')],
                         'the race arm\'s proof author is its own (cheap) model')

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

    def test_a_done_claim_and_odds_refusal_do_not_pass_an_impossible_task_on_the_arms_own_words(self):
        # review blocker: the arm wrote the NOT DONE reason from odd's text ("no test file", the slug "2h"), and the
        # t17 keyword grade credited a conflict no session ever named
        t17 = 't17-conflicting-visible-test'
        shutil.copytree(os.path.join(BENCH, 'tasks', t17), os.path.join(self.root, 'tasks', t17))
        done, recs = self.run_arms(['odd-race'], mode='t17done', task=t17)
        r = recs['odd-race']
        self.assertEqual(r['claim'], 'NOT DONE', r['final'])
        self.assertEqual(r['claim_reason'], '', 'a reason the arm built is never graded as the agent\'s')
        self.assertIn('could not be sealed', r['arm_reason'])
        self.assertIs(r['passed'], False, r['final'])
        self.assertEqual((r['agent_claim'], r['claim_source']), ('DONE', 'arm'))

    def test_the_claim_source_says_whose_claim_was_graded(self):
        done, recs = self.run_arms(['plain', 'odd-race'])
        self.assertEqual((recs['plain']['claim_source'], recs['plain']['agent_claim']), ('agent', 'DONE'))
        self.assertEqual((recs['odd-race']['claim_source'], recs['odd-race']['agent_claim']), ('arm', 'DONE'))
        self.assertEqual(recs['odd-race']['budget_scope'], 'run')

    def test_a_parked_first_session_is_the_agents_own_claim(self):
        done, recs = self.run_arms(['odd-race'], mode='park')
        self.assertEqual((recs['odd-race']['claim_source'], recs['odd-race']['agent_claim']), ('agent', 'NOT DONE'))

    def test_a_capped_first_session_ends_the_arm_and_the_run_is_stopped_at_the_cap(self):
        done, recs = self.run_arms(['plain', 'odd-race'], mode='capfirst')
        r = recs['odd-race']
        self.assertEqual([c['role'] for c in self.calls() if c['role'] != 'plain'], ['outcome'],
                         'no attempt runs after a first session stopped at a cap')
        self.assertEqual((r['claim'], r['stopped_at'], r['error']), ('none', 'max_turns', None), r['final'])

    def test_the_turn_and_budget_caps_hold_for_the_whole_run_not_each_session(self):
        done, recs = self.run_arms(['odd-cascade'], mode='weak', extra=['--max-turns', '20', '--max-budget-usd', '0.05'])
        attempts = [c for c in self.calls() if c['role'] == 'attempt']
        caps = [(c['model'], c['flags'][c['flags'].index('--max-turns') + 1],
                 float(c['flags'][c['flags'].index('--max-budget-usd') + 1])) for c in attempts]
        self.assertEqual([c[:2] for c in caps], [('haiku', '18'), ('sonnet', '16')], 'what is left of the run\'s turns')
        self.assertAlmostEqual(caps[0][2], 0.04)
        self.assertAlmostEqual(caps[1][2], 0.01)

    def test_a_session_is_refused_once_the_runs_turns_are_spent(self):
        done, recs = self.run_arms(['plain', 'odd-race'], extra=['--max-turns', '2', '--max-budget-usd', '0.02'])
        r = recs['odd-race']
        self.assertEqual(sorted(c['role'] for c in self.calls()), ['outcome', 'plain'], 'no attempt was started')
        self.assertAlmostEqual(r['cost_usd'], 0.01)
        self.assertEqual(r['num_turns'], 2)
        self.assertEqual((r['stopped_at'], r['error']), ('max_turns', None), r['final'])

    def test_no_session_can_reach_an_earlier_sessions_transcript_by_walking_up_its_tree(self):
        done, recs = self.run_arms(['odd-race'], mode='peeklog')
        self.assertEqual([c['peeked'] for c in self.calls() if c['role'] == 'attempt'], [[], [], []])
        self.assertFalse(recs['odd-race']['contaminated'], recs['odd-race']['contaminated_by'])

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


    def test_a_failed_gate_is_given_by_its_first_problem_not_a_passing_outcomes_summary(self):
        gate = ('odd gate --recompute: base 1234567890, 4 file(s) changed, 2 outcome(s) in this change\n'
                '  ok      one: A caller of m.f() receives 1.\n'
                '          took out 1 file(s), 6 line(s); without them the proof said: AssertionError: 0 != 1 / FAILED\n'
                'FAIL\n'
                '  m.py is inside the boundary of one and two: within one change a file belongs to one outcome.\n')
        self.assertTrue(module('arm_agent').why(gate).startswith('m.py is inside the boundary of one and two'))

    def test_stated_outcomes_follow_the_build_order_of_a_chain_file_the_session_wrote(self):
        helper, repo = module('arm_agent'), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, repo, True)
        git = lambda *a: subprocess.run(['git', '-C', repo] + list(a), check=True, capture_output=True)  # noqa: E731
        git('init', '-q', '-b', 'main')
        write(os.path.join(repo, 'README.md'), 'x\n')
        git('add', '-A')
        git('-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-qm', 'init')
        for slug in ('a', 'b', 'c'):
            write(os.path.join(repo, '.odd', 'outcomes', slug + '.md'), '---\n')
        here = os.getcwd()
        os.chdir(repo)
        try:
            self.assertEqual([os.path.basename(p) for p in helper.stated_outcomes()], ['a.md', 'b.md', 'c.md'])
            write(os.path.join(repo, '.odd', 'chains', 'T-1.md'), '# build order\nc\n- a\n')
            self.assertEqual([os.path.basename(p) for p in helper.stated_outcomes()], ['c.md', 'a.md', 'b.md'])
        finally:
            os.chdir(here)

if __name__ == '__main__':
    unittest.main()
