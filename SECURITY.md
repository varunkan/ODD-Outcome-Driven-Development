# Security

## Reporting a problem

Report it privately through GitHub: the repository's **Security** tab, **Report a vulnerability**. Please do not open
a public issue for it. Say what you ran, what happened and what you expected; a small repository that shows it helps
most. You will get an answer on the report itself.

## What counts

odd runs commands that an outcome file names (`proof:`, `same:`, `probe:`, `entry:`, premises, standing checks) with
your own rights, on your machine and in your CI. That is its job and not a vulnerability: review an outcome file the
way you review a script. These are in scope:

- a way for a change to make `odd gate --recompute` pass without its proof having failed with the change taken out;
- a way for a pull request to weaken the settings, the tool or the held-out proofs that CI reads from the target
  branch;
- a way for an agent's attempt to write outside its own copy of the repository, or to plant a verification;
- anything in the GitHub Action (`action.yml`) that leaks a token or runs code from an untrusted place.

## Supported versions

The latest release. odd is one file with no dependencies beyond Python's standard library.
