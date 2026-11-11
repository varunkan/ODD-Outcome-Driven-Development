"""Acceptance tests for the undo and redo request: the buffer. Copied into the repository after the session ends."""
import unittest

from editor.buffer import TextBuffer


class UndoRedoTests(unittest.TestCase):

    def test_new_buffer_has_nothing_to_undo_or_redo(self):
        for buffer in (TextBuffer(), TextBuffer('hello')):
            before = buffer.text
            self.assertIs(buffer.can_undo, False)
            self.assertIs(buffer.can_redo, False)
            self.assertIs(buffer.undo(), False)
            self.assertIs(buffer.redo(), False)
            self.assertEqual(buffer.text, before)

    def test_insert_is_undone_and_redone(self):
        buffer = TextBuffer('hello')
        buffer.insert(2, '--')
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, 'hello')
        self.assertIs(buffer.redo(), True)
        self.assertEqual(buffer.text, 'he--llo')

    def test_delete_is_undone_and_redone(self):
        buffer = TextBuffer('hello world')
        self.assertEqual(buffer.delete(2, 9), 'llo wor')
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, 'hello world')
        self.assertIs(buffer.redo(), True)
        self.assertEqual(buffer.text, 'held')

    def test_append_and_clear_are_steps(self):
        buffer = TextBuffer('one')
        buffer.append(' two')
        buffer.clear()
        self.assertEqual(buffer.text, '')
        self.assertTrue(buffer.undo())
        self.assertEqual(buffer.text, 'one two')
        self.assertTrue(buffer.undo())
        self.assertEqual(buffer.text, 'one')
        self.assertFalse(buffer.undo())
        self.assertTrue(buffer.redo())
        self.assertTrue(buffer.redo())
        self.assertEqual(buffer.text, '')

    def test_replace_is_one_step(self):
        buffer = TextBuffer('hello world')
        buffer.replace(0, 5, 'good morning')
        self.assertEqual(buffer.text, 'good morning world')
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, 'hello world')
        self.assertIs(buffer.can_undo, False)
        self.assertIs(buffer.undo(), False)
        self.assertIs(buffer.redo(), True)
        self.assertEqual(buffer.text, 'good morning world')
        self.assertIs(buffer.can_redo, False)
        self.assertIs(buffer.redo(), False)

    def test_steps_are_undone_newest_first_and_redone_in_order(self):
        buffer = TextBuffer('abc')
        states = [buffer.text]
        for edit in (lambda: buffer.append('def'), lambda: buffer.delete(1, 3), lambda: buffer.replace(0, 2, 'XYZ'),
                     lambda: buffer.insert(1, '\n')):
            edit()
            states.append(buffer.text)
        self.assertEqual(states, ['abc', 'abcdef', 'adef', 'XYZef', 'X\nYZef'])
        for expected in reversed(states[:-1]):
            self.assertIs(buffer.undo(), True)
            self.assertEqual(buffer.text, expected)
        self.assertIs(buffer.undo(), False)
        self.assertEqual(buffer.text, 'abc')
        for expected in states[1:]:
            self.assertIs(buffer.redo(), True)
            self.assertEqual(buffer.text, expected)
        self.assertIs(buffer.redo(), False)
        self.assertEqual(buffer.text, 'X\nYZef')

    def test_can_undo_and_can_redo_follow_the_history(self):
        buffer = TextBuffer()
        buffer.append('a')
        self.assertIs(buffer.can_undo, True)
        self.assertIs(buffer.can_redo, False)
        buffer.append('b')
        buffer.undo()
        self.assertIs(buffer.can_undo, True)
        self.assertIs(buffer.can_redo, True)
        buffer.undo()
        self.assertIs(buffer.can_undo, False)
        self.assertIs(buffer.can_redo, True)
        buffer.redo()
        buffer.redo()
        self.assertIs(buffer.can_undo, True)
        self.assertIs(buffer.can_redo, False)

    def test_new_step_discards_what_could_be_redone(self):
        buffer = TextBuffer()
        buffer.append('a')
        buffer.append('b')
        buffer.append('c')
        buffer.undo()
        buffer.undo()
        buffer.append('X')
        self.assertEqual(buffer.text, 'aX')
        self.assertIs(buffer.can_redo, False)
        self.assertIs(buffer.redo(), False)
        self.assertEqual(buffer.text, 'aX')
        self.assertTrue(buffer.undo())
        self.assertEqual(buffer.text, 'a')
        self.assertTrue(buffer.undo())
        self.assertEqual(buffer.text, '')
        self.assertFalse(buffer.undo())

    def test_calls_that_change_nothing_are_not_steps(self):
        buffer = TextBuffer('abc')
        buffer.append('def')
        buffer.insert(3, '')
        buffer.append('')
        self.assertEqual(buffer.delete(2, 2), '')
        self.assertEqual(buffer.replace(1, 4, 'bcd'), 'bcd')
        self.assertEqual(buffer.text, 'abcdef')
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, 'abc')
        self.assertIs(buffer.can_undo, False)
        empty = TextBuffer()
        empty.clear()
        self.assertIs(empty.can_undo, False)
        self.assertIs(empty.undo(), False)

    def test_calls_that_change_nothing_keep_what_could_be_redone(self):
        buffer = TextBuffer('abc')
        buffer.append('def')
        buffer.undo()
        buffer.insert(1, '')
        buffer.delete(3, 3)
        buffer.replace(0, 3, 'abc')
        self.assertIs(buffer.can_redo, True)
        self.assertIs(buffer.redo(), True)
        self.assertEqual(buffer.text, 'abcdef')

    def test_call_that_raises_leaves_the_history_alone(self):
        buffer = TextBuffer('abc')
        buffer.append('def')
        buffer.append('ghi')
        buffer.undo()
        for edit in (lambda: buffer.insert(99, 'x'), lambda: buffer.delete(2, 50), lambda: buffer.replace(4, 9, 'zz')):
            with self.assertRaises(IndexError):
                edit()
        self.assertEqual(buffer.text, 'abcdef')
        self.assertIs(buffer.can_redo, True)
        self.assertIs(buffer.redo(), True)
        self.assertEqual(buffer.text, 'abcdefghi')
        self.assertTrue(buffer.undo())
        self.assertTrue(buffer.undo())
        self.assertEqual(buffer.text, 'abc')
        self.assertFalse(buffer.undo())

    def test_edits_still_return_what_they_removed(self):
        buffer = TextBuffer('hello world')
        self.assertEqual(buffer.replace(0, 5, 'HELLO'), 'hello')
        self.assertEqual(buffer.delete(5, 11), ' world')
        self.assertEqual(buffer.clear(), 'HELLO')
        self.assertEqual(len(buffer), 0)
        buffer.undo()
        self.assertEqual(len(buffer), 5)

    def test_buffers_do_not_share_a_history(self):
        first, second = TextBuffer('one'), TextBuffer('two')
        first.append('!')
        self.assertIs(second.can_undo, False)
        self.assertIs(second.undo(), False)
        self.assertEqual(second.text, 'two')
        self.assertIs(first.undo(), True)
        self.assertEqual(first.text, 'one')


