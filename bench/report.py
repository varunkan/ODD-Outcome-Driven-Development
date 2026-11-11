#!/usr/bin/env python3
"""Aggregate one results directory: print a Markdown report and write summary.json into that directory.

usage: report.py <results dir> [--baseline ARM]

Per arm, and per arm and task kind: runs, pass rate, false-done rate, honest not-done count, and the median with the
minimum and maximum of cost, seconds and turns. Then every other arm against the baseline arm (default: plain when it
ran, otherwise the first arm by name).

The spread of a figure is, per arm, its range over the repeats: each repeat's own figure over the tasks it ran, highest
minus lowest. A comparison uses the larger of the two arms' spreads, and a difference no larger than that is reported
as "within spread", never as a result. With one repeat there is no spread, and the report says so.

A run that could not be graded (its setup failed, so no session ran) is counted apart and enters no rate.
"""
import argparse
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MEASURES = (('pass_rate', 'pass rate'), ('false_done_rate', 'false-done rate'),
            ('cost_usd', 'median cost, USD'), ('seconds', 'median seconds'))
COLUMNS = ['runs', 'pass rate', 'false-done rate', 'honest not-done', 'cost USD: median (min-max)',
           'seconds: median (min-max)', 'turns: median (min-max)']


def load(directory):
    runs = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith('.json'):
            continue
        try:
            with open(os.path.join(directory, name), encoding='utf-8') as f:
                found = json.load(f)
        except ValueError:
            print('skipped %s: not valid JSON' % name, file=sys.stderr)
            continue
        if isinstance(found, dict) and 'task' in found and 'arm' in found:  # summary.json has neither
            runs.append(found)
    return runs


def seconds(run):
    """The CLI's own duration; the wall clock only where the CLI gave none (a session that was stopped)."""
    return run['duration_ms'] / 1000.0 if run.get('duration_ms') is not None else run.get('wall_seconds')


def dist(values):
    values = sorted(v for v in values if v is not None)
    return {'median': statistics.median(values), 'min': values[0], 'max': values[-1]} if values else None


def stats(runs):
    graded = [r for r in runs if r.get('passed') is not None]
    n = len(graded)
    passed = sum(1 for r in graded if r['passed'])
    false_done = sum(1 for r in graded if r.get('claim') == 'DONE' and not r['passed'])
    checked = [r for r in graded if r.get('arm_check') is not None]
    return {'runs': n, 'not_graded': len(runs) - n,
            'passed': passed, 'pass_rate': passed / n if n else None,
            'false_done': false_done, 'false_done_rate': false_done / n if n else None,
            'honest_not_done': sum(1 for r in graded if r.get('claim') == 'NOT DONE' and not r['passed']),
            'cost_usd': dist(r.get('cost_usd') for r in graded),
            'seconds': dist(seconds(r) for r in graded),
            'turns': dist(r.get('num_turns') for r in graded),
            'own_check': {'runs': len(checked), 'passed': sum(1 for r in checked if r['arm_check'] == 0),
                          'passed_but_failed_hidden': sum(1 for r in checked
                                                          if r['arm_check'] == 0 and not r['passed'])}}


def figure(s, measure):
    value = s[measure]
    return value['median'] if isinstance(value, dict) else value


def spread(runs):
    """Per measure: highest minus lowest of the repeats' own figures; None when fewer than two repeats have one."""
    by_repeat = {}
    for r in runs:
        by_repeat.setdefault(r.get('repeat'), []).append(r)
    out = {}
    for measure, _ in MEASURES:
        figures = [f for f in (figure(stats(rs), measure) for rs in by_repeat.values()) if f is not None]
        out[measure] = max(figures) - min(figures) if len(figures) >= 2 else None
    return out


def differences(arms, baseline):
    rows = []
    for arm in sorted(arms):
        for measure, _ in MEASURES if arm != baseline else ():
            a, b = figure(arms[arm], measure), figure(arms[baseline], measure)
            sa, sb = arms[arm]['spread'][measure], arms[baseline]['spread'][measure]
            diff = None if a is None or b is None else a - b
            limit = None if sa is None or sb is None else max(sa, sb)
            reading = ('not measured' if diff is None else 'same' if diff == 0
                       else 'spread unknown: one repeat' if limit is None
                       else 'within spread' if abs(diff) <= limit else 'differs')
            rows.append({'arm': arm, 'baseline': baseline, 'measure': measure, 'value': a, 'baseline_value': b,
                         'difference': diff, 'spread': limit, 'reading': reading})
    return rows


def known_limits():
    try:
        with open(os.path.join(HERE, 'SPEC.md'), encoding='utf-8') as f:
            found = re.search(r'^## Known limits[^\n]*\n(.*?)(?=^## |\Z)', f.read(), re.S | re.M)
    except OSError:
        return 'SPEC.md was not found beside report.py, so its known limits could not be printed.'
    return found.group(1).strip() if found else 'SPEC.md has no "Known limits" section.'


