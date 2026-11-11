#!/usr/bin/env python3
"""Aggregate one results directory into report.md (for the repository) and summary.json (for a website), both made
from one computed structure; the Markdown is printed as well.

usage: report.py <results dir> [--baseline ARM] [--arms DIR]

Which runs count. A run with `passed` null was not graded (its setup failed, the CLI gave no result, or it gave an error
that is not a cap), and a contaminated run (its transcript touched the bench, the hidden tests or another session's
directory) keeps its grade in the record. Neither enters any rate, median or comparison; both are counted per arm. A run
stopped at a cap was graded on the tree it left: it counts, and is also counted apart.

Comparing an arm with the baseline (plain by default) is done task by task, so that tasks flipping between repeats do
not cancel out: per task, the arm's mean over its repeats minus the baseline's (for pass and false done that is the
difference in counts divided by the repeats), then the mean over the tasks both ran, with a 95% bootstrap interval over
tasks (fixed seed). "differs" only when the interval excludes zero and every paired task has at least three repeats on
both sides; with fewer the reading is "not enough repeats". The raw counts are printed beside every reading.
"""
import argparse
import json
import os
import random
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_REPEATS = 3
BOOTSTRAP, SEED = 4000, 20261111
TOKEN_KEYS = ('input_tokens', 'output_tokens', 'cache_read_tokens', 'cache_creation_tokens')
DISTS = (('cost_usd', 'cost USD', '%.2f'), ('tokens', 'tokens', '%d'), ('turns', 'turns', '%g'),
         ('seconds', 'seconds', '%.0f'), ('changed_lines', 'changed lines', '%d'),
         ('changed_lines_py', 'changed lines, *.py', '%d'))
CLAIMS = (('done_passed', 'DONE, passed'), ('false_done', 'DONE, failed (false done)'),
          ('under_claim', 'NOT DONE, passed (under-claim)'), ('honest_not_done', 'NOT DONE, failed'),
          ('no_claim', 'no claim'))
COMPARED = (('passed', 'pass rate'), ('false_done', 'false-done rate'), ('cost_usd', 'cost USD'),
            ('seconds', 'seconds'))
BINARY = ('passed', 'false_done')


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


def counts(run):
    """In the rates: graded, and not contaminated."""
    return run.get('passed') is not None and not run.get('contaminated')


def seconds(run):
    """The CLI's own duration; the wall clock only where the CLI gave none (a session that was stopped)."""
    return run['duration_ms'] / 1000.0 if run.get('duration_ms') is not None else run.get('wall_seconds')


def value(run, measure):
    if measure == 'passed':
        return 1 if run['passed'] else 0
    if measure in dict(CLAIMS):
        return 1 if claim_of(run) == measure else 0
    if measure == 'seconds':
        return seconds(run)
    if measure == 'turns':
        return run.get('num_turns')
    if measure == 'tokens':
        parts = [run[k] for k in TOKEN_KEYS if run.get(k) is not None]
        return sum(parts) if parts else None
    return run.get(measure)


def claim_of(run):
    claim = run.get('claim')
    if claim == 'DONE':
        return 'done_passed' if run['passed'] else 'false_done'
    if claim == 'NOT DONE':
        return 'under_claim' if run['passed'] else 'honest_not_done'
    return 'no_claim'


def dist(values):
    values = sorted(v for v in values if v is not None)
    return {'median': statistics.median(values), 'min': values[0], 'max': values[-1]} if values else None


def stats(runs):
    rated = [r for r in runs if counts(r)]
    n = len(rated)
    claims = dict.fromkeys((k for k, _ in CLAIMS), 0)
    for r in rated:
        claims[claim_of(r)] += 1
    caps = {}
    for r in runs:
        if r.get('stopped_at'):
            caps[r['stopped_at']] = caps.get(r['stopped_at'], 0) + 1
    passed = sum(value(r, 'passed') for r in rated)
    regression = [r for r in rated if r.get('regression_passed') is not None]
    checked = [r for r in rated if r.get('arm_check') is not None]
    s = {'runs': len(runs), 'graded': sum(1 for r in runs if r.get('passed') is not None),
         'not_graded': sum(1 for r in runs if r.get('passed') is None),
         'contaminated': sum(1 for r in runs if r.get('contaminated')),
         'stopped_at': caps, 'left_outside': sum(1 for r in runs if r.get('left_outside')),
         'rated': n, 'tasks': len({r['task'] for r in rated}),
         'passed': passed, 'pass_rate': passed / n if n else None,
         'claims': claims, 'false_done_rate': claims['false_done'] / n if n else None,
         'regression': {'measured': len(regression),
                        'failed': sum(1 for r in regression if not r['regression_passed'])},
         'own_check': {'runs': len(checked), 'passed': sum(1 for r in checked if r['arm_check'] == 0),
                       'passed_but_failed_hidden': sum(1 for r in checked if r['arm_check'] == 0 and not r['passed']),
                       'failed_but_passed_hidden': sum(1 for r in checked if r['arm_check'] != 0 and r['passed'])},
         'models': sorted({m for r in runs for m in r.get('models') or ()})}
    for key, _, _ in DISTS:
        s[key] = dist(value(r, key) for r in rated)
    return s


