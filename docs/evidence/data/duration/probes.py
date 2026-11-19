#!/usr/bin/env python3
"""Frozen probes for the duration task (evidence 20), counted the way the calculator's are (probes.py).

The list of inputs is fixed here. The expected (exit code, standard output) of a probe is what TWO programs written
apart agree on: the reference in this file and a second program written by a separate session from the ticket's text
alone. A probe they do not agree on is left out and listed, not decided by one program.

usage: probes.py freeze OUT.json SECOND_REFERENCE.py
       probes.py count  IN.json NAME=DUR.py ...
       probes.py ref "<duration>"
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'calculator'))  # run() and same()
from probes import run, same  # noqa: E402

VALID = ['90s', '1w', '25h', '1h0m5s', '0s', '1h30m', '2d 4h', ' 90s ', '3600s', '86400s', '1w1d', '59s', '60m', '60s',
         '1d24h', '007m', '0h0m', '1w 2d 3h 4m 5s', '365d', '52w1d', '100m100s', '0w', '0d0h0m0s', '1w0s', '23h59m59s',
         '24h', '1d', '1m', '1s', '61s', '3661s', '1d1s', '1w1s', '000s', '  1h  30m  ', '1h   30m', '1w1d1h1m1s',
         '52w', '8760h', '525600m', '31536000s', '364d23h59m60s', '364d 24h', '51w 8d', '10d10h10m10s', '0001h',
         '1w 1s', '2w3d', '1d 1m', '1h1s', '59m60s', '23h60m', '6d24h', '0w0d', '99s', '999m', '48h', '7d', '14d0h']
TOO_LONG = ['366d', '365d1s', '53w', '9999h', '52w2d', '365d 1s', '31536001s', '525601m', '8761h', '365d0h0m1s',
            '1000d', '99999999999999999999s', '52w1d1s', '364d25h', '365d1m', '100w']
INVALID = ['', ' ', '   ', '90', 's', '1 h', '1x', '1H', '30m1h', '1h2h', '-1h', '1.5h', '1h,30m', 'abc', '1h 30', 'h1',
           '1h30', '1hh', 'h', '1 h 30 m', '1D', '1W', '1M', '1S', '+1h', '1h+30m', '1h-30m', '1e3s', '1_000s', '1h30m ago',
           '1s1m', '1m1h', '1h1d', '1d1w', '1s1s', '1w1w', '1h1m1h', '1ms', '1 s', '1h 30 m', '1h\t30m', '1h\n', '.5h',
           '1,5h', '1h;', 'w', 'wd', '1wd', '1w d', 'd1', '1h30m5', '5 5s', '1y', '1mo', '1min', '1sec', '1h30m!',
           '366d x', '999d5', '366d 1h 1h', '400d1x', '9999h -', '53w w', '1s366d', '366', '366dd', '١s', '1 h',
           '1h  ', 's1h', '0', '00', '0x1s', '1h 2', '1d1', '1 1h']
PROBES = VALID + TOO_LONG + INVALID
UNITS = (('w', 604800), ('d', 86400), ('h', 3600), ('m', 60), ('s', 1))
PART = re.compile(r' *([0-9]+)([wdhms])')


def reference(text):
    """(exit code, standard output) by the ticket: the whole input is checked for validity before its length."""
    body, pos, total, last = text.strip(' '), 0, 0, -1
    order = [u for u, _ in UNITS]
    if not body or not text.isascii():
        return 2, ''
    while pos < len(body):
        m = PART.match(body, pos)
        if not m or order.index(m.group(2)) <= last:
            return 2, ''
        last, pos = order.index(m.group(2)), m.end()
        total += int(m.group(1)) * dict(UNITS)[m.group(2)]
    if total > 365 * 86400:
        return 1, ''
    out = ''
    for unit, size in UNITS[1:]:
        if total // size:
            out += '%d%s' % (total // size, unit)
        total %= size
    return 0, (out or '0s') + '\n'


if __name__ == '__main__':
    if sys.argv[1] == 'ref':
        print(reference(sys.argv[2]))
    elif sys.argv[1] == 'freeze':
        kept, left = [], []
        for x in PROBES:
            ref, got = reference(x), run(sys.argv[3], x)
            if same(ref, got):
                kept.append({'input': x, 'exit': ref[0], 'stdout': ref[1] if ref[0] == 0 else None})
            else:
                left.append({'input': x, 'reference': ref, 'second': got})
        with open(sys.argv[2], 'w') as f:
            json.dump({'kept': kept, 'left_out': left}, f, indent=1)
        print('%d probes kept, %d left out' % (len(kept), len(left)))
        for r in left:
            print('  left out %r: reference %s, second program %s' % (r['input'], r['reference'], r['second']))
    else:
        probes = json.load(open(sys.argv[2]))['kept']
        for arg in sys.argv[3:]:
            name, prog = arg.split('=', 1)
            got = [(p, run(prog, p['input'])) for p in probes]
            bad = [(p['input'], g) for p, g in got if not same((p['exit'], p['stdout']), g)]
            print('%-14s %d of %d differ%s' % (name, len(bad), len(probes), ''.join(
                '\n    %r -> exit %s %r' % (x, g[0], g[1].strip()) for x, g in bad)))
