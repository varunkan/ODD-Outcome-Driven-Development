import glob
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def calc(*args):
    r = subprocess.run([sys.executable, 'calc.py'] + list(args), cwd=ROOT, capture_output=True, text=True, timeout=20)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


class Values(unittest.TestCase):
    CASES = [('1+2', '3'), ('2+3*4', '14'), ('(2+3)*4', '20'), ('10/4', '2.5'), ('2/1', '2'), ('7-10', '-3'),
             ('-(2+3)*-2', '10'), ('2--3', '5'), ('--3', '3'), ('+4', '4'), ('2*-3', '-6'), ('((((1))))', '1'),
             ('  12 *  ( 3 + 4 ) - 6 / 2 ', '81'), ('.5+.5', '1'), ('2.5*2', '5'), ('0.1 + 0.2', '0.3'),
             ('1/3', '0.3333333333'), ('2/3', '0.6666666667'), ('100000*100000', '10000000000'), ('8/2/2', '2'),
             ('2-3-4', '-5'), ('1.5+1.25', '2.75'), ('3*(2+(4-1))/5', '3'), ('0*5', '0'), ('-0.5*4', '-2')]

    def test_values(self):
        for expr, want in self.CASES:
            with self.subTest(expr=expr):
                self.assertEqual(calc(expr), (0, want, ''))


class Errors(unittest.TestCase):
    def test_division_by_zero(self):
        for expr in ('1/0', '5/(2-2)', '1/0.0'):
            with self.subTest(expr=expr):
                self.assertEqual(calc(expr), (1, '', 'error: division by zero'))

    def test_invalid_expressions(self):
        for expr in ('', '   ', '(1+2', '1+2)', '()', '2 * * 3', '2+', '1 2', '2 $ 3', 'abc', '1e3', '2 / / 2', '*3',
                     '(2+)3', '1..2'):
            with self.subTest(expr=expr):
                self.assertEqual(calc(expr), (2, '', 'error: invalid expression'))

    def test_usage(self):
        for args in ((), ('1', '2')):
            with self.subTest(args=args):
                self.assertEqual(calc(*args), (2, '', 'usage: calc.py "<expression>"'))


class Rules(unittest.TestCase):
    def test_no_eval_or_exec(self):
        for path in glob.glob(os.path.join(ROOT, '**', '*.py'), recursive=True):
            rel = os.path.relpath(path, ROOT)
            if rel.split(os.sep)[0] in ('tests', 'tests_hidden', '.odd', '.specify', '.claude', 'specs'):
                continue
            with open(path, encoding='utf-8') as f:
                src = f.read()
            self.assertNotRegex(src, r'\b(eval|exec)\s*\(', rel)

    def test_own_unit_tests_exist_and_pass(self):
        self.assertTrue(glob.glob(os.path.join(ROOT, 'tests', '**', 'test*.py'), recursive=True), 'no tests under tests/')
        r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=ROOT,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-600:])


if __name__ == '__main__':
    unittest.main()
