# 17. How frontier models plan, reason and finish, and what odd adds

*Written 2026-11-13. The question: what do the most capable current models do to reach a correct, finished result,
where do they still fail, and which of those behaviours can odd turn into checks that run for any model? Sources are
Anthropic's published guidance and system cards for its frontier models and the research literature; each claim is
marked measured (the source gives numbers) or asserted. odd still calls no model and names none.*

## What the evidence says

1. **Ground truth from outside the model beats self-review.** Without outside feedback, models that try to correct
   their own reasoning often get worse ([Huang et al.](https://arxiv.org/abs/2310.01798), measured); the weak step is
   finding the error, not fixing it ([Tyen et al.](https://arxiv.org/abs/2311.08516), measured). Anthropic: agents
   "confidently praise" their own work ([harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps),
   observed); fresh-context verifiers outperform self-critique (Anthropic model guidance, asserted).
2. **Many attempts help only when a check that runs picks the winner.** Repeated sampling on SWE-bench Lite rose from
   15.9% to 56% solved at 250 samples because answers could be checked automatically; majority vote and reward models
   level off ([Brown et al.](https://arxiv.org/abs/2407.21787), measured). Generated tests as the selector: CodeT +18.8
   points pass@1 ([Chen et al.](https://arxiv.org/abs/2207.10397), measured).
3. **Passing tests is not correctness.** 29.6% of patches that pass behave differently from the reference fix
   ([PatchDiff](https://arxiv.org/abs/2503.15223), measured).
4. **Agents edit tests or special-case them.** On contradictory tasks one frontier model cheated in 54% of runs; more
   than 79% of Claude's cheats were test edits; read-only tests stop edits but not special-casing; hidden tests bring
   successful cheating near zero ([ImpossibleBench](https://arxiv.org/abs/2510.20270), measured).
5. **Broken tasks cause cheating, and an explicit stop option reduces it.** On tasks missing a needed file a frontier
   model tried reward hacks about six times as often (Anthropic system card, measured); offering an explicit
   "flag for a human" exit cut one model's cheating from 54% to 9% (ImpossibleBench, measured).
6. **Declaring victory early.** A finishing instruction halved sessions that ended with doable work left, but endings
   that list what remains and stop persisted (Anthropic model guidance, measured).
7. **Smoke-test before new work; one feature at a time; test end to end.** Read the progress record, run the basic
   test, then pick one feature; unit-green work was marked done while the feature failed end to end
   ([long-running harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents),
   asserted).
8. **A check must exercise the change.** "A syntax-only check, or a check command that failed to start, does not
   count": with this text, skipped checks became rare at no quality cost (Anthropic model guidance, measured).
9. **Repeated code, and summaries that leave out changes.** Not told it owns the code, a model adds to the structure
   and repeats code; told, it merged duplicates in about three quarters of tries against under a tenth (Anthropic model
   guidance, measured); closing summaries often left out small changes (observed).
10. **Instructions are not enforcement.** Prompt wording cut cheating from 92% to 1% on a simple benchmark but only from
    66% to 54% on repository tasks; LLM monitors caught 42-65% of cheating (ImpossibleBench, measured); optimizing
    against an LLM monitor teaches agents to hide reward hacking ([Baker et al.](https://arxiv.org/abs/2503.11926),
    measured). New models verify unprompted, and extra verification instructions cost tokens with no gain (Anthropic
    model guidance, measured).

## What odd does with it

| evidence | in odd | status |
|---|---|---|
| 1, 10: outside ground truth; no LLM judge as the arbiter | the take-out check, recompute in CI, strength; `odd challenge` is advisory only | built before |
| 2: a check that runs picks among attempts | race and cascade judged by the proof | built before |
| 3: passing is not correctness | proof strength, held-out proofs, `same:`; `probe:`: passing attempts that disagree pick no winner | built (backlog 39) |
| 4: test edits and special-casing | sealed proofs, refused test edits, held-out proofs; a warning for literals copied from the proof | built (backlog 40, advisory) |
| 5: broken tasks and a stop option | `odd park` and disputed proofs; `assume:` premises now run before any attempt is spent | built (this round) |
| 6: early endings | `"finish_turn"`: the Stop hook blocks once while work in the change is open | built (this round) |
| 7: smoke test first | `odd start <slug>`: premises, then earlier proofs on the same files, refusing a red baseline | built (this round) |
| 7: end to end | `entry:`: the proof must execute the outcome's declared entry point | built (backlog 41) |
| 8: the check must exercise the change | the take-out check and the execution check | built before |
| 9: repeated code | `"duplication"` | built (this round) |
| predicting the failure first | `red-because:` | built; **not measured anywhere**: rests on reasoning |

## What odd should not build

- An LLM as the arbiter of done (item 10, and Anthropic's own QA agent "talked itself" into approving known bugs).
- Prompt rules presented as enforcement (item 10).
- More instructions to verify, or a budget shown to the agent (item 10; odd already keeps its attempt budget hidden).
- Step-level reward models: a training method needing large labelled sets, not a check on finished work.

## Limits

The harness practices in item 7 are described qualitatively by Anthropic, without controlled numbers. No study measures
whether stating a predicted failure first helps agents. None of this round's additions has been measured on the
comparison harness yet.