def per_task(runs, measure):
    out = {}
    for r in runs:
        v = value(r, measure) if counts(r) else None
        if v is not None:
            out.setdefault(r['task'], []).append(v)
    return out


def interval(diffs):
    """95% percentile bootstrap of the mean over tasks; a fixed seed, so a report reads the same every time."""
    rng, k = random.Random(SEED), len(diffs)
    means = sorted(sum(rng.choice(diffs) for _ in range(k)) / k for _ in range(BOOTSTRAP))
    return [means[int(0.025 * BOOTSTRAP)], means[int(0.975 * BOOTSTRAP) - 1]]


def compare(arm_runs, base_runs, measure):
    a, b = per_task(arm_runs, measure), per_task(base_runs, measure)
    tasks = sorted(set(a) & set(b))
    mean = statistics.mean
    row = {'measure': measure, 'tasks': len(tasks),
           'repeats': min((min(len(a[t]), len(b[t])) for t in tasks), default=0),
           'arm_total': sum(sum(a[t]) for t in tasks), 'arm_runs': sum(len(a[t]) for t in tasks),
           'baseline_total': sum(sum(b[t]) for t in tasks), 'baseline_runs': sum(len(b[t]) for t in tasks),
           'arm_mean': None, 'baseline_mean': None, 'difference': None, 'interval': None}
    if not tasks:
        return dict(row, reading='not measured')
    diffs = [mean(a[t]) - mean(b[t]) for t in tasks]
    row.update(arm_mean=mean(mean(a[t]) for t in tasks), baseline_mean=mean(mean(b[t]) for t in tasks),
               difference=mean(diffs))
    if measure == 'false_done':  # never stands without the counts that could have bought it
        for side, runs in (('arm', arm_runs), ('baseline', base_runs)):
            for key, name in (('under_claim', 'under'), ('no_claim', 'none')):
                found = per_task(runs, key)
                row['%s_%s' % (side, name)] = sum(sum(found[t]) for t in tasks)
    if row['repeats'] < MIN_REPEATS:
        return dict(row, reading='not enough repeats')
    row['interval'] = interval(diffs)
    lo, hi = row['interval']
    return dict(row, reading='differs' if lo > 0 or hi < 0 else 'no clear difference')


def section(path, heading):
    """The body of a "## <heading>" section of a Markdown file, or None."""
    try:
        with open(path, encoding='utf-8') as f:
            found = re.search(r'^## %s[^\n]*\n(.*?)(?=^## |\Z)' % re.escape(heading), f.read(), re.S | re.M)
    except OSError:
        return None
    return found.group(1).strip() if found else None


def arm_facts(arms_dir, arm, runs):
    """What the reader must know about an arm: the version that ran (from the records) and its stated caveats."""
    versions = sorted({str((r.get('provenance') or {}).get('arm_version')) for r in runs
                       if (r.get('provenance') or {}).get('arm_version')})
    if not versions:
        try:
            with open(os.path.join(arms_dir, arm, 'VERSION'), encoding='utf-8') as f:
                versions = [f.readline().strip()]
        except OSError:
            versions = ['unknown']
    notes = section(os.path.join(arms_dir, arm, 'NOTES.md'), 'To state with the results')
    return {'version': ' / '.join(versions), 'versions_differ': len(versions) > 1,
            'to_state': notes or 'arms/%s/NOTES.md has no "## To state with the results" section.' % arm}


