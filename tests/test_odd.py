"""Tests for odd.py. Each test builds a throwaway git repository and drives the tool the way an agent or CI would.

Run: python3 -m unittest discover -s tests        (from the repository root)

The "attack" tests are the reason the tool exists: each one is a way an agent could report done without the outcome
holding, and each must end in a non-zero exit.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ODD = os.path.join(os.path.dirname(HERE), 'odd.py')
sys.path.insert(0, os.path.dirname(HERE))
import odd as oddmod  # noqa: E402

PROOF = '%s -m unittest -q tests.test_calc' % sys.executable
BROKEN = 'def add(a, b):\n    return 0\n'
FIXED = 'def add(a, b):\n    return a + b\n'
TEST = ('import unittest\nfrom calc import add\n\n\nclass T(unittest.TestCase):\n    def test_add(self):\n'
        '        self.assertEqual(add(2, 3), 5)\n')


class Repo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='odd-test-')
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.com')
        self.git('config', 'user.name', 't')
        self.write('calc.py', BROKEN)
        self.write('README.md', 'calc\n')
        self.write('.gitignore', '__pycache__/\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'init')
        self.git('checkout', '-q', '-b', 'feat')

    def git(self, *a):
        return subprocess.run(['git'] + list(a), cwd=self.dir, capture_output=True, text=True, check=True).stdout

    def write(self, rel, text):
        p = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            f.write(text)

    def read(self, rel):
        with open(os.path.join(self.dir, rel)) as f:
            return f.read()

    def odd(self, *a, stdin=None, env=None):
        e = dict(os.environ, **(env or {}))
        e.pop('ODD_BASE', None)
        r = subprocess.run([sys.executable, ODD] + list(a), cwd=self.dir, capture_output=True, text=True, input=stdin, env=e)
        return r.returncode, r.stdout + r.stderr

    def ok(self, *a, **k):
        rc, out = self.odd(*a, **k)
        self.assertEqual(rc, 0, out)
        return out

    def no(self, *a, code=1, **k):
        rc, out = self.odd(*a, **k)
        self.assertEqual(rc, code, out)
        return out

    def outcome(self, slug='add', proof=PROOF, in_='calc.py', sentence='A caller of add(2, 3) receives 5.', *extra):
        self.ok('new', slug, sentence, '--proof', proof, '--in', in_, *extra)

    def solve(self):
        self.write('tests/test_calc.py', TEST)
        self.write('calc.py', FIXED)


class HappyPath(Repo):
    def test_outcome_proof_red_change_done_gate(self):
        self.ok('init')
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.assertIn('red', self.ok('red', 'add'))
        self.write('calc.py', FIXED)
        out = self.ok('done', 'add')
        self.assertIn('fails with the change taken out (1 file(s))', out)
        self.assertIn('not yet proven on the real system', out)
        self.assertEqual(self.read('calc.py'), FIXED, 'the change is put back after the counterfactual run')
        self.assertIn('status: done', self.read('.odd/outcomes/add.md'))
        self.assertIn('PASS', self.ok('gate'))
        self.assertIn('PASS', self.ok('gate', '--recompute'))

    def test_real_system_proofs_are_reported_as_proven(self):
        self.outcome('add', PROOF, 'calc.py', 'A caller of add(2, 3) receives 5.', '--real')
        self.solve()
        self.assertIn('PROVEN on the real system', self.ok('done', 'add'))

    def test_a_commit_or_an_unrelated_edit_stales_nothing(self):
        self.outcome()
        self.solve()
        self.ok('done', 'add')
        self.git('add', '-A')
        self.git('commit', '-qm', 'work')
        self.write('README.md', 'calc\nmore words\n')
        self.assertIn('PASS', self.ok('gate'))
        self.assertIn('done ', self.ok('status'))

    def test_an_edit_inside_the_boundary_after_done_makes_it_stale(self):
        self.outcome()
        self.solve()
        self.ok('done', 'add')
        self.write('calc.py', FIXED + '# later edit\n')
        self.assertIn('files changed since it was verified', self.no('gate'))
        self.assertIn('stale', self.ok('status'))

    def test_red_refuses_a_proof_that_already_passes(self):
        self.outcome('add', 'true')
        self.assertIn('already passes before the change', self.no('red', 'add'))

    def test_new_and_deleted_files_and_file_modes_survive_the_counterfactual(self):
        self.git('checkout', '-q', 'main')
        self.write('old.py', 'x = 1\n')
        self.write('run.sh', '#!/bin/sh\nexit 1\n')
        os.chmod(os.path.join(self.dir, 'run.sh'), 0o755)
        self.git('add', '-A')
        self.git('commit', '-qm', 'more')
        self.git('checkout', '-q', '-B', 'feat')
        self.outcome('swap', "test -f new.py && test ! -f old.py && grep -q 'exit 0' run.sh", 'new.py, old.py, run.sh',
                     'A maintainer finds new.py in place of old.py and run.sh exits 0.')
        self.write('new.py', 'y = 2\n')
        os.remove(os.path.join(self.dir, 'old.py'))
        self.write('run.sh', '#!/bin/sh\nexit 0\n')
        self.assertIn('3 file(s)', self.ok('done', 'swap'))
        self.assertEqual(self.read('new.py'), 'y = 2\n')
        self.assertFalse(os.path.exists(os.path.join(self.dir, 'old.py')))
        self.assertTrue(os.access(os.path.join(self.dir, 'run.sh'), os.X_OK))


class Attacks(Repo):
    """Ways to claim done without the outcome holding. Every one must fail."""

    def test_a_proof_that_cannot_fail_is_rejected(self):
        self.outcome('add', 'true')
        self.write('calc.py', FIXED)
        self.assertIn('still passes with the change taken out', self.no('done', 'add'))
        self.assertIn('status: open', self.read('.odd/outcomes/add.md'))

    def test_a_weakened_test_is_rejected(self):
        self.outcome()
        self.write('calc.py', FIXED)
        self.write('tests/test_calc.py', TEST.replace('self.assertEqual(add(2, 3), 5)', 'self.assertTrue(True)'))
        self.assertIn('does not depend on the change', self.no('done', 'add'))

    def test_a_failing_proof_is_rejected(self):
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.assertIn('the proof fails', self.no('done', 'add'))

    def test_files_written_outside_the_boundary_are_seen_even_from_a_shell(self):
        self.outcome()
        self.solve()
        subprocess.run('seq 1 40 > smuggled.py', shell=True, cwd=self.dir, check=True)
        self.assertIn('smuggled.py', self.no('done', 'add'))
        self.ok('widen', 'add', 'smuggled.py', 'the table the adder reads')
        self.ok('done', 'add')
        self.assertIn('widened: smuggled.py', self.read('.odd/outcomes/add.md'))

    def test_status_set_by_hand_does_not_pass_the_gate(self):
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.write('calc.py', BROKEN + '\n' * 30)
        md = self.read('.odd/outcomes/add.md').replace('status: open', 'status: done')
        self.write('.odd/outcomes/add.md', md)
        self.assertIn('FAIL', self.no('gate'))

    def test_forged_evidence_passes_locally_and_fails_when_recomputed(self):
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.write('calc.py', BROKEN + '# 1\n' * 30)  # the outcome does NOT hold
        self.write('.odd/outcomes/add.md', self.read('.odd/outcomes/add.md').replace('status: open', 'status: done'))
        cfg = oddmod.load_config(self.dir)
        base = oddmod.gate_base(self.dir, cfg)
        o = oddmod.Outcome.load(self.dir, 'add')
        h = oddmod.content_hash(self.dir, cfg, o, oddmod.changed_files(self.dir, base))
        with open(os.path.join(self.dir, '.odd/evidence/add.jsonl'), 'a') as f:
            f.write(json.dumps({'ts': 'forged', 'kind': 'done', 'ok': True, 'hash': h}) + '\n')
        self.assertIn('PASS', self.ok('gate'))                      # local evidence is fast feedback, not proof
        self.assertIn('the proof fails', self.no('gate', '--recompute'))  # CI trusts nothing recorded

    def test_a_change_cannot_loosen_its_own_gate(self):
        self.ok('init')
        self.git('add', '-A')
        self.git('commit', '-qm', 'adopt odd')
        self.git('branch', '-f', 'main', 'HEAD')
        cfg = json.loads(self.read('.odd/config.json'))
        cfg['trivial_lines'] = 100000
        self.write('.odd/config.json', json.dumps(cfg))
        self.write('big.py', 'x = 1\n' * 60)
        self.assertIn('PASS', self.ok('gate'))
        out = self.no('gate', '--recompute', '--base', 'main')
        self.assertIn('CONTROL FILES CHANGED', out)
        self.assertIn('not covered by a verified outcome', out)

    def test_the_proof_may_not_be_a_file_the_check_takes_out(self):
        self.write('check.sh', '#!/bin/sh\nexit 1\n')
        os.chmod(os.path.join(self.dir, 'check.sh'), 0o755)
        self.git('add', '-A')
        self.git('commit', '-qm', 'a check script')
        self.outcome('add', './check.sh', 'calc.py, check.sh')
        self.write('check.sh', '#!/bin/sh\nexit 0\n')
        self.write('calc.py', FIXED)
        self.assertIn('the proof runs check.sh', self.no('done', 'add'))

    def test_a_proof_that_cannot_run_without_the_change_is_not_counted_as_failing(self):
        self.outcome('add', 'sh -c "./tool.sh"', 'tool.sh', 'A maintainer running tool.sh sees it exit 0.')
        self.write('tool.sh', '#!/bin/sh\nexit 0\n')
        os.chmod(os.path.join(self.dir, 'tool.sh'), 0o755)
        out = self.no('done', 'add', code=2)  # exit 127 on the tree without tool.sh: nothing was established
        self.assertIn('could not run', out)
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'tool.sh')), 'the change is put back')

    def test_skipping_the_counterfactual_is_counted_and_can_be_capped(self):
        self.outcome('add', 'true', 'calc.py', 'A reader of calc.py finds the adder renamed with no behaviour change.',
                     '--skip-counterfactual', 'pure rename, nothing can fail first')
        self.write('calc.py', BROKEN.replace('a, b', 'x, y'))
        self.assertIn('counterfactual skipped', self.ok('done', 'add'))
        self.assertIn('1 outcome(s) skip the counterfactual check', self.ok('gate'))
        self.write('.odd/config.json', json.dumps({'max_skips': 0}))
        self.assertIn('this project allows 0', self.no('gate'))


class Messages(Repo):
    def test_unignored_build_output_is_named_as_such(self):
        os.remove(os.path.join(self.dir, '.gitignore'))
        self.git('commit', '-qam', 'no ignore file')
        self.outcome()
        self.solve()
        out = self.no('done', 'add')
        self.assertIn('__pycache__', out)
        self.assertIn('add it to .gitignore', out)


class SmallChangeLane(Repo):
    def test_a_few_lines_need_no_outcome_and_more_do(self):
        self.write('calc.py', BROKEN + '# note\n')
        self.assertIn('small-change lane', self.ok('gate'))
        self.write('calc.py', BROKEN + '# note\n' * 30)
        out = self.no('gate')
        self.assertIn('not covered by a verified outcome', out)
        self.assertIn('odd new', out)

    def test_exempt_paths_never_need_an_outcome(self):
        self.write('README.md', 'words\n' * 200)
        self.assertIn('PASS', self.ok('gate'))


class HonestExits(Repo):
    def test_park_and_abort_need_a_reason_and_are_recorded(self):
        self.outcome()
        self.no('park', 'add', 'x')
        self.ok('park', 'add', 'waiting on the payments sandbox key from the owner')
        self.assertIn('status: parked', self.read('.odd/outcomes/add.md'))
        self.ok('abort', 'add', 'the API has no endpoint that returns totals per seat')
        self.assertIn('aborted', self.ok('status'))

    def test_a_parked_outcome_does_not_pass_the_gate_but_done_reopens_it(self):
        self.outcome()
        self.solve()
        self.write('calc.py', FIXED + '# pad\n' * 30)
        self.ok('park', 'add', 'blocked on a decision about rounding')
        self.assertIn('PARKED', self.no('gate'))
        self.ok('done', 'add')
        self.assertIn('PASS', self.ok('gate'))


class Robustness(Repo):
    def test_two_open_outcomes_share_a_change(self):
        self.outcome()
        self.outcome('doc', 'grep -q usage notes.txt', 'notes.txt', 'A new developer finds a usage line in notes.txt.')
        self.solve()
        self.write('notes.txt', 'usage: add(a, b)\n' * 30)
        self.assertIn('still open in this change: doc', self.ok('done', 'add'))
        self.no('gate')
        self.ok('done', 'doc')
        self.assertIn('PASS', self.ok('gate'))

    def test_a_proof_that_times_out_is_could_not_run_not_pass_or_fail(self):
        self.write('.odd/config.json', json.dumps({'proof_timeout': 1}))
        self.outcome('add', 'sleep 5')
        self.write('calc.py', FIXED)
        self.assertIn('could not run', self.no('done', 'add', code=2))

    def test_outside_git_is_could_not_run(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        r = subprocess.run([sys.executable, ODD, 'gate'], cwd=d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_outcome_files_are_parsed_strictly(self):
        self.outcome()
        md = self.read('.odd/outcomes/add.md')
        self.write('.odd/outcomes/add.md', md.replace('outcome: A caller of add(2, 3) receives 5.',
                                                    'outcome: A caller of add(2, 3)\n  receives 5.'))
        self.assertIn('receives 5.', self.ok('status'))          # an indented line continues the value
        self.write('.odd/outcomes/add.md', md.replace('proof:', 'this is not a field\nproof:'))
        self.assertIn('expected "key: value"', self.no('status'))  # anything else is refused, never dropped silently
        self.write('.odd/outcomes/add.md', '\n'.join(l for l in md.split('\n') if not l.startswith('proof:')))
        self.assertIn('missing "proof:"', self.no('status'))

    def test_globs(self):
        m = oddmod.matches
        self.assertTrue(m('a.py', ['a.py']))
        self.assertFalse(m('data.py', ['a.py']))
        self.assertTrue(m('src/pay/x/y.py', ['src/pay']))
        self.assertTrue(m('src/pay/x/y.py', ['src/**']))
        self.assertFalse(m('src2/y.py', ['src']))
        self.assertTrue(m('README.md', ['**/*.md']) and m('docs/a/b.md', ['**/*.md']))
        self.assertFalse(m('src/a/b.py', ['src/*.py']))
        self.assertTrue(m('src/b.py', ['./src/*.py']))

    def test_an_interrupted_check_puts_the_change_back(self):
        marker = 'sleep 31.7'
        self.outcome('add', "grep -q 'a + b' calc.py && exit 0; %s" % marker)
        self.write('calc.py', FIXED)
        for sig, expect_restored_at_once in ((signal.SIGTERM, True), (signal.SIGKILL, False)):
            p = subprocess.Popen([sys.executable, ODD, 'done', 'add'], cwd=self.dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            deadline = time.time() + 15
            while time.time() < deadline and self.read('calc.py') != BROKEN:
                time.sleep(0.05)
            self.assertEqual(self.read('calc.py'), BROKEN, 'the counterfactual run reverts the change in place')
            p.send_signal(sig)
            p.wait(10)
            subprocess.run(['pkill', '-f', marker], capture_output=True)
            if expect_restored_at_once:
                self.assertEqual(self.read('calc.py'), FIXED, 'SIGTERM restores before exiting')
            else:
                self.assertEqual(self.read('calc.py'), BROKEN, 'SIGKILL leaves the tree reverted...')
                self.assertIn('1 file(s) were put back', self.no('status', code=2))  # ...the next command puts it back, and says so
                self.assertEqual(self.read('calc.py'), FIXED)
                self.ok('status')

    def test_stats_and_escape(self):
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.no('done', 'add')
        self.write('calc.py', FIXED)
        self.ok('done', 'add')
        self.ok('escape', 'add', 'add(0.1, 0.2) returned 0.30000000000000004 on the receipt')
        out = self.ok('stats')
        self.assertIn('1 needed more than one attempt', out)
        self.assertIn('1 escaped defect(s)', out)


class Setup(Repo):
    def test_init_is_idempotent_and_renders_one_method_text_everywhere(self):
        self.ok('init', '--claude', '--cursor', '--copilot', '--ci', '--hook', 'pre-push')
        self.ok('init', '--claude', '--cursor', '--copilot', '--ci', '--hook', 'pre-push')
        body = oddmod.METHOD.replace('{trivial}', '25').rstrip('\n')
        for rel in ('AGENTS.md', '.github/copilot-instructions.md', '.cursor/rules/odd.mdc'):
            text = self.read(rel)
            self.assertEqual(text.count(body), 1, rel)
        self.assertEqual(self.read('AGENTS.md').count(oddmod.BEGIN), 1)
        self.assertIn('@AGENTS.md', self.read('CLAUDE.md'))
        hooks = json.loads(self.read('.claude/settings.json'))['hooks']
        self.assertEqual([len(hooks[e]) for e in ('PreToolUse', 'Stop', 'SessionStart')], [1, 1, 1])
        self.assertEqual(self.read('.odd/odd.py'), open(ODD).read())
        self.assertEqual(self.read('.git/hooks/pre-push').count(oddmod.HOOK_MARK), 1)
        self.assertIn('fetch-depth: 0', self.read('.github/workflows/odd.yml'))
        self.assertIn('enforcement of record', self.ok('doctor'))

    def test_init_keeps_what_is_already_there(self):
        self.write('AGENTS.md', '# House rules\n\nBe kind.\n')
        self.write('.claude/settings.json', json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'mine.sh'}]}]}}))
        self.ok('init')
        self.assertIn('Be kind.', self.read('AGENTS.md'))
        self.assertIn('mine.sh', self.read('.claude/settings.json'))

    def test_doctor_warns_when_nothing_recomputes_the_gate(self):
        self.ok('init')
        self.assertIn('no enforcement of record', self.no('doctor'))

    def test_the_vendored_copy_runs_on_its_own(self):
        self.ok('init')
        r = subprocess.run([sys.executable, '.odd/odd.py', 'status'], cwd=self.dir, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


class EditorHooks(Repo):
    def hook(self, event, payload):
        payload = dict({'session_id': 's1', 'cwd': self.dir}, **payload)
        rc, out = self.odd('hook', event, stdin=json.dumps(payload))
        self.assertEqual(rc, 0, out)
        return out

    def test_writes_stay_inside_the_open_outcome(self):
        w = lambda rel: self.hook('pre-tool', {'tool_name': 'Write', 'tool_input': {'file_path': os.path.join(self.dir, rel)}})
        self.assertEqual(w('anything.py'), '', 'no outcome open: small edits are free')
        self.outcome()
        self.assertEqual(w('calc.py'), '')
        self.assertEqual(w('tests/test_calc.py'), '', "the proof's own files are always allowed")
        self.assertEqual(w('README.md'), '')
        self.assertIn('outside the open outcome', w('other.py'))
        self.assertIn('written only by the odd tool', w('.odd/evidence/add.jsonl'))
        self.write('.odd/config.json', json.dumps({'guard': 'off'}))
        self.assertEqual(w('other.py'), '')

    def test_turn_end_blocks_only_when_this_turn_changed_files_and_the_work_is_unproven(self):
        self.hook('session-start', {})
        self.assertEqual(self.hook('stop', {}), '', 'a question or a discussion is never blocked')
        self.outcome()
        self.solve()
        self.write('calc.py', FIXED + '# pad\n' * 30)
        self.assertIn('"block"', self.hook('stop', {}))
        self.assertEqual(self.hook('stop', {}), '', 'the same state is not blocked twice')
        self.write('calc.py', FIXED + '# pad\n' * 31)
        self.assertEqual(self.hook('stop', {'stop_hook_active': True}), '', 'never loops')
        self.write('calc.py', FIXED + '# pad\n' * 32)
        self.ok('park', 'add', 'blocked on a decision about rounding')
        self.assertEqual(self.hook('stop', {}), '', 'a parked outcome is an honest end to the turn')
        self.ok('done', 'add')
        self.assertEqual(self.hook('stop', {}), '', 'proven work ends the turn')

    def test_hooks_fail_open_and_doctor_says_so(self):
        self.ok('init', '--hook', 'pre-push')
        self.write('.odd/outcomes/bad.md', 'not an outcome file\n')
        rc, out = self.odd('hook', 'pre-tool', stdin=json.dumps({'tool_input': {'file_path': 'x.py'}, 'cwd': self.dir}))
        self.assertEqual((rc, out), (0, ''))
        self.assertIn('failed open 1 time(s)', self.no('doctor'))
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        r = subprocess.run([sys.executable, ODD, 'hook', 'stop'], cwd=d, input='{}', capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ''))


if __name__ == '__main__':
    unittest.main()
