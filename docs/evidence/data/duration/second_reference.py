#!/usr/bin/env python3
"""Command-line duration normaliser: python3 dur.py "<duration>"."""
import re
import sys

UNIT_SECONDS = {"w": 604800, "d": 86400, "h": 3600, "m": 60, "s": 1}
ORDER = "wdhms"  # largest to smallest
LIMIT = 365 * 86400  # exactly 365 days is allowed

# A part: ASCII digits directly followed by one unit letter.
_PART = re.compile(r"([0-9]+)([wdhms])")
# Whole input: optional spaces, one or more parts optionally separated by spaces.
_WHOLE = re.compile(r" *(?:[0-9]+[wdhms] *)+")


class InvalidDuration(Exception):
    pass


class TooLong(Exception):
    pass


def parse(text):
    """Return total seconds; raise InvalidDuration or TooLong."""
    if _WHOLE.fullmatch(text) is None:
        raise InvalidDuration()
    parts = _PART.findall(text)
    # Validity (order, repetition) is decided before length.
    last = -1
    for _, unit in parts:
        rank = ORDER.index(unit)
        if rank <= last:
            raise InvalidDuration()
        last = rank
    total = 0
    for digits, unit in parts:
        digits = digits.lstrip("0")
        if len(digits) > 9:  # over 365 days in any unit; avoids huge int parsing
            raise TooLong()
        total += int(digits or "0") * UNIT_SECONDS[unit]
    if total > LIMIT:
        raise TooLong()
    return total


def fmt(total):
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    out = "".join(
        "%d%s" % (n, u)
        for n, u in ((days, "d"), (hours, "h"), (minutes, "m"), (seconds, "s"))
        if n
    )
    return out or "0s"


def main(argv):
    if len(argv) != 2:
        sys.stderr.write('usage: dur.py "<duration>"\n')
        return 2
    try:
        total = parse(argv[1])
    except InvalidDuration:
        sys.stderr.write("error: invalid duration\n")
        return 2
    except TooLong:
        sys.stderr.write("error: too long\n")
        return 1
    sys.stdout.write(fmt(total) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
