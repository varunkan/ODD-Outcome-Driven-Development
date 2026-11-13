# editor

The editing core of a small text editor: the text, and a cursor to edit it with. No screen and no files, only the
text. Python 3, standard library only.

## What is in it

`editor.buffer`: the text.

- `TextBuffer(text="")`. Positions count characters from 0, and a range `start, end` runs from `start` up to, but
  not including, `end`.
- `insert(position, text)` and `append(text)` add text.
- `delete(start, end)` removes a range, `replace(start, end, text)` puts other text in its place and `clear()`
  removes everything. Each returns the text it took out.
- `text` is the whole text and `len(buffer)` its length. `slice(start, end)`, `find(needle, start=0)`, `lines()`,
  `line_count` and `line_span(position)` read parts of it.
- A position or range outside the text raises `IndexError` and changes nothing. Text that is not a string raises
  `TypeError`.

`editor.session`: editing at a cursor.

- `Editor(buffer=None)` edits the buffer it is given, or a new empty one. `buffer` is that buffer, `text` its text
  and `cursor` a position from 0 up to the length of the text. It starts at the end.
- `move_to(position)` and `move(distance)` move the cursor and keep it inside the text. `home()` and `end()` go to
  the start and the end of the current line.
- `type(text)` inserts at the cursor and leaves the cursor after the new text.
- `backspace(count=1)` removes characters before the cursor, `delete_forward(count=1)` after it. Both return what
  they removed.

## Example

```python
from editor.session import Editor

editor = Editor()
editor.type("Dear Ann,\nthanks for teh flowers.")
editor.move_to(24)              # just after "teh"
editor.backspace(2)             # "eh"
editor.type("he")
editor.text                     # "Dear Ann,\nthanks for the flowers."
editor.home()                   # 10: the start of the second line
editor.buffer.line_count        # 2
```

## Tests

```
python3 -m unittest
```
