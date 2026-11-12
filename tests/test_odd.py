"""Tests for odd.py. Each test builds a throwaway git repository and drives the tool the way an agent or CI would.

Run: python3 -m unittest discover -s tests        (from the repository root)

The "Attacks" tests are the reason the tool exists: each is a way an agent could report done without the outcome
holding, and each must end in a non-zero exit. "GitShapes" and "InPlaceCheck" hold one fixture per hole the design
review named (docs/evidence/10-design-review.md).
"""
import json
import os
import re
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
SENTENCE = 'A caller of add(2, 3) receives 5.'


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
        self.commit('init')
        self.git('checkout', '-q', '-b', 'feat')

    def git(self, *a):
        return subprocess.run(['git'] + list(a), cwd=self.dir, capture_output=True, text=True, check=True).stdout

    def commit(self, msg):
        self.git('add', '-A')
        self.git('commit', '-qm', msg)

    def path(self, rel):
        return os.path.join(self.dir, rel)

    def write(self, rel, text, mode=None):
        os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
        with open(self.path(rel), 'w') as f:
            f.write(text)
        if mode:
            os.chmod(self.path(rel), mode)

    def read(self, rel):
        with open(self.path(rel)) as f:
            return f.read()

    def odd(self, *a, stdin=None, tool=ODD):
        e = dict(os.environ)
        e.pop('ODD_BASE', None)
        r = subprocess.run([sys.executable, tool] + list(a), cwd=self.dir, capture_output=True, text=True, input=stdin, env=e)
        return r.returncode, r.stdout + r.stderr

    def ok(self, *a, **k):
        rc, out = self.odd(*a, **k)
        self.assertEqual(rc, 0, out)
        return out

    def no(self, *a, code=1, **k):
        rc, out = self.odd(*a, **k)
        self.assertEqual(rc, code, out)
        return out

    def outcome(self, slug='add', proof=PROOF, in_='calc.py', sentence=SENTENCE):
        self.ok('new', slug, sentence, '--proof', proof, '--in', in_)

    def solve(self):
        self.write('tests/test_calc.py', TEST)
        self.write('calc.py', FIXED)

    def add_line(self, slug, line):
        md = self.read('.odd/outcomes/%s.md' % slug).split('\n')
        self.write('.odd/outcomes/%s.md' % slug, '\n'.join(md[:4] + [line] + md[4:]))


class HappyPath(Repo):
    def test_outcome_change_done_gate(self):
        self.outcome()
        self.assertEqual(self.read('.odd/outcomes/add.md').split('\n')[:5],
                         ['---', 'outcome: ' + SENTENCE, 'proof: ' + PROOF, 'in: calc.py', '---'])
        self.solve()
        out = self.ok('done', 'add')
        self.assertIn('add: verified. took out 1 file(s), 2 line(s); without them the proof said: FAILED', out)
        self.assertIn('PASS', out)
        self.assertEqual(self.read('calc.py'), FIXED, 'the change is put back')
        self.assertNotIn('done', self.read('.odd/outcomes/add.md'), '"done" is never written to a committed file')
        self.assertIn('PASS', self.ok('gate'))
        self.assertIn('PASS', self.ok('gate', '--recompute'))
        self.assertFalse(os.path.exists(self.path('.odd/evidence')), 'evidence is local, under the git directory')

    def test_a_commit_or_an_unrelated_edit_stales_nothing(self):
        self.outcome()
        self.solve()
        self.ok('done', 'add')
        self.commit('work')
        self.write('README.md', 'calc\nmore words\n')
        self.assertIn('PASS', self.ok('gate'))

    def test_an_edit_inside_the_boundary_after_done_needs_done_again(self):
        self.outcome()
        self.solve()
        self.ok('done', 'add')
        self.write('calc.py', FIXED + '# later edit\n')
        out = self.no('gate')
        self.assertIn('add: run: python3', out)
        self.assertNotIn('outside every outcome', out, 'one problem, one remedy')

    def test_messages_name_the_tool_as_it_was_invoked(self):
        self.ok('init')
        self.outcome()
        rc, out = self.odd('gate', tool='.odd/odd.py')
        self.assertIn('run: python3 .odd/odd.py done add', out)


