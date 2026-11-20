# plain-check

The smallest odd: `plain-tests` plus one Stop hook that runs `odd check`. No outcome file, no method text, no gate.
The hook blocks the end of a turn once, with the check's result, when the tests the session wrote pass with its
change taken out, or do not pass.

On 48 kept runs of real bug fixes (evidence 22 and 23) the check's "passes without the change" named 5 runs, and the
hidden tests fail in all 5. This arm asks whether telling the agent so, during the session, turns those into correct
work or into an honest NOT DONE.

## To state with the results

- False DONE and hidden tests beside `plain-tests` and `plain-persist`.
- How often the hook blocked, and what the session did next, read from the transcript.
- The arm check (`odd check` after the session) against the hidden tests.
