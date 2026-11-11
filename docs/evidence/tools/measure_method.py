#!/usr/bin/env python3
"""Measure the POS build method from the repository's own history (mechanical; no LLM).

Weekly series on main: product vs test vs process work, merges, REQs merged, lead time, rework signals, decisions,
activity-log honesty, governance weight vs product size; plus a directive timeline and per-period comparison.
usage: measure_method.py <repo> <out.json>
"""
import collections
import datetime as dt
import json
import re
import subprocess
import sys

R = sys.argv[1]
OUT = sys.argv[2]


def git(*a, text=True):
    return subprocess.run(['git', '-C', R] + list(a), capture_output=True, text=text, check=False).stdout


def wk(d):
    d = d.date() if isinstance(d, dt.datetime) else d
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def cat(path):
    if path.startswith(('lib/', 'android/', 'ios/', 'web/', 'functions/', 'onboarding-agent/', 'admin-console/')):
        return 'product'
    if path.startswith(('test/', 'testcases/', 'integration_test/')):
        return 'test'
    if path.startswith(('docs/', '.claude/', 'scripts/', 'specs/', '.githooks/', '.cursor/', '.github/')) or \
            re.match(r'^[^/]+\.md$', path):
        return 'process'
    return 'other'


# ---- commits (all non-merge commits reachable from main) ----
log = git('log', 'main', '--no-merges', '--date=iso-strict', '--numstat', '--format=@@%H|%ad|%s')
commits, cur = [], None
for line in log.splitlines():
    if line.startswith('@@'):
        h, d, s = line[2:].split('|', 2)
        cur = {'h': h, 'd': dt.datetime.fromisoformat(d), 's': s, 'lines': collections.Counter()}
        commits.append(cur)
    elif line.strip() and cur is not None:
        parts = line.split('\t')
        if len(parts) == 3:
            a, b, p = parts
            n = (int(a) if a.isdigit() else 0) + (int(b) if b.isdigit() else 0)
            cur['lines'][cat(p)] += n

weekly = collections.defaultdict(lambda: collections.Counter())
for c in commits:
    w = wk(c['d'])
    tot = sum(c['lines'].values()) or 1
    kind = 'product' if c['lines']['product'] else ('test' if c['lines']['test'] and not c['lines']['process'] else
                                                     ('process' if c['lines']['process'] else 'other'))
    weekly[w]['commits'] += 1
    weekly[w]['commits_' + kind] += 1
    for k, v in c['lines'].items():
        weekly[w]['lines_' + k] += v
    s = c['s'].lower()
    if re.search(r'\brevert', s):
        weekly[w]['reverts'] += 1
    if re.search(r'\brework\b|\brevise\b|round \d+|re-cert', s):
        weekly[w]['rework_msgs'] += 1

# ---- merges on main (first parent) and lead time ----
merges = git('log', 'main', '--first-parent', '--merges', '--date=iso-strict', '--format=%H|%P|%ad|%s').splitlines()
merge_rows = []
for m in merges:
    h, parents, d, s = m.split('|', 3)
    ps = parents.split()
    if len(ps) < 2:
        continue
    base = git('merge-base', ps[0], ps[1]).strip()
    first = git('log', '--reverse', '--format=%ad', '--date=iso-strict', '%s..%s' % (base, ps[1])).splitlines()
    nbranch = len(first)
    md = dt.datetime.fromisoformat(d)
    lead_h = (md - dt.datetime.fromisoformat(first[0])).total_seconds() / 3600 if first else 0
    names = git('diff', '--name-only', base, ps[1]).splitlines()
    product = any(cat(n) == 'product' for n in names)
    reqs = sorted(set(re.findall(r'REQ-\d+', s, re.I))) if product else []
    merge_rows.append({'d': d, 'lead_h': round(lead_h, 1), 'branch_commits': nbranch, 'reqs': len(reqs),
                       'product': product, 'files': len(names)})  # counts only: commit subjects stay private
    w = wk(md)
    weekly[w]['merges'] += 1
    if product:
        weekly[w]['product_merges'] += 1
        weekly[w]['reqs_merged'] += len(reqs)

