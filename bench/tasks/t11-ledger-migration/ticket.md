# Pending and cancelled entries in the ledger

We keep the shop's bank accounts in ledgerbook. There are two things we cannot record today, and both have bitten
us at the month end:

- **Card payments that the bank has not cleared yet.** We book them on the day, but the bank statement only shows
  them two or three days later, so when we compare with the statement we cannot tell which entries the bank has
  not seen yet.
- **Entries that were cancelled**: a payment that bounced, a line imported twice. Today we delete them, and then
  the accountant asks where entry 412 went. We want to keep them in the ledger, marked as cancelled, and have them
  count for nothing.

Please give every entry a status: `'cleared'`, `'pending'` or `'void'`.

1. `Ledger.add(date, account, category, amount, memo='', status='cleared')` takes the status;
   `Ledger.set_status(entry_id, status)` changes it later. Entries (from `Ledger.get` and `Ledger.entries`) have a
   `status` attribute. Any other status raises `ValueError` and changes nothing; `set_status` on an id that does
   not exist raises `KeyError` like `get` does.
2. **A void entry counts for nothing, anywhere.** Not in `Ledger.balance` or `Ledger.balances`, not in the
   functions of `ledgerbook.balances`, not in any figure of `ledgerbook.report.monthly` (income, spending, net,
   by_category, the entries count, the closing balances) and not in `ledgerbook.budget.Budget` (`spent`,
   `remaining`, `over`). It is still listed by `Ledger.entries()` and `Ledger.get`, and it is still saved to and
   loaded from the file: the point is that it stays on record.
3. **A pending entry counts like a cleared one** in all of the above: the money has gone. Two additions so we can
   check against the bank statement:
   - `Ledger.cleared_balance(account, until=None)`: the balance counting only cleared entries, with `until` working
     like it does for `Ledger.balance`.
   - `report.monthly(ledger, year, month)` gets one more key, `'pending'`: the sum, in cents with its sign, of the
     amounts of the pending entries dated in that month.

   The closing balances in a month's report must stay exactly `Ledger.balances(until=<the month's last day>)`, as
   the README promises.
4. **Files.** `save` / `dumps` must store the status, and `load` / `loads` must give back the same entries: same
   ids, fields and statuses. Memos stay free text: any character except a line break, semicolons included, exactly
   as today.

   We have five years of ledger files written by the version we run now (the format in the README), in the backups
   and on the office laptop. Every one of them must still load, unchanged, with every entry in it cleared, and
   with every memo exactly as it was written. After loading one, saving it writes the new format, and that loads
   back the same.

Nothing else should change: the command line keeps working on old and new files, and entries with no status given
are cleared.
