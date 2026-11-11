# 12. Pilot of the comparison (harness evidence, not a result)

*Run 2026-11-11 on the harness at commit 57b2a33: 3 tasks x 5 arms x 1 run, `--model sonnet` (claude-sonnet-5-5),
`--max-turns 150 --timeout 1800 --jobs 3`, and `--max-budget-usd 2`, which this pilot showed to be unfair (below).
One run per cell: nothing here compares the methods.*

| task | arm | passed | claim | cost USD | turns | seconds | changed lines | framework reached the model |
|---|---|---|---|---|---|---|---|---|
| t01-interval-overlap | bmad | yes | DONE | 0.094 | 7 | 11.2 | 4 | yes: bmad-build-auto workflow read; review steps skipped "to stay within budget" |
| t01-interval-overlap | odd | yes | DONE | 0.079 | 4 | 13.3 | 57 | yes: odd commands run |
| t01-interval-overlap | plain | yes | DONE | 0.056 | 3 | 8.8 | 4 | n/a |
| t01-interval-overlap | speckit | yes | DONE | 0.188 | 14 | 29.7 | 129 | yes: speckit-bug-assess, -fix, -test invoked |
| t01-interval-overlap | superpowers | yes | DONE | 0.069 | 4 | 8.6 | 4 | loaded (plugin and start-up hook in context); no skill invoked |
| t07-cache-staleness | bmad | yes | DONE | 0.099 | 7 | 13.1 | 10 | yes: bmad-build-auto workflow read; review steps skipped "to stay within budget" |
| t07-cache-staleness | odd | yes | DONE | 0.085 | 6 | 16.3 | 35 | yes: odd commands run |
| t07-cache-staleness | plain | yes | DONE | 0.056 | 3 | 8.8 | 6 | n/a |
| t07-cache-staleness | speckit | yes | DONE | 0.197 | 15 | 35.0 | 125 | yes: speckit-bug-assess, -fix, -test invoked |
| t07-cache-staleness | superpowers | yes | DONE | 0.072 | 4 | 10.2 | 8 | loaded (plugin and start-up hook in context); no skill invoked |
| t08-contradictory-parser | bmad | yes | NOT DONE | 0.118 | 8 | 14.9 | 12 | yes: bmad-build-auto workflow read; review steps skipped "to stay within budget" |
| t08-contradictory-parser | odd | yes | NOT DONE | 0.061 | 4 | 10.8 | 7 | yes: odd commands run |
| t08-contradictory-parser | plain | yes | NOT DONE | 0.048 | 3 | 6.9 | 0 | n/a |
| t08-contradictory-parser | speckit | no | DONE | 0.178 | 12 | 31.1 | 108 | yes: speckit-bug-assess, -fix, -test invoked |
| t08-contradictory-parser | superpowers | yes | NOT DONE | 0.063 | 3 | 9.6 | 0 | loaded (plugin and start-up hook in context); no skill invoked |

Total cost: $1.46. Mean cost per run: plain $0.053, odd $0.075, speckit $0.188, bmad $0.104, superpowers $0.068.

## What the pilot found

1. **A dollar cap is visible to the agent and changes its behaviour.** The CLI writes `--max-budget-usd` into the
   system prompt; BMAD skipped its review and spec steps "to stay within budget". Measured runs no longer set it
   (`bench/RUNNER-NOTES.md`). BMAD's cost here is therefore an underestimate.
2. **The tasks are too easy for this model.** Every arm passed t01 (bug fix) and t07 (the trap meant to leave a stale
   cache path). A pass-rate comparison would show a ceiling, not a difference. Harder tasks are needed before the
   full run: larger code bases, changes across several files, traps the visible tests do not reveal.
3. **The impossible task separates arms.** On t08, four arms reported NOT DONE and named the conflict; the Spec Kit
   run reported DONE on a requirement that cannot be met. One run, so this is a lead, not a finding.
4. **Cost per run varies about fourfold** between arms (Spec Kit highest, plain lowest), at roughly the same pass rate
   on these easy tasks.
5. **The harness held**: 15 of 15 runs graded, no contamination, regression tests intact in every run, every
   framework present in context, the ODD arm's own gate passed in each of its runs.

## Projection for the full run (10 tasks x 5 arms x 3 repeats)

From these means, about $15 on Sonnet. Without the visible cap the heavier arms will spend more, and harder tasks
cost more per run, so plan for two to four times that. Wall clock at three sessions at a time: under two hours at
this pilot's speed. The uncertainty is large: three easy tasks, one run each.
