# Undo and redo for the editor

People lose work in the editor because an edit cannot be taken back. `editor.buffer.TextBuffer` needs undo and redo,
and `editor.session.Editor` has to offer them as well. The history must not grow without end: a long session already
uses a lot of memory, so it keeps a limited number of steps.

## The buffer: `editor.buffer.TextBuffer`

- Every call that changes the text is one step: `insert`, `append`, `delete`, `replace` and `clear`. A `replace` is
  one step, not a delete followed by an insert.
- `undo()` takes back the newest step that has not been taken back yet, so that the text is exactly what it was
  before that step, and returns `True`. With nothing to take back it returns `False` and changes nothing.
- `redo()` makes the step that was undone last happen again and returns `True`. With nothing to redo it returns
  `False` and changes nothing.
- So steps are undone newest first, and redone in the order they were made.
- Making a new step throws away everything that could be redone.
- `can_undo` and `can_redo` are properties, `True` or `False`: would `undo()` or `redo()` do something right now?
- A call that leaves the text as it was is not a step: inserting or appending an empty string, deleting an empty
  range, clearing an empty buffer, replacing a range with the text it already holds. A call that raises is not a
  step either. Neither of them touches the history: whatever could be undone or redone before the call can still be
  undone or redone after it.
- The text a buffer is created with is not a step. A new buffer has nothing to undo.
- `TextBuffer(text="", history_limit=100)`: the buffer remembers at most `history_limit` steps. When one more is
  made, the oldest is forgotten and can no longer be undone. With `history_limit=0` nothing is remembered: `undo()`
  always returns `False`, and editing works as it does today. `history_limit` is a whole number of at least 0;
  anything else raises `ValueError`.
- Two buffers never share a history.

```python
from editor.buffer import TextBuffer

buffer = TextBuffer("hello", history_limit=2)
buffer.append(" world")         # "hello world"
buffer.replace(0, 5, "HELLO")   # "HELLO world"
buffer.delete(5, 11)            # "HELLO"
buffer.undo()                   # True, and buffer.text is "HELLO world"
buffer.undo()                   # True, "hello world"
buffer.undo()                   # False, still "hello world": the append was forgotten
buffer.redo()                   # True, "HELLO world"
buffer.insert(0, ">> ")         # ">> HELLO world"
buffer.redo()                   # False: the delete can no longer be redone
buffer.can_undo                 # True
```

## The editor: `editor.session.Editor`

- `Editor.undo()` and `Editor.redo()` do the same to the editor's buffer, and return the same `True` or `False`.
- They also put the cursor back. After an undo, `cursor` is where it was just before that step was made. After a
  redo, it is where it was just after that step was made. This holds for every step made through the editor:
  `type`, `backspace` and `delete_forward`.
- Moving the cursor (`move_to`, `move`, `home`, `end`) is not a step.
- With nothing to undo or redo, the cursor stays where it is.
- The editor uses the history of its buffer, so `Editor(TextBuffer(history_limit=20))` remembers 20 steps.

```python
from editor.session import Editor

editor = Editor()
editor.type("hello")            # editor.text is "hello", editor.cursor is 5
editor.move_to(0)
editor.type(">> ")              # ">> hello", cursor 3
editor.move_to(8)
editor.undo()                   # True: "hello", cursor 0
editor.undo()                   # True: "", cursor 0
editor.redo()                   # True: "hello", cursor 5
editor.redo()                   # True: ">> hello", cursor 3
editor.redo()                   # False
```

Everything else the buffer and the editor do today stays as it is.
