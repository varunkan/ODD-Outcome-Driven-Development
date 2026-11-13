# tinycsv

A small reader and writer for delimited text. Python 3 standard library only.

## Reading

```python
import tinycsv

tinycsv.parse_line('1001,Washer,0.04')
# ['1001', 'Washer', '0.04']

tinycsv.read_rows('a,b\n\nc,d\n')
# [['a', 'b'], ['c', 'd']]            blank lines are skipped

tinycsv.read_dicts('code,name\n1001,Washer\n')
# [{'code': '1001', 'name': 'Washer'}]
```

- `parse_line(line, delimiter=',')` returns the fields of one line as a list of strings.
- `read_rows(text, delimiter=',')` returns one list per non-blank line.
- `read_dicts(text, delimiter=',')` treats the first non-blank line as the header and returns one dictionary per
  data row. Short rows are padded with empty strings.

Every value is a string. Spaces around a field are kept. The delimiter is a single character. A field does not run
over more than one line.

## Writing

```python
tinycsv.format_line(['1001', 'Washer', 0.04])
# '1001,Washer,0.04'

tinycsv.write_rows([['a', 'b'], ['c', 'd']])
# 'a,b\nc,d\n'
```

- `format_line(fields, delimiter=',')` writes one line without a line ending. A value containing the delimiter or a
  double quote is wrapped in double quotes, and each double quote inside it is doubled.
- `write_rows(rows, delimiter=',')` writes every row, one per line.

## Tests

```
python3 -m unittest discover -s tests
```
