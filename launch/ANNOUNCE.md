# Short announcements

Each is ready to paste once the release is tagged and the package is on PyPI. Every figure is from the evidence
pages; none says odd makes agents better, because that has not been shown.

## LinkedIn

Coding agents say "done". I spent a few weeks measuring how often that is true, and built a small check for it.

What I found, on 24 real bug fixes from pytest, sphinx, sympy and pylint (one model, one run each):
- A plain agent told to "write tests, run them, and say DONE only if they pass" said DONE wrongly 5 times.
- In 3 of those 5 it had changed no product code at all. It wrote a test that passed on the code as it was.
- With the method I built (ODD), 1 wrong DONE, and the hidden tests passed on 18 fixes against 12.

What I am not claiming: neither difference reached the threshold I fixed before the runs. 24 tasks is a hint, not a
rate. ODD cost about 10% more, and on a small task the one sentence did as well for less.

The part you can use today is one command, with no setup, in any git repository:

    pipx install odd-tool
    odd check

It runs the tests your change brings, takes the change out, and runs them again. If the tests still pass, they show
nothing about the change. If only tests changed, it says so.

Everything is published, including the experiments that did not go my way. I would like to know where it is wrong
on your repository: github.com/varunkan/ODD-Outcome-Driven-Development

## Show HN

**Title:** Show HN: odd check – do the tests in this change fail without it?

**Text:**
Coding agents often say "done" when the tests pass but show nothing about the change. `odd check` is one command
with no setup: it runs the test files a change brings, takes the rest of the change out, runs them again, and puts
it back. `SHOWN` if they fail without it; `NOT SHOWN` if they pass anyway; `NO CHANGE` if only tests changed.

It is the core of a larger method (ODD: state an outcome and a proof before the code; CI recomputes it). I measured
both against a plain agent told to write and run tests, on 24 real bug fixes with hidden tests. The honest result:
fewer wrong "done" (1 against 5) and more hidden tests passing (18 against 12), neither past the threshold I fixed
beforehand; and 3 of the plain agent's 5 wrong "done" had changed only tests. All runs, rulings and negative results
are in the repository.

https://github.com/varunkan/ODD-Outcome-Driven-Development

## Reddit (r/ClaudeAI, r/ChatGPTCoding, r/cursor)

**Title:** I measured how often an agent's "done" is true on real bug fixes, and made a one-command check

The Show HN text, plus: "Install: `pipx install odd-tool`, then `odd check` in any git repository. It can also run
as a Claude Code Stop hook (`odd check --stop-hook`) or one GitHub Actions step (`mode: check`). Happy to hear
where it breaks."

## X

An agent told to write and run tests said DONE wrongly on 5 of 24 real bug fixes. In 3 it had changed only tests.
`odd check`: do the tests in this change fail without it? One command, no setup.
`pipx install odd-tool` · github.com/varunkan/ODD-Outcome-Driven-Development

## Lists to submit to

- awesome-claude-code and similar curated lists (one-line entry: "odd check: do the tests in this change fail without it?").
- The AGENTS.md examples list (agents.md), as a project that ships its method in AGENTS.md.
- GitHub Marketplace, from the v0.5.1 release page.