def summarise(runs, baseline=None, arms_dir=None):
    arms_dir = arms_dir or os.path.join(HERE, 'arms')
    by_arm, by_kind, kinds = {}, {}, {}
    for r in runs:
        kind = r.get('kind') or 'unknown'
        by_arm.setdefault(r['arm'], []).append(r)
        by_kind.setdefault(r['arm'], {}).setdefault(kind, []).append(r)
        kinds.setdefault(kind, set()).add(r['task'])
    baseline = baseline or ('plain' if 'plain' in by_arm else sorted(by_arm)[0])
    if baseline not in by_arm:
        sys.exit('baseline arm %r has no runs here; arms: %s' % (baseline, ', '.join(sorted(by_arm))))
    pass_counts = {}
    for arm, rs in by_arm.items():
        for task, vs in per_task(rs, 'passed').items():
            pass_counts.setdefault(task, {})[arm] = {'passed': sum(vs), 'runs': len(vs)}
    spec = section(os.path.join(HERE, 'SPEC.md'), 'Known limits')
    return {'runs': len(runs), 'tasks': sorted({r['task'] for r in runs}),
            'repeats': len({r.get('repeat') for r in runs}), 'baseline': baseline,
            'requested_models': sorted({str(r.get('model')) for r in runs}),
            'models': sorted({m for r in runs for m in r.get('models') or ()}),
            'arms': {arm: dict(stats(rs), **arm_facts(arms_dir, arm, rs)) for arm, rs in by_arm.items()},
            'kinds': {kind: len(tasks) for kind, tasks in kinds.items()},
            'by_kind': {arm: {kind: stats(rs) for kind, rs in ks.items()} for arm, ks in by_kind.items()},
            'pass_counts': pass_counts,
            'comparisons': [dict(compare(by_arm[arm], by_arm[baseline], m), arm=arm, baseline=baseline)
                            for arm in sorted(by_arm) if arm != baseline for m, _ in COMPARED],
            'known_limits': spec or 'SPEC.md beside report.py has no "Known limits" section.'}


def pct(k, n):
    return '%d%% (%d/%d)' % (round(100.0 * k / n), k, n) if n else '-'


def span(d, fmt):
    return '%s (%s-%s)' % (fmt % d['median'], fmt % d['min'], fmt % d['max']) if d else '-'


def amount(measure, v, change=False):
    """A per-task mean, or with change=True a difference: rates read in points, and gains carry a +."""
    if v is None:
        return '-'
    sign = '+' if change and v > 0 else ''
    if measure in BINARY:
        return '%s%.0f%s' % (sign, 100 * v, ' points' if change else '%')
    return sign + ('%.2f' if measure == 'cost_usd' else '%.0f') % v


def few(n):
    return '%d%s' % (n, {1: ' (one task only)', 2: ' (two tasks only)'}.get(n, ''))


def capped(caps):
    total = sum(caps.values())
    return '%d (%s)' % (total, ', '.join('%s %d' % kv for kv in sorted(caps.items()))) if total else 0


def table(head, rows):
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    return lines + ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]


def outcome_cells(s):
    """The false-done rate never stands without the under-claim and no-claim counts beside it."""
    c = s['claims']
    return [s['rated'], pct(s['passed'], s['rated']), pct(c['false_done'], s['rated']), c['under_claim'],
            c['no_claim']]


def raw(d, s):
    if d['measure'] not in BINARY:
        return amount(d['measure'], d['%s_mean' % s])
    text = '%d/%d' % (d['%s_total' % s], d['%s_runs' % s])
    return text + ('; under-claim %d, no claim %d' % (d['%s_under' % s], d['%s_none' % s])
                   if d['measure'] == 'false_done' else '')


