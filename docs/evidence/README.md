# Evidence: why this approach, and where it is weak

Everything learned while deciding whether Outcome Driven Development is worth packaging, kept so that anyone can check
the reasoning instead of taking it on trust. The short argument is in [`../../WHY.md`](../../WHY.md); these are the
documents behind it.

| # | document | what it answers | how it was produced |
|---|---|---|---|
| 01 | [The method, measured](01-method-measured.md) | Did delivery change as the method matured? What did the process itself weigh? | A script over 6,047 commits of the POS repository. No model. |
| 02 | [What paid and what was waste](02-pos-evidence-ledger.md) | Which working methods have a recorded before/after, and which cost more than they returned? | A read-only agent, using only numbers recorded in the POS repository, each cited. |
| 03 | [The instruction catalog](03-instruction-catalog.md) | What were all 1,856 instructions, and how many were ever proven? | Twelve read-only agents over every instruction source; grouped by script. |
| 04 | [Spec Kit, BMAD, Superpowers](04-spec-kit-bmad-superpowers.md) | What do the existing frameworks do, how do they enforce it, and what is the evidence for them? | Read-only research agents on primary sources, with URLs. |
| 05 | [Practice and model trends](05-practice-and-model-trends.md) | What does software-engineering research say, and which scaffolding survives better models? | Read-only research agents, with URLs. |
| 06 | [Audit of the first draft](06-first-draft-audit.md) | What was wrong with the first toolkit built from these rules? | A read-only review agent that ran its tests and tried to defeat it. |
| 07 | [Validation, comparison and verdict](07-validation-and-verdict.md) | Is the toolkit worth building, how does it compare with Spec Kit, BMAD, Superpowers and Claude Code alone, and what is the lean design? | A 31-agent run: validators, a skeptic per area, a comparison, three independent critics, one decision. |
| 08 | [The refined method](08-refined-method.md) | What is left when only the supported rules are kept? | Composed from the surviving rules, each principle traced to its rulings. |
| 09 | [The rulings](09-rulings.md) | What happened to each of the 1,856 instructions? | 224 rule clusters with verdict, evidence grade and durability; drops and overturned rulings explained. |
| 10 | [Design review](10-design-review.md) | What was wrong with the first design of the lean tool, and what changed? | Four critics (tamper, correctness, friction, portability) and one ruling: 23 required changes. |
| 11 | [Red team of 0.2.0](11-red-team.md) | Can the tool be made to report done, lose work or crash? | Six attackers, each finding reproduced independently; each confirmed one is now a test. |
| 12 | [Pilot of the comparison](12-pilot.md) | Does the harness measure fairly, and what will the full run cost? | 15 real sessions; harness evidence, not a result. |
| 13 | [Verdict so far, and where ODD is useful](13-verdict-and-use.md) | Is it worth using, for whom, and what is not shown? | Both halves of the comparison, the red team and the source project. |
| 14 | [What research says would make ODD more valuable](14-research.md) | Can anything make ODD 100 times better (no), which augmentations have evidence, and what will not help? | Three research angles over about 30 papers with URLs, each claim re-checked by a skeptic pass; numbers from the papers, none yet measured on our harness. |
| 15 | [The comparison](15-comparison.md) | Does ODD, Spec Kit, BMAD or Superpowers do better than plain Claude Code? | 480 runs on two models, hidden tests, both grades and every reason verbatim. |
| 16 | [The new arms](16-new-arms.md) | Do race, cascade or a strong model's proof make Haiku as good as Sonnet for less? | 288 runs; as built, no: less delivered than plain Haiku at higher cost, two causes found and one fixed. |

## Data and tools

- `data/method_metrics.json`: weekly series, weekly snapshots of governance weight against product size, and one row
  per merge (date, lead time, sizes; commit subjects are not published).
- `data/catalog/<area>.json`: the full catalog, one file per area. Each item has an id (`FR-`, `PM-`, `OD-`, `VE-`,
  `DL-`, `SA-`), the instruction, its recorded outcome, the owner's words where recorded, its enforcement point and
  its sources.
- `data/research/*.json`: the research and audit results as returned, before rendering.
- `data/design-review.json`: the four critiques and the ruling on the tool's design, as returned.
- `data/validation/*.json`: every ruling with the instruction ids it covers, the method, the comparison, the three
  critiques and the decision, as returned.
- `tools/measure_method.py`: the measurement. `tools/group_catalog.py`: groups the raw catalog and merges exact
  duplicates. `tools/render_evidence.py`: renders documents 02 to 10 from the data.

## How to read it

- Documents 01 and the counts in 03 are mechanical. Documents 02 and 04 to 09 were written by agents: each figure
  carries a source, and each has a "Not verified" or limits section. Treat a figure without a source as unproven.
- The measurements are observational. Periods differ in length, work mix and model version, and several directives
  landed in the same week, so no single instruction's effect is isolated.
- The performance tag on each catalog item ("proven to pay", "mandated, never measured" and so on) is one agent's
  reading of the outcome recorded beside the instruction. The validation rulings (09) re-examine every item.
- The evidence comes from one project and one team. It shows what happened there; it does not show the same numbers
  will hold elsewhere. That is why the toolkit is expected to measure itself, with and without, on the same tasks.
