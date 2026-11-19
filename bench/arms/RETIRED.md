# Arms that were measured and then removed

These arms depended on the setting `"reach": "require"`, which was removed after it failed correct work on a second
task ([evidence 20](../../docs/evidence/20-a-second-task.md)). Their runs stay in the evidence; the arms as run are
in the repository's history at the commit named.

| arm | what it was | measured in | last commit that has it |
|---|---|---|---|
| `odd-reach` | edge cases and reach required | evidence 19, fourth round | 2634136 |
| `odd-pair` | two attempts raced on a sealed proof, then compared | evidence 19, fifth round | 2634136 |
| `odd-second` | one session, then `odd second`, then a settling session | evidence 19, sixth round | 2634136 |
| `odd-claim` | reach required, hooks, `"report": "claim"` | evidence 20 | 2634136 |
