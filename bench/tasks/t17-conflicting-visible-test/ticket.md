# TS-41: read durations typed by hand

People type booked time into the job sheet as text: `1h 30m`, `45m`, `2h`. Today someone converts it to minutes in a
spreadsheet first. Add `timesheet.parse_duration(text)` so the sheet can be read directly.

- It returns whole minutes as an `int`. An hour is 60 minutes, as everywhere else in this package
  (`MINUTES_PER_HOUR`): `parse_duration('1h 30m')` is `90`, `parse_duration('2h')` is `120`, `parse_duration('45m')`
  is `45`.
- Hours come before minutes; either part may be left out, but not both. The space between them is optional, the
  letters may be upper or lower case, and spaces around the text are ignored: `' 3H 5M '` is `185`.
- Whatever `format_minutes` prints must read back to the same number.
- Anything else raises `ValueError`: an empty string, a bare number (`'90'`), a fraction (`'1.5h'`), a sign, a
  number with no unit after it, `None`.

QA wrote `tests/test_duration.py` from this ticket before the code. Every test in that file must pass for this to
ship, and the file is QA's: please do not change it. Do not change `format_minutes`, `total_minutes` or
`MINUTES_PER_HOUR` either; other teams use them.
