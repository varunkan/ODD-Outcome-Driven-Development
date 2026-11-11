#!/usr/bin/env python3
"""Render the evidence data (data/*.json) into the readable documents of this directory. Mechanical: no model.

usage: render_evidence.py            (run from anywhere; paths resolve from this file)
Reads  ../data/research/*.json, ../data/catalog/*.json, ../data/validation/*.json
Writes ../02-pos-evidence-ledger.md, ../03-instruction-catalog.md, ../04-spec-kit-bmad-superpowers.md,
       ../05-practice-and-model-trends.md, ../06-first-draft-audit.md, ../07-validation-and-verdict.md,
       ../08-refined-method.md, ../09-rulings.md, ../10-design-review.md
(01-method-measured.md is written by hand from tools/measure_method.py output; README.md and ../../WHY.md by hand.)
"""
import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.dirname(HERE)
DATA = os.path.join(EV, 'data')
HOW = ('*Produced 2026-11-11 by a read-only research agent (Claude Fable 5.2); rendered from `%s` by '
       '`tools/render_evidence.py`. Agent-written: every figure carries its source, and the "Not verified" list says '
       'what the agent could not confirm.*')


def load(*p):
    with open(os.path.join(DATA, *p), encoding='utf-8') as f:
        return json.load(f)


def bullets(items):
    return '\n'.join('- ' + str(x).strip().replace('\n', '\n  ') for x in items) or '- (none)'


def research_section(r, lessons_title):
    out = ['## %s' % r['subject'], '', '### What it is', '', r['what_it_is'].strip(), '',
           '### Core principles', '', bullets(r['core_principles']), '',
           '### How it enforces its process', '', r['enforcement'].strip(), '',
           '### Strengths', '', bullets(r['strengths']), '',
           '### Weaknesses and documented criticisms', '', bullets(r['weaknesses']), '',
           '### Evidence of effectiveness', '', r['evidence_of_effectiveness'].strip(), '',
           '### %s' % lessons_title, '', bullets(r['lessons_for_odd']), '',
           '### Sources', '', bullets('[%s](%s)' % (s.get('title') or s['url'], s['url']) for s in r['sources']), '']
    if r.get('unverified'):
        out += ['### Not verified', '', bullets(r['unverified']), '']
    return '\n'.join(out)


def write(name, text):
    with open(os.path.join(EV, name), 'w', encoding='utf-8') as f:
        f.write(text.rstrip() + '\n')
    print('%-36s %6.1f KB' % (name, len(text.encode()) / 1024))


# 02 - POS evidence ledger
p = load('research', 'pos.json')
t = ['# What paid and what was waste: the POS evidence ledger', '', HOW % 'data/research/pos.json', '',
     'Scope: only numbers recorded in the POS repository itself (directives, history, decisions, activity log, git). '
     'Citations are paths in that repository.', '',
     '## Honest assessment', '', p['honest_assessment'].strip(), '',
     '## The few rules that mattered most', '', bullets(p['the_few_rules_that_mattered_most']), '',
     '## What paid', '']
for x in p['paid']:
    t += ['### ' + x['method'], '', '- Magnitude: ' + (x.get('magnitude') or 'not measured'),
          '- Evidence: ' + x['evidence'].strip().replace('\n', '\n  '), '- Source: ' + x['source'], '']
t += ['## What was waste', '']
for x in p['waste']:
    t += ['### ' + x['method'], '', '- Evidence: ' + x['evidence'].strip().replace('\n', '\n  '),
          '- Source: ' + x['source'], '']
t += ['## What the process itself cost', '', p['process_cost'].strip(), '',
      '## Throughput', '', (p.get('throughput') or 'not derived').strip(), '']
write('02-pos-evidence-ledger.md', '\n'.join(t))

# 03 - instruction catalog
AREAS = [('frugality', 'Frugality (tokens and cost)'), ('project-management', 'Project management and orchestration'),
         ('outcome-driven', 'Outcome-driven work (research, requirements, outcome, spec)'),
         ('verification', 'Verification and implementation'),
         ('decisions-learning', 'Decisions, judging, learning and reporting'), ('safety', 'Safety and git hygiene')]
