# Tax rounding: some invoices come out a cent short

Our accountant went through last quarter's invoices and found tax amounts one cent below what they should be. The
smallest case:

```python
>>> from invoicing import Book, Line
>>> book = Book()
>>> invoice = book.issue_invoice('Cafe Rosa', '2024-05-02', [Line('Oat milk 1l', 1, 130, '5')])
>>> invoice.tax
6
```

5 % of 1.30 is 6.5 cents, and she says that must be 7. The rule, as she wrote it down for us:

> Tax is worked out per line: the line's net amount (quantity x unit price) times its rate, rounded to the nearest
> cent. An amount exactly halfway between two cents is rounded away from zero: 6.5 cents is 7 cents, and on a
> credit note -6.5 cents is -7 cents. A document's tax is the sum of its lines' tax.

Please make every tax figure we produce follow it:

1. **Invoices** issued with `Book.issue_invoice(customer, date, lines)`: each line's `tax`, and so the document's
   `tax` and `total`.
2. **Credit notes** issued with `Book.refund(number, date, quantities=None)`: each line's `tax` by the same rule,
   worked out on the refunded (negative) net. She adds one rule of her own: a fully refunded invoice must come back
   to exactly zero. Once every unit of an invoice line has been refunded, in one credit note or in several, the
   credit-note lines for it must add up to exactly that line's net and tax with the sign turned. So the credit note
   that refunds the last units of a line gives back whatever of that line's tax has not been given back yet.
3. **The CSV export**, `invoicing.export.to_csv(documents)` and `invoicing.export.rows(documents)`. Her software
   matches every row against the document it names and rejects the whole file if a figure is off by one cent. Each
   row's `tax` must be the tax that document charged at that rate (the sum of its lines' tax at that rate), `net`
   and `gross` likewise, and the `TOTAL` row the sum of the rows.

The documents already in our `book.json` were issued under the old rounding, and an issued document must never
change. `Book.get`, `render` and the export keep showing their figures exactly as they were issued, and refunding
one of them follows point 2 like any other invoice: a line refunded in full gives back exactly what it was charged,
even where the new rule would have charged a cent more. Only documents issued from now on use the new rule. The
book file format stays as it is.
