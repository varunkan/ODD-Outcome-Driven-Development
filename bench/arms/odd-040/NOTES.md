# odd-040

Exactly the `odd` arm (`setup.sh` and `post.sh` call `arms/odd/`'s): `odd init` writes the method into `AGENTS.md`,
one claude session works the ticket, and `post.sh` runs the pinned `odd gate --recompute --base main` in P. The only
difference is the name, so results of runs with odd as committed at HEAD (0.4.0 plus the backlog features: the R3
park wording, proof strength, sealed proofs, race, cascade, spec, ...) never mix with the earlier `odd` records, which
ran odd at 0e38e3e (docs/evidence/15-comparison.md).

## To state with the results

- The house arm, as `odd`: the benchmark, its tasks and its runner are written by the ODD project.
- odd as committed at the bench commit in `provenance.odd_commit` (`odd_sha256` names the exact file), not a tagged
  release; the new commands are available to the session but nothing tells it to use race, cascade or spec.
- One claude session, as plain: only the `AGENTS.md` text differs.
