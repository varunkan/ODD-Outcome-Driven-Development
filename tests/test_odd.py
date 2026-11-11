"""Tests for odd.py. Each test builds a throwaway git repository and drives the tool the way an agent or CI would.

Run: python3 -m unittest discover -s tests        (from the repository root)

The "Attacks" tests are the reason the tool exists: each is a way an agent could report done without the outcome
holding, and each must end in a non-zero exit. "GitShapes" and "InPlaceCheck" hold one fixture per hole the design
review named (docs/evidence/10-design-review.md).
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
        changed = oddmod.changed_files(self.dir, oddmod.find_base(self.dir, cfg))
        oddmod.record(self.dir, 'add', ok=True, hash=oddmod.content_hash(self.dir, cfg, o, changed), files=1, lines=30,
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
        self.assertIn('a binary file or submodule pointer', self.no('gate'))


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
        self.assertTrue(m('src/pay/x/y.py', ['src/pay']) and m('src/pay/x/y.py', ['src/**']))
        self.assertFalse(m('src2/y.py', ['src']))
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


if __name__ == '__main__':
    unittest.main()
