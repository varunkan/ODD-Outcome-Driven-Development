#!/usr/bin/env python3
"""Frozen probes for the calculator task (evidence 19), so "a defect of its own" is counted the same way every time.

The list of expressions is fixed here. The expected result of a probe is (exit code, standard output) on which FOUR
programs written apart agree: a reference written for this file (exact fractions, the ticket's rules) and the three
Spec Kit calculators the second judge found no defect in. A probe they do not agree on is left out and listed, not
decided by one program. A calculator's defects are the kept probes where it differs.

Where the ticket does not fix the notation (a result of 1e10 or more, or under 0.0001, that is not whole), the
expectation is the number itself and the output is read as a number.

usage: probes.py freeze OUT.json CALC.py CALC.py CALC.py     (writes the expectations; done once)
       probes.py count  IN.json NAME=CALC.py ...             (prints each program's differing probes)
       probes.py ref "<expression>"                          (the reference calculator itself)
"""
import json
import subprocess
import sys
from fractions import Fraction

VALID = ['3', '2.5', '.5', '0', '007', '1+2', '1 + 2', ' 1+2 ', '2*3+4', '2+3*4', '(2+3)*4', '((2))', '(((1+2)))*3',
         '--3', '-+-3', '+3', '-3', '- 3', '2--3', '2-+3', '2*-3', '2/-4', '-(2+3)', '-(-(2))', '+(+2)', '10/4', '1/3',
         '2/3', '0.1+0.2', '1.5*2', '3.0', '6/2', '7/2', '1/8', '100*100', '1e', '0.5+.5', '.5+.5', '5.+1', '1/3*3',
         '2*(3+4)*5', '2 * ( 3 + 4 )', '8/2/2', '8-2-2', '2-3', '0-0', '-0', '0*5', '0/5', '1/7', '22/7', '1/1000',
         '1/4096', '123456789*1000', '99999999999', '1234567890.5', '12345678901.5', '123456789012.25', '0.000123',
         '1/3+1/3', '0.1*3', '1.10', '2.50*2', '1000000/3', '12345.6789*10', '3.14159265358979', '(1)', '( 1 )',
         '1+(2*(3+(4*5)))', '-2*-2', '4/2*3', '1-2*3', '9.99+0.01', '0.3-0.1', '1/2+1/2', '5/2.5']
ZERO = ['1/0', '1/(2-2)', '0/0', '1/0.0', '(1/0)', '5/(3-3)*2', '1/(1-1)+1', '-1/0', '2*(4/0)']
INVALID = ['', ' ', '()', '( )', '(', ')', '(1', '1)', '((1)', '(1))', '1+', '1-', '1*', '1/', '+', '-', '*', '/',
           '2 * * 3', '2 + * 3', '2 / / 3', '2 3', '2.5 3', '1 2 3', 'a', '1+a', '2x', '1,2', '1e5', '2^3', '2%3',
           '.', '1..2', '1.2.3', '..5', '. 5', '1/0+', '1/0)', '(1/0', '1/0 2', '1/0*', '0/0/', '1/(2-2', '1/0 +',
           '*3', '/3', '3(4)', '(3)(4)', '(3)4', '1+()', '()1', '2**3', '2//3', '--', '1 + + ', '$', '1;2', '1=1']
PROBES = VALID + ZERO + INVALID


class Bad(Exception):
    pass


def reference(text):
    """(exit code, standard output) by the ticket: fractions, so no rounding before the output is formatted."""
    pos, n = 0, len(text)

    def peek():
        nonlocal pos
        while pos < n and text[pos] == ' ':
            pos += 1
        return text[pos] if pos < n else ''

    def number():
        nonlocal pos
        start = pos
        while pos < n and text[pos].isdigit():
            pos += 1
        if pos < n and text[pos] == '.':
            pos += 1
            while pos < n and text[pos].isdigit():
                pos += 1
        lit = text[start:pos]
        if not any(c.isdigit() for c in lit) or not lit.isascii():
            raise Bad()
        return Fraction(lit if not lit.endswith('.') else lit + '0')

    def factor():
        nonlocal pos
        c = peek()
        if c in ('+', '-'):
            pos += 1
            v = factor()
            return -v if c == '-' else v
        if c == '(':
            pos += 1
            v = expr()
            if peek() != ')':
                raise Bad()
            pos += 1
            return v
        if c.isdigit() or c == '.':
            return number()
        raise Bad()

    def term():
        nonlocal pos
        v = factor()
        while peek() in ('*', '/'):
            op = text[pos]
            pos += 1
            w = factor()
            if op == '*':
                v = None if v is None or w is None else v * w
            else:
                v = None if v is None or w is None or w == 0 else v / w  # None: divided by zero; the rest is still parsed
        return v

    def expr():
        nonlocal pos
        v = term()
        while peek() in ('+', '-'):
            op = text[pos]
            pos += 1
            w = term()
            v = None if v is None or w is None else (v + w if op == '+' else v - w)
        return v

    try:
        v = expr()
        if peek() != '':
            raise Bad()
    except Bad:
        return 2, ''
    if v is None:
        return 1, ''
    if v.denominator == 1:
        return 0, '%d\n' % v.numerator
    if Fraction(1, 10000) <= abs(v) < 10 ** 10:
        return 0, '%s\n' % repr(float('%.10g' % float(v)))
    return 0, float(v)  # the ticket does not fix the notation here: the output is checked as a number, to 10 digits


def run(calc, x):
    try:
        p = subprocess.run(['python3', calc, x], capture_output=True, text=True, timeout=20)
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        return None, ''


def same(a, b):
    """Exit codes equal and, when the exit code is 0, standard output equal (an error's text goes to standard error);
    where the expectation is a number, the output read as a number equals it to 10 significant digits."""
    if a[0] != b[0] or a[0] != 0:
        return a[0] == b[0]
    if isinstance(a[1], float):
        try:
            return abs(float(b[1]) - a[1]) <= 1e-9 * abs(a[1])
        except ValueError:
            return False
    return a[1] == b[1]


if __name__ == '__main__':
    if sys.argv[1] == 'ref':
        print(reference(sys.argv[2]))
    elif sys.argv[1] == 'freeze':
        kept, left = [], []
        for x in PROBES:
            ref, got = reference(x), [run(c, x) for c in sys.argv[3:]]
            if all(same(ref, g) for g in got):
                kept.append({'input': x, 'exit': ref[0], 'stdout': ref[1] if ref[0] == 0 else None})
            else:
                left.append({'input': x, 'reference': ref, 'programs': got})
        with open(sys.argv[2], 'w') as f:
            json.dump({'kept': kept, 'left_out': left}, f, indent=1)
        print('%d probes kept, %d left out' % (len(kept), len(left)))
        for r in left:
            print('  left out %r: reference %s, programs %s' % (r['input'], r['reference'], r['programs']))
    else:
        probes = json.load(open(sys.argv[2]))['kept']
        for arg in sys.argv[3:]:
            name, calc = arg.split('=', 1)
            bad = [(p['input'], run(calc, p['input'])) for p in probes]
            bad = [(x, g) for (x, g), p in zip(bad, probes) if not same((p['exit'], p['stdout']), g)]
            print('%-12s %d of %d differ%s' % (name, len(bad), len(probes), ''.join(
                '\n    %r -> exit %s %r' % (x, g[0], g[1].strip()) for x, g in bad)))