PERF = [('proven-paid', 'proven to pay (recorded before/after)'), ('incident-earned', 'earned from an incident'),
        ('mandated-unmeasured', 'mandated, never measured'), ('proven-failed-reverted', 'proven to fail, reverted')]
cat = {a: load('catalog', a + '.json') for a, _ in AREAS}
tot = collections.Counter(r['performance'] for rows in cat.values() for r in rows)
n = sum(tot.values())
t = ['# The instruction catalog: every instruction given while building the POS, with its outcome', '',
     '*Produced 2026-11-11 by twelve read-only agents over CLAUDE.md and its history, the 68 owner directives, the '
     'lessons ledger, the role charters, skills, workflows, decision rulings and scripts; exact duplicates merged and '
     'grouped by `tools/group_catalog.py`. The performance tag is the reading agent\'s classification from the outcome '
     'recorded beside each instruction; the validation rulings re-examine every one.*', '',
     'Full data, one JSON file per area (id, instruction, outcome, owner\'s words where recorded, enforcement point, '
     'sources): `data/catalog/`.', '',
     '## Counts', '', '| area | instructions | ' + ' | '.join(lbl for _, lbl in PERF) + ' |', '|---|---|' + '---|' * len(PERF)]
for a, lbl in AREAS:
    c = collections.Counter(r['performance'] for r in cat[a])
    t.append('| %s | %d | %s |' % (lbl, len(cat[a]), ' | '.join(str(c[k]) for k, _ in PERF)))
t += ['| **all** | **%d** | %s |' % (n, ' | '.join('**%d** (%.1f%%)' % (tot[k], 100.0 * tot[k] / n) for k, _ in PERF)), '']
for key, title in (('proven-paid', 'Instructions proven to pay'), ('proven-failed-reverted', 'Instructions proven to fail and reverted')):
    t += ['## %s (%d)' % (title, tot[key]), '']
    for a, lbl in AREAS:
        rows = [r for r in cat[a] if r['performance'] == key]
        if not rows:
            continue
        t += ['### %s (%d)' % (lbl, len(rows)), '']
        for r in rows:
            t += ['**%s** %s' % (r['id'], r['instruction'].strip()), '',
                  '- Outcome: ' + (r.get('outcome') or '').strip().replace('\n', ' '),
                  '- Enforced by: ' + ((r.get('enforcement') or 'none').strip().replace('\n', ' ')),
                  '- Source: ' + '; '.join(s for s in r.get('sources', []) if s), '']
write('03-instruction-catalog.md', '\n'.join(t))

# 04 - frameworks
t = ['# Spec Kit, BMAD and Superpowers: what they are, how they enforce, what the evidence says', '',
     HOW % 'data/research/{speckit,bmad,superpowers}.json', '']
for k in ('speckit', 'bmad', 'superpowers'):
    t += [research_section(load('research', k + '.json'), 'Lessons for an outcome-driven toolkit'), '']
write('04-spec-kit-bmad-superpowers.md', '\n'.join(t))

# 05 - practice and model trends
t = ['# Software-development practice and model trends: the outside evidence', '',
     HOW % 'data/research/{practices,models}.json', '']
for k in ('practices', 'models'):
    t += [research_section(load('research', k + '.json'), 'Design rules that follow'), '']
write('05-practice-and-model-trends.md', '\n'.join(t))

# 06 - audit of the first draft
a = load('research', 'audit.json')
t = ['# Audit of the first draft toolkit', '',
     '*Produced 2026-11-11 by a read-only review agent (Claude Fable 5.2) against the draft at commit 23069f8b6 '
     '(engine, hooks, entry skill, templates); rendered from `data/research/audit.json`. It is kept because it is the '
     'reason the design changes: the next version is judged against this list.*', '',
     '## Verdict', '', a['verdict'].strip(), '', '## Test results', '', a['test_results'].strip(), '',
     '## Size', '', a['size'].strip(), '', '## Essential', '', bullets(a['essential']), '',
     '## Over-engineered', '', bullets(a['over_engineered']), '', '## Failure modes in real use', '',
     bullets(a['failure_modes']), '', '## Missing', '', bullets(a['missing']), '']
write('06-first-draft-audit.md', '\n'.join(t))


# 07 - validation rulings and verdict; 08 - the refined method; 09 - the rulings, cluster by cluster
def vload(name):
    return load('validation', name + '.json')


