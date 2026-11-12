"""The ledger file: plain UTF-8 text, one entry per line, so it can be read, diffed and backed up as it is.

    ledgerbook 1
    1;2024-03-01;checking;salary;250000;March pay
    2;2024-03-02;checking;groceries;-4599;market; bread and cheese

The first line names the format. Every other line is one entry: id, date, account, category, amount in cents and
memo, separated by semicolons. The memo is last and is free text: it may contain semicolons, so a line is split at
its first five semicolons only. Blank lines are ignored.
"""
import os
import tempfile

from .entry import Entry
from .ledger import Ledger

HEADER = 'ledgerbook 1'
SEPARATOR = ';'


class LedgerFormatError(ValueError):
    """The text is not a ledger file this version can read. `line` is the 1-based line number, when known."""

    def __init__(self, message, line=None):
        super().__init__(message if line is None else 'line %d: %s' % (line, message))
        self.line = line


def _entry_line(entry):
    return SEPARATOR.join((str(entry.id), entry.date, entry.account, entry.category, str(entry.amount), entry.memo))


def dumps(ledger):
    """The whole ledger as the text of a ledger file."""
    lines = [HEADER]
    lines.extend(_entry_line(entry) for entry in sorted(ledger.entries(), key=lambda entry: entry.id))
    return '\n'.join(lines) + '\n'


def _parse_int(text, what, number):
    try:
        if text.strip() != text or not text:
            raise ValueError(text)
        return int(text)
    except ValueError:
        raise LedgerFormatError('%s is not a whole number: %r' % (what, text), number) from None


def _parse_line(line, number):
    parts = line.split(SEPARATOR, 5)
    if len(parts) != 6:
        raise LedgerFormatError('expected id;date;account;category;amount;memo, got %r' % line, number)
    entry_id, date, account, category, amount, memo = parts
    return Entry(_parse_int(entry_id, 'id', number), date, account, category, _parse_int(amount, 'amount', number),
                 memo)


def loads(text):
    """A Ledger from the text of a ledger file. Raises LedgerFormatError when the text is not one."""
    lines = text.split('\n')
    if lines[0].lstrip('\ufeff').rstrip('\r') != HEADER:
        raise LedgerFormatError('not a ledgerbook file, or a format this version cannot read: %r' % lines[0][:40], 1)
    ledger = Ledger()
    for number, line in enumerate(lines[1:], start=2):
        line = line.rstrip('\r')
        if not line.strip():
            continue
        entry = _parse_line(line, number)
        try:
            ledger.insert(entry)
        except ValueError as problem:
            raise LedgerFormatError(str(problem), number) from None
    return ledger


def dump(ledger, handle):
    handle.write(dumps(ledger))


def save(ledger, path):
    """Write the ledger to `path`. The old file is replaced only once the new one is completely written."""
    directory = os.path.dirname(os.path.abspath(path))
    descriptor, temporary = tempfile.mkstemp(prefix='.ledger-', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            dump(ledger, handle)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def load(path):
    """The Ledger stored at `path`."""
    with open(path, encoding='utf-8', newline='') as handle:
        return loads(handle.read())
