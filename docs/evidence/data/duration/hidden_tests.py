import glob
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dur(*args):
    r = subprocess.run([sys.executable, 'dur.py'] + list(args), cwd=ROOT, capture_output=True, text=True, timeout=20)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


class Values(unittest.TestCase):
    CASES = [('90s', '1m30s'), ('1w', '7d'), ('25h', '1d1h'), ('1h0m5s', '1h5s'), ('0s', '0s'), ('1h30m', '1h30m'),
             ('2d 4h', '2d4h'), (' 90s ', '1m30s'), ('3600s', '1h'), ('86400s', '1d'), ('1w1d', '8d'), ('59s', '59s'),
             ('60m', '1h'), ('1d24h', '2d'), ('007m', '7m'), ('0h0m', '0s'), ('1w 2d 3h 4m 5s', '9d3h4m5s'),
             ('365d', '365d'), ('52w1d', '365d'), ('100m100s', '1h41m40s')]

    def test_values(self):
        for text, want in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(dur(text), (0, want, ''))


class Errors(unittest.TestCase):
    def test_too_long(self):
        for text in ('366d', '365d1s', '53w', '9999h'):
            with self.subTest(text=text):
                self.assertEqual(dur(text), (1, '', 'error: too long'))

    def test_invalid(self):
        for text in ('', '   ', '90', 's', '1 h', '1x', '1H', '30m1h', '1h2h', '-1h', '1.5h', '1h,30m', 'abc', '1h 30',
                     'h1'):
            with self.subTest(text=text):
                self.assertEqual(dur(text), (2, '', 'error: invalid duration'))

    def test_usage(self):
        for args in ((), ('1h', '2m')):
            with self.subTest(args=args):
                self.assertEqual(dur(*args), (2, '', 'usage: dur.py "<duration>"'))


class Project(unittest.TestCase):
    def test_its_own_tests_pass(self):
        self.assertTrue(glob.glob(os.path.join(ROOT, 'tests', '**', '*.py'), recursive=True), 'no tests under tests/')
        r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=ROOT,
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])


if __name__ == '__main__':
    unittest.main()