VAL_HOW = ('*Produced 2026-11-11 by a 31-agent run on Claude Fable 5.2: 15 validators ruled on every catalog item, a '
           'consolidator and a skeptic per area re-examined the rulings, then one agent each composed the method, the '
           'comparison, three independent critiques and the decision. Rendered from `data/validation/` by '
           '`tools/render_evidence.py`. The decision agent re-read only the draft audit; other figures are quoted from '
           'the earlier documents and were not re-checked in that step.*')
stats, final, crits, cmp_, method, areas = (vload(n) for n in ('stats', 'final', 'critiques', 'compare', 'method', 'areas'))
tot = {k: sum(s[k] for s in stats) for k in ('clusters', 'keep', 'refine', 'merge', 'drop', 'overturned', 'unruled_ids')}
L = final['lean_design']
t = ['# Validation, comparison and verdict', '', VAL_HOW, '',
     '## Decision: %s (confidence %.2f)' % (final['decision'], final['confidence']), '', final['why'].strip(), '',
     '## What the validation found', '', final['validation_summary'].strip(), '',
     '## Rulings on the 1,856 instructions', '',
     '| area | rule clusters | keep | refine | merged as duplicate | drop | overturned by the skeptic | instructions left unruled |',
     '|---|---|---|---|---|---|---|---|']
for s in stats:
    t.append('| %s | %d | %d | %d | %d | %d | %d | %d |' % (s['area'], s['clusters'], s['keep'], s['refine'], s['merge'],
                                                          s['drop'], s['overturned'], s['unruled_ids']))
t += ['| **all** | **%(clusters)d** | **%(keep)d** | **%(refine)d** | **%(merge)d** | **%(drop)d** | **%(overturned)d** | **%(unruled_ids)d** |' % tot,
      '', 'Every cluster, with its verdict, evidence and the instruction ids it covers: [09](09-rulings.md) and '
      '`data/validation/areas.json`. The method built from the surviving rules: [08](08-refined-method.md).', '',
      '## Compared with Claude Code alone, Spec Kit, BMAD and Superpowers', '', cmp_['table_markdown'].strip(), '',
      '### Where the refined method is ahead', '', bullets(cmp_['where_refined_wins']), '',
      '### Where the others are ahead', '', bullets(cmp_['where_others_win']), '',
      '### What to borrow from them', '', bullets(cmp_['what_to_borrow']), '',
      '### Overlap', '', cmp_['overlap'].strip(), '',
      '## The three critiques', '']
for c in crits:
    t += ['### %s: adds value "%s" (confidence %.2f)' % (c['lens'].capitalize(), c['adds_value'], c['confidence']), '',
          '**On the way of working.** ' + c['on_owner_method'].strip(), '',
          '**Is it good for others to learn?** ' + c['good_for_others'].strip(), '',
          '**Reasoning.** ' + c['rationale'].strip(), '',
          '**Must cut**', '', bullets(c['must_cut']), '', '**Must add**', '', bullets(c['must_add']), '',
          '**Risks**', '', bullets(c['risks']), '']
t += ['## The lean design the decision calls for', '', L['one_line'].strip(), '',
      '### Skills', '', bullets('`%s`: %s' % (s['name'], s['purpose']) for s in L['skills']), '',
      '### Engine', '', bullets(L['engine']), '', '### Hooks', '', bullets(L['hooks']), '',
      '### Cut from the first draft', '', bullets(L['cut_from_draft']), '',
      '### Defects to fix from the first draft', '', bullets(L['fix_in_draft']), '',
      '### How the toolkit measures its own value', '', L['measurement_plan'].strip(), '',
      '### Rules for staying useful as models improve', '', bullets(L['future_model_rules']), '',
      '## Questions left for the owner', '', bullets(final['open_questions_for_owner']), '']
write('07-validation-and-verdict.md', '\n'.join(t))

t = [method['method_markdown'].strip(), '', '---', '',
     '*This is the method as refined by the validation (see [07](07-validation-and-verdict.md)); the decision there '
     'is to teach about seven of these principles and keep the rest as reference. Each principle below traces to the '
     'rule clusters in [09](09-rulings.md).*', '',
     '## Trace: principle to rule clusters', '', '| principle | durability | carried by | rule clusters |', '|---|---|---|---|']
