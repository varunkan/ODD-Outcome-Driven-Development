"""A text buffer: one piece of text that is changed by inserting, deleting and replacing ranges."""


class TextBuffer:
    """Holds text. Positions count characters from 0. A range `start, end` runs from `start` up to, but not
    including, `end`."""

    def __init__(self, text=''):
        self._text = self._checked(text)

    @staticmethod
    def _checked(text):
        if not isinstance(text, str):
            raise TypeError('text must be a string')
        return text

    def _check_range(self, start, end):
        for position in (start, end):
            if isinstance(position, bool) or not isinstance(position, int):
                raise TypeError('a position must be a whole number')
        if not 0 <= start <= end <= len(self._text):
            raise IndexError('%d:%d is outside the text, which is %d long' % (start, end, len(self._text)))

    @property
    def text(self):
        return self._text

    def __len__(self):
        return len(self._text)

    def __str__(self):
        return self._text

    # Changing the text

    def insert(self, position, text):
        """Insert `text` so that it starts at `position`."""
        self._checked(text)
        self._check_range(position, position)
        self._text = self._text[:position] + text + self._text[position:]

    def append(self, text):
        """Add `text` at the end."""
        self.insert(len(self._text), text)

    def delete(self, start, end):
        """Remove the range and return the text that was in it."""
        self._check_range(start, end)
        removed = self._text[start:end]
        self._text = self._text[:start] + self._text[end:]
        return removed

    def replace(self, start, end, text):
        """Put `text` in place of the range and return the text that was there."""
        self._checked(text)
        removed = self.delete(start, end)
        self.insert(start, text)
        return removed

    def clear(self):
        """Remove everything and return what was there."""
        return self.delete(0, len(self._text))

    # Reading the text

    def slice(self, start, end):
        """The text in the range."""
        self._check_range(start, end)
        return self._text[start:end]

    def find(self, needle, start=0):
        """Where `needle` first occurs at or after `start`, or -1."""
        return self._text.find(needle, start)

    def lines(self):
        """The text as a list of lines, without their line breaks."""
        return self._text.split('\n')

    @property
    def line_count(self):
        return self._text.count('\n') + 1

    def line_span(self, position):
        """`(start, end)` of the line that holds `position`. `end` is where the line break is, or the end of the
        text on the last line."""
        self._check_range(position, position)
        start = self._text.rfind('\n', 0, position) + 1
        end = self._text.find('\n', position)
        return start, (len(self._text) if end == -1 else end)
