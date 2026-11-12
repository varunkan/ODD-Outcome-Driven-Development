# Does the odd comment save review time? A measurement protocol

Status: a protocol only. No figure has been measured, and none is claimed anywhere in this repository.

The claim to test: on a merged pull request written by a coding agent, a reviewer who has the odd gate's comment
(verdict, outcome sentences, proofs, what each proof said with the change taken out, strength score, exemptions)
spends fewer minutes reviewing it than one who does not, and lets no more defects through.

## What is compared

Two arms on the same repositories, the same agent and the same gate:

- **With:** the Action runs with `comment: auto` (the default). The comment is on the pull request.
- **Without:** the Action runs with `comment: false`. The gate still runs and is still a required check; only the
  comment (and the step summary, which the reviewer is asked not to open) is absent.

So the arms differ only in what the reviewer reads, not in whether the gate exists.

Assign each agent pull request to an arm at random when it is opened (for example, the parity of the pull request
number, decided before anyone looks at it). Do not let the reviewer or the author choose.

## What to log, per pull request

One row, written when the pull request merges (or is closed unmerged, which is logged too, never dropped):

| field | how it is obtained |
|---|---|
| pull request number, repository, arm | from the assignment |
| reviewer | the person who approved |
| lines changed (product, test, other) | `git diff --numstat` against the merge base, split by odd's own path classes |
| outcomes in play, skips, gate verdict on the final commit | `odd gate --recompute --json FILE` on the merged commit |
| **active review minutes** | see below |
| review rounds | count of "changes requested" reviews |
| defects found in review | comments that led to a code change, counted by the reviewer at merge |
| defects found later | any bug traced to this pull request within 30 days of merge (a revert, a fix that names it) |

**Active review minutes** is the hard part. Wall clock between "review requested" and "approved" measures waiting,
not reading. Use one of, and keep the same one for both arms:

1. The reviewer starts and stops a timer per sitting (a shell alias that appends `start`/`stop` lines with the pull
   request number to a file). Self-reported, but the same bias is in both arms.
2. Editor or browser time on the pull request's pages, from a tool the reviewer already uses, if one exists.

Round to the minute. A sitting interrupted by something else is stopped and restarted.

## How many

Review time on pull requests is skewed (a few long reviews dominate). Plan for at least 40 merged pull requests per
arm, across at least three reviewers, before looking at any comparison; more if pull request sizes vary widely.
Fix the stopping rule in advance (a count or a date), not when the numbers look good.

## How to compare

- Primary: the ratio of median active review minutes, with-arm over without-arm, per changed product line or within
  size bands (for example under 50, 50 to 300, over 300 product lines), since a bigger change takes longer whatever
  the arm. Report a bootstrap interval for the ratio, not only the point estimate.
- Guard rail: defects found later per pull request, per arm. A time saving bought with more escaped defects is not a
  saving; report both together, always.
- Per reviewer: the same comparison within each reviewer, so one fast reviewer in one arm does not decide it.
- Report every pull request in the log, including closed-unmerged ones and those where the gate failed or could not
  run, and say how many there were in each arm.

## What this cannot show

- Reviewers cannot be blinded: they see whether the comment is there. A reviewer who believes in it may read faster
  in that arm for that reason alone.
- Reviewers learn. After weeks of reading the comment, a reviewer may review differently in the without-arm too.
  Alternating arms by pull request, not by week, spreads that over both.
- The figure holds for the repositories, agent and reviewers measured. It says nothing about a team that does not
  use outcome files the way these did.
- Self-timed minutes are approximate. A difference of a minute or two on a median of ten is within what the method
  can resolve only with many more pull requests than the minimum above.

Publish the raw log with the result, and the result whichever way it goes.
