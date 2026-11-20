# Coding agents say "done". Make them prove it.

*Draft launch post. Every figure links to its source in the repository.*

I spent three months building a production restaurant point-of-sale system with coding agents: several tills, money,
offline sync, a printer. It worked. It also produced 1,856 instructions from me to the agents, a 100 KB instruction
file at its peak, and a lot of process. When I measured it, two things stood out.

**The work got better as the method got simpler.** Measured from 6,047 commits, the ratio of process lines to product
lines fell from 9.9 to 2.4, the share of commits that touched the product rose from 15% to 33%, and the slowest tenth of
changes went from 133 hours to 12 ([the measurement](../docs/evidence/01-method-measured.md)). The period where that
happened is the one where every piece of work started from one outcome sentence and one proof.

**Written rules did not hold.** The two costliest mistakes in the project were its own process rules, and across 294
agents, every rule that was broken was already written down ([why](../WHY.md),
[the waste record](../docs/evidence/02-pos-evidence-ledger.md)). An instruction is something the model may or may not
follow. That stays true however good the model gets; a better model just produces more unreviewed change per hour.

So I kept only the part that does not depend on the model agreeing. That is ODD.

## The whole idea

1. Before code: one sentence saying who observes what, a command that exits 0 only when it is true, and the files the
   change may touch.
2. The agent makes the change.
3. `odd done` runs the proof, then **takes the change out and runs it again**. If the proof still passes, it proves
   nothing, and the work is not done. Then it puts the change back and runs it a third time.
4. In CI, `odd gate --recompute` does all of it again from the code, with its own copy of the tool and the settings
   from the target branch, and every changed file must sit inside a verified outcome.

That is the difference from Spec Kit, BMAD and Superpowers, which are good at structure (specs, plans, roles,
skills): in each of them, "done" is the model's claim or a ticked checklist. ODD can sit underneath any of them.

[60-second demo: an agent's test that asserts nothing gets refused, then a real one passes](demo.sh)

## What the measurements say

I compared it with a plain agent told in one sentence to write tests, run them, and say DONE only if they pass.

- On 24 real bug fixes from pytest, sphinx, sympy and pylint, with hidden tests, one model and one run each: ODD
  said DONE wrongly once, the plain agent five times; the hidden tests passed on 18 against 12
  ([22](../docs/evidence/22-real-bug-fixes.md), [23](../docs/evidence/23-real-bug-fixes-pass-rate.md)).
- Three of the plain agent's five wrong DONE were runs where it changed no product code at all: it wrote a test
  that passed on the code as it was ([24](../docs/evidence/24-the-check-with-no-setup.md)).

## What I am not claiming

Not that it beats anything. Neither difference above reached the threshold fixed before the runs; 24 tasks give a
hint, not a rate. ODD cost about a tenth more. On a small task the one sentence did as well for less
([21](../docs/evidence/21-is-the-core-worth-more-than-a-sentence.md)), and on easy tasks every way of working got
everything right ([15](../docs/evidence/15-comparison.md)). The experiments that did not go my way are published
with the rest.

It also has limits I would rather you hear from me: it checks that the proof depends on the change, not that the proof
is thorough; on your laptop an agent with a shell can get around any local check, so the gate counts only as a
required CI check; and only Claude Code has been run with it so far.

Try the one check with no setup: `pipx install odd-tool`, then `odd check` in any git repository. The whole method:
`odd init`, or one line in GitHub Actions. Everything, including the waste record and
every ruling on those 1,856 instructions, is at github.com/varunkan/ODD-Outcome-Driven-Development.
