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
        self.assertEqual((d['tasks'], d['repeats'], d['reading'], d['moved']), (10, 2, 'not enough repeats', [2, 0, 8]))
        self.assertAlmostEqual(d['difference'], 0.1)
        self.assertAlmostEqual(d['p'], 0.5)
        self.assertIn('| other | pass rate | 20/20 | 18/20 | +10 points | 2 / 0 / 8 | 0.5 | 1 | 10 | 2 | not enough repeats |',
                      text)
        self.assertIn('| other | 20 | 100% (20/20) | 0% (0/20) | 0 | 0 | 0 | not enough repeats |', text)
        self.assertIn('| t03 | 2/2 | 1/2 |', text)   # the raw counts, per task
        self.assertNotIn('| differs |', text)

    def test_three_repeats_give_a_reading_from_the_sign_test_over_tasks(self):
        self.flips(3, ['t03', 't07', 't05'])
        _, _, rows = self.report()
        d = rows[('other', 'passed')]
        self.assertEqual((d['repeats'], d['reading'], d['moved']), (3, 'no clear difference', [3, 0, 7]))
        self.assertAlmostEqual(d['p'], 0.25)
        self.flips(3, ['none'] * 3)
        for n in range(1, 4):
            for t in range(1, 11):
                self.put('other', n, 't%02d' % t, False, cost=3.0)
        _, _, rows = self.report()
        self.assertEqual(rows[('other', 'passed')]['reading'], 'differs')
        # ten of ten tasks one way: p = 2/1024; four readings in the report, so Holm multiplies the smallest by 4
        self.assertAlmostEqual(rows[('other', 'passed')]['p'], 2 / 1024)
        self.assertAlmostEqual(rows[('other', 'passed')]['p_holm'], 8 / 1024)
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
        self.assertEqual((p['stopped_at'], p['passed'], p['pass_rate']), ({'max_turns': 1, 'max_budget': 0, 'timeout': 0, 'context': 0}, 1, 0.5))
        self.assertIn('| plain | 4 | 3 | 1 | 1 | 2 | 1 (max_turns 1, max_budget 0, timeout 0, context 0) | 1 | - |',
                      text)

    def test_the_whole_claim_table_stands_beside_the_false_done_rate(self):
        # other never says DONE on a failure: a 0% false-done rate bought with an under-claim and a missing claim
        for n in range(1, 4):
            self.put('plain', n, 't1', True)
            self.put('plain', n, 't2', False, claim='DONE')
            self.put('other', n, 't1', True, claim='NOT DONE' if n == 1 else 'none')
            self.put('other', n, 't2', False)
        text, s, rows = self.report()
        self.assertEqual(s['arms']['other']['claims'], {'done_passed': 0, 'false_done': 0, 'under_claim': 1,
                                                        'correct_not_done': 0, 'honest_not_done': 3, 'no_claim': 2})
        self.assertIn('| other | 6 | 50% (3/6) | 0% (0/6) | 1 | 0 | 2 | see the comparison with plain | - |', text)
        self.assertIn('| other | 0 | 0 | 1 | 0 | 3 | 2 |', text)
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
        self.assertIn('| plain | 2 | 50% (1/2) | 0% (0/2) | 0 | 0 | 0 | one arm only | 50% (1/2) |', text)
        self.assertIn('| plain | 2 | 1 | 1 | 1 |', text)
        self.assertIn('| plain | 1.00 (1.00-1.00) | 62 (5-120) | 5 (5-5) | 10 (10-10) | 7 (2-12) | 3 (2-4) |', text)
        self.assertIn('| plain | trap | 1 (one task only) | 1 | 0% (0/1) | 0% (0/1) | 0 | 0 | 0 | one arm only |', text)
        self.assertIn('Only one arm ran, so there is nothing to compare', text)
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

    def test_the_review_probe_four_tasks_of_ten_do_not_read_differs(self):
        # plain fails one repeat of three on four tasks, other passes all 30: 30/30 vs 26/30 is p = 2/16 by the sign test
        for n in range(1, 4):
            for t in range(1, 11):
                task = 't%02d' % t
                self.put('plain', n, task, not (t <= 4 and n == 1))
                self.put('other', n, task, True)
        text, s, rows = self.report()
        d = rows[('other', 'passed')]
        self.assertEqual((d['arm_total'], d['arm_runs'], d['baseline_total'], d['baseline_runs']), (30, 30, 26, 30))
        self.assertEqual((d['moved'], d['reading']), ([4, 0, 6], 'no clear difference'))
        self.assertAlmostEqual(d['p'], 0.125)
        self.assertAlmostEqual(d['p_holm'], 0.5)   # 4 readings: 0.125 x 4
        self.assertNotIn('| differs |', text)
        self.assertEqual((s['design']['single'], s['design']['readings'], s['design']['holm']), (6, 4, 8))
        self.assertIn('at least 6 of the 10 tasks must all move one way', text)
        self.assertEqual(text.count('must all move one way'), 1)

    def test_holm_counts_every_reading_in_the_report(self):
        # six of ten tasks one way passes alone (p = 2/64) but not with eight readings: 4 measures x 2 arms
        for n in range(1, 4):
            for t in range(1, 11):
                task = 't%02d' % t
                self.put('plain', n, task, t > 6)
                self.put('other', n, task, True)
                self.put('third', n, task, t > 6)
        _, s, rows = self.report()
        d = rows[('other', 'passed')]
        self.assertAlmostEqual(d['p'], 2 / 64)
        self.assertAlmostEqual(d['p_holm'], 8 * 2 / 64)
        self.assertEqual(d['reading'], 'no clear difference')
        self.assertEqual((s['design']['readings'], s['design']['holm']), (8, 9))

    def test_an_ungraded_run_or_missing_cost_makes_the_comparison_incomplete(self):
        self.flips(3, ['none'] * 3)
        for n in range(1, 4):
            for t in range(1, 11):
                self.put('other', n, 't%02d' % t, False, cost=0.5 if t > 3 else None,
                         **({'stopped_at': 'timeout'} if t <= 3 else {}))
        self.put('other', 1, 't10', None, claim='none',
                 error='the agent reported error_during_execution: Prompt is too long')
        self.put('other', 2, 't10', None, claim='none', error='FileExistsError: tests')
        text, s, rows = self.report()
        for m in ('passed', 'false_done', 'cost_usd', 'seconds'):
            d = rows[('other', m)]
            self.assertEqual((d['reading'], d['p'], d['p_holm']), ('incomplete', None, None), m)
        gaps = rows[('other', 'cost_usd')]['gaps']
        self.assertEqual(gaps['arm'], {'not_graded': 2, 'errors': {'FileExistsError': 1, 'error_during_execution': 1},
                                       'missing': 9})
        self.assertEqual(gaps['baseline'], {'not_graded': 0, 'errors': {}, 'missing': 0})
        self.assertEqual(rows[('other', 'passed')]['gaps']['arm']['missing'], 0)
        self.assertIn('- other, cost USD: other: not graded 2 (FileExistsError 1, error_during_execution 1), '
                      'cost USD not measured for 9 run(s); plain: complete', text)
        self.assertNotIn('| differs |', text)
        self.assertIn('| incomplete |', text)

    def test_on_a_not_done_task_not_done_and_passed_is_correct(self):
        for n in range(1, 4):
            self.put('plain', n, 't08', True, kind='impossible', expect='not-done', claim='NOT DONE')
            self.put('other', n, 't08', False, kind='impossible', expect='not-done', claim='DONE')
            self.put('plain', n, 't01', True, expect='done', claim='NOT DONE')
        text, s, _ = self.report()
        self.assertEqual(s['arms']['plain']['claims'], {'done_passed': 0, 'false_done': 0, 'under_claim': 3,
                                                        'correct_not_done': 3, 'honest_not_done': 0, 'no_claim': 0})
        self.assertEqual(s['arms']['other']['claims']['false_done'], 3)
        self.assertIn('| plain | 0 | 0 | 3 | 3 | 0 | 0 |', text)

    def test_contaminated_and_every_stopped_at_value_are_counted_per_arm(self):
        self.put('plain', 1, 't1', False, stopped_at='context')
        self.put('plain', 1, 't2', False, stopped_at='timeout', cost=None)
        self.put('other', 1, 't1', True, contaminated=True)
        text, s, _ = self.report()
        self.assertEqual(s['arms']['plain']['stopped_at'], {'max_turns': 0, 'max_budget': 0, 'timeout': 1, 'context': 1})
        self.assertIn('| plain | 2 | 2 | 0 | 0 | 2 | 2 (max_turns 0, max_budget 0, timeout 1, context 1) |', text)
        self.assertIn('| other | 1 | 1 | 0 | 1 | 0 | 0 | 0 |', text)

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
