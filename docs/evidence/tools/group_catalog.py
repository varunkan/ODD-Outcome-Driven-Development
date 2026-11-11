#!/usr/bin/env python3
"""Group the raw instruction catalog (workflow journal) into the owner's method areas, mechanically.

usage: group_catalog.py <journal.jsonl> <outdir>
Writes <outdir>/<area>.json (items, exact-duplicate instructions merged with all sources kept) and prints counts.
"""
import collections
import json
import os
import re
import sys

AREAS = {
    'frugality': {'tokens-efficiency'},
    'project-management': {'orchestration', 'plan', 'tasks'},
    'outcome-driven': {'outcome', 'requirements', 'spec', 'research'},
    'verification': {'verify', 'implement'},
    'decisions-learning': {'judge-decide', 'self-heal', 'meta', 'reporting'},
    'safety': {'git-safety'},
}
STAGE_TO_AREA = {s: a for a, ss in AREAS.items() for s in ss}

journal, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
items = []
for line in open(journal):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    r = e.get('result')
    if e.get('type') == 'result' and isinstance(r, dict) and isinstance(r.get('items'), list):
        items += r['items']

groups = collections.defaultdict(dict)
for it in items:
    area = STAGE_TO_AREA.get(it.get('stage'), 'decisions-learning')
    key = re.sub(r'\W+', ' ', (it.get('instruction') or '').lower()).strip()[:160]
    if not key:
        continue
    g = groups[area]
    if key in g:
        g[key]['sources'].append(it.get('source', ''))
        if len(it.get('outcome', '')) > len(g[key]['outcome']):
            g[key]['outcome'] = it.get('outcome', '')
    else:
        g[key] = {'instruction': it.get('instruction', ''), 'outcome': it.get('outcome', ''),
                  'owner_words': it.get('owner_words', ''), 'enforcement': it.get('enforcement', ''),
                  'performance': it.get('performance', ''), 'generalizable': it.get('generalizable', True),
                  'stage': it.get('stage', ''), 'sources': [it.get('source', '')]}
total = 0
for area, g in sorted(groups.items()):
    rows = list(g.values())
    total += len(rows)
    json.dump(rows, open(os.path.join(out, area + '.json'), 'w'), indent=1)
    perf = collections.Counter(r['performance'] for r in rows)
    print('%-20s %4d items  %s' % (area, len(rows), dict(perf)))
print('raw items: %d, after exact-duplicate merge: %d' % (len(items), total))
