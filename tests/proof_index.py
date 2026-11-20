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
      'SealedProof', 'ReproduceFirst', 'HeldOut', 'SameBehaviour', 'Successive', 'EntryPoint', 'Anchored', 'RejectStable', 'Hostile', 'Check']),
    ('CI cannot be talked out of it',
     'In CI the tool, its settings and the base come from the target branch, and nothing recorded is trusted.',
     ['HappyPath', 'Exemptions', 'Checks', 'RegressionGuard', 'Distribution', 'ReviewSummary']),
    ('Honest about the real system',
     'The claim is generated from the checks that ran and states what is not proven; a proof says what it ran against, '
     'steps owed on a device or by a person keep work open, and a release is bound to the gated commit.',
     ['Claim', 'ReportClaim', 'Target', 'Owed', 'Ship', 'EscapedDefects']),
    ('More correct work, not only checked work',
     'Aids that catch weak proofs, missing requirements, wrong proofs and leftovers before review.',
     ['ProofStrength', 'Coverage', 'AmbiguityStop', 'KindTemplates', 'FailureFeedback', 'AttemptFeedback', 'InertFiles',
      'InertHunks', 'LookAlikes', 'Challenge', 'Disputes', 'Probe', 'Apart', 'Second', 'Reread', 'CopiedLiterals', 'Cases', 'Spec', 'Plan', 'Reasoning', 'Duplication', 'FinishTurn', 'PreFlight']),
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
repeats per arm, every reason read by a person; then ten real sympy issues. Full write-ups: [15](evidence/15-comparison.md),
[16](evidence/16-new-arms.md) and [18](evidence/18-real-repositories.md).

| claim | measured | where |
|---|---|---|
| odd's own check agrees with hidden tests | on Sonnet, it never passed work the hidden tests failed (48 synthetic runs); on real sympy issues it passed 5 runs the hidden tests failed, each where the proof encoded less than the hidden test asked | [15](evidence/15-comparison.md), [18](evidence/18-real-repositories.md) |
| it costs little to leave on | about 1 to 3 cents a task more than plain Claude Code; Spec Kit and BMAD cost 2 to 5 times plain | [15](evidence/15-comparison.md) |
| it lowers false "done" | cascade and race: 0 false DONE in 48 runs each, plain Haiku 2; honest NOT DONE on contradictions 6 of 6 against 4 of 6 (a hint: six runs) | [16](evidence/16-new-arms.md#with-disputed-proofs) |
| a cheap model can match a strong one's honesty | cascade (Haiku, then Sonnet when needed): 41 of 42 doable tasks, no false DONE, at about a quarter of plain Sonnet's cost; plain Haiku delivered all 42 on these tasks | [16](evidence/16-new-arms.md#with-disputed-proofs) |
| a wrong proof no longer blocks correct work | in 18 runs a disputed proof went back to its author: 17 then delivered, none claimed DONE falsely | [16](evidence/16-new-arms.md#with-disputed-proofs) |
| running the method found real defects | the gate refused correct work proven in steps (34 runs), fixed and shown on agents: refused correct work 11-13 per arm, then 0 | [16](evidence/16-new-arms.md) |
| holds for any model by construction | a proof that fails without the change means the same whichever model wrote the code; the measured gains above are Claude's | [THE-RULE](../THE-RULE.md) |
| a head-to-head with Spec Kit on one task | building a calculator with Haiku 4.5, three runs each. Nobody answering: odd delivered 3 of 3 for $0.68, Spec Kit 1 of 3, and a blind judge chose odd. With Spec Kit told to continue: both 3 of 3, and a blind judge chose Spec Kit narrowly, because each odd calculator had a defect of its own on inputs no test covered; odd cost $0.68 against $2.65. One task, a hint | [19](evidence/19-calculator-head-to-head.md) |
| better than a plain agent | **only where the plain agent is told nothing about tests**: on the calculator a plain agent said DONE falsely in 2 of 3 runs and odd in 0 of 9; a plain agent told in one sentence to write and run tests also made none in 3, at 60% of lean odd's cost. On a second task all three deliver the same and odd costs more. Three runs an arm, hints | [19](evidence/19-calculator-head-to-head.md), [20](evidence/20-a-second-task.md), [21](evidence/21-is-the-core-worth-more-than-a-sentence.md) |
| better than a plain agent told to write tests, on real bug fixes | **not tested**: twelve pairs on real pytest, sphinx, sympy and pylint issues, one run each. The plain agent made 2 false DONE and lean odd 1, too few to test. Counts only: hidden tests pass 5 of 12 against 9 of 12 (lean odd ahead on 4 tasks, behind on none), at $4.51 against $4.81. odd's take-out check would have refused 1 of the 2 false DONE | [22](evidence/22-real-bug-fixes.md) |
| passes hidden tests more often than that plain agent, on real bug fixes | **not confirmed**: twelve new pairs, fixed beforehand. Lean odd passed on 9 of 12 and the plain agent on 7 of 12; ahead on 2 tasks, behind on none, where 5 were needed. False DONE 3 against 0 (too few to test); the take-out check would have refused 2 of the 3. $4.71 against $4.27 | [23](evidence/23-real-bug-fixes-pass-rate.md) |
| the take-out check with no setup (`odd check`) finds wrong work | **seen, not tested**, at no cost: replayed on 48 kept real bug-fix runs and 33 small-task runs, no correct fix reads as tests that pass anyway or as no change. The fault it was built for appears once. Three of the plain agent's five false DONE changed only tests and no product file, which it names; the other two it cannot see. Report only | [24](evidence/24-the-check-with-no-setup.md) |
| the six real bug fixes lean odd fails close with more money or a stronger model | **no sign by the rule fixed beforehand**, 17 runs for $7.18. The unchanged arm, rerun, passed 2 of the 6: one run a task was too thin. Twice the money passed 2 of 5 and bought 2 wrong DONE. A stronger model passed 6 of 6 for less, mostly without needing odd's check: a result about the model | [25](evidence/25-the-six-that-fail.md) |
| a reading of the ticket made apart from a fix catches a fix that is wrong the same way as its tests | **seen with no model, not tested with the command**: on 65 kept attempts at 24 real bug fixes, another attempt's tests fail on 22 of 24 wrong fixes and on 11 of 33 right ones; of 56 disagreements 52 have a wrong side; 18 of 57 agreements are two wrong attempts. `odd reread` is advisory | [26](evidence/26-a-second-reading.md) |
| a check tuned on one task holds on the next | **no**: the reject rule gave 74 true and 0 false alarms on the calculator and 0 true and 81 false on the second task; it is report only now, and a check may fail work only by the admission rule | [20](evidence/20-a-second-task.md) |
| more correct work on real repositories | **not shown**: ten sympy issues, 90 runs: cascade 24 of 30, plain Haiku 25, plain Sonnet 25; 5 false DONE each | [18](evidence/18-real-repositories.md) |
| no change, no done | by construction `odd done` refuses when nothing changed (test FailureFeedback); on real issues plain agents claimed done with no source change 3 times, odd's arm 0, all on one stale ticket: a hint, the check was not triggered | [18](evidence/18-real-repositories.md) |
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