class InPlaceCheck(Repo):
    """Taking the change out and putting it back, for every kind of change."""

    def test_added_untracked_deleted_renamed_and_mode_changes_are_all_taken_out_and_put_back(self):
        self.git('checkout', '-q', 'main')
        self.write('old.py', 'x = 1\n')
        self.write('moved_from.py', 'm = 1\n')
        self.write('run.sh', '#!/bin/sh\nexit 1\n', 0o644)
        self.commit('more')
        self.git('checkout', '-q', '-B', 'feat')
        proof = ("test -f untracked.py && test -f tracked.py && test ! -f old.py && test -f moved_to.py "
                 "&& test ! -f moved_from.py && test -x run.sh")
        self.outcome('swap', proof, 'untracked.py, tracked.py, old.py, moved_from.py, moved_to.py, run.sh',
                     'A maintainer finds the new layout in place and run.sh executable.')
        self.write('untracked.py', 'u = 1\n')
        self.write('tracked.py', 't = 1\n')
        self.git('add', 'tracked.py')
        self.git('rm', '-q', 'old.py')
        self.git('mv', 'moved_from.py', 'moved_to.py')
        os.chmod(self.path('run.sh'), 0o755)
        before = self.git('status', '--porcelain')
        self.assertIn('took out 6 file(s)', self.ok('done', 'swap'))
        self.assertEqual(self.git('status', '--porcelain'), before, 'working tree and index are exactly as they were')
        self.assertEqual(self.read('untracked.py'), 'u = 1\n')
        self.assertTrue(os.access(self.path('run.sh'), os.X_OK))
        self.assertIn('PASS', self.ok('gate', '--recompute'))

    def test_symlinks_and_binary_files(self):
        self.git('checkout', '-q', 'main')
        self.write('a.txt', 'a\n')
        self.write('b.txt', 'b\n')
        os.symlink('a.txt', self.path('current'))
        with open(self.path('blob.bin'), 'wb') as f:
            f.write(b'\0\1\2old')
        self.commit('links')
        self.git('checkout', '-q', '-B', 'feat')
        self.outcome('link', 'test "$(readlink current)" = b.txt && grep -q new blob.bin', 'current, blob.bin',
                     'A reader of current is sent to b.txt and blob.bin holds the new payload.')
        os.remove(self.path('current'))
        os.symlink('b.txt', self.path('current'))
        with open(self.path('blob.bin'), 'wb') as f:
            f.write(b'\0\1\2new')
        self.ok('done', 'link')
        self.assertEqual(os.readlink(self.path('current')), 'b.txt', 'a link is put back as a link')
        with open(self.path('blob.bin'), 'rb') as f:
            self.assertEqual(f.read(), b'\0\1\2new')

    def test_non_ascii_paths(self):
        self.outcome('cafe', "grep -q 'a + b' 'src/café.py'", 'src/**', 'A caller of the café module gets the sum.')
        self.write('src/café.py', FIXED)
        self.ok('done', 'cafe')
        self.assertIn('PASS', self.ok('gate'))

    def test_stale_bytecode_does_not_hide_a_same_size_change(self):
        self.write('calc.py', 'def add(a, b):\n    return a - b\n')
        self.commit('a same-size bug')
        self.git('branch', '-f', 'main')
        self.outcome()
        self.solve()  # '+' for '-': same file size, and the three proof runs happen within the same second
        self.ok('done', 'add')

    def _interrupt(self, sig):
        marker = 'sleep 31.7'
        self.outcome('add', "grep -q 'a + b' calc.py && exit 0; %s" % marker)
        self.write('calc.py', FIXED)
        p = subprocess.Popen([sys.executable, ODD, 'done', 'add'], cwd=self.dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 15
        while time.time() < deadline and self.read('calc.py') != BROKEN:
            time.sleep(0.05)
        self.assertEqual(self.read('calc.py'), BROKEN, 'the check takes the change out in place')
        p.send_signal(sig)
        p.wait(10)
        subprocess.run(['pkill', '-f', marker], capture_output=True)

    def test_sigterm_puts_the_change_back_before_exiting(self):
        self._interrupt(signal.SIGTERM)
        self.assertEqual(self.read('calc.py'), FIXED)

    def test_kill_9_then_git_commit_a_loses_nothing(self):
        self._interrupt(signal.SIGKILL)
        self.assertEqual(self.read('calc.py'), BROKEN, 'SIGKILL leaves the tree without the change...')
        self.git('add', '-A')
        self.git('commit', '-qm', 'a commit made while the change was out', '--allow-empty')
        self.assertNotIn('journal', self.git('show', '--stat', '--name-only', 'HEAD'), 'the journal cannot be committed')
        self.assertIn('1 file(s) were put back', self.no('gate', code=2))  # ...the next command puts it back, and stops
        self.assertEqual(self.read('calc.py'), FIXED)

    def test_an_edit_made_after_a_killed_check_is_kept_and_the_earlier_version_saved(self):
        self._interrupt(signal.SIGKILL)
        redo = 'def add(a, b):\n    return b + a\n'
        self.write('calc.py', redo)  # the agent saw its change gone and wrote it again
        out = self.no('gate', code=2)
        self.assertIn('Edited meanwhile and left as they are: calc.py', out)
        self.assertEqual(self.read('calc.py'), redo, 'the newer edit is never overwritten')
        kept = out.split('your earlier version is at ')[1].split(')')[0]
        with open(kept) as f:
            self.assertEqual(f.read(), FIXED)

    def test_two_checks_cannot_interleave(self):
        marker = 'sleep 31.9'
        self.outcome('slow', "grep -q 'a + b' calc.py && exit 0; %s" % marker)
        self.outcome('other', 'grep -q hello other.py', 'other.py', 'A reader of other.py finds the greeting.')
        self.write('calc.py', FIXED)
        self.write('other.py', 'hello\n')
        p = subprocess.Popen([sys.executable, ODD, 'done', 'slow'], cwd=self.dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 15
        while time.time() < deadline and self.read('calc.py') != BROKEN:
            time.sleep(0.05)
        try:
            self.assertIn('another check is taking a change out', self.no('done', 'other', code=2))
            self.assertEqual(self.read('other.py'), 'hello\n')
        finally:
            p.send_signal(signal.SIGTERM)
            p.wait(10)
            subprocess.run(['pkill', '-f', marker], capture_output=True)


class Attacks(Repo):
    """Ways to claim done without the outcome holding. Every one must end non-zero."""

    def test_a_proof_that_cannot_fail(self):
        self.outcome('add', 'true')
        self.write('calc.py', FIXED)
        out = self.no('done', 'add')
        self.assertIn('still passes with the change taken out', out)
        self.assertIn('taken out: calc.py', out)

    def test_a_weakened_test(self):
        self.outcome()
        self.write('calc.py', FIXED)
        self.write('tests/test_calc.py', TEST.replace('self.assertEqual(add(2, 3), 5)', 'self.assertTrue(True)'))
        self.assertIn('does not depend on the change', self.no('done', 'add'))

    def test_a_failing_proof(self):
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.assertIn('the proof fails', self.no('done', 'add'))

    def test_a_proof_that_fails_whenever_it_runs_twice_is_not_counted_as_depending_on_the_change(self):
        self.outcome('add', "test ! -e .ran && touch .ran && grep -q 'a + b' calc.py")
        self.write('calc.py', FIXED)
        self.assertIn('did not pass again with the change put back', self.no('done', 'add'))

    def test_a_proof_that_is_itself_part_of_the_change(self):
        self.git('checkout', '-q', 'main')
        self.write('check.sh', '#!/bin/sh\nexit 1\n', 0o755)
        self.commit('a check script')
        self.git('checkout', '-q', '-B', 'feat')
        self.outcome('add', './check.sh', 'calc.py, check.sh')
        self.write('check.sh', '#!/bin/sh\nexit 0\n', 0o755)
        self.write('calc.py', FIXED)
        self.assertIn('the proof runs check.sh', self.no('done', 'add', code=2))

    def test_a_proof_that_cannot_run_without_the_change_is_not_counted_as_failing(self):
        self.outcome('add', 'sh -c "./tool.sh"', 'tool.sh', 'A maintainer running tool.sh sees it exit 0.')
        self.write('tool.sh', '#!/bin/sh\nexit 0\n', 0o755)
        self.assertIn('could not run (exit 127)', self.no('done', 'add', code=2))
        self.assertTrue(os.path.exists(self.path('tool.sh')), 'the change is put back')

    def test_files_written_outside_the_boundary_are_seen_even_from_a_shell(self):
        self.outcome()
        self.solve()
        subprocess.run('seq 1 40 > smuggled.py', shell=True, cwd=self.dir, check=True)
        self.ok('done', 'add')
        out = self.no('gate')
        self.assertIn('40 changed line(s) in 1 file(s) are outside every outcome', out)
        self.assertIn('outcome: <one sentence', out, 'the failure prints the three lines to add by hand')
        md = self.read('.odd/outcomes/add.md')
        self.write('.odd/outcomes/add.md', md.replace('in: calc.py', 'in: calc.py, smuggled.py'))
        self.ok('done', 'add')
        self.assertIn('PASS', self.ok('gate'))

    def test_a_done_line_written_by_hand_is_refused(self):
        self.outcome()
        self.add_line('add', 'status: done')
        self.assertIn('unknown field "status"', self.no('gate'))

    def test_forged_local_evidence_passes_locally_and_fails_when_recomputed(self):
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.write('calc.py', BROKEN + '# 1\n' * 30)  # the outcome does NOT hold
        cfg = oddmod.load_config(self.dir)
        o = oddmod.Outcome.load(self.dir, 'add')
        changed = oddmod.changed_files(self.dir, oddmod.find_base(self.dir, cfg)[0])
        oddmod.record(self.dir, 'add', ok=True, hash=oddmod.content_hash(self.dir, cfg, o, changed)[0], tests=['tests/test_calc.py'], files=1, lines=30,
                      seconds=[0, 0, 0], red_says='forged', skip='')
        self.assertIn('PASS', self.ok('gate'))                             # local evidence is fast feedback, not proof
        self.assertIn('the proof fails', self.no('gate', '--recompute'))   # recomputation trusts nothing recorded

    def _adopt_on_main(self):
        self.git('checkout', '-q', 'main')
        self.ok('init')
        self.commit('adopt odd')
        self.git('checkout', '-q', '-B', 'feat')

    def test_a_change_cannot_loosen_its_own_settings(self):
        self._adopt_on_main()
        self.write('.odd/config.json', json.dumps({'trivial_lines': 10 ** 6, 'exempt': ['**']}))
        self.write('big.py', 'x = 1\n' * 60)
        self.assertIn('PASS', self.ok('gate'))
        out = self.no('gate', '--recompute', '--base', 'main')
        self.assertIn('CONTROL FILES CHANGED', out)
        self.assertIn('60 changed line(s) in 1 file(s) are outside every outcome', out)

    def test_a_change_cannot_replace_the_tool_that_judges_it(self):
        self._adopt_on_main()
        self.write('.odd/odd.py', 'import sys\nsys.exit(0)\n')
        self.write('big.py', 'x = 1\n' * 60)
        self.assertEqual(self.odd('gate', '--recompute', tool='.odd/odd.py')[0], 0, 'the fake passes itself')
        base_tool = os.path.join(tempfile.mkdtemp(), 'odd.py')  # the documented CI step: the tool from the base
        with open(base_tool, 'w') as f:
            f.write(self.git('show', 'main:.odd/odd.py'))
        out = self.no('gate', '--recompute', '--base', 'main', tool=base_tool)
        self.assertIn('CONTROL FILES CHANGED', out)

    def test_two_outcomes_cannot_share_a_file(self):
        self.outcome()
        self.outcome('ride', PROOF, 'calc.py', 'A caller of add gets rounding to two places.')
        self.solve()
        self.ok('done', 'add')
        self.ok('done', 'ride')  # each verifies alone on the other's change...
        out = self.no('gate')    # ...so the gate refuses the pair
        self.assertIn('calc.py is inside the boundary of add and ride', out)

    def test_a_skip_is_an_exemption_named_in_the_result(self):
        self.outcome('tidy', 'true', 'calc.py', 'A reader of calc.py finds clearer argument names and the same behaviour.')
        self.add_line('tidy', 'counterfactual: skip - pure rename, nothing can fail first')
        self.write('calc.py', BROKEN.replace('a, b', 'x, y'))
        self.assertIn('SKIPPED the take-out check (pure rename, nothing can fail first)', self.ok('done', 'tidy'))
        self.assertIn('PASS (1 skipped the take-out check: tidy - pure rename, nothing can fail first, 2 line(s))', self.ok('gate'))
        md = self.read('.odd/outcomes/tidy.md')
        self.write('.odd/outcomes/tidy.md', md.replace('proof: true', 'proof: false'))
        self.assertIn('the proof fails', self.no('done', 'tidy'))  # a skip still needs a passing proof

    def test_a_parked_outcome_covers_no_files(self):
        self.outcome()
        self.solve()
        self.write('calc.py', FIXED + '# pad\n' * 30)
        self.no('park', 'add', 'x')
        self.ok('park', 'add', 'blocked on a decision about rounding')
        out = self.no('gate')
        self.assertIn('parked  add: blocked on a decision about rounding', out)
        self.assertIn('are outside every outcome', out)
        self.ok('done', 'add')  # verifying it un-parks it
        self.assertNotIn('parked', self.read('.odd/outcomes/add.md'))
        self.assertIn('PASS', self.ok('gate'))


class ProofStrength(Repo):
    """After green, red, green: small breaks ("mutants") in the changed lines, one at a time. A mutant the proof does
    not notice ("survivor") is a changed line the proof does not depend on."""
    TWO = FIXED + '\n\ndef sub(a, b):\n    return a - b\n'   # the proof checks add only

    def test_a_weak_proof_is_reported_with_each_survivor(self):
        self.outcome()
        self.solve()
        self.write('calc.py', self.TWO)
        out = self.ok('done', 'add')
        self.assertIn('strength: the proof caught 1 of 2 mutant(s)', out)
        self.assertIn('survived: calc.py:6 - -> +: return a - b', out)
        self.assertEqual(self.read('calc.py'), self.TWO, 'every mutant is put back')
        self.assertIn('survived: calc.py:6', self.ok('gate'), 'the local gate reports what done measured')

    def test_a_strong_proof_catches_every_mutant(self):
        self.outcome()
        self.solve()
        out = self.ok('done', 'add')
        self.assertIn('strength: the proof caught 1 of 1 mutant(s)', out)
        self.assertNotIn('survived', out)

    def test_enforce_makes_a_survivor_a_fail_and_recompute_reads_it_from_the_target(self):
        self.git('checkout', '-q', 'main')
        self.write('.odd/config.json', json.dumps({'strength': 'enforce'}))
        self.commit('enforce')
        self.git('checkout', '-q', '-B', 'feat')
        self.outcome()
        self.solve()
        self.write('calc.py', self.TWO)
        out = self.no('done', 'add')
        self.assertIn('the proof does not notice 1 of 2', out)
        self.assertIn('calc.py:6 - -> +', out)
        self.commit('weak')
        self.assertIn('the proof does not notice 1 of 2', self.no('gate', '--recompute', '--base', 'main'))
        self.write('calc.py', FIXED)
        self.commit('only what the proof checks')
        self.assertIn('PASS', self.ok('gate', '--recompute', '--base', 'main'))

    def test_off_runs_no_mutant_and_a_wrong_value_stops(self):
        self.write('.odd/config.json', json.dumps({'strength': 'off'}))
        self.outcome()
        self.solve()
        self.assertNotIn('strength', self.ok('done', 'add'))
        self.write('.odd/config.json', json.dumps({'strength': 'loud'}))
        self.assertIn('"strength" has the wrong kind of value', self.no('gate', code=2))
        self.write('.odd/config.json', json.dumps({'mutants': -1}))
        self.assertIn('"mutants" has the wrong kind of value', self.no('gate', code=2))

    def test_a_mutant_the_proof_cannot_run_on_is_neither_caught_nor_survived(self):
        self.write('tests/check.py', 'import sys\nsys.path.insert(0, ".")\nimport rc\n'
                                     'sys.exit(0 if rc.code() == 126 else rc.code())\n')
        self.outcome('rc', '%s tests/check.py' % sys.executable, 'rc.py', 'A caller of rc.code() receives 126.')
        self.write('rc.py', 'def code():\n    return 126\n')
        out = self.ok('done', 'rc')
        self.assertIn('strength: the proof caught 0 of 0 mutant(s); 1 could not run', out)
        self.assertIn('could not run: rc.py:2 126 -> 127: return 126 (exit 127)', out)

    def test_the_cap_bounds_the_proof_runs(self):
        self.write('.odd/config.json', json.dumps({'mutants': 1}))
        self.outcome()
        self.solve()
        self.write('calc.py', self.TWO)
        self.assertIn('strength: the proof caught 1 of 1 mutant(s) (1 of 2 sampled)', self.ok('done', 'add'))

    def test_a_kill_while_a_mutant_is_in_puts_it_back(self):
        marker = 'sleep 31.6'
        self.outcome('add', "grep -q 'a - b' calc.py && %s; grep -q 'a + b' calc.py" % marker)
        self.write('calc.py', FIXED)
        p = subprocess.Popen([sys.executable, ODD, 'done', 'add'], cwd=self.dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        deadline = time.time() + 15
        while time.time() < deadline and 'a - b' not in self.read('calc.py'):
            time.sleep(0.05)
        self.assertIn('a - b', self.read('calc.py'), 'the mutant is made in place')
        p.send_signal(signal.SIGKILL)
        p.wait(10)
        subprocess.run(['pkill', '-f', marker], capture_output=True)
        self.assertIn('1 file(s) were put back', self.no('gate', code=2))
        self.assertEqual(self.read('calc.py'), FIXED)

    def test_an_edit_made_while_a_mutant_is_in_is_kept_and_the_earlier_version_saved(self):
        redo = 'def add(a, b):\n    return b + a\n'
        self.outcome('add', "grep -q 'a - b' calc.py && printf 'def add(a, b):\\n    return b + a\\n' > calc.py; "
                            "grep -q 'a + b' calc.py")
        self.write('calc.py', FIXED)
        out = self.no('done', 'add', code=2)
        self.assertIn('your earlier version is at', out)
        self.assertEqual(self.read('calc.py'), redo, 'the newer edit is never overwritten')
        with open(out.split('your earlier version is at ')[1].split(')')[0]) as f:
            self.assertEqual(f.read(), FIXED)

    def test_mutations_skip_strings_and_comments_in_a_fixed_order(self):
        text = ('x = a < b and c  # a > b\n'
                's = "1 + 2"\n'
                'if y >= 10 or not z: return True\n'
                'f = (a) => a->b === c; i++; k = 1e-5 + 1.5 && d\n'
                '"""prose with and or 3\n'
                'more prose or 4"""\n'
                'q = r != s')
        got = [(n, old, new) for n, _, old, new in oddmod.mutations(text, None)]
        self.assertEqual(got, [(1, '<', '<='), (1, 'and', 'or'), (3, '>=', '>'), (3, '10', '11'), (3, 'or', 'and'),
                               (3, 'True', 'False'), (4, '+', '-'), (4, '&&', '||'), (7, '!=', '==')])
        self.assertEqual([n for n, _, _, _ in oddmod.mutations(text, {3})], [3, 3, 3, 3])
        self.assertEqual(oddmod.pick(list(range(20)), 4), [0, 5, 10, 15])
        self.assertEqual(oddmod.pick([1, 2], 8), [1, 2])
        self.assertEqual(oddmod.pick([1, 2], 0), [])


class Exemptions(Repo):
    def test_a_few_lines_need_no_outcome_and_more_do(self):
        self.write('calc.py', BROKEN + '# note\n')
        self.assertIn('small-change lane: 1 line(s)', self.ok('gate'))
        self.write('calc.py', BROKEN + '# note\n' * 30)
        self.assertIn('are outside every outcome', self.no('gate'))

    def test_a_small_fix_with_its_test_still_fits_the_lane(self):
        self.write('calc.py', FIXED)
        self.write('tests/test_calc.py', TEST + '\n# more\n' * 20)
        out = self.ok('gate')
        self.assertIn('small-change lane: 2 line(s)', out)
        self.assertIn('test files: 1 changed', out)

    def test_a_test_that_existed_before_and_was_changed_is_named(self):
        self.git('checkout', '-q', 'main')
        self.write('tests/test_calc.py', TEST)
        self.commit('a test')
        self.git('checkout', '-q', '-B', 'feat')
        self.write('tests/test_calc.py', TEST.replace('self.assertEqual(add(2, 3), 5)', 'pass'))
        self.assertIn('existed before and were modified or deleted: tests/test_calc.py', self.ok('gate'))

    def test_markdown_and_lockfiles_are_exempt_and_counted(self):
        self.write('README.md', 'words\n' * 200)
        self.write('package-lock.json', '{}\n' * 600)
        self.assertIn('exempt paths: 2 file(s), 801 line(s)', self.ok('gate'))

    def test_a_binary_file_outside_an_outcome_is_never_small(self):
        with open(self.path('model.bin'), 'wb') as f:
            f.write(b'\0\1\2')
        self.assertIn('a binary file, directory or submodule pointer', self.no('gate'))


class GitShapes(Repo):
    def _verified_branch(self):
        self.outcome()
        self.solve()
        self.ok('done', 'add')
        self.commit('work')

    def test_a_rebased_branch(self):
        self._verified_branch()
        self.git('checkout', '-q', 'main')
        self.write('upstream.py', 'u = 1\n' * 50)
        self.commit('upstream work')
        self.git('checkout', '-q', 'feat')
        self.git('rebase', '-q', 'main')
        out = self.ok('gate')
        self.assertNotIn('upstream.py', out, "the target branch's own work is not part of this change")
        self.assertIn('PASS', self.ok('gate', '--recompute'))

    def test_a_merge_from_the_target_branch(self):
        self._verified_branch()
        self.git('checkout', '-q', 'main')
        self.write('upstream.py', 'u = 1\n' * 50)
        self.commit('upstream work')
        self.git('checkout', '-q', 'feat')
        self.git('merge', '-q', '--no-edit', 'main')
        self.assertIn('PASS', self.ok('gate', '--recompute'))

    def test_squash_merged_history_takes_old_outcomes_out_of_play(self):
        self._verified_branch()
        self.git('checkout', '-q', 'main')
        self.git('merge', '-q', '--squash', 'feat')
        self.git('commit', '-qm', 'squashed')
        self.git('checkout', '-q', '-b', 'next')
        self.assertIn('0 outcome(s) in this change', self.ok('gate'))
        self.write('.odd/outcomes/add.md', self.read('.odd/outcomes/add.md') + 'a later note\n')
        self.assertIn('add: run: python3', self.no('gate'), 'editing a merged outcome file puts it back in play')

    def test_a_shallow_clone_is_could_not_run_with_the_fetch_command(self):
        self._verified_branch()
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        subprocess.run(['git', 'clone', '-q', '--depth', '1', '--no-single-branch', 'file://' + self.dir, d], check=True, capture_output=True)
        subprocess.run(['git', 'checkout', '-q', 'feat'], cwd=d, check=True, capture_output=True)
        r = subprocess.run([sys.executable, ODD, 'gate', '--recompute', '--base', 'origin/main'], cwd=d, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn('git fetch', r.stderr)

    def test_an_unknown_base_is_could_not_run(self):
        self.assertIn('not found', self.no('gate', '--base', 'origin/nope', code=2))

    def test_a_timeout_and_a_directory_outside_git_are_could_not_run(self):
        self.write('.odd/config.json', json.dumps({'proof_timeout': 1}))
        self.outcome('add', 'sleep 5')
        self.write('calc.py', FIXED)
        self.assertIn('could not run', self.no('done', 'add', code=2))
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        self.assertEqual(subprocess.run([sys.executable, ODD, 'gate'], cwd=d, capture_output=True).returncode, 2)


class Files(Repo):
    def test_outcome_files_are_parsed_strictly(self):
        self.outcome()
        md = self.read('.odd/outcomes/add.md')
        self.write('.odd/outcomes/add.md', md.replace('outcome: ' + SENTENCE, 'outcome: A caller of add(2, 3)\n  receives 5.'))
        self.assertEqual(oddmod.Outcome.load(self.dir, 'add').get('outcome'), SENTENCE)  # an indented line continues the value
        self.write('.odd/outcomes/add.md', md.replace('proof:', 'this is not a field\nproof:'))
        self.assertIn('expected "key: value"', self.no('gate'))     # anything else is refused, never dropped silently
        self.write('.odd/outcomes/add.md', '\n'.join(l for l in md.split('\n') if not l.startswith('proof:')))
        self.assertIn('missing "proof:"', self.no('gate'))

    def test_globs(self):
        m = oddmod.matches
        self.assertTrue(m('a.py', ['a.py']))
        self.assertFalse(m('data.py', ['a.py']))
        self.assertTrue(m('src/pay/x/y.py', ['src/pay'], True) and m('src/pay/x/y.py', ['src/**']))
        self.assertFalse(m('src2/y.py', ['src'], True) or m('src/pay/x/y.py', ['src/pay']))
        self.assertTrue(m('README.md', ['**/*.md']) and m('docs/a/b.md', ['**/*.md']))
        self.assertFalse(m('src/a/b.py', ['src/*.py']))
        self.assertTrue(m('src/b.py', ['./src/*.py']))
        tg = oddmod.DEFAULTS['test_globs']
        self.assertTrue(m('tests/x.py', tg) and m('pkg/api/tests/x.py', tg) and m('src/foo.test.ts', tg) and m('a/b_test.go', tg))
        self.assertFalse(m('src/contest/x.py', tg) or m('latest.py', tg))

    def test_stats_are_labelled_self_reported(self):
        self.outcome()
        self.write('tests/test_calc.py', TEST)
        self.no('done', 'add')
        self.write('calc.py', FIXED)
        self.ok('done', 'add')
        out = self.ok('stats')
        self.assertIn('self-reported', out)
        self.assertRegex(out, r'add\s+2\s+1')


class Setup(Repo):
    def test_adopting_the_tool_passes_its_own_gate(self):
        self.ok('init', '--claude-hooks')
        self.commit('adopt odd')
        out = self.ok('gate', '--recompute')
        self.assertIn('CONTROL FILES CHANGED', out)
        self.assertNotIn('settings.local.json', self.git('ls-files'), 'the hooks file is per developer, never committed')

    def test_init_is_idempotent_and_keeps_what_is_there(self):
        self.write('AGENTS.md', '# House rules\n\nBe kind.\n')
        self.write('CLAUDE.md', '# Project\n')
        self.write('.claude/settings.local.json', json.dumps({'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'mine.sh'}]}]}}))
        self.ok('init', '--claude-hooks')
        out = self.ok('init', '--claude-hooks')
        agents = self.read('AGENTS.md')
        self.assertTrue(agents.startswith(oddmod.BEGIN), 'the method goes at the top on first insertion')
        self.assertEqual(agents.count(oddmod.METHOD.replace('{trivial}', '25').rstrip('\n')), 1)
        self.assertIn('Be kind.', agents)
        self.assertEqual(self.read('CLAUDE.md').count('@AGENTS.md'), 1)
        hooks = json.loads(self.read('.claude/settings.local.json'))['hooks']
        self.assertEqual([len(hooks['Stop']), len(hooks['SessionStart'])], [2, 1])
        self.assertEqual(self.read('.odd/odd.py'), open(ODD).read())
        self.assertIn('required check', out, 'init prints the conditions under which CI is the authority')
        self.assertFalse(os.path.exists(self.path('.github')), 'no workflow file is written')

    def test_no_claude_file_is_created_and_a_symlinked_one_is_left_alone(self):
        self.ok('init')
        self.assertFalse(os.path.exists(self.path('CLAUDE.md')))
        os.symlink('AGENTS.md', self.path('CLAUDE.md'))
        self.ok('init')
        self.assertNotIn('@AGENTS.md', self.read('AGENTS.md'))

    def test_the_vendored_copy_runs_on_its_own(self):
        self.ok('init')
        self.assertEqual(self.odd('gate', tool='.odd/odd.py')[0], 0)


class ClaudeHooks(Repo):
    def hook(self, event, payload=None):
        rc, out = self.odd('hook', event, stdin=json.dumps(dict({'session_id': 's1', 'cwd': self.dir}, **(payload or {}))))
        self.assertEqual(rc, 0, out)
        return out

    def test_turn_end_blocks_only_for_unproven_work_changed_this_turn(self):
        self.hook('session-start')
        self.assertEqual(self.hook('stop'), '', 'a question or a discussion is never blocked')
        self.write('calc.py', BROKEN + '# pad\n' * 30)
        self.assertIn('with no outcome', self.hook('stop'))
        self.assertEqual(self.hook('stop'), '', 'the same state is not blocked twice')
        self.write('calc.py', BROKEN + '# pad\n' * 31)
        self.assertEqual(self.hook('stop', {'stop_hook_active': True}), '')
        self.write('calc.py', BROKEN + '# pad\n' * 32)
        self.assertEqual(self.hook('stop', {'loop_count': 1}), '', 'never loops, whichever tool runs the hook')

    def test_an_unverified_outcome_is_a_status_line_and_a_stale_one_blocks(self):
        self.hook('session-start')
        self.outcome()
        self.solve()
        out = json.loads(self.hook('stop'))
        self.assertEqual(list(out), ['systemMessage'], 'work in progress on a stated outcome is not blocked')
        self.ok('done', 'add')
        self.assertEqual(self.hook('stop'), '')
        self.write('calc.py', FIXED + '# later\n')
        self.assertIn('was verified and its files have changed since', self.hook('stop'))

    def test_compaction_does_not_reset_the_turn(self):
        self.hook('session-start')
        self.write('calc.py', BROKEN + '# pad\n' * 30)
        self.hook('session-start', {'source': 'compact'})
        self.assertIn('"block"', self.hook('stop'))

    def test_hook_commands_cannot_fail(self):
        self.ok('init', '--claude-hooks')
        cmds = [h['hooks'][0]['command'] for e in json.loads(self.read('.claude/settings.local.json'))['hooks'].values() for h in e]
        env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        for cmd in cmds:
            for cwd in (self.dir, d):  # inside the project, and somewhere that is not a repository at all
                r = subprocess.run(cmd, shell=True, cwd=cwd, input='not json', capture_output=True, text=True, env=env)
                self.assertEqual(r.returncode, 0, cmd)
        self.write('.odd/outcomes/bad.md', 'not an outcome file\n')
        self.assertEqual(self.hook('stop'), '')
        self.assertIn('hooks failed', self.ok('init'), 'a hook that failed open is reported, not hidden')


class RedTeam(Repo):
    """One fixture per defect the red team confirmed in 0.2.0 (docs/evidence/11-red-team.md)."""

    def pad(self, rel, n=300):
        self.write(rel, ''.join('x%d = %d\n' % (i, i) for i in range(n)))

    def remote(self):
        bare = tempfile.mkdtemp(prefix='odd-remote-')
        self.addCleanup(shutil.rmtree, bare, True)
        subprocess.run(['git', 'init', '-q', '--bare', bare], check=True)
        self.git('remote', 'add', 'origin', bare)
        self.git('push', '-q', 'origin', 'main')
        self.git('fetch', '-q', 'origin')

    # ---- which revision the change is measured from

    def test_a_tag_or_branch_named_like_the_remote_branch_cannot_stand_in_for_it(self):
        self.remote()
        self.pad('big.py')
        self.commit('300 lines, no outcome')
        self.assertIn('outside every outcome', self.no('gate', '--recompute', '--base', 'origin/main'))
        self.git('tag', 'origin/main', 'HEAD')
        self.assertIn('more than one ref', self.no('gate', '--recompute', '--base', 'origin/main', code=2))
        self.assertIn('outside every outcome', self.no('gate', '--recompute'), 'the default looks at the remote branch itself')
        self.assertIn('outside every outcome', self.no('gate', '--recompute', '--base', 'refs/remotes/origin/main'))
        self.git('tag', '-d', 'origin/main')
        self.git('branch', 'origin/main', 'HEAD')
        self.assertIn('more than one ref', self.no('gate', '--recompute', '--base', 'origin/main', code=2))

    def test_recomputing_reads_the_settings_at_the_tip_of_the_target_branch(self):
        self.git('checkout', '-q', 'main')
        self.write('.odd/config.json', json.dumps({'trivial_lines': 5}))
        self.commit('the budget is tightened after the branch was cut')
        self.git('checkout', '-q', 'feat')
        self.pad('small.py', 20)
        self.commit('20 lines')
        self.assertIn('up to 5 need none', self.no('gate', '--recompute', '--base', 'main'))

    def test_recomputing_ignores_a_default_branch_the_change_names_itself(self):
        self.write('.odd/config.json', json.dumps({'default_branch': 'feat'}))
        self.pad('big.py')
        self.commit('points the base at its own branch')
        out = self.no('gate', '--recompute')
        self.assertIn('outside every outcome', out)
        self.assertIn('CONTROL FILES CHANGED', out)

    def test_recomputing_refuses_a_tree_that_is_not_what_was_committed(self):
        self.pad('big.py')
        self.commit('300 lines, no outcome')
        os.remove(self.path('big.py'))  # reverted in the working tree only: a merge would still bring it
        self.assertIn('big.py', self.no('gate', '--recompute', code=2))

    def test_work_committed_on_the_branch_it_is_measured_from(self):
        self.git('checkout', '-q', 'main')
        self.outcome()
        self.solve()
        self.commit('fixed on main')  # what a tool that commits for the agent does
        out = self.no('done', 'add')
        self.assertIn('--base', out)
        self.assertNotIn('counterfactual: skip', out, 'the way out is not an exemption')
        self.assertIn('took out 1 file(s)', self.ok('done', 'add', '--base', 'HEAD~1'))

    def test_a_target_branch_with_another_name(self):
        self.git('branch', '-m', 'main', 'trunk')
        self.assertIn('default_branch', self.ok('init'), 'init says it cannot tell where work leaves from')
        self.outcome()
        self.solve()
        self.assertIn('--base', self.no('done', 'add', code=2))
        out = self.ok('done', 'add', '--base', 'trunk')
        self.assertIn('add: verified', out)
        self.assertIn('PASS', out, 'the closing gate uses the same base')

    # ---- what counts as changed, and how much

    def test_a_file_named_like_a_pattern_is_only_that_file(self):
        self.git('checkout', '-q', 'main')
        self.write('src/v2.py', 'a = 1\n')
        self.write('src/v[2].py', 'old\n')
        self.commit('two files')
        self.git('checkout', '-q', '-B', 'feat')
        self.pad('src/v[2].py', 400)
        self.write('src/v2.py', 'a = 1\nb = 2\n')
        self.assertIn('outside every outcome', self.no('gate'), 'the 400 lines are counted, not the neighbour\'s one')
        self.outcome('v', "grep -q x399 'src/v[2].py'", 'src/v[2].py', 'A reader of the second version finds all four hundred values.')
        self.ok('done', 'v')
        self.assertEqual(self.read('src/v2.py'), 'a = 1\nb = 2\n', 'the neighbour outside the outcome is never rewritten')

    def test_a_module_written_on_one_line_is_not_a_small_change(self):
        self.write('one.py', '; '.join('x%d = %d' % (i, i) for i in range(2000)) + '\n')
        self.assertIn('outside every outcome', self.no('gate'))
        os.remove(self.path('one.py'))
        self.write('calc.py', BROKEN + '; '.join('y%d = %d' % (i, i) for i in range(2000)) + '\n')
        self.assertIn('outside every outcome', self.no('gate'), 'one long line added to an existing file')
        self.write('calc.py', BROKEN)
        for i in range(26):
            self.write('empty%d.py' % i, '')
        self.assertIn('outside every outcome', self.no('gate'), 'an empty file or a mode change costs one line')

    def test_a_link_to_a_directory_is_one_line_and_a_submodule_pointer_is_never_small(self):
        os.symlink('tests', self.path('latest'))
        self.assertIn('small-change lane: 1 line(s)', self.ok('gate'))
        os.remove(self.path('latest'))
        sub = tempfile.mkdtemp(prefix='odd-sub-')
        self.addCleanup(shutil.rmtree, sub, True)
        for args in (['init', '-q', '-b', 'main'], ['-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-q',
                                                    '--allow-empty', '-m', 'one']):
            subprocess.run(['git'] + args, cwd=sub, check=True, capture_output=True)
        self.git('checkout', '-q', 'main')
        self.git('-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', sub, 'vendor/lib')
        self.commit('a submodule')
        self.git('checkout', '-q', '-B', 'feat')
        subprocess.run(['git', '-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-q', '--allow-empty', '-m',
                        'two'], cwd=self.path('vendor/lib'), check=True, capture_output=True)
        self.write('.gitmodules', self.read('.gitmodules') + '\tignore = all\n')
        self.git('add', '.gitmodules', 'vendor/lib')
        out = self.no('gate')
        self.assertIn('vendor/lib', out, 'the pointer moved, whatever .gitmodules says about ignoring it')

    def test_a_directory_named_like_an_exempt_or_test_file_exempts_nothing(self):
        m = oddmod.matches
        self.assertFalse(m('notes.md/payload.py', oddmod.DEFAULTS['exempt']) or m('app.lock/worker.py', oddmod.DEFAULTS['exempt']))
        self.assertFalse(m('LICENSE-tools/run.py', oddmod.DEFAULTS['exempt']) or m('x.test.d/run.py', oddmod.DEFAULTS['test_globs']))
        self.pad('notes.md/payload.py')
        self.assertIn('outside every outcome', self.no('gate'))

    def test_bytecode_and_files_a_proof_writes_are_not_the_change(self):
        self.write('.gitignore', '')  # a project that does not ignore __pycache__
        self.write('pkg/__init__.py', '')
        self.write('pkg/calc.py', BROKEN)
        self.commit('a package')
        self.git('branch', '-f', 'main')
        proof = "test -f tests/seen.txt || echo first > tests/seen.txt; %s -m unittest -q tests.test_pkg" % sys.executable
        self.outcome('pkg', proof, 'pkg/**')
        self.write('tests/test_pkg.py', TEST.replace('from calc', 'from pkg.calc'))
        self.write('pkg/calc.py', FIXED)
        subprocess.run(proof, shell=True, cwd=self.dir, capture_output=True)  # the agent runs its test first
        self.assertTrue(os.path.isdir(self.path('pkg/__pycache__')))
        out = self.ok('done', 'pkg')
        self.assertNotIn('\nFAIL', out, 'done does not contradict itself in one output')
        self.ok('done', 'pkg')
        self.assertIn('PASS', self.ok('gate'))
        self.assertEqual([n for n in os.listdir(self.path('.git/odd')) if n.startswith('displaced')], [])

    # ---- proofs

    def test_a_proof_handed_to_an_interpreter_from_inside_the_change(self):
        self.write('check.py', 'print("ok")\n')
        self.write('calc.py', FIXED)
        self.outcome('a', '%s check.py' % sys.executable, 'calc.py, check.py')
        self.assertIn('part of the change', self.no('done', 'a', code=2))
        self.write('shop/__init__.py', '')
        self.write('shop/tests.py', 'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_nothing(self):\n        self.assertTrue(True)\n')
        self.outcome('b', '%s -m unittest shop.tests -q' % sys.executable, 'shop/**', 'A shopper sees the tests of the shop pass.')
        self.assertIn('shop/tests.py', self.no('done', 'b', code=2))

    def test_a_proof_that_leaves_a_process_behind_does_not_hold_the_check(self):
        self.write('.odd/config.json', json.dumps({'proof_timeout': 3}))
        bg = "%s -c 'import os, time; os.setsid(); time.sleep(8.031)' &" % sys.executable
        self.outcome('add', "%s grep -q 'a + b' calc.py" % bg)
        self.write('calc.py', FIXED)
        t0 = time.time()
        try:
            self.assertIn('add: verified', self.ok('done', 'add'))
            self.assertLess(time.time() - t0, 6, 'the proof ended; what it left running is not waited for')
        finally:
            subprocess.run(['pkill', '-f', 'time.sleep(8.031)'], capture_output=True)

    def test_exit_255_without_the_change_is_a_failure_like_any_other(self):
        self.outcome('add', "grep -q 'a + b' calc.py || exit 255")
        self.write('calc.py', FIXED)
        self.assertIn('add: verified', self.ok('done', 'add'))

    # ---- taking the change out and putting it back

    def test_a_directory_turned_into_a_file_or_a_link_is_refused_before_anything_is_touched(self):
        self.git('checkout', '-q', 'main')
        self.write('plugin/a.py', 'a = 1\n')
        self.write('vendor/lib/v.py', 'V = 1\n')
        self.write('shared/v.py', 'V = 2\n')
        self.commit('directories')
        self.git('checkout', '-q', '-B', 'feat')
        self.git('rm', '-rq', 'plugin', 'vendor/lib')
        self.write('plugin', 'single-file plugin, uncommitted\n')
        os.makedirs(self.path('vendor'), exist_ok=True)
        os.symlink('../shared', self.path('vendor/lib'))
        self.outcome('p', 'test -f plugin', 'plugin, plugin/**', 'A maintainer finds the plugin as a single file.')
        self.outcome('l', 'test -L vendor/lib', 'vendor/**', 'A maintainer finds vendor/lib linked to the shared copy.')
        for slug in ('p', 'l'):
            self.assertIn('counterfactual: skip', self.no('done', slug, code=2))
        self.assertEqual(self.read('plugin'), 'single-file plugin, uncommitted\n')
        self.assertEqual(os.readlink(self.path('vendor/lib')), '../shared')
        self.assertEqual(self.read('shared/v.py'), 'V = 2\n')
        self.ok('stats')

    def test_a_removed_tree_goes_back_to_absent_and_a_file_the_proof_rewrote_is_named(self):
        self.git('checkout', '-q', 'main')
        self.write('legacy/sub/x.py', 'x = 1\n')
        self.write('old.txt', 'old\n')
        self.commit('legacy')
        self.git('checkout', '-q', '-B', 'feat')
        self.git('rm', '-rq', 'legacy', 'old.txt')
        self.outcome('gone', 'test ! -d legacy', 'legacy/**', 'A maintainer no longer finds the legacy package.')
        self.ok('done', 'gone')
        self.assertFalse(os.path.exists(self.path('legacy')), 'the directories the check created are removed again')
        self.outcome('old', 'test ! -f old.txt || { echo reformatted >> old.txt; exit 1; }', 'old.txt',
                     'A maintainer no longer finds the old notes file.')
        out = self.no('done', 'old', code=2)
        self.assertIn('old.txt', out)
        self.assertIn('did not exist before the check', out)

    def test_losing_a_saved_copy_stops_with_the_paths_named_and_puts_the_rest_back(self):
        self.write('other.py', 'o = 1\n')
        self.commit('another file')
        self.git('branch', '-f', 'main')
        self.outcome('two', "grep -q 'a + b' calc.py && exit 0; rm -f .git/odd/cf-*/0; exit 1", 'calc.py, other.py')
        self.write('calc.py', FIXED)
        self.write('other.py', 'o = 2\n')
        out = self.no('done', 'two', code=2)
        self.assertIn('calc.py', out)
        self.assertEqual(self.read('other.py'), 'o = 2\n', 'one path that cannot be put back does not strand the others')
        self.assertEqual(self.odd('stats')[0], 2, 'and it is said again, not crashed on, until someone looks')

    def test_recovery_puts_the_change_back_into_the_tree_it_runs_in(self):
        InPlaceCheck._interrupt(self, signal.SIGKILL)
        moved = self.dir + '-moved'
        os.rename(self.dir, moved)
        self.addCleanup(shutil.rmtree, moved, True)
        old, self.dir = self.dir, moved
        self.assertIn('1 file(s) were put back', self.no('stats', code=2))
        self.assertEqual(self.read('calc.py'), FIXED)
        self.assertFalse(os.path.exists(old), 'nothing is written under the path the tree used to have')

    def test_a_killed_check_is_recovered_even_when_its_pid_still_answers(self):
        InPlaceCheck._interrupt(self, signal.SIGKILL)
        jp = [os.path.join(self.path('.git/odd'), n, 'journal.json') for n in os.listdir(self.path('.git/odd')) if n.startswith('cf-')][0]
        with open(jp) as f:
            j = json.load(f)
        j['pid'] = os.getpid()  # a pid namespace, or a zombie: the number answers although the check is gone
        with open(jp, 'w') as f:
            json.dump(j, f)
        self.assertIn('1 file(s) were put back', self.no('stats', code=2))
        self.assertEqual(self.read('calc.py'), FIXED)

    def test_a_check_killed_before_it_noted_what_it_left_never_overwrites_a_later_edit(self):
        InPlaceCheck._interrupt(self, signal.SIGKILL)
        jp = [os.path.join(self.path('.git/odd'), n, 'journal.json') for n in os.listdir(self.path('.git/odd')) if n.startswith('cf-')][0]
        with open(jp) as f:
            j = json.load(f)
        for e in j['files']:
            e.pop('left', None)  # killed between writing the journal and noting what the take-out left
        with open(jp, 'w') as f:
            json.dump(j, f)
        redo = 'def add(a, b):\n    return b + a\n'
        self.write('calc.py', redo)
        self.assertIn('Edited meanwhile', self.no('stats', code=2))
        self.assertEqual(self.read('calc.py'), redo)

    # ---- settings, outcome files, messages

    def test_settings_of_the_wrong_shape_stop_the_gate(self):
        for text, word in (('{"exempt": "docs/**"}', 'exempt'), ('{"trivial_lines": 0,}', 'JSON'), ('{"trivial_line": 0}', 'trivial_line'),
                           ('[]', 'config.json'), ('{"trivial_lines": true}', 'trivial_lines'), ('{"proof_timeout": "9"}', 'proof_timeout')):
            self.write('.odd/config.json', text)
            self.assertIn(word, self.no('gate', code=2), text)
        self.commit('a string where a list belongs')
        self.git('branch', '-f', 'main')
        self.pad('big.py')
        self.assertIn('proof_timeout', self.no('gate', '--recompute', '--base', 'main', code=2), 'the same for settings read from the base')

    def test_errors_nobody_planned_for_are_could_not_run_and_say_where(self):
        self.outcome()
        with open(self.path('.odd/outcomes/add.md'), 'ab') as f:
            f.write(b'caf\xe9\n')
        self.assertIn('add.md', self.no('gate'), 'an outcome file that is not UTF-8 is named')
        os.remove(self.path('.odd/outcomes/add.md'))
        os.mkdir(self.path('AGENTS.md'))
        self.assertIn('AGENTS.md', self.no('init', code=2))
        os.rmdir(self.path('AGENTS.md'))
        self.write('.claude/settings.local.json', '{"hooks": {},}')
        self.assertIn('settings.local.json', self.no('init', '--claude-hooks', code=2))
        self.assertFalse(os.path.exists(self.path('AGENTS.md')), 'nothing is half applied')

    def test_new_writes_only_what_done_can_read(self):
        self.assertIn('one line', self.no('new', 'a', SENTENCE, '--proof', 'true\nfalse', '--in', 'calc.py'))
        self.ok('new', 'b', SENTENCE, '--proof', 'true', '--in', 'calc.py', '--in', 'other.py')
        self.assertIn('in: calc.py, other.py', self.read('.odd/outcomes/b.md'))
        self.assertIn('comma', self.ok('new', 'c', SENTENCE, '--proof', 'true', '--in', 'calc.py other.py'))

    def test_the_local_gate_goes_by_the_latest_attempt_and_a_new_test_elsewhere_stales_nothing(self):
        self.write('scale.txt', '3\n')
        self.outcome('add', "grep -q 'a + b' calc.py && grep -q 3 scale.txt")
        self.write('calc.py', FIXED)
        self.ok('done', 'add')
        self.write('tests/test_other.py', 'import unittest\n')
        self.assertIn('PASS', self.ok('gate'), 'a test file added for something else leaves this outcome verified')
        self.write('scale.txt', '4\n')
        self.no('done', 'add')
        self.assertIn('add: run:', self.no('gate'), 'the latest attempt on this content failed')

    def test_parking_says_what_the_gate_will_do(self):
        self.outcome()
        self.write('calc.py', FIXED + '# pad\n' * 30)
        out = self.ok('park', 'add', 'the rounding rule contradicts the ticket')
        self.assertIn('more than 25', out)

    # ---- Claude Code hooks and files

    hook = lambda self, event, payload=None: ClaudeHooks.hook(self, event, payload)  # noqa: E731

    def test_hooks_see_untracked_work_and_do_not_block_again_for_a_commit(self):
        self.hook('session-start')
        self.pad('newdir/big.py')
        self.assertIn('with no outcome', self.hook('stop'))
        self.hook('prompt-submit')
        self.pad('newdir/big.py', 301)
        self.assertIn('with no outcome', self.hook('stop'), 'an edit to an untracked file is this turn\'s work')
        self.hook('prompt-submit')
        self.git('add', '-A')
        self.assertEqual(self.hook('stop'), '', 'staging changes no file')
        self.git('commit', '-qm', 'wip')
        self.assertEqual(self.hook('stop'), '', 'nor does a commit')

    def test_a_question_is_not_blocked_for_edits_made_before_it(self):
        self.hook('session-start')
        self.write('calc.py', BROKEN + '# pad\n' * 30)
        self.assertIn('"block"', self.hook('stop'))
        self.write('calc.py', BROKEN + '# pad\n' * 33)  # the forced continuation edits again
        self.assertEqual(self.hook('stop', {'stop_hook_active': True}), '')
        self.hook('prompt-submit')
        self.assertEqual(self.hook('stop'), '', 'the next turn only asked a question')
        self.write('calc.py', BROKEN + '# pad\n' * 40)  # the person types between turns
        self.hook('prompt-submit')
        self.assertEqual(self.hook('stop'), '')

    def test_parking_is_not_blocked_as_work_with_no_outcome(self):
        self.hook('session-start')
        self.outcome()
        self.write('calc.py', BROKEN + '# pad\n' * 40)
        self.ok('park', 'add', 'blocked: the owner must supply the rounding rule')
        self.assertNotIn('"block"', self.hook('stop'))

    def test_init_keeps_the_persons_own_hooks_and_refuses_a_shape_it_does_not_know(self):
        mine = {'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': './notify-me.sh'},
                                              {'type': 'command', 'command': 'python3 .odd/odd.py gate >> gate.log'}]}]}}
        self.write('.claude/settings.local.json', json.dumps(mine))
        self.ok('init', '--claude-hooks')
        self.ok('init', '--claude-hooks')
        hooks = json.loads(self.read('.claude/settings.local.json'))['hooks']
        cmds = [h['command'] for g in hooks['Stop'] for h in g['hooks']]
        self.assertIn('./notify-me.sh', cmds)
        self.assertIn('python3 .odd/odd.py gate >> gate.log', cmds)
        self.assertEqual(len(cmds), 3)
        self.assertEqual(sorted(hooks), ['SessionStart', 'Stop', 'UserPromptSubmit'])
        odd_shape = json.dumps({'hooks': {'Stop': {'hooks': [{'type': 'command', 'command': 'x.sh'}]}}})
        self.write('.claude/settings.local.json', odd_shape)
        self.assertIn('Stop', self.no('init', '--claude-hooks', code=2))
        self.assertEqual(self.read('.claude/settings.local.json'), odd_shape)

    def test_every_claude_file_claude_code_reads_instead_of_agents_md_gets_a_working_import(self):
        self.write('.claude/CLAUDE.md', '# Project\n\n@AGENTS.md\n')  # what 0.2.0 wrote: resolves to .claude/AGENTS.md
        self.ok('init')
        self.ok('init')
        text = self.read('.claude/CLAUDE.md')
        self.assertEqual(text.count('@../AGENTS.md'), 1)
        self.assertNotIn('\n@AGENTS.md', text)
        os.remove(self.path('.claude/CLAUDE.md'))
        self.write('CLAUDE.local.md', 'my notes\n')
        self.assertIn('CLAUDE.local.md', self.ok('init'))
        self.assertIn('@AGENTS.md', self.read('CLAUDE.local.md'))


class Distribution(Repo):
    """The two ways odd reaches people besides the single file: `pip install odd-tool` and the GitHub Action."""

    REPO = os.path.dirname(HERE)

    def test_the_installed_command_is_the_same_tool(self):
        venv = tempfile.mkdtemp(prefix='odd-venv-')
        self.addCleanup(shutil.rmtree, venv, True)
        src = os.path.join(venv, 'src')  # built from a copy, so nothing is left in the repository
        os.makedirs(src)
        for name in ('pyproject.toml', 'odd.py', 'README.md', 'LICENSE'):
            shutil.copy(os.path.join(self.REPO, name), src)
        subprocess.run([sys.executable, '-m', 'venv', venv], check=True)
        r = subprocess.run([os.path.join(venv, 'bin', 'python'), '-m', 'pip', 'install', '-q', '--no-deps',
                            '--disable-pip-version-check', src], capture_output=True, text=True)
        if r.returncode != 0 and re.search(r'(?i)connection|network|resolve|proxy|index', r.stderr):
            self.skipTest('pip could not fetch setuptools to build with: ' + r.stderr.strip()[-200:])
        self.assertEqual(r.returncode, 0, r.stderr)
        odd = os.path.join(venv, 'bin', 'odd')
        run = lambda *a: subprocess.run([odd] + list(a), cwd=self.dir, capture_output=True, text=True)  # noqa: E731
        self.assertEqual(run('--version').stdout.strip(), 'odd ' + oddmod.VERSION)
        self.assertEqual(run('init').returncode, 0)
        self.assertEqual(self.read('.odd/odd.py'), open(ODD).read(), 'the vendored copy is the installed file')
        self.outcome()
        self.solve()
        out = run('done', 'add')
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn('ok      add', out.stdout, 'the closing gate of the installed command')

    def test_the_launch_demo_still_shows_what_it_claims(self):
        r = subprocess.run(['bash', os.path.join(self.REPO, 'launch', 'demo.sh')], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('the proof still passes with the change taken out', r.stdout)
        self.assertIn('split: verified', r.stdout)
        self.assertEqual(r.stdout.count('\nPASS'), 2)

    def action_step(self):
        """The shell the Action runs, read out of action.yml (stdlib only, so no YAML parser)."""
        with open(os.path.join(self.REPO, 'action.yml')) as f:
            text = f.read()
        body = text.split('      run: |\n', 1)[1]
        return '\n'.join(l[8:] for l in body.split('\n') if l.startswith('        ') or not l.strip())

    def ci(self, target='main'):
        """A pull request's checkout as CI sees it: a depth-1 clone of the feature branch, then the Action's step."""
        d = tempfile.mkdtemp(prefix='odd-ci-')
        self.addCleanup(shutil.rmtree, d, True)
        subprocess.run(['git', 'clone', '-q', '--depth', '1', '--branch', 'feat', 'file://' + self.dir, d], check=True,
                       capture_output=True)
        env = dict(os.environ, TARGET=target, GITHUB_ACTION_PATH=self.REPO)
        env.pop('ODD_BASE', None)
        r = subprocess.run(['bash', '-c', self.action_step()], cwd=d, env=env, capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_the_action_passes_proven_work_and_fails_unproven_work(self):
        self.outcome()
        self.solve()
        self.commit('proven')
        rc, out = self.ci()
        self.assertEqual(rc, 0, out)
        self.assertIn('ok      add', out)
        self.write('big.py', ''.join('x%d = %d\n' % (i, i) for i in range(300)))
        self.commit('unproven')
        rc, out = self.ci()
        self.assertEqual(rc, 1, out)
        self.assertIn('outside every outcome', out)

    def test_the_action_judges_with_its_own_copy_never_the_one_the_change_carries(self):
        self.ok('init')
        self.commit('adopt odd')
        self.git('checkout', '-q', 'main')
        self.git('merge', '-q', 'feat')
        self.git('checkout', '-q', 'feat')
        self.write('.odd/odd.py', 'import sys\nprint("PASS")\nsys.exit(0)\n')
        self.write('big.py', ''.join('x%d = %d\n' % (i, i) for i in range(300)))
        self.commit('a change that brings its own judge')
        rc, out = self.ci()
        self.assertEqual(rc, 1, out)
        self.assertIn('CONTROL FILES CHANGED', out)


if __name__ == '__main__':
    unittest.main()