class HistoryLimitTests(unittest.TestCase):

    def test_oldest_step_is_forgotten_beyond_the_limit(self):
        buffer = TextBuffer(history_limit=3)
        for letter in 'abcde':
            buffer.append(letter)
        for expected in ('abcd', 'abc', 'ab'):
            self.assertIs(buffer.undo(), True)
            self.assertEqual(buffer.text, expected)
        self.assertIs(buffer.can_undo, False)
        self.assertIs(buffer.undo(), False)
        self.assertEqual(buffer.text, 'ab')
        for expected in ('abc', 'abcd', 'abcde'):
            self.assertIs(buffer.redo(), True)
            self.assertEqual(buffer.text, expected)
        self.assertIs(buffer.redo(), False)

    def test_the_example_from_the_request(self):
        buffer = TextBuffer('hello', history_limit=2)
        buffer.append(' world')
        buffer.replace(0, 5, 'HELLO')
        buffer.delete(5, 11)
        self.assertEqual(buffer.text, 'HELLO')
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, 'HELLO world')
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, 'hello world')
        self.assertIs(buffer.undo(), False)
        self.assertEqual(buffer.text, 'hello world')
        self.assertIs(buffer.redo(), True)
        self.assertEqual(buffer.text, 'HELLO world')
        buffer.insert(0, '>> ')
        self.assertEqual(buffer.text, '>> HELLO world')
        self.assertIs(buffer.redo(), False)
        self.assertIs(buffer.can_undo, True)

    def test_limit_of_one_remembers_only_the_newest_step(self):
        buffer = TextBuffer('x', history_limit=1)
        buffer.append('y')
        buffer.append('z')
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, 'xy')
        self.assertIs(buffer.undo(), False)
        self.assertIs(buffer.redo(), True)
        self.assertEqual(buffer.text, 'xyz')

    def test_steps_thrown_away_by_a_new_step_do_not_count_towards_the_limit(self):
        buffer = TextBuffer(history_limit=2)
        buffer.append('a')
        buffer.append('b')
        buffer.undo()
        buffer.append('c')
        self.assertEqual(buffer.text, 'ac')
        self.assertIs(buffer.undo(), True)
        self.assertIs(buffer.undo(), True)
        self.assertEqual(buffer.text, '')
        self.assertIs(buffer.undo(), False)

    def test_limit_of_zero_remembers_nothing(self):
        buffer = TextBuffer('x', history_limit=0)
        buffer.append('y')
        self.assertEqual(buffer.replace(0, 1, 'X'), 'x')
        self.assertEqual(buffer.text, 'Xy')
        self.assertIs(buffer.can_undo, False)
        self.assertIs(buffer.undo(), False)
        self.assertIs(buffer.redo(), False)
        self.assertEqual(buffer.text, 'Xy')

    def test_default_limit_is_one_hundred_steps(self):
        buffer = TextBuffer()
        for number in range(101):
            buffer.append('%d,' % number)
        undone = 0
        while buffer.undo():
            undone += 1
            self.assertLessEqual(undone, 101)
        self.assertEqual(undone, 100)
        self.assertEqual(buffer.text, '0,')

    def test_limit_must_be_a_whole_number_of_at_least_zero(self):
        for limit in (-1, 2.5):
            with self.assertRaises(ValueError, msg='history_limit %r' % (limit,)):
                TextBuffer('hello', history_limit=limit)


if __name__ == '__main__':
    unittest.main()
