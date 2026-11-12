"""Command line: python3 -m ledgerbook <command> FILE ...

    balance FILE [--until DATE]                 every account's balance
    add FILE DATE ACCOUNT CATEGORY AMOUNT [MEMO] book an entry (AMOUNT like -45.99); prints its id
    remove FILE ID                              delete an entry
    report FILE YYYY-MM                         the monthly report
    over FILE YYYY-MM CATEGORY=LIMIT ...        categories over their limit (LIMIT like 300.00)
    init FILE                                   start an empty ledger file
"""
import argparse
import os
import sys

from . import report as _report
from .budget import Budget
from .ledger import Ledger
from .money import format_amount, parse_amount
from .store import LedgerFormatError, load, save


def _year_month(text):
    try:
        year, month = text.split('-')
        year, month = int(year), int(month)
    except ValueError:
        raise argparse.ArgumentTypeError('expected YYYY-MM, got %r' % text) from None
    if not 1 <= month <= 12:
        raise argparse.ArgumentTypeError('expected YYYY-MM, got %r' % text)
    return year, month


def _limit(text):
    category, sep, amount = text.partition('=')
    if not sep or not category:
        raise argparse.ArgumentTypeError('expected CATEGORY=LIMIT, got %r' % text)
    try:
        return category, parse_amount(amount)
    except ValueError as problem:
        raise argparse.ArgumentTypeError(str(problem)) from None


def _parser():
    parser = argparse.ArgumentParser(prog='ledgerbook')
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('init')
    command.add_argument('file')
    command = commands.add_parser('balance')
    command.add_argument('file')
    command.add_argument('--until')
    command = commands.add_parser('add')
    command.add_argument('file')
    for name in ('date', 'account', 'category', 'amount'):
        command.add_argument(name)
    command.add_argument('memo', nargs='?', default='')
    command = commands.add_parser('remove')
    command.add_argument('file')
    command.add_argument('id', type=int)
    command = commands.add_parser('report')
    command.add_argument('file')
    command.add_argument('month', type=_year_month)
    command = commands.add_parser('over')
    command.add_argument('file')
    command.add_argument('month', type=_year_month)
    command.add_argument('limits', nargs='+', type=_limit)
    return parser


def main(argv=None, out=None):
    out = out or sys.stdout
    args = _parser().parse_args(argv)
    try:
        if args.command == 'init':
            if os.path.exists(args.file):
                raise ValueError('%s exists already' % args.file)
            save(Ledger(), args.file)
            return 0
        ledger = load(args.file)
        if args.command == 'balance':
            for account, amount in ledger.balances(args.until).items():
                out.write('%-20s %14s\n' % (account, format_amount(amount, thousands=True)))
        elif args.command == 'add':
            entry_id = ledger.add(args.date, args.account, args.category, parse_amount(args.amount), args.memo)
            save(ledger, args.file)
            out.write('%d\n' % entry_id)
        elif args.command == 'remove':
            ledger.remove(args.id)
            save(ledger, args.file)
        elif args.command == 'report':
            out.write(_report.render(_report.monthly(ledger, *args.month)))
        elif args.command == 'over':
            for category, used, limit in Budget(dict(args.limits)).over(ledger, *args.month):
                out.write('%s: spent %s of %s\n' % (category, format_amount(used), format_amount(limit)))
        return 0
    except (OSError, KeyError, ValueError, LedgerFormatError) as problem:
        sys.stderr.write('ledgerbook: %s\n' % (problem.args[0] if isinstance(problem, KeyError) else problem))
        return 1
