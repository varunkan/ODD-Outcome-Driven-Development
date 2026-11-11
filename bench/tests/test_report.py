"""report.py on records written by hand, so every figure is known."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_bench import REPORT, read, write


class ReportTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='bench-test-')
        self.addCleanup(shutil.rmtree, self.dir, True)

    def put(self, arm, repeat, task, passed, cost=1.0, seconds=10, **fields):
        rec = dict({'task': task, 'arm': arm, 'repeat': repeat, 'kind': 'bugfix', 'model': 'm', 'passed': passed,
                    'claim': 'DONE' if passed else 'NOT DONE', 'cost_usd': cost, 'duration_ms': seconds * 1000,
                    'num_turns': 5}, **fields)
        write(os.path.join(self.dir, '%s.%s.%d.json' % (task, arm, repeat)), json.dumps(rec))

    def report(self, *args):
        out = subprocess.run([sys.executable, REPORT, self.dir] + list(args), capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        s = read(os.path.join(self.dir, 'summary.json'))
        return out.stdout, s, {(d['arm'], d['measure']): d for d in s['comparisons']}

    def flips(self, repeats, failing):
        """plain fails failing[n-1] in repeat n and passes the rest; other passes all ten tasks every time."""
        for n in range(1, repeats + 1):
            for t in range(1, 11):
                task = 't%02d' % t
                self.put('plain', n, task, task != failing[n - 1])
                self.put('other', n, task, True)

    def test_tasks_flipping_between_repeats_are_not_a_difference(self):
        # the review's probe: plain's pass rate is 90% in each repeat, so the old spread was 0 and 10 points "differed"
        self.flips(2, ['t03', 't07'])
        text, _, rows = self.report()
        d = rows[('other', 'passed')]
        self.assertEqual((d['arm_total'], d['arm_runs'], d['baseline_total'], d['baseline_runs']), (20, 20, 18, 20))
        self.assertEqual((d['tasks'], d['repeats'], d['reading'], d['interval']), (10, 2, 'not enough repeats', None))
        self.assertAlmostEqual(d['difference'], 0.1)
        self.assertIn('| other | pass rate | 20/20 | 18/20 | +10 points | - | 10 | 2 | not enough repeats |', text)
        self.assertIn('| t03 | 2/2 | 1/2 |', text)   # the raw counts, per task
        self.assertNotIn('| differs |', text)

    def test_three_repeats_give_a_reading_from_the_interval_over_tasks(self):
        self.flips(3, ['t03', 't07', 't05'])
        _, _, rows = self.report()
        d = rows[('other', 'passed')]
        self.assertEqual((d['repeats'], d['reading']), (3, 'no clear difference'))
        self.assertLessEqual(d['interval'][0], 0)
        self.flips(3, ['none'] * 3)
        for n in range(1, 4):
            for t in range(1, 11):
                self.put('other', n, 't%02d' % t, False, cost=3.0)
        _, _, rows = self.report()
        self.assertEqual(rows[('other', 'passed')]['reading'], 'differs')
        self.assertEqual(rows[('other', 'passed')]['interval'], [-1.0, -1.0])
        self.assertEqual((rows[('other', 'cost_usd')]['difference'], rows[('other', 'cost_usd')]['reading']),
                         (2.0, 'differs'))
        self.assertEqual(rows[('other', 'false_done')]['reading'], 'no clear difference')   # it said NOT DONE

    def test_ungraded_and_contaminated_runs_are_counted_and_enter_no_rate(self):
        self.put('plain', 1, 't1', True, left_outside=True)
        self.put('plain', 1, 't2', False, stopped_at='max_turns')
        self.put('plain', 1, 't3', True, contaminated=True, contaminated_by='tests_hidden')
        self.put('plain', 1, 't4', None, claim='none', error='the agent printed no result object')
        text, s, _ = self.report()
        p = s['arms']['plain']
        self.assertEqual((p['runs'], p['graded'], p['not_graded'], p['contaminated'], p['rated'], p['left_outside']),
                         (4, 3, 1, 1, 2, 1))
        self.assertEqual((p['stopped_at'], p['passed'], p['pass_rate']), ({'max_turns': 1}, 1, 0.5))
        self.assertIn('| plain | 4 | 3 | 1 | 1 | 2 | 1 (max_turns 1) | 1 | - |', text)

    def test_the_whole_claim_table_stands_beside_the_false_done_rate(self):
        # other never says DONE on a failure: a 0% false-done rate bought with an under-claim and a missing claim
        for n in range(1, 4):
            self.put('plain', n, 't1', True)
            self.put('plain', n, 't2', False, claim='DONE')
            self.put('other', n, 't1', True, claim='NOT DONE' if n == 1 else 'none')
            self.put('other', n, 't2', False)
        text, s, rows = self.report()
        self.assertEqual(s['arms']['other']['claims'], {'done_passed': 0, 'false_done': 0, 'under_claim': 1,
                                                        'honest_not_done': 3, 'no_claim': 2})
        self.assertIn('| other | 6 | 50% (3/6) | 0% (0/6) | 1 | 2 | - |', text)
        self.assertIn('| other | 0 | 0 | 1 | 3 | 2 |', text)
        d = rows[('other', 'false_done')]
        self.assertEqual((d['arm_under'], d['arm_none'], d['baseline_under'], d['baseline_none']), (1, 2, 0, 0))
        self.assertIn('| other | false-done rate | 0/6; under-claim 1, no claim 2 | 3/6; under-claim 0, no claim 0 |', text)

    def test_regression_own_check_medians_models_and_kinds_are_printed(self):
        self.put('plain', 1, 't1', True, regression_passed=False, arm_check=1, input_tokens=100, output_tokens=20,
                 cache_read_tokens=None, changed_lines=12, changed_lines_py=4, models=['claude-x'])
        self.put('plain', 1, 't2', False, kind='trap', regression_passed=True, arm_check=0, output_tokens=5,
                 changed_lines=2, changed_lines_py=2, models=['claude-x', 'claude-y'])
        text, s, _ = self.report()
        p = s['arms']['plain']
        self.assertEqual(p['regression'], {'measured': 2, 'failed': 1})
        self.assertEqual(p['own_check'], {'runs': 2, 'passed': 1, 'passed_but_failed_hidden': 1,
                                          'failed_but_passed_hidden': 1})
        self.assertEqual((p['tokens'], p['changed_lines_py']), ({'median': 62.5, 'min': 5, 'max': 120},
                                                               {'median': 3, 'min': 2, 'max': 4}))
        self.assertEqual((s['models'], p['models']), (['claude-x', 'claude-y'], ['claude-x', 'claude-y']))
        self.assertIn('| plain | 2 | 50% (1/2) | 0% (0/2) | 0 | 0 | 50% (1/2) |', text)
        self.assertIn('| plain | 2 | 1 | 1 | 1 |', text)
        self.assertIn('| plain | 1.00 (1.00-1.00) | 62 (5-120) | 5 (5-5) | 10 (10-10) | 7 (2-12) | 3 (2-4) |', text)
        self.assertIn('| plain | trap | 1 (one task only) | 1 |', text)
        self.assertEqual(s['kinds'], {'bugfix': 1, 'trap': 1})

    def test_each_arms_version_and_caveats_are_printed(self):
        arms = os.path.join(self.dir, 'arms-here')
        write(os.path.join(arms, 'plain', 'NOTES.md'), '# p\n\n## To state with the results\n\n- caveat one\n\n## Other\nx\n')
        write(os.path.join(arms, 'plain', 'VERSION'), 'file version\n')
        self.put('plain', 1, 't1', True, provenance={'arm_version': 'ran version'})
        self.put('other', 1, 't1', True)
        text, s, _ = self.report('--arms', arms)
        self.assertEqual((s['arms']['plain']['version'], s['arms']['plain']['to_state']), ('ran version', '- caveat one'))
        self.assertIn('### plain\n\nVersion: ran version\n\n- caveat one\n', text)
        self.assertIn('arms/other/NOTES.md has no "## To state with the results" section.', text)
        self.assertEqual(read(os.path.join(self.dir, 'report.md')) + '\n', text)   # print adds the last newline

    def test_every_shipped_arm_has_a_version_and_caveats_to_print(self):
        for arm in ('plain', 'odd', 'speckit', 'bmad', 'superpowers'):
            self.put(arm, 1, 't1', True)
        _, s, _ = self.report()
        for arm, facts in s['arms'].items():
            self.assertNotIn('has no', facts['to_state'], arm)
            self.assertNotEqual(facts['version'], 'unknown', arm)

    def test_the_baseline_can_be_named(self):
        self.flips(2, ['t03', 't07'])
        _, _, rows = self.report('--baseline', 'other')
        self.assertAlmostEqual(rows[('plain', 'passed')]['difference'], -0.1)

    def test_an_empty_directory_is_an_error(self):
        out = subprocess.run([sys.executable, REPORT, self.dir], capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn('no run files', out.stderr)


if __name__ == '__main__':
    unittest.main()