def summarise(runs, baseline=None):
    by_arm, by_kind = {}, {}
    for r in runs:
        by_arm.setdefault(r['arm'], []).append(r)
        by_kind.setdefault(r['arm'], {}).setdefault(r.get('kind') or 'unknown', []).append(r)
    arms = {arm: dict(stats(rs), spread=spread(rs)) for arm, rs in by_arm.items()}
    baseline = baseline or ('plain' if 'plain' in arms else sorted(arms)[0])
    if baseline not in arms:
        sys.exit('baseline arm %r has no runs here; arms: %s' % (baseline, ', '.join(sorted(arms))))
    return {'runs': len(runs), 'models': sorted({str(r.get('model')) for r in runs}),
            'tasks': sorted({r['task'] for r in runs}), 'repeats': len({r.get('repeat') for r in runs}),
            'baseline': baseline, 'arms': arms,
            'by_kind': {arm: {kind: stats(rs) for kind, rs in kinds.items()} for arm, kinds in by_kind.items()},
            'differences': differences(arms, baseline), 'known_limits': known_limits()}


def pct(k, n):
    return '%d%% (%d/%d)' % (round(100.0 * k / n), k, n) if n else '-'


def span(d, fmt):
    return '%s (%s-%s)' % (fmt % d['median'], fmt % d['min'], fmt % d['max']) if d else '-'


def cells(s):
    return [s['runs'], pct(s['passed'], s['runs']), pct(s['false_done'], s['runs']), s['honest_not_done'],
            span(s['cost_usd'], '%.2f'), span(s['seconds'], '%.0f'), span(s['turns'], '%g')]


def amount(measure, value, change=False):
    """A figure, or with change=True a difference or a spread: rates then read in points, and gains carry a +."""
    if value is None:
        return '-'
    sign = '+' if change and value > 0 else ''
    if measure.endswith('_rate'):
        return '%s%.0f%s' % (sign, 100 * value, ' points' if change else '%')
    return sign + ('%.2f' if measure == 'cost_usd' else '%.0f') % value


def table(head, rows):
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    return lines + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]


def render(s, title):
    arms, base = s['arms'], s['baseline']
    out = ['# Comparison: %s' % title, '',
           '%d run(s): %d task(s), %d arm(s), %d repeat(s). Model: %s.'
           % (s['runs'], len(s['tasks']), len(arms), s['repeats'], ', '.join(s['models'])), '', '## Per arm', '']
    out += table(['arm'] + COLUMNS, [[arm] + cells(arms[arm]) for arm in sorted(arms)])
    not_graded = sum(a['not_graded'] for a in arms.values())
    if not_graded:
        out += ['', '%d run(s) could not be graded (see "error" in their files) and are in no figure above.' % not_graded]
    out += ['', '## Per arm and task kind', '']
    out += table(['arm', 'kind'] + COLUMNS, [[arm, kind] + cells(s['by_kind'][arm][kind])
                                             for arm in sorted(arms) for kind in sorted(s['by_kind'][arm])])
    out += ['', '## Each arm against %s' % base, '',
            'Spread: the range of the figure over the repeats, the larger of the two arms. A difference no larger than',
            'the spread is no difference.', '']
    labels = dict(MEASURES)
    out += table(['arm', 'measure', 'arm', base, 'difference', 'spread', 'reading'],
                 [[d['arm'], labels[d['measure']], amount(d['measure'], d['value']),
                   amount(d['measure'], d['baseline_value']), amount(d['measure'], d['difference'], True),
                   amount(d['measure'], d['spread'], True).lstrip('+'), d['reading']] for d in s['differences']])
    if not s['differences']:
        out += ['', 'Only one arm ran, so there is nothing to compare.']
    checked = [arm for arm in sorted(arms) if arms[arm]['own_check']['runs']]
    if checked:
        out += ['', "## The arm's own check", '',
                "An arm's post.sh ran after the session and before the hidden tests were copied in.", '']
        out += table(['arm', 'runs checked', 'own check passed', 'own check passed, hidden tests failed'],
                     [[arm] + [arms[arm]['own_check'][k] for k in ('runs', 'passed', 'passed_but_failed_hidden')]
                      for arm in checked])
    return '\n'.join(out + ['', '## Known limits', '', s['known_limits'], ''])


def main(argv=None):
    ap = argparse.ArgumentParser(description='Aggregate a results directory into a table and summary.json.')
    ap.add_argument('results', help='a directory written by run.py')
    ap.add_argument('--baseline', metavar='ARM', help='the arm the others are compared with (default: plain)')
    a = ap.parse_args(argv)
    runs = load(a.results)
    if not runs:
        sys.exit('no run files in %s' % a.results)
    summary = summarise(runs, a.baseline)
    print(render(summary, os.path.basename(os.path.abspath(a.results))))
    with open(os.path.join(a.results, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
        f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
