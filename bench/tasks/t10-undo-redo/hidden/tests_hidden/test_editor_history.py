"""Acceptance tests for the undo and redo request: the editor. Copied into the repository after the session ends."""
import unittest

from editor.buffer import TextBuffer
from editor.session import Editor


def state(editor):
    return editor.text, editor.cursor


class EditorUndoRedoTests(unittest.TestCase):

    def test_nothing_to_undo_or_redo_leaves_text_and_cursor_alone(self):
        editor = Editor(TextBuffer('hello'))
        editor.move_to(2)
        self.assertIs(editor.undo(), False)
        self.assertIs(editor.redo(), False)
        self.assertEqual(state(editor), ('hello', 2))

    def test_the_example_from_the_request(self):
        editor = Editor()
        editor.type('hello')
        self.assertEqual(state(editor), ('hello', 5))
        editor.move_to(0)
        editor.type('>> ')
        self.assertEqual(state(editor), ('>> hello', 3))
        editor.move_to(8)
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('hello', 0))
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('', 0))
        self.assertIs(editor.redo(), True)
        self.assertEqual(state(editor), ('hello', 5))
        self.assertIs(editor.redo(), True)
        self.assertEqual(state(editor), ('>> hello', 3))
        self.assertIs(editor.redo(), False)
        self.assertEqual(state(editor), ('>> hello', 3))

    def test_backspace_is_undone_with_the_cursor_where_it_was(self):
        editor = Editor()
        editor.type('hello world')
        editor.move_to(5)
        self.assertEqual(editor.backspace(3), 'llo')
        self.assertEqual(state(editor), ('he world', 2))
        editor.move_to(8)
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('hello world', 5))
        editor.move_to(0)
        self.assertIs(editor.redo(), True)
        self.assertEqual(state(editor), ('he world', 2))

    def test_delete_forward_is_undone_with_the_cursor_where_it_was(self):
        editor = Editor()
        editor.type('hello world')
        editor.move_to(1)
        self.assertEqual(editor.delete_forward(4), 'ello')
        self.assertEqual(state(editor), ('h world', 1))
        editor.move_to(7)
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('hello world', 1))
        editor.move_to(11)
        self.assertIs(editor.redo(), True)
        self.assertEqual(state(editor), ('h world', 1))

    def test_moving_the_cursor_is_not_a_step(self):
        editor = Editor()
        editor.type('one\ntwo')
        editor.move_to(1)
        editor.move(2)
        editor.home()
        editor.end()
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('', 0))
        self.assertIs(editor.undo(), False)
        editor.move_to(0)
        self.assertIs(editor.redo(), True)
        self.assertEqual(state(editor), ('one\ntwo', 7))

    def test_several_steps_are_undone_and_redone_with_their_cursors(self):
        editor = Editor()
        editor.type('abc')              # abc|
        editor.type('def')              # abcdef|
        editor.move_to(3)
        editor.backspace(1)             # ab|def
        editor.delete_forward(2)        # ab|f
        editor.type('-')                # ab-|f
        self.assertEqual(state(editor), ('ab-f', 3))
        editor.move_to(0)
        expected = [('abf', 2), ('abdef', 2), ('abcdef', 3), ('abc', 3), ('', 0)]
        for want in expected:
            self.assertIs(editor.undo(), True)
            self.assertEqual(state(editor), want)
        self.assertIs(editor.undo(), False)
        self.assertEqual(state(editor), ('', 0))
        for want in (('abc', 3), ('abcdef', 6), ('abdef', 2), ('abf', 2), ('ab-f', 3)):
            self.assertIs(editor.redo(), True)
            self.assertEqual(state(editor), want)
        self.assertIs(editor.redo(), False)

    def test_typing_after_an_undo_discards_what_could_be_redone(self):
        editor = Editor()
        editor.type('one')
        editor.type(' two')
        editor.undo()
        editor.type(' three')
        self.assertIs(editor.redo(), False)
        self.assertEqual(state(editor), ('one three', 9))
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('one', 3))

    def test_edits_that_change_nothing_are_not_steps(self):
        editor = Editor()
        editor.type('abc')
        editor.type('')
        editor.delete_forward(5)
        editor.move_to(0)
        editor.backspace(2)
        self.assertEqual(state(editor), ('abc', 0))
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('', 0))
        self.assertIs(editor.undo(), False)

    def test_editor_uses_the_history_of_its_buffer(self):
        editor = Editor(TextBuffer(history_limit=2))
        for letter in 'abc':
            editor.type(letter)
        self.assertIs(editor.undo(), True)
        self.assertIs(editor.undo(), True)
        self.assertEqual(state(editor), ('a', 1))
        self.assertIs(editor.undo(), False)
        self.assertEqual(state(editor), ('a', 1))
        self.assertIs(editor.buffer.can_undo, False)
        self.assertIs(editor.buffer.can_redo, True)
        self.assertIs(editor.redo(), True)
        self.assertEqual(state(editor), ('ab', 2))

    def test_editor_without_history_edits_as_before(self):
        editor = Editor(TextBuffer('hello', history_limit=0))
        editor.type(' world')
        self.assertEqual(editor.backspace(5), 'world')
        self.assertIs(editor.undo(), False)
        self.assertIs(editor.redo(), False)
        self.assertEqual(state(editor), ('hello ', 6))


if __name__ == '__main__':
    unittest.main()
