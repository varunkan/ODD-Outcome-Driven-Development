#!/usr/bin/env python3
"""No model: is the rule behind odd's "reject:" check sound on a second kind of program?

The rule: an ending the proof shows rejected after one example must be rejected after every other example that is not
rejected. For every pair (tests of run T, program of run P) of the same task, the generated inputs are built as odd
builds them, under four variants of the rule: an ending needs 1 or 2 witnesses (pairs of examples that show it), and
an ending is or is not dropped when the proof itself shows it accepted after some example. Each generated input the
program does not reject is looked up in the task's reference: a TRUE alarm if the reference rejects it (the program
is wrong), a FALSE alarm if the reference does not (the rule is wrong).

Tasks: the calculator (15 kept programs) and the duration normaliser (9 kept programs). Writes replay3.json.

usage: replay3.py
"""
import glob
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.dirname(HERE)
sys.path.insert(0, '/home/user/odd-outcome-driven-development')
sys.path.insert(0, HERE)
import dprobes  # noqa: E402
import odd  # noqa: E402
import probes  # noqa: E402

TASKS = {
    'calculator': dict(file='calc.py', ref=probes.reference, runs=[
        ('odd', n, 'calc-out') for n in (1, 2, 3)] + [('speckit', n, 'calc-out') for n in (1, 2, 3)] + [
        ('odd-cases', n, 'calc-out2') for n in (1, 2, 3)] + [('odd-reach', n, 'calc-out3') for n in (1, 2, 3)] + [
        ('odd-second', n, 'calc-out5') for n in (1, 2, 3)]),
    'duration': dict(file='dur.py', ref=dprobes.reference, runs=[
        (a, n, 'dur-out') for a in ('plain', 'odd', 'odd-claim') for n in (1, 2, 3)]),
}
RULES = [(w, drop) for w in (1, 2) for drop in (False, True)]


class Outcome:
    def __init__(self, fields):
        self.fields, self.rel = fields, '.odd/outcomes/replay.md'

    def get(self, k):
        return self.fields.get(k)


def project(task, arm, n, out):
    return json.load(open(os.path.join(S, out, '%s.%s.%d.json' % (task, arm, n))))['session_dir']


def literals(task, t):
    d = tempfile.mkdtemp(prefix='replay3-')
    try:
        shutil.copytree(os.path.join(project(task, *t), 'tests'), os.path.join(d, 'tests'),
                        ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
        subprocess.run(['git', 'init', '-q'], cwd=d, check=True)
        tests = sorted(os.path.relpath(f, d) for f in glob.glob(os.path.join(d, 'tests', '**', '*.py'), recursive=True))
        return odd.pick(odd._entry_inputs(d, dict(odd.DEFAULTS), Outcome({'proof': 'python3 -m pytest ' + ' '.join(tests)})),
                        odd.REJECT_INPUTS)
    finally:
        shutil.rmtree(d, True)


def one(job):
    task, t, p, known = job
    spec = TASKS[task]
    prog, seen = os.path.join(project(task, *p), spec['file']), {}

    def end(x):
        if x not in seen:
            seen[x] = probes.run(prog, x)[0]
        return seen[x]

    passing, refused = [x for x in known if end(x) not in (None, 2)], [x for x in known if end(x) == 2]
    wit = {}
    for b in refused:
        for a in passing:
            if b.startswith(a) and 0 < len(b) - len(a) <= odd.REJECT_ENDING:
                wit.setdefault(b[len(a):], []).append(a)
    out = {}
    for need, drop in RULES:
        ends = [s for s in sorted(wit, key=lambda s: (len(s), s)) if len(wit[s]) >= need
                and not (drop and any(a + s in passing for a in passing))][:odd.REJECT_ENDINGS]
        made = odd.pick([(a, s) for s in ends for a in passing if a + s not in known], odd.REJECT_INPUTS)
        true, false = [], []
        for a, s in made:
            if end(a + s) not in (None, 2):
                (true if spec['ref'](a + s)[0] == 2 else false).append(a + s)
        out['%d%s' % (need, '+drop' if drop else '')] = dict(made=len(made), true=true[:5], false=false[:5],
                                                             n_true=len(true), n_false=len(false))
    return dict(task=task, tests='%s.%d' % t[:2], program='%s.%d' % p[:2], rules=out)


if __name__ == '__main__':
    jobs = []
    for task, spec in TASKS.items():
        lits = {t: literals(task, t) for t in spec['runs']}
        jobs += [(task, t, p, lits[t]) for t in spec['runs'] for p in spec['runs']]
    with multiprocessing.Pool(8) as pool:
        rows = pool.map(one, jobs, chunksize=1)
    json.dump(rows, open(os.path.join(HERE, 'replay3.json'), 'w'), indent=1)
    for task in TASKS:
        for rule in ['%d%s' % (w, '+drop' if d else '') for w, d in RULES]:
            rs = [r for r in rows if r['task'] == task]
            own = [r for r in rs if r['tests'] == r['program']]
            f = lambda sel, k: sum(1 for r in sel if r['rules'][rule][k])  # noqa: E731
            print('%-10s rule %-6s pairs with a true alarm %3d of %d, with a false alarm %3d; own tests: true %2d, false %2d of %d; '
                  'generated %d' % (task, rule, f(rs, 'n_true'), len(rs), f(rs, 'n_false'), f(own, 'n_true'), f(own, 'n_false'),
                                    len(own), sum(r['rules'][rule]['made'] for r in rs)))
        ex = [(r['tests'], r['program'], r['rules']['1']['false'][:2]) for r in rows if r['task'] == task and r['rules']['1']['false']][:4]
        print('   false alarms under rule 1, examples:', ex)
        ex = [(r['tests'], r['program'], r['rules']['2+drop']['false'][:2]) for r in rows if r['task'] == task and r['rules']['2+drop']['false']][:4]
        print('   false alarms under rule 2+drop, examples:', ex)
