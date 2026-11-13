import unittest

from editor.buffer import TextBuffer
from editor.session import Editor


class EditorTests(unittest.TestCase):

    def test_typing_and_removing_at_the_cursor(self):
        editor = Editor()
        editor.type('Dear Ann,\nthanks for teh flowers.')
        editor.move_to(24)
        self.assertEqual(editor.backspace(2), 'eh')
        editor.type('he')
        self.assertEqual(editor.text, 'Dear Ann,\nthanks for the flowers.')
        self.assertEqual(editor.cursor, 24)
        self.assertEqual(editor.delete_forward(8), ' flowers')
        self.assertEqual(editor.text, 'Dear Ann,\nthanks for the.')
        self.assertEqual(editor.cursor, 24)
        self.assertEqual(editor.backspace(100), 'Dear Ann,\nthanks for the')
        self.assertEqual(editor.delete_forward(100), '.')
        self.assertEqual((editor.text, editor.cursor), ('', 0))

    def test_the_cursor_stays_inside_the_text(self):
        editor = Editor(TextBuffer('one\ntwo'))
        self.assertEqual(editor.cursor, 7)
        self.assertEqual(editor.move_to(99), 7)
        self.assertEqual(editor.move_to(-3), 0)
        self.assertEqual(editor.move(5), 5)
        self.assertEqual(editor.move(-1), 4)
        self.assertEqual(editor.move(-10), 0)

    def test_home_and_end_stay_on_the_current_line(self):
        editor = Editor(TextBuffer('one\ntwo\nthree'))
        editor.move_to(5)
        self.assertEqual(editor.home(), 4)
        self.assertEqual(editor.end(), 7)
        editor.move_to(0)
        self.assertEqual(editor.end(), 3)
        self.assertEqual(editor.home(), 0)
        self.assertIs(editor.buffer.text, editor.text)


if __name__ == '__main__':
    unittest.main()