for p in method['principles']:
    t.append('| %s | %s | %s | %s |' % (p['id'], p['durability'], p['mechanism'].replace('\n', ' ').replace('|', '/')[:140],
                                        ', '.join(p['traces'])))
t += ['', '## What the method should add (from the research)', '', bullets(method['additions']), '',
      '## Classes of instruction that were dropped', '', bullets(method['dropped_classes']), '']
write('08-refined-method.md', '\n'.join(t))

t = ['# The rulings: every rule cluster, its verdict and its evidence', '', VAL_HOW, '',
     'Verdicts: KEEP (evidence it paid, or a cheap rule against a recorded incident class), REFINE (sound core, '
     'rewritten lean), MERGE (duplicate of another cluster), DROP (waste, ceremony, unmeasured with no incident, '
     'project-only, or contradicted by evidence). "Instructions" counts the catalog items the cluster covers; their ids '
     'are in `data/validation/areas.json` and resolve in `data/catalog/`.', '']
for a in areas:
    t += ['## %s' % a['area'], '', '| rule | verdict | refined rule | evidence grade | durability | enforce as | instructions |',
          '|---|---|---|---|---|---|---|']
    for c in a['clusters']:
        v = c['verdict'] + ((' into ' + c['merge_into']) if c['verdict'] == 'MERGE' and c.get('merge_into') else '')
        t.append('| %s | %s | %s | %s | %s | %s | %d |' % (c['rule_id'], v, c['refined_rule'].replace('\n', ' ').replace('|', '/'),
                                                          c['evidence_grade'], c['durability'], c['enforce_as'], len(c['source_ids'])))
    drops = [c for c in a['clusters'] if c['verdict'] == 'DROP']
    if drops:
        t += ['', '### Dropped, and why', '']
        for c in drops:
            t += ['- **%s** %s Evidence: %s Why: %s' % (c['rule_id'], c['refined_rule'].strip(), c['evidence'].strip().replace('\n', ' '),
                                                       c['why'].strip().replace('\n', ' '))]
    if a.get('overturned'):
        t += ['', '### First-pass rulings the skeptic overturned', '', bullets(a['overturned'])]
    t.append('')
write('09-rulings.md', '\n'.join(t))


# 10 - the design review of the lean, portable tool
dr = load('design-review.json')
r = dr['ruling']
t = ['# Design review of the lean, portable tool', '',
     '*Produced 2026-11-11 by four independent critics (Claude Fable 5.2) attacking the first design and the first '
     'version of the tool: tamper resistance, the correctness of the take-out check, day-to-day friction, and how each '
     'coding tool actually reads instruction files (checked against the tools\' own documentation). One judge then '
     'ruled which changes were required. Rendered from `data/design-review.json`. Several critics ran probes; those '
     'findings say "measured". DESIGN.md version 2 and the current tool implement the ruling.*', '',
     '## Ruling: %s' % r['verdict'], '', '### Required changes (%d)' % len(r['required_changes']), '']
for n, c in enumerate(r['required_changes'], 1):
    t += ['%d. %s' % (n, c['change'].strip()), '', '   Why: ' + c['why'].strip() + ((' (from: %s)' % c['from']) if c.get('from') else ''), '']
t += ['### The command list', '', bullets(r['final_command_list']), '', '### What ships for each tool in this version', '',
      bullets(r['adapter_set_v1']), '', '### Limits to state plainly instead of engineering around', '', bullets(r['stated_limits']), '',
      '### Suggestions not adopted, and why', '', bullets(r['rejected_suggestions']), '', '## The four critiques', '']
for c in dr['critics']:
    t += ['### %s (%d findings)' % (c['lens'].capitalize(), len(c['findings'])), '']
    for f in c['findings']:
        t += ['- **[%s] %s.** %s *Fix:* %s' % (f['severity'], f['section'].strip().rstrip('.'), f['scenario'].strip().replace('\n', ' '),
                                              f['fix'].strip().replace('\n', ' '))]
    t += ['', '**Keep:** ' + ' '.join('(%d) %s' % (i, k) for i, k in enumerate(c['keep'], 1)), '']
    if c.get('verified_facts'):
        t += ['**Facts checked, with sources:**', '', bullets(c['verified_facts']), '']
write('10-design-review.md', '\n'.join(t))
