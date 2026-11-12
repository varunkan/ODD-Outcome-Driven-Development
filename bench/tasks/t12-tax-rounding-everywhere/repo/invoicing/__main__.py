"""python3 -m invoicing export BOOK [--from YYYY-MM-DD] [--to YYYY-MM-DD]   CSV for the accountant, on stdout
   python3 -m invoicing show BOOK NUMBER                                  one document as printed
"""
import argparse
import sys

from .book import Book
from .export import between, to_csv


def main(argv=None):
    parser = argparse.ArgumentParser(prog='invoicing')
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('export')
    command.add_argument('book')
    command.add_argument('--from', dest='start')
    command.add_argument('--to', dest='end')
    command = commands.add_parser('show')
    command.add_argument('book')
    command.add_argument('number')
    args = parser.parse_args(argv)
    book = Book(args.book)
    if args.command == 'export':
        sys.stdout.write(to_csv(between(book.documents(), args.start, args.end)))
    else:
        sys.stdout.write(book.get(args.number).render())
    return 0


if __name__ == '__main__':
    sys.exit(main())
