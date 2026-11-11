# checkout

Order lines, percentage discounts, totals and a plain-text receipt. Python 3 standard library only.

```python
from checkout import Order, order_total_cents, render_receipt

order = Order()
order.add('Tea', 250, quantity=2)
order.add('Kettle', 2000, discount_percent=10)

order_total_cents(order)      # 2300
print(render_receipt(order))
# 2 x Tea                             5.00
# 1 x Kettle (-10%)                  18.00
# You saved                           2.00
# TOTAL                              23.00
```

## What is in it

- `LineItem(name, unit_price_cents, quantity=1, discount_percent=0)`: one line. Prices are whole cents.
  `discount_percent` is a whole number from 0 to 100.
- `Order()`: `order.add(name, unit_price_cents, quantity=1, discount_percent=0)` appends a line and returns it;
  `order.lines` is the list of lines.
- `line_gross_cents(line)`: unit price times quantity.
- `line_total_cents(line)`: the line after its discount.
- `order_subtotal_cents(order)`, `order_total_cents(order)`, `order_discount_cents(order)`: the order before
  discounts, after discounts, and the difference.
- `format_cents(cents)` and `render_receipt(order)`: text output.

## Tests

```
python3 -m unittest discover -s tests
```
