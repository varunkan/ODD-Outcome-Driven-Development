Build a command-line duration normaliser in this repository.

`python3 dur.py "<duration>"` prints the duration in normal form on one line and exits 0.

- Input: one or more parts. A part is a whole number (digits only, leading zeros allowed) followed directly by one
  unit letter: `w` weeks, `d` days, `h` hours, `m` minutes, `s` seconds. Parts may be separated by spaces, and spaces
  may surround the whole input (`1h30m`, `2d 4h`, ` 90s `). Units must go from largest to smallest, each at most
  once (`1h30m` is valid; `30m1h` and `1h2h` are not).
- Output: the same length of time as days, hours, minutes and seconds, largest first, with no spaces: hours under 24,
  minutes under 60, seconds under 60, weeks turned into days, and parts that are zero left out (`90s` prints `1m30s`;
  `1w` prints `7d`; `25h` prints `1d1h`; `1h0m5s` prints `1h5s`). A duration of zero prints `0s`.
- A duration longer than 365 days prints `error: too long` to standard error and exits 1. Exactly 365 days is allowed.
- An invalid duration prints `error: invalid duration` to standard error and exits 2. Invalid means: empty or only
  spaces, a number with no unit, a unit with no number, a space between a number and its unit, a unit letter other
  than the five above (upper case included), units out of order or repeated, a sign or a decimal point, or any other
  character.
- Called with no argument, or with more than one, it prints `usage: dur.py "<duration>"` to standard error and
  exits 2.
- Include unit tests under `tests/` that run with `python3 -m unittest`.
