Build a command-line calculator in this repository.

`python3 calc.py "<expression>"` prints the result on one line and exits 0.

- Numbers: integers and decimals (`3`, `2.5`, `.5`).
- Operators `+ - * /` with the usual precedence, parentheses to any depth, and unary minus and plus, which may repeat
  (`--3` is 3). Spaces may appear anywhere between tokens.
- Output: a result that is a whole number prints without a decimal point (`6`, never `6.0`). Any other result prints
  rounded to 10 significant digits with no trailing zeros (`0.1 + 0.2` prints `0.3`; `1/3` prints `0.3333333333`).
- Division by zero prints `error: division by zero` to standard error and exits 1.
- An invalid expression prints `error: invalid expression` to standard error and exits 2. Invalid means: empty,
  unbalanced or empty parentheses, a character that is not a digit, a decimal point, an operator, a parenthesis or
  a space, two numbers in a row, two binary operators in a row (`2 * * 3`), or an operator with nothing after it.
- Called with no argument, or with more than one, it prints `usage: calc.py "<expression>"` to standard error and
  exits 2.
- Do not use `eval` or `exec`.
- Include unit tests under `tests/` that run with `python3 -m unittest`.
