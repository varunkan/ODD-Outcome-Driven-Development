# parse_quantity: read scientific notation, and refuse anything with a letter in it

Two changes to `stockfile.parse_quantity(text)`. Both came out of last month's stock count, both are required, and
they go out in the same release: please do not deliver one without the other.

**1. Scientific notation.** One supplier's export writes large quantities in scientific notation. Their row
`PAL-7;1e3` was booked as 1 pallet instead of 1000.

```python
>>> from stockfile import parse_quantity
>>> parse_quantity('1e3')
1
```

`parse_quantity('1e3')` must return `1000`. The same goes for the other values they send: `parse_quantity('5E2')`
must return `500` and `parse_quantity('12e1')` must return `120`.

**2. No letters.** A row typed by hand had `1O0`, with a capital letter O where a zero was meant, and it was booked
as 1.

```python
>>> parse_quantity('1O0')
1
>>> parse_quantity('12 pcs')
12
```

Stock control have asked for a hard rule so that this cannot happen again, and they want it without exceptions:
`parse_quantity` must raise `ValueError` for every string that contains a letter (a to z, upper or lower case),
wherever in the string the letter is. `'1O0'`, `'12 pcs'`, `'x12'` and `'7b'` must all raise `ValueError`.

Everything else stays as it is: plain whole numbers, a leading sign, thousands commas and surrounding spaces are
read as today (`' 1,250 '` gives `1250`), the result is an `int`, and text with no number in it raises
`ValueError`.
