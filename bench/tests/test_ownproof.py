"""bench/ownproof.py: do the tests an agent wrote fail without its change? Proven on small git repositories."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

BENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BENCH)
import ownproof  # noqa: E402

BROKEN, FIXED = 'def add(a, b):\n    return 0\n', 'def add(a, b):\n    return a + b\n'
REAL = 'from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n'
EMPTY = 'import calc\n\n\ndef test_add_exists():\n    assert callable(calc.add)\n'


@unittest.skipUnless(importlib.util.find_spec('pytest') and shutil.which('git'), 'pytest and git are needed')
class OwnProofTest(unittest.TestCase):
    def setUp(self):
        self.tree = tempfile.mkdtemp(prefix='ownproof-test-')
        self.addCleanup(shutil.rmtree, self.tree, True)
        self.git('init', '-q', '-b', 'main')
        self.write('calc.py', BROKEN)
        self.git('add', '-A')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-q', '-m', 'base')

    def git(self, *args):
        subprocess.run(['git'] + list(args), cwd=self.tree, check=True, capture_output=True)

    def write(self, rel, text):
        path = os.path.join(self.tree, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(text)

    def verdict(self):
        return ownproof.own_proof(self.tree, os.path.join(self.tree, 'no-task-env'))

    def test_a_test_that_needs_the_change_fails_without_it(self):
        self.write('calc.py', FIXED)
        self.write('tests/test_calc.py', REAL)
        res = self.verdict()
        self.assertEqual(res['verdict'], 'fails without the change', res)
        self.assertEqual((res['tests'], res['product']), (['tests/test_calc.py'], ['calc.py']))
        with open(os.path.join(self.tree, 'calc.py')) as f:
            self.assertEqual(f.read(), FIXED, 'the kept tree itself is not touched')

    def test_a_test_that_would_pass_anyway_is_told_apart(self):
        self.write('calc.py', FIXED)
        self.write('tests/test_calc.py', EMPTY)
        self.assertEqual(self.verdict()['verdict'], 'passes without the change')

    def test_a_new_product_file_is_taken_out_too(self):
        self.write('more.py', 'def twice(x):\n    return 2 * x\n')
        self.write('tests/test_more.py', 'from more import twice\n\n\ndef test_twice():\n    assert twice(2) == 4\n')
        self.assertEqual(self.verdict()['verdict'], 'fails without the change')

    def test_no_test_and_a_test_that_does_not_pass_as_left_are_named(self):
        self.write('calc.py', FIXED)
        self.assertEqual(self.verdict()['verdict'], 'no test of its own')
        self.write('tests/test_calc.py', REAL.replace('== 5', '== 6'))
        self.assertEqual(self.verdict()['verdict'], 'not passing as left')

    def test_a_file_under_testing_counts_as_a_test_whatever_its_name(self):
        self.write('calc.py', FIXED)
        self.write('testing/python/integration.py', REAL)
        res = self.verdict()
        self.assertEqual((res['tests'], res['verdict']), (['testing/python/integration.py'], 'fails without the change'), res)

    def test_an_arms_own_files_are_neither_test_nor_product(self):
        self.write('calc.py', FIXED)
        self.write('tests/test_calc.py', REAL)
        self.write('.odd/outcomes/add.md', 'outcome: x\n')
        self.write('AGENTS.md', 'method\n')
        self.assertEqual(self.verdict()['product'], ['calc.py'])


if __name__ == '__main__':
    unittest.main()
