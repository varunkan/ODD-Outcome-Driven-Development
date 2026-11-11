import unittest

from editor.buffer import TextBuffer


class TextBufferTests(unittest.TestCase):

    def test_text_is_inserted_deleted_and_replaced(self):
        buffer = TextBuffer('hello')
        buffer.append(' world')
        buffer.insert(0, '>> ')
        self.assertEqual(buffer.text, '>> hello world')
        self.assertEqual(buffer.delete(0, 3), '>> ')
        self.assertEqual(buffer.replace(0, 5, 'goodbye'), 'hello')
        self.assertEqual(buffer.text, 'goodbye world')
        self.assertEqual(len(buffer), 13)
        self.assertEqual(str(buffer), 'goodbye world')
        self.assertEqual(buffer.clear(), 'goodbye world')
        self.assertEqual(buffer.text, '')

    def test_positions_outside_the_text_are_refused(self):
        buffer = TextBuffer('hello')
        for edit in (lambda: buffer.insert(6, '!'), lambda: buffer.insert(-1, '!'), lambda: buffer.delete(3, 2),
                     lambda: buffer.delete(0, 6), lambda: buffer.replace(4, 9, '!'), lambda: buffer.slice(2, 8)):
            with self.assertRaises(IndexError):
                edit()
        for edit in (lambda: buffer.insert(0, 5), lambda: buffer.insert('0', 'x'), lambda: buffer.replace(0, 1, None),
                     lambda: TextBuffer(None)):
            with self.assertRaises(TypeError):
                edit()
        self.assertEqual(buffer.text, 'hello')

    def test_lines_and_search(self):
        buffer = TextBuffer('one\ntwo\n\nfour')
        self.assertEqual(buffer.lines(), ['one', 'two', '', 'four'])
        self.assertEqual(buffer.line_count, 4)
        self.assertEqual(TextBuffer().line_count, 1)
        self.assertEqual(buffer.line_span(0), (0, 3))
        self.assertEqual(buffer.line_span(5), (4, 7))
        self.assertEqual(buffer.line_span(8), (8, 8))
        self.assertEqual(buffer.line_span(13), (9, 13))
        self.assertEqual(buffer.find('two'), 4)
        self.assertEqual(buffer.find('o', 3), 6)
        self.assertEqual(buffer.find('five'), -1)
        self.assertEqual(buffer.slice(4, 7), 'two')


if __name__ == '__main__':
    unittest.main()
