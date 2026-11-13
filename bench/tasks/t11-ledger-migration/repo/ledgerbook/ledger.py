"""The ledger: entries in memory, numbered from 1. Reading and writing files is store.py's job."""
from . import balances as _balances
from .entry import EDITABLE, Entry, check_entry


class Ledger:
    def __init__(self):
        self._entries = {}      # id -> Entry
        self._next_id = 1

    # writing

    def add(self, date, account, category, amount, memo=''):
        """Book an entry and return its id. Raises ValueError when a field is malformed."""
        entry = check_entry(Entry(self._next_id, date, account, category, amount, memo))
        self._entries[entry.id] = entry
        self._next_id += 1
        return entry.id

    def insert(self, entry):
        """Put back an entry that already has its id (used when a file is loaded)."""
        check_entry(entry)
        if entry.id in self._entries:
            raise ValueError('there is already an entry %d' % entry.id)
        self._entries[entry.id] = entry.copy()
        self._next_id = max(self._next_id, entry.id + 1)

    def edit(self, entry_id, **fields):
        """Change date, account, category, amount or memo of an entry. Returns the entry as it now is."""
        unknown = sorted(set(fields) - set(EDITABLE))
        if unknown:
            raise ValueError('cannot edit %s' % ', '.join(unknown))
        changed = self._find(entry_id).copy()
        for name, value in fields.items():
            setattr(changed, name, value)
        check_entry(changed)
        self._entries[entry_id] = changed
        return changed.copy()

    def remove(self, entry_id):
        """Delete an entry. Its id is never given out again."""
        self._find(entry_id)
        del self._entries[entry_id]

    # reading

    def get(self, entry_id):
        return self._find(entry_id).copy()

    def entries(self, account=None, category=None):
        """Every entry, ordered by date and then id, optionally only one account's or one category's."""
        chosen = [entry.copy() for entry in self._entries.values()
                  if (account is None or entry.account == account)
                  and (category is None or entry.category == category)]
        chosen.sort(key=lambda entry: (entry.date, entry.id))
        return chosen

    def accounts(self):
        return sorted({entry.account for entry in self._entries.values()})

    def categories(self):
        return sorted({entry.category for entry in self._entries.values()})

    def balance(self, account, until=None):
        """The balance of one account in cents, optionally up to and including the date `until`."""
        return _balances.balance(self.entries(account=account), account, until)

    def balances(self, until=None):
        """{account: balance in cents} for every account."""
        return _balances.balances(self.entries(), until)

    def __len__(self):
        return len(self._entries)

    def __contains__(self, entry_id):
        return entry_id in self._entries

    def _find(self, entry_id):
        try:
            return self._entries[entry_id]
        except KeyError:
            raise KeyError('no entry %r' % (entry_id,)) from None
