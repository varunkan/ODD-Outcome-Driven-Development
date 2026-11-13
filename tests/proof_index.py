"""Writes docs/PROOF.md: every claim odd makes, and the tests that prove it, read from tests/test_odd.py.

Run:   python3 tests/proof_index.py           (rewrite docs/PROOF.md)
       python3 tests/proof_index.py --check   (exit 1 if docs/PROOF.md is out of date; CI runs this)

Every test class must belong to exactly one theme below, so a new test cannot be left out of the page.
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SOURCE = os.path.join(HERE, 'test_odd.py')
PAGE = os.path.join(ROOT, 'docs', 'PROOF.md')
HELPERS = {'Repo', 'Agents', 'ProofAuthors'}  # base classes and mixins: no tests of their own

THEMES = [
    ('A false "done" is refused',
     'Each test is a way an agent could report done without the outcome holding; each must end non-zero.',
     ['Attacks', 'RedTeam', 'FailClosed', 'InPlaceCheck', 'GitShapes', 'Files', 'MaskedPipe', 'TextualProof', 'Flaky',
      'SealedProof', 'ReproduceFirst', 'HeldOut', 'SameBehaviour', 'Successive']),
    ('CI cannot be talked out of it',
     'In CI the tool, its settings and the base come from the target branch, and nothing recorded is trusted.',
     ['HappyPath', 'Exemptions', 'Checks', 'RegressionGuard', 'Distribution', 'ReviewSummary']),
    ('Honest about the real system',
     'A proof says what it ran against, steps owed on a device or by a person keep work open, and a release is bound '
     'to the gated commit.',
     ['Target', 'Owed', 'Ship', 'EscapedDefects']),
    ('More correct work, not only checked work',
     'Aids that catch weak proofs, missing requirements, wrong proofs and leftovers before review.',
     ['ProofStrength', 'Coverage', 'AmbiguityStop', 'KindTemplates', 'FailureFeedback', 'AttemptFeedback', 'InertFiles',
      'InertHunks', 'LookAlikes', 'Challenge', 'Disputes', 'Spec', 'Plan', 'Reasoning', 'Duplication', 'FinishTurn', 'PreFlight']),
    ('Cheaper and faster',
     'Cheap models first, parallel attempts, no repeated work, no waiting, and a budget that stops spending.',
     ['Race', 'Cascade', 'Chain', 'Isolation', 'VerifyCache', 'AffectedGuards', 'RaceCache', 'StopWhenProven',
      'AttemptBudget', 'CostPerOutcome', 'Background', 'BoundaryContext', 'BoundaryPrompt']),
    ('Fits the way people already work',
     'One file, standard library only, the method in AGENTS.md, an MCP server, Claude Code hooks, an auto-merge lane '
     'a repository may opt into, and trends over time.',
     ['Setup', 'Adoption', 'ClaudeHooks', 'AutoLane', 'ProofQualityTrends']),
]

RESULTS = '''## What the measurements show

Measured on the comparison harness ([bench/](../bench/SPEC.md)): 16 tasks with hidden acceptance tests, three
repeats per arm, every reason read by a person. Full write-ups: [15](evidence/15-comparison.md) and
[16](evidence/16-new-arms.md).

| claim | measured | where |
|---|---|---|
| odd's own check agrees with hidden tests | on Sonnet, it never passed work the hidden tests failed (48 runs) | [15](evidence/15-comparison.md) |
| it costs little to leave on | about 1 to 3 cents a task more than plain Claude Code; Spec Kit and BMAD cost 2 to 5 times plain | [15](evidence/15-comparison.md) |
| it lowers false "done" | cascade and race: 0 false DONE in 48 runs each, plain Haiku 2; honest NOT DONE on contradictions 6 of 6 against 4 of 6 (a hint: six runs) | [16](evidence/16-new-arms.md#with-disputed-proofs) |
| a cheap model can match a strong one's honesty | cascade (Haiku, then Sonnet when needed): 41 of 42 doable tasks, no false DONE, at about a quarter of plain Sonnet's cost; plain Haiku delivered all 42 on these tasks | [16](evidence/16-new-arms.md#with-disputed-proofs) |
| a wrong proof no longer blocks correct work | in 18 runs a disputed proof went back to its author: 17 then delivered, none claimed DONE falsely | [16](evidence/16-new-arms.md#with-disputed-proofs) |
| running the method found real defects | the gate refused correct work proven in steps (34 runs), fixed and shown on agents: refused correct work 11-13 per arm, then 0 | [16](evidence/16-new-arms.md) |
| holds for any model by construction | a proof that fails without the change means the same whichever model wrote the code; the measured gains above are Claude's | [THE-RULE](../THE-RULE.md) |
| not shown yet | more correct work on real repositories where plain agents fail | [BACKLOG](../BACKLOG.md) item 18 |
'''


def human(name):
    return name[len('test_'):].replace('_', ' ')


def classes():
    tree = ast.parse(open(SOURCE, encoding='utf-8').read())
    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name not in HELPERS:
            tests = [f.name for f in node.body if isinstance(f, ast.FunctionDef) and f.name.startswith('test_')]
            if tests:
                doc = ' '.join((ast.get_docstring(node) or '').split())
                out.append((node.name, doc, tests))
    return out


def render():
    found = {name: (doc, tests) for name, doc, tests in classes()}
    placed = [c for _, _, members in THEMES for c in members]
    missing = sorted(set(found) - set(placed))
    unknown = sorted(set(placed) - set(found))
    twice = sorted({c for c in placed if placed.count(c) > 1})
    if missing or unknown or twice:
        sys.exit('tests/proof_index.py: put every test class in exactly one theme. Missing: %s; not a test class: %s; '
                 'in two themes: %s' % (', '.join(missing) or '-', ', '.join(unknown) or '-', ', '.join(twice) or '-'))
    total = sum(len(t) for _, t in found.values())
    md = ['# Proof: what odd claims, and the tests that show it', '',
          '> **The rule:** nothing counts as done until a check that runs says so: a check that fails without the change, '
          'run by someone other than the one claiming it ([THE-RULE.md](../THE-RULE.md)).', '',
          '*Generated by `python3 tests/proof_index.py` from [tests/test_odd.py](../tests/test_odd.py); CI fails when '
          'this page is out of date. %d tests in %d groups, run on Linux (Python 3.8 and 3.13) and macOS on every push '
          '(`python3 -m unittest discover -s tests`).*' % (total, len(found)), '', RESULTS,
          '## The tests, by what they prove', '']
    md += ['| theme | test groups | tests |', '|---|---|---|']
    for title, _, members in THEMES:
        md.append('| [%s](#%s) | %d | %d |' % (title, anchor(title), len(members), sum(len(found[c][1]) for c in members)))
    for title, why, members in THEMES:
        md += ['', '### %s' % title, '', why]
        for c in members:
            doc, tests = found[c]
            md += ['', '**%s** (%d) %s' % (c, len(tests), doc)]
            md += ['- %s' % human(t) for t in tests]
    return '\n'.join(md) + '\n'


def anchor(title):
    return ''.join(ch for ch in title.lower().replace(' ', '-') if ch.isalnum() or ch == '-')


def main(argv):
    text = render()
    if '--check' in argv:
        current = open(PAGE, encoding='utf-8').read() if os.path.exists(PAGE) else ''
        if current != text:
            sys.exit('docs/PROOF.md is out of date: run python3 tests/proof_index.py and commit it')
        print('docs/PROOF.md is up to date')
        return
    with open(PAGE, 'w', encoding='utf-8') as f:
        f.write(text)
    print('wrote docs/PROOF.md')


if __name__ == '__main__':
    main(sys.argv[1:])
