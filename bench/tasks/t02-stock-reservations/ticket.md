# Reserve stock for orders

When a sales order comes in we want to put its stock aside, so it cannot be shipped to someone else before the order
is packed. Today the ledger in the `inventory` package only knows what is on hand.

## Ledger (`inventory.ledger.Ledger`)

- `reserve(sku, quantity, ref)` holds `quantity` units of `sku` for the order `ref` (a string such as `"SO-1042"`).
  One order can hold several SKUs, and reserving the same SKU again for the same order adds to what it already
  holds. `quantity` follows the same rule as in `receive`: a positive whole number, otherwise `ValueError`.
  Reserving more than is available raises `inventory.errors.InsufficientStock` and changes nothing: what was held
  before stays held, and nothing is added.
- `release(ref)` drops everything held for that order and returns the number of units it freed. For an order that
  holds nothing it returns 0; that is not an error.
- `available(sku)` is what is on hand minus what is held for any order. `on_hand(sku)` keeps its meaning: reserving
  does not move stock.
- `reserve` and `available` raise `inventory.errors.UnknownSku` for a SKU the ledger does not have, like the other
  ledger methods.
- `ship(sku, quantity)` must not take reserved stock: it raises `InsufficientStock` when `quantity` is more than
  `available(sku)`. Shipping a reserved order stays two calls, `release(ref)` and then `ship(...)`; nothing fancier
  is needed.

```python
from inventory.ledger import Ledger

ledger = Ledger()
ledger.add_item("BOLT-M8", "Bolt M8", reorder_level=20)
ledger.receive("BOLT-M8", 100)
ledger.reserve("BOLT-M8", 30, "SO-1042")
ledger.on_hand("BOLT-M8")      # 100
ledger.available("BOLT-M8")    # 70
ledger.ship("BOLT-M8", 80)     # InsufficientStock
ledger.release("SO-1042")      # 30
ledger.available("BOLT-M8")    # 100
```

## Report (`inventory.report`)

- Every row from `stock_rows(ledger)` gains `"reserved"` and `"available"` next to `"on_hand"`.
- `low_stock(ledger)` goes by what is available, not by what is on hand: an item is low when its available quantity
  is at or below its reorder level.
- `render_table(ledger)` shows two more columns, headed `Reserved` and `Available`, between `On hand` and
  `Reorder at`.

## Storage (`inventory.storage`)

- Reservations survive `save(ledger, path)` and `read(path)`: after reading the file back, the same orders hold the
  same quantities.
- Files saved before this change must still open with `read`, with nothing reserved.
