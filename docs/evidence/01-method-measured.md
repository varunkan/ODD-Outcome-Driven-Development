# The POS build method, measured from its own git history

*Produced 2026-11-11 by a script, no model: `tools/measure_method.py` over the full history of the POS repository
(6,047 commits since 2025-08-16; 4,572 non-merge commits on main; 850 first-parent merges). Raw weekly series,
snapshots and every merge row: `data/method_metrics.json`. Re-run: `python3 tools/measure_method.py <repo> out.json`.*

First CLAUDE.md commit: 2026-08-11. Directive dates from docs/product/OWNER_DIRECTIVES.md.

**Read with care.** These are observational series, not experiments: periods differ in length (1-22 weeks), work mix,
and model versions; several directives landed in the same week. Lines changed is a weak proxy for value. Lead time is
branch-first-commit to merge on branches that changed product code (`lib/`, `android/`, `ios/`, `web/`,
`functions/`, `onboarding-agent/`, `admin-console/`), and is distorted by train/integration branches.
Activity-log entries exist only from October (older entries are not in the file); token usage was not logged in git,
only quoted inside directives (see the POS evidence ledger for those figures).

## Periods

| period | weeks | commits/wk | product-commit share | process-only commit share | process:product lines | test:product lines | product merges/wk | product-merge lead h (median / p90) | reverts/wk |
|---|---|---|---|---|---|---|---|---|---|
| P0 pre-CLAUDE.md (2025-08 .. 2026-08-11) | 22 | 9.6 | 0.69 | 0.19 | 0.20 | 0.09 | 0.5 | 7.1 / 5126 | 0.45 |
| P1 CLAUDE.md, before pods/directives (to 09-04) | 3 | 367 | 0.15 | 0.76 | **9.93** | 2.63 | 6.7 | 9.1 / 133 | 2.67 |
| P2 pods + directives #23-#44 (09-04 .. 09-08) | 1 | 275 | 0.12 | 0.84 | 5.51 | 3.82 | 13.0 | 1.8 / 104 | 4.0 |
| P3 #45-#50 invariant batching, measure-first, 3-min steps, legs-as-code, scripts-not-agents (09-08 .. 09-29) | 3 | 385 | 0.18 | 0.79 | 3.38 | 2.20 | 21.7 | 43.5 / 305 | 2.0 |
| P4 #51-#60 decision judge, judged swarm (09-29 .. 10-07) | 1 | 134 | 0.20 | 0.69 | 3.96 | 7.33 | 9.0 | 2.2 / 723 | 0.0 |
| P5 #61-#67 outcome-first, scripts-before-judges, step caps, simulation, local CI (10-07 .. 11-11) | 5 | 339 | **0.33** | **0.58** | **2.41** | 3.82 | 12.4 | 0.8 / **11.7** | 1.0 |

## Governance weight vs product size (weekly snapshots of main)

| week | CLAUDE.md bytes | directives | live lessons | charter bytes | governance scripts | process docs MB (all files) | lib dart MB | test files | integration tests | mutation batteries |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-10 | 23,259 | 0 | 0 | 0 | 2 | 0.4 | 4.3 | 121 | 3 | 0 |
| 2026-08-31 | 48,420 | 36 | 64 | 227,205 | 86 | 18.6 | 4.7 | 250 | 3 | 3 |
| 2026-09-07 | 80,025 | 49 | 69 | 301,473 | 184 | 23.3 | 5.0 | 381 | 25 | 35 |
| 2026-09-28 | **95,335** | 52 | 60 | 361,883 | 308 | 43.2 | 6.7 | 778 | 72 | 87 |
| 2026-10-05 | 31,940 (budget #64) | 65 | 60 | 274,765 | 352 | 47.8 | 6.9 | 906 | 74 | 92 |
| 2026-11-09 | 31,500 | 67 | 60 | 276,689 | 382 | 60.9 | 8.0 | 1,307 | 82 | 169 |

Composition on main today: process markdown **43.1 MB in 1,552 files** (docs/, .claude/, specs/) vs **7.7 MB of
product Dart in 407 files**; 108 PNG screenshots 12.5 MB; 449 files under scripts/.

## Peaks worth naming
- Week of 2026-08-31: 746 commits, 579 of them process-only; 200,926 process lines vs 12,826 product lines (15.7x).
- Week of 2026-10-05 (judged swarm): 284 decision-judge rulings recorded in one week; 71,426 test lines vs 9,750 product.
- CLAUDE.md grew 23 KB -> 95 KB in seven weeks, then the context budget (#64) held it at 31.5 KB for six weeks.
- Directives that themselves record being restated or not followed (text markers, needs human confirmation of each):
  #46 ("same thing again", "violated"), #48 ("not at all followed"), #49 ("fourth" telling), #65 ("reaffirmed");
  weaker markers ("ignored") on #32, #34, #44 may be phrasing ("should not be ignored").

## What the series supports (and what it does not)
- Supported: process overhead fell steadily as the method matured: process:product line ratio 9.9 -> 2.4; product
  share of commits 0.15 -> 0.33; process-only commits 0.76 -> 0.58; p90 lead time of product merges 133 h -> 12 h in
  the outcome-first period; reverts 2.7/wk -> 1.0/wk.
- Supported: testing investment rose by an order of magnitude after Claude: test:product lines 0.09 -> 2-7; test files
  121 -> 1,307; device legs as code 3 -> 82 integration tests; 169 committed mutation batteries.
- Supported: governance weight grew far faster than the product (process markdown 5.6x the product code; 382
  governance scripts; 67 directives in nine weeks), and rules written as prose were repeatedly not followed until
  enforced by a script or hook.
- Not supported by git alone: token cost per period (not logged), defect escape rate (no incident tracker), causal
  attribution of any single directive.
