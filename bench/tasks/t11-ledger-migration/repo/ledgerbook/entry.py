"""One entry of the ledger: money into (positive) or out of (negative) one account, filed under one category."""
import datetime

FIELDS = ('id', 'date', 'account', 'category', 'amount', 'memo')
EDITABLE = ('date', 'account', 'category', 'amount', 'memo')


class Entry:
    """A plain record. Ledger hands out copies, so changing an Entry you were given changes nothing stored."""

    __slots__ = FIELDS

    def __init__(self, id, date, account, category, amount, memo=''):
        self.id = id
        self.date = date
        self.account = account
        self.category = category
        self.amount = amount
        self.memo = memo

    @property
    def month(self):
        """'2024-03' for an entry dated '2024-03-17'."""
        return self.date[:7]

    def copy(self):
        return Entry(*self.as_tuple())

    def as_tuple(self):
        return tuple(getattr(self, name) for name in FIELDS)

    def __eq__(self, other):
        if not isinstance(other, Entry):
            return NotImplemented
        return self.as_tuple() == other.as_tuple()

    def __repr__(self):
        return 'Entry(%s)' % ', '.join('%s=%r' % (name, getattr(self, name)) for name in FIELDS)


def _check_name(field, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('%s must be a non-empty string' % field)
    if value != value.strip():
        raise ValueError('%s must not start or end with spaces: %r' % (field, value))
    if any(bad in value for bad in (';', '\n', '\r')):
        raise ValueError('%s must not contain a semicolon or a line break: %r' % (field, value))


def check_entry(entry):
    """Raise ValueError unless every field of the entry is well formed. Returns the entry."""
    if isinstance(entry.id, bool) or not isinstance(entry.id, int) or entry.id < 1:
        raise ValueError('id must be a whole number from 1 up, got %r' % (entry.id,))
    if not isinstance(entry.date, str):
        raise ValueError('date must be text like 2024-03-17, got %r' % (entry.date,))
    try:
        parsed = datetime.datetime.strptime(entry.date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('date must be a real date like 2024-03-17, got %r' % entry.date) from None
    if parsed.isoformat() != entry.date:
        raise ValueError('date must be written as YYYY-MM-DD, got %r' % entry.date)
    _check_name('account', entry.account)
    _check_name('category', entry.category)
    if isinstance(entry.amount, bool) or not isinstance(entry.amount, int):
        raise ValueError('amount must be a whole number of cents, got %r' % (entry.amount,))
    if entry.amount == 0:
        raise ValueError('an entry of zero moves no money')
    if not isinstance(entry.memo, str) or '\n' in entry.memo or '\r' in entry.memo:
        raise ValueError('memo must be text on one line, got %r' % (entry.memo,))
    return entry
