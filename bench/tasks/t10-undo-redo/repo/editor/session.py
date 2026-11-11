"""An editing session: a text buffer and the cursor that edits it."""
from .buffer import TextBuffer


class Editor:
    """Edits a `TextBuffer` at a cursor. The cursor is a position from 0 up to the length of the text."""

    def __init__(self, buffer=None):
        self.buffer = buffer if buffer is not None else TextBuffer()
        self.cursor = len(self.buffer)

    @property
    def text(self):
        return self.buffer.text

    # Moving the cursor

    def move_to(self, position):
        """Put the cursor at `position`, or as near to it as the text allows. Returns where the cursor is."""
        self.cursor = max(0, min(position, len(self.buffer)))
        return self.cursor

    def move(self, distance):
        """Move the cursor `distance` characters: forward, or back when it is negative."""
        return self.move_to(self.cursor + distance)

    def home(self):
        """Move to the start of the line the cursor is on."""
        return self.move_to(self.buffer.line_span(self.cursor)[0])

    def end(self):
        """Move to the end of the line the cursor is on."""
        return self.move_to(self.buffer.line_span(self.cursor)[1])

    # Editing at the cursor

    def type(self, text):
        """Insert `text` at the cursor and leave the cursor after it."""
        self.buffer.insert(self.cursor, text)
        self.cursor += len(text)

    def backspace(self, count=1):
        """Remove up to `count` characters before the cursor and return them. The cursor moves back with them."""
        start = max(0, self.cursor - count)
        removed = self.buffer.delete(start, self.cursor)
        self.cursor = start
        return removed

    def delete_forward(self, count=1):
        """Remove up to `count` characters after the cursor and return them. The cursor stays where it is."""
        end = min(len(self.buffer), self.cursor + count)
        return self.buffer.delete(self.cursor, end)
