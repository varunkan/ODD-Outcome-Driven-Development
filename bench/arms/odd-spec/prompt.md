{ticket}

Work as AGENTS.md describes, with one difference: in this session you only state the outcome with `odd new` (its
proof command and the files the change may touch). Another agent then writes the proof's tests and seals them, and a
coding agent writes the code. Do not write tests or change the product code. Say DONE when the outcome is stated; if
the request cannot be done as written, run `odd park` and say NOT DONE with the reason.

Prefer one outcome for the whole request. Split it only when each part can be proven by changing the files inside
its own `in:` once the parts before it are built; then list the slugs in the order to build them, one per line, in
`.odd/chains/<ticket>.md` (`<ticket>` a short name for the request).
