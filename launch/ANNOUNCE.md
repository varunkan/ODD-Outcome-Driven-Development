# Short announcements

Each is ready to paste once the release is tagged. None quotes a comparison figure; when the comparison has run, add
one line with its headline number and spread, and link the results page.

## Show HN

**Title:** Show HN: ODD – coding agents' "done" checked by taking the change out and re-running the test

**Text:**
Coding agents often say "done" when the tests pass but test nothing the change does. ODD is a single Python file
that makes "done" a command's verdict instead: before code, the agent states one outcome sentence, a proof command
and the files it may touch; `odd done` runs the proof, takes the change out and runs it again (it must fail), then
puts it back (it must pass). In CI, `odd gate --recompute` redoes it from the code and trusts nothing recorded.

It works with any agent that reads AGENTS.md (Codex, Cursor, Copilot, Claude Code). It came out of three months of
building a POS system with agents; the instructions I gave, what they cost, and what I dropped are published with it.
I make no performance claim yet: a same-task comparison against plain Claude Code, Spec Kit, BMAD and Superpowers is in
the repo and will be published with its spread.

https://github.com/varunkan/ODD-Outcome-Driven-Development

## Reddit (r/ClaudeAI, r/ChatGPTCoding, r/cursor)

**Title:** I made agents prove "done": the test must fail with the change taken out

Same text as above, shortened to the first paragraph, plus: "Install: `pipx install odd-tool && odd init`. CI: one
GitHub Actions step. Happy to hear where it breaks."

## X / LinkedIn

Coding agents say "done". ODD makes them prove it: the proof must pass, fail with the change taken out, and pass
again. In CI it is recomputed from the code. One file, any agent that reads AGENTS.md.
`pipx install odd-tool` · github.com/varunkan/ODD-Outcome-Driven-Development

## Lists to submit to

- awesome-claude-code and similar curated lists (one-line entry: "ODD: done is a proof that fails without the change").
- The AGENTS.md examples list (agents.md), as a project that ships its method in AGENTS.md.
- GitHub Marketplace, from the v0.4.0 release page.
