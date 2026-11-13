# invoicing

Invoices, credit notes and the quarterly CSV export for our wholesale business. Python 3 standard library only.

```python
from invoicing import Book, Line
from invoicing.export import to_csv

book = Book('book.json')                     # created on the first issue
invoice = book.issue_invoice('Cafe Rosa', '2024-05-02', [
    Line('Coffee beans 1kg', 4, 2500, '20'),  # 4 x 25.00 at 20 %
    Line('Oat milk 1l', 10, 130, '5'),        # 10 x 1.30 at 5 %
])
invoice.number, invoice.net, invoice.tax, invoice.total     # ('INV-0001', 11300, 2065, 13365)
note = book.refund('INV-0001', '2024-05-09', {0: 2})        # credit note CRN-0001 for 2 bags of beans
print(to_csv(book.documents()))
```

## Documents

- `Line(description, quantity, unit_price, rate)`: `unit_price` in cents, `rate` a percent string (`'20'`, `'5'`,
  `'7.5'`, `'0'`). `line.net` is quantity x unit price; `line.tax` is set when the document is issued.
- `Book(path=None)`: the issued documents, saved to a JSON file after every issue (in memory only without a path).
  - `issue_invoice(customer, date, lines)` returns the `Document`, numbered `INV-0001`, `INV-0002`, ...
  - `refund(number, date, quantities=None)` issues a credit note (`CRN-0001`, ...) against an invoice.
    `quantities` is `{line index: units}`, line indexes from 0; `None` refunds everything not refunded yet. A line
    can never be refunded for more units than it was invoiced for; `RefundError` otherwise.
  - `get(number)`, `documents(kind=None)`, `credit_notes_for(number)`, `refunded(number, index)`.
- `Document`: `number`, `kind` (`'invoice'` or `'credit'`), `customer`, `date`, `lines`, `refers_to` (a credit
  note's invoice), `net`, `tax`, `total`, `tax_by_rate()` and `render()`. On a credit note quantities, net and tax
  are negative.

The tax of a document is the sum of the tax of its lines. Once issued, a document's figures are stored and never
change.

## The book file

```json
{"format": 1, "documents": [
  {"number": "INV-0001", "kind": "invoice", "customer": "Cafe Rosa", "date": "2024-05-02",
   "lines": [{"description": "Oat milk 1l", "quantity": 10, "unit_price": 130, "rate": "5", "net": 1300, "tax": 65}]},
  {"number": "CRN-0001", "kind": "credit", "customer": "Cafe Rosa", "date": "2024-05-09",
   "refers_to": "INV-0001", "origin_lines": [0],
   "lines": [{"description": "Oat milk 1l", "quantity": -2, "unit_price": 130, "rate": "5", "net": -260, "tax": -13}]}
]}
```

`origin_lines` gives, for each line of a credit note, the index of the invoice line it refunds.

## Export

`invoicing.export.to_csv(documents)` writes the file the accountant imports: columns
`number,kind,date,customer,rate,net,tax,gross`, one row per document and tax rate (highest rate first), amounts
with two decimals, and a last `TOTAL` row. `invoicing.export.rows(documents)` gives the same rows as dictionaries
in cents. From the shell: `python3 -m invoicing export book.json --from 2024-04-01 --to 2024-06-30`.

## Tests

```
python3 -m unittest discover -s tests
```