# ---- decisions and activity log ----
def dated_headings(path, pat):
    out = collections.Counter()
    try:
        txt = git('show', 'main:' + path)
    except Exception:
        return out
    for m in re.finditer(pat, txt, re.M):
        try:
            out[wk(dt.date.fromisoformat(m.group(1)))] += 1
        except ValueError:
            pass
    return out


for w, n in dated_headings('docs/product/pos-zero-defect/DECISIONS.md', r'^## (\d{4}-\d{2}-\d{2}) · D\d+').items():
    weekly[w]['decisions'] += n
act = git('show', 'main:docs/activity-log/ACTIVITY_LOG.md')
for blk in re.split(r'\n(?=## \d{4}-\d{2}-\d{2})', act):
    m = re.match(r'## (\d{4}-\d{2}-\d{2})', blk)
    if not m:
        continue
    w = wk(dt.date.fromisoformat(m.group(1)))
    weekly[w]['activity_entries'] += 1
    if re.search(r'not verified|NOT VERIFIED|NOT RUN|not run', blk):
        weekly[w]['activity_names_unverified'] += 1

# ---- weekly snapshots of governance weight vs product size ----
def snapshot(rev):
    def size(path):
        out = git('cat-file', '-s', '%s:%s' % (rev, path)).strip()
        return int(out) if out.isdigit() else 0
    tree = git('ls-tree', '-r', '-l', rev).splitlines()
    files = []
    for t in tree:
        parts = t.split(None, 4)
        if len(parts) == 5:
            sz, path = parts[3], parts[4]
            files.append((path, int(sz) if sz.isdigit() else 0))
    od = git('show', '%s:docs/product/OWNER_DIRECTIVES.md' % rev)
    dirs = set(re.findall(r'^\| (\d+) \|', od, re.M)) | set(re.findall(r'^## #(\d+)', od, re.M))
    les = git('show', '%s:.claude/agents/LESSONS.md' % rev)
    return {
        'claude_md_bytes': size('CLAUDE.md'),
        'directives': len(dirs),
        'lessons_live': len(re.findall(r'^\| L-\d+ \|', les, re.M)) + len(re.findall(r'^### L-\d+', les, re.M)),
        'agent_charter_bytes': sum(s for p, s in files if p.startswith('.claude/agents/') and p.endswith('.md')),
        'governance_scripts': sum(1 for p, _ in files if re.match(r'^scripts/(pipeline|verify|gates)/', p)),
        'governance_script_bytes': sum(s for p, s in files if re.match(r'^scripts/(pipeline|verify|gates)/', p)),
        'process_doc_bytes': sum(s for p, s in files if p.startswith(('docs/', '.claude/', 'specs/'))),
        'lib_dart_bytes': sum(s for p, s in files if p.startswith('lib/') and p.endswith('.dart')),
        'test_files': sum(1 for p, _ in files if p.endswith('_test.dart')),
        'integration_tests': sum(1 for p, _ in files if p.startswith('integration_test/') and p.endswith('.dart')),
        'mutation_batteries': sum(1 for p, _ in files if p.startswith('test/mutations/') and p.endswith('.yaml')),
    }


all_weeks = sorted(weekly)
snaps = {}
for w in all_weeks:
    end = (dt.date.fromisoformat(w) + dt.timedelta(days=7)).isoformat()
    rev = git('rev-list', '-1', '--before=' + end, 'main').strip()
    if rev:
        snaps[w] = snapshot(rev)

# ---- directive timeline ----
od = git('show', 'main:docs/product/OWNER_DIRECTIVES.md')
timeline = []
for m in re.finditer(r'^## #(\d+)[^\n]*?\((\d{4}-\d{2}-\d{2})\)', od, re.M):
    timeline.append((int(m.group(1)), m.group(2)))
for m in re.finditer(r'^\| (\d+) \| ([^|]*)', od, re.M):
    d = re.search(r'(\d{4}-\d{2}-\d{2})', m.group(2))
    if d:
        timeline.append((int(m.group(1)), d.group(1)))
timeline = sorted(set(timeline))
first_claude = git('log', '--reverse', '--format=%ad', '--date=short', 'main', '--', 'CLAUDE.md').splitlines()
first_claude = first_claude[0] if first_claude else None

