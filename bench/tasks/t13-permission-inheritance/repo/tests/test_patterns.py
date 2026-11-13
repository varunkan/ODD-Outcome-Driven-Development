import unittest

from rolegate.patterns import check_resource, is_literal, matches, split


class MatchTest(unittest.TestCase):
    def test_literal(self):
        self.assertTrue(matches('docs/a.txt', 'docs/a.txt'))
        self.assertFalse(matches('docs/a.txt', 'docs/b.txt'))
        self.assertFalse(matches('docs', 'docs/a.txt'))

    def test_one_segment(self):
        self.assertTrue(matches('docs/*', 'docs/a'))
        self.assertFalse(matches('docs/*', 'docs/a/b'))
        self.assertFalse(matches('docs/*', 'docs'))
        self.assertTrue(matches('*/readme', 'src/readme'))

    def test_any_segments(self):
        for resource in ('docs', 'docs/a', 'docs/a/b/c'):
            with self.subTest(resource=resource):
                self.assertTrue(matches('docs/**', resource))
        self.assertFalse(matches('docs/**', 'doc'))
        self.assertTrue(matches('**', 'anything/at/all'))
        self.assertTrue(matches('docs/**/q3.pdf', 'docs/finance/2026/q3.pdf'))
        self.assertTrue(matches('docs/**/q3.pdf', 'docs/q3.pdf'))
        self.assertFalse(matches('docs/**/q3.pdf', 'docs/finance/q4.pdf'))

    def test_wildcards_only_as_whole_segments(self):
        self.assertFalse(matches('docs/q*.pdf', 'docs/q3.pdf'))
        self.assertTrue(matches('docs/q*.pdf', 'docs/q*.pdf'))
        self.assertFalse(is_literal('docs/*'))
        self.assertTrue(is_literal('docs/q*.pdf'))


class PathTest(unittest.TestCase):
    def test_bad_paths(self):
        for bad in ('', '/docs', 'docs/', 'docs//a', None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                split(bad)

    def test_resources_have_no_wildcards(self):
        with self.assertRaises(ValueError):
            check_resource('docs/*')
        self.assertEqual(check_resource('docs/a'), 'docs/a')
