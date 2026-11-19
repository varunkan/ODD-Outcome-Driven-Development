# odd-claim

The odd-reach arm with odd's Claude Code hooks installed (`odd init --claude-hooks`) and `"report": "claim"`
(backlog 47). Same prompt and method text.

With the setting, the Stop hook reads the session's last message. If it leaves out the verdict line of `odd claim`
or the start of any of its NOT PROVEN points, the turn is blocked once, and the reason carries the claim's text.

Why: in six runs of the odd-cases and odd-reach arms every session ran `odd claim`, and no final report carried any
of the three or four points it listed as not proven (evidence 19).

## To state with the results

- Final reports that carry the verdict and every not-proven point, beside 0 of 6.
- Whether the hook fired, and whether the report after it says anything the claim does not.
- The hooks also block a turn that leaves unproven work; that is part of this arm and not of odd-reach.
