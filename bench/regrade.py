#!/usr/bin/env python3
"""Grade kept runs a second time, with the harness's own grade(), and say where the two grades disagree.

One recorded failure could not be reproduced: the same grading function passed on the kept tree every time it was
tried (evidence 22). So a count is not read from one grade any more. For each run record that names a kept tree, a
fresh copy of that tree is graded again, exactly as run.py grades (the task's own environment, a temporary folder of
its own), and the result is printed beside the recorded one. A run whose two grades differ is listed for a person to
look at; what to do with it in a comparison is that comparison's rule, fixed before its runs.

usage: regrade.py --root ROOT RECORD.json [RECORD.json ...]
Prints one JSON object per record (task, arm, repeat, recorded, regraded, agree, and the regrade's last lines), then
the counts.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run as bench  # noqa: E402


def regrade(rec, root):
    """(passed, last lines) of one more grade of the tree the record kept, or (None, why) when there is none."""
    tree = rec.get('session_dir') or ''
    if not os.path.isdir(tree):
        return None, 'no kept tree'
    task_dir = os.path.join(root, 'tasks', rec['task'])
    with open(os.path.join(task_dir, 'task.json'), encoding='utf-8') as f:
        task = dict(json.load(f), dir=task_dir)
    work = tempfile.mkdtemp(prefix='regrade-')
    try:
        again = {'final': rec.get('final') or '', 'claim': rec.get('claim'), 'claim_reason': '', 'warnings': []}
        bench.grade(task, bench.copy_of(tree, work), dict(os.environ), again, [])
        return again['passed'], again.get('grade_tail') or ''
    finally:
        shutil.rmtree(work, True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', required=True)
    ap.add_argument('records', nargs='+')
    a = ap.parse_args(argv)
    differ = 0
    for path in a.records:
        with open(path, encoding='utf-8') as f:
            rec = json.load(f)
        passed, tail = regrade(rec, a.root)
        agree = passed is not None and passed == rec.get('passed')
        differ += passed is not None and not agree
        print(json.dumps(dict(task=rec['task'], arm=rec['arm'], repeat=rec.get('repeat'), recorded=rec.get('passed'),
                              regraded=passed, agree=agree, tail=tail[-300:])))
    print('%d record(s), %d where the two grades differ' % (len(a.records), differ))
    return 0


if __name__ == '__main__':
    sys.exit(main())
