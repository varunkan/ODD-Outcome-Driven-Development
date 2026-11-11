# Discounted totals are a cent out, and receipt lines do not add up to the total

Totals from `checkout` are wrong on some discounted orders. The one a customer showed us: one Notebook at 9.95 with
15% off. 9.95 less 15% is 8.4575, so the price is 8.46. We charged 8.45.

```python
>>> from checkout import Order, line_total_cents, order_total_cents
>>> order = Order()
>>> line = order.add('Notebook', 995, quantity=1, discount_percent=15)
>>> line_total_cents(line), order_total_cents(order)
(845, 845)
```

Expected: `(846, 846)`.

On longer orders we also see receipts where the amounts printed per line do not add up to the printed total.

The rule the accounts team works to, and which the code has to follow:

1. All money is whole cents held as `int`. `line_total_cents(line)` and `order_total_cents(order)` return an `int`.
2. A line's amount is unit price × quantity, less the line's discount percentage, rounded to whole cents. It is the
   amount the customer pays for the line that is rounded.
3. Rounding is half up: exactly half a cent always goes up to the next cent. Less than half goes down, more than
   half goes up.
4. Rounding is done once per line, on the line's amount: not on each unit, and not on the order as a whole.
5. The order total is the sum of the rounded line amounts, so a receipt always adds up.

The interface stays as it is:

- `checkout.LineItem(name, unit_price_cents, quantity=1, discount_percent=0)`
- `checkout.Order()`, with `order.add(name, unit_price_cents, quantity=1, discount_percent=0)` returning the new
  line, and `order.lines` holding the lines
- `checkout.line_total_cents(line)` and `checkout.order_total_cents(order)`

`discount_percent` is a whole number from 0 to 100.
