{ticket}

Work as AGENTS.md describes, with one difference: in this session you state the outcome and write its proof only;
coding agents started after you write the code, and the proof decides which of their attempts is kept. State the
outcome with `odd new`, write the test its proof command runs so that it fails now, and seal it with `odd seal
<slug>`. Do not change the product code. Say DONE when the proof is sealed; if the request cannot be done as written,
run `odd park` and say NOT DONE with the reason.

Prefer one outcome for the whole request. Split it only when each part can be proven by changing the files inside
its own `in:` once the parts before it are built; then list the slugs in the order to build them, one per line, in
`.odd/chains/<ticket>.md` (`<ticket>` a short name for the request).
