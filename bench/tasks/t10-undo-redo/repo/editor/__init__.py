"""A small text editing core: a text buffer and an editing session with a cursor."""
from .buffer import TextBuffer
from .session import Editor

__all__ = ['Editor', 'TextBuffer']