def render(s, title):
    arms, base = s['arms'], s['baseline']
    names = sorted(arms)
    out = ['# Comparison: %s' % title, '',
           '%d run(s): %d task(s), %d arm(s), %d repeat(s). Model asked for: %s. Models that did work: %s.'
           % (s['runs'], len(s['tasks']), len(arms), s['repeats'], ', '.join(s['requested_models']),
              ', '.join(s['models']) or 'not recorded'), '', '## Runs per arm', '',
           'Every figure below uses only the runs "in the rates": graded and not contaminated. A run stopped at a cap',
           'was graded on the tree it left and is in the rates.', '']
    out += table(['arm', 'runs', 'graded', 'not graded (error)', 'contaminated', 'in the rates', 'stopped at a cap',
                  'work left outside the graded tree', 'models seen'],
                 [[a, arms[a]['runs'], arms[a]['graded'], arms[a]['not_graded'], arms[a]['contaminated'],
                   arms[a]['rated'], capped(arms[a]['stopped_at']),
                   arms[a]['left_outside'], ', '.join(arms[a]['models']) or '-'] for a in names])
    out += ['', '## Results per arm', '']
    out += table(['arm', 'in the rates', 'pass rate', 'false-done rate', 'under-claim', 'no claim',
                  'visible tests broken (regression)'],
                 [[a] + outcome_cells(arms[a]) + [pct(arms[a]['regression']['failed'], arms[a]['regression']['measured'])]
                  for a in names])
    out += ['', '## Claims against the grade', '']
    out += table(['arm'] + [label for _, label in CLAIMS], [[a] + [arms[a]['claims'][k] for k, _ in CLAIMS]
                                                           for a in names])
    out += ['', '## Cost and size: median (min-max)', '',
            'Tokens are input, output, cache read and cache creation, summed over every model that did work.', '']
    out += table(['arm'] + [label for _, label, _ in DISTS],
                 [[a] + [span(arms[a][k], fmt) for k, _, fmt in DISTS] for a in names])
    out += ['', '## Per arm and task kind', '',
            'A figure for a kind with one or two tasks is a figure about those tasks, not about the kind.', '']
    out += table(['arm', 'kind', 'tasks', 'in the rates', 'pass rate', 'false-done rate', 'under-claim', 'no claim'],
                 [[a, k, few(s['kinds'][k])] + outcome_cells(s['by_kind'][a][k])
                  for a in names for k in sorted(s['by_kind'][a])])
    out += ['', '## Passes per task', '']
    out += table(['task'] + names, [[t] + ['%(passed)d/%(runs)d' % s['pass_counts'][t][a] if a in s['pass_counts'][t]
                                           else '-' for a in names] for t in sorted(s['pass_counts'])])
    out += ['', '## Each arm against %s, task by task' % base, '',
            'Difference: per task, the arm\'s mean over its repeats minus %s\'s, averaged over the tasks both ran.' % base,
            'Interval: 95%% bootstrap over tasks. "differs" only when it excludes zero with at least %d repeats.'
            % MIN_REPEATS, '']
    labels = dict(COMPARED)
    out += table(['arm', 'measure', 'arm', base, 'difference', '95% interval', 'tasks', 'repeats', 'reading'],
                 [[d['arm'], labels[d['measure']], raw(d, 'arm'), raw(d, 'baseline'),
                   amount(d['measure'], d['difference'], True),
                   '-' if d['interval'] is None else '%s to %s' % tuple(amount(d['measure'], v, True)
                                                                         for v in d['interval']),
                   d['tasks'], d['repeats'], d['reading']] for d in s['comparisons']])
    if not s['comparisons']:
        out += ['', 'Only one arm ran, so there is nothing to compare.']
    checked = [a for a in names if arms[a]['own_check']['runs']]
    if checked:
        out += ['', "## The arm's own check", '',
                "An arm's post.sh ran on a copy of the session, apart from the grade.", '']
        keys = ('runs', 'passed', 'passed_but_failed_hidden', 'failed_but_passed_hidden')
        out += table(['arm', 'runs checked', 'own check passed', 'own check passed, hidden tests failed',
                      'own check failed, hidden tests passed'],
                     [[a] + [arms[a]['own_check'][k] for k in keys] for a in checked])
    out += ['', '## What each arm is, and what to state with its results', '']
    for a in names:
        out += ['### %s' % a, '', 'Version: %s%s' % (arms[a]['version'], ' (more than one version in these results)'
                                                     if arms[a]['versions_differ'] else ''), '',
                arms[a]['to_state'], '']
    return '\n'.join(out + ['## Known limits', '', s['known_limits'], ''])


def main(argv=None):
    ap = argparse.ArgumentParser(description='Aggregate a results directory into report.md and summary.json.')
    ap.add_argument('results', help='a directory written by run.py')
    ap.add_argument('--baseline', metavar='ARM', help='the arm the others are compared with (default: plain)')
    ap.add_argument('--arms', metavar='DIR', help='where each arm\'s NOTES.md and VERSION are (default: arms/ here)')
    a = ap.parse_args(argv)
    runs = load(a.results)
    if not runs:
        sys.exit('no run files in %s' % a.results)
    summary = summarise(runs, a.baseline, a.arms)
    text = render(summary, os.path.basename(os.path.abspath(a.results)))
    print(text)
    with open(os.path.join(a.results, 'report.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    with open(os.path.join(a.results, 'summary.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
        f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
