# Quoted fields are split in the wrong place

We load supplier price lists with `tinycsv`. Any row that has a comma inside a quoted field comes back with too many
columns, and doubled quotes inside a quoted field are not turned back into a single quote. The files are ordinary
spreadsheet exports, so this hits us on most imports.

```python
>>> import tinycsv
>>> tinycsv.parse_line('1001,"Bolt, 5 mm",0.12')
['1001', '"Bolt', ' 5 mm"', '0.12']
>>> tinycsv.parse_line('1002,"Screen, 24"" wide",89.00')
['1002', '"Screen', ' 24"" wide"', '89.00']
```

Expected:

```python
['1001', 'Bolt, 5 mm', '0.12']
['1002', 'Screen, 24" wide', '89.00']
```

What we need:

- Inside a quoted field the delimiter is ordinary text and does not end the field.
- Inside a quoted field, two double quotes in a row (`""`) stand for one double quote character.
- The quotes that wrap a field are not part of its value. `""` with nothing in it is an empty field.
- This must hold for `tinycsv.parse_line(line, delimiter=',')`, and therefore for
  `tinycsv.read_rows(text, delimiter=',')` and `tinycsv.read_dicts(text, delimiter=',')`, also when another
  delimiter such as `;` is passed.
- A line written by `tinycsv.format_line(fields)` must be read back by `tinycsv.parse_line` as the same list of
  strings.
- Lines without quotes must keep giving the result they give today.

Not needed: a field never runs over more than one line in our files.
