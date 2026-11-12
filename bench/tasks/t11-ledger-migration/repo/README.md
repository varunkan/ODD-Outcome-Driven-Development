# ledgerbook

The shop's bank-account ledger. Entries live in memory in a `Ledger` and on disk in one plain text file per
ledger. Python 3 standard library only.

```python
from ledgerbook import Ledger, load, save
from ledgerbook import report
from ledgerbook.budget import Budget

ledger = Ledger()
ledger.add('2024-03-01', 'checking', 'salary', 250000, 'March pay')          # returns the id, 1
ledger.add('2024-03-02', 'checking', 'groceries', -4599, 'market; bread and cheese')
ledger.balance('checking')            # 245401 (cents)
ledger.balances()                     # {'checking': 245401}
save(ledger, 'shop.ledger')
ledger = load('shop.ledger')

report.monthly(ledger, 2024, 3)       # {'month': '2024-03', 'income': 250000, 'spending': 4599, ...}
Budget({'groceries': 30000}).spent(ledger, 'groceries', 2024, 3)     # 4599
```

## Entries

An entry has an `id` (given by the ledger, from 1, never reused), a `date` (`YYYY-MM-DD`), an `account` (the bank
account the money moved in), a `category`, an `amount` in whole cents (positive: money in; negative: money out;
never zero) and a `memo` (free text on one line). Account and category names cannot contain a semicolon.

- `Ledger.add(date, account, category, amount, memo='')` returns the new id.
- `Ledger.get(entry_id)`, `Ledger.edit(entry_id, **fields)`, `Ledger.remove(entry_id)`.
- `Ledger.entries(account=None, category=None)`: copies, ordered by date then id.
- `Ledger.balance(account, until=None)`, `Ledger.balances(until=None)`: in cents, `until` a date, inclusive.

## Totals

- `ledgerbook.balances`: `balance(entries, account, until=None)`, `balances(entries, until=None)`, `net_worth`.
- `ledgerbook.report.monthly(ledger, year, month)`: a dictionary with `month`, `income`, `spending` (positive),
  `net`, `by_category`, `entries` (the count) and `closing` (every account's balance at the end of the month).
  `report.render(r)` turns it into the text we e-mail to the accountant; `report.yearly(ledger, year)`.
- `ledgerbook.budget.Budget(limits)`: `spent(ledger, category, year, month)`, `remaining(...)`,
  `over(ledger, year, month)`.

The closing balances of a month's report are always the same numbers as `Ledger.balances(until=<last day>)`.

## The file

```
ledgerbook 1
1;2024-03-01;checking;salary;250000;March pay
2;2024-03-02;checking;groceries;-4599;market; bread and cheese
```

UTF-8. The first line names the format. Every other line is one entry: id, date, account, category, amount in
cents, memo. The memo is last and may contain semicolons, so a line is split at its first five semicolons. Blank
lines are ignored. `save` replaces the file only once the new one is fully written. `load` raises
`LedgerFormatError` for text it cannot read.

## Command line

```
python3 -m ledgerbook init shop.ledger
python3 -m ledgerbook add shop.ledger 2024-03-02 checking groceries -45.99 "market"
python3 -m ledgerbook balance shop.ledger
python3 -m ledgerbook report shop.ledger 2024-03
python3 -m ledgerbook over shop.ledger 2024-03 groceries=300.00
```

## Tests

```
python3 -m unittest discover -s tests
```