# ---- periods ----
PERIODS = [
    ('P0 pre-CLAUDE.md', '2025-08-01', first_claude or '2026-08-01'),
    ('P1 CLAUDE.md, before pods/directives', first_claude or '2026-08-01', '2026-09-04'),
    ('P2 pods + directives #23-#44', '2026-09-04', '2026-09-08'),
    ('P3 #45-#50 invariant batching, measure, 3-min steps, legs-as-code, scripts', '2026-09-08', '2026-09-29'),
    ('P4 #51-#60 decision judge, judged swarm', '2026-09-29', '2026-10-07'),
    ('P5 #61-#67 outcome-first, step caps, simulation, local CI', '2026-10-07', '2026-11-12'),
]


def period_of(w):
    for name, a, b in PERIODS:
        if a <= w < b:
            return name
    return None


per = collections.OrderedDict((p[0], collections.Counter()) for p in PERIODS)
nweeks = collections.Counter()
for w in all_weeks:
    p = period_of(w)
    if not p:
        continue
    nweeks[p] += 1
    per[p].update(weekly[w])
leads = collections.defaultdict(list)
for r in merge_rows:
    p = period_of(wk(dt.datetime.fromisoformat(r['d'])))
    if p and r['product']:
        leads[p].append(r['lead_h'])


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def p90(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * 0.9))] if xs else None


period_summary = {}
for name, c in per.items():
    n = max(nweeks[name], 1)
    commits_ = c['commits'] or 1
    period_summary[name] = {
        'weeks': nweeks[name],
        'commits_per_week': round(c['commits'] / n, 1),
        'product_commit_share': round(c['commits_product'] / commits_, 2),
        'process_only_commit_share': round(c['commits_process'] / commits_, 2),
        'product_lines_per_week': round(c['lines_product'] / n),
        'test_lines_per_week': round(c['lines_test'] / n),
        'process_lines_per_week': round(c['lines_process'] / n),
        'process_to_product_line_ratio': round(c['lines_process'] / max(c['lines_product'], 1), 2),
        'merges_per_week_all': round(c['merges'] / n, 1),
        'product_merges_per_week': round(c['product_merges'] / n, 1),
        'reqs_in_product_merge_subjects_per_week': round(c['reqs_merged'] / n, 1),
        'product_merge_lead_hours_median': med(leads[name]),
        'product_merge_lead_hours_p90': p90(leads[name]),
        'test_to_product_line_ratio': round(c['lines_test'] / max(c['lines_product'], 1), 2),
        'reverts_per_week': round(c['reverts'] / n, 2),
        'rework_msgs_per_week': round(c['rework_msgs'] / n, 1),
        'decisions_per_week': round(c['decisions'] / n, 1),
        'activity_entries_per_week': round(c['activity_entries'] / n, 1),
        'activity_unverified_named_share': round(c['activity_names_unverified'] / max(c['activity_entries'], 1), 2),
    }

restate = []
for m in re.finditer(r'(?ms)^(?:\| (\d+) \||## #(\d+))(.*?)(?=^\| \d+ \||^## |\Z)', od):
    n, body = m.group(1) or m.group(2), m.group(3)
    hits = re.findall(r'not (?:at all )?followed|again and again|same thing again|fourth|third time|reaffirmed|'
                      r'ignored|violated|still not|was not followed|never followed|stated (?:three|four|twice)', body, re.I)
    if hits:
        restate.append({'directive': int(n), 'markers': sorted(set(h.lower() for h in hits))})
json.dump({'restated_directives': restate, 'first_claude_md': first_claude, 'commits_total': len(commits), 'merges_total': len(merge_rows),
           'periods': PERIODS, 'period_summary': period_summary,
           'weekly': {w: dict(weekly[w]) for w in all_weeks}, 'snapshots': snaps,
           'directive_timeline': timeline, 'merges': merge_rows}, open(OUT, 'w'), indent=1, default=str)
print('directives carrying restatement/violation markers:', len(restate), [r['directive'] for r in restate])
print('first CLAUDE.md commit:', first_claude, '| commits:', len(commits), '| merges on main:', len(merge_rows))
for name, s in period_summary.items():
    print('\n' + name)
    for k, v in s.items():
        print('  %-32s %s' % (k, v))
