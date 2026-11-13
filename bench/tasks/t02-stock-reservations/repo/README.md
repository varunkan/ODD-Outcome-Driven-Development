# inventory

A small stock ledger for a stockroom: the items, what is on hand, and the movements behind it. Python 3, standard
library only.

## Modules

`inventory.ledger`

- `Ledger()` starts empty.
- `add_item(sku, name, reorder_level=0)` registers an item with nothing on hand.
- `receive(sku, quantity, note="")` books goods in; `ship(sku, quantity, note="")` books goods out and raises
  `InsufficientStock` when there is not enough.
- `adjust(sku, counted, note="")` sets the stock to a counted figure and returns the difference.
- `on_hand(sku)`, `item(sku)`, `skus()`, `history(sku=None)`.
- Quantities are positive whole numbers; anything else raises `ValueError`. An unknown SKU raises `UnknownSku`.

`inventory.errors`: `InventoryError`, with `UnknownSku` and `InsufficientStock` derived from it.

`inventory.report`

- `stock_rows(ledger)`: one dict per item in SKU order, with `sku`, `name`, `on_hand` and `reorder_level`.
- `low_stock(ledger)`: the SKUs at or below their reorder level.
- `render_table(ledger)`: the rows as a text table; items to reorder end with `LOW`.

`inventory.storage`

- `save(ledger, path)` writes the ledger to a JSON file; `read(path)` gives it back.
- `dump(ledger)` and `load(data)` do the same with plain data instead of a file.

## Example

```python
from inventory.ledger import Ledger
from inventory.report import render_table

ledger = Ledger()
ledger.add_item("BOLT-M8", "Bolt M8", reorder_level=20)
ledger.add_item("NUT-M8", "Nut M8", reorder_level=20)
ledger.receive("BOLT-M8", 100)
ledger.receive("NUT-M8", 30)
ledger.ship("NUT-M8", 12, note="order 17")
print(render_table(ledger))
```

```
SKU      Name     On hand  Reorder at
BOLT-M8  Bolt M8      100          20
NUT-M8   Nut M8        18          20  LOW
```

## File format

A saved ledger is one JSON object:

```json
{
  "version": 1,
  "items": [
    {"sku": "NUT-M8", "name": "Nut M8", "reorder_level": 20, "on_hand": 18}
  ],
  "history": [
    {"kind": "receive", "sku": "NUT-M8", "quantity": 30, "note": ""},
    {"kind": "ship", "sku": "NUT-M8", "quantity": 12, "note": "order 17"}
  ]
}
```

`read` refuses a file whose `version` it does not know.

## Tests

```
python3 -m unittest
```
