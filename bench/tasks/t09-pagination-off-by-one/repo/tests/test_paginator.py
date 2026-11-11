import unittest

from paging.paginator import Page, PageNotFound, Paginator


class PaginatorTests(unittest.TestCase):

    def setUp(self):
        self.results = Paginator(list(range(1, 26)), per_page=10)     # 25 items

    def test_a_list_is_split_into_pages(self):
        self.assertEqual(self.results.count, 25)
        self.assertEqual(self.results.num_pages, 3)
        self.assertEqual(list(self.results.page_range), [1, 2, 3])
        self.assertEqual(self.results.page(1).items, list(range(1, 11)))
        self.assertEqual(self.results.page(2).items, list(range(11, 21)))
        self.assertEqual(self.results.last_page().items, [21, 22, 23, 24, 25])
        self.assertEqual([len(page) for page in self.results.pages()], [10, 10, 5])

    def test_a_page_knows_its_neighbours_and_positions(self):
        first, last = self.results.first_page(), self.results.last_page()
        self.assertIsInstance(first, Page)
        self.assertFalse(first.has_previous)
        self.assertTrue(first.has_next)
        self.assertEqual(first.next_number, 2)
        self.assertTrue(last.has_previous)
        self.assertFalse(last.has_next)
        self.assertEqual(last.previous_number, 2)
        self.assertEqual((last.start_index, last.end_index), (21, 25))
        with self.assertRaises(PageNotFound):
            first.previous_number
        with self.assertRaises(PageNotFound):
            last.next_number

    def test_page_numbers_that_are_not_pages_are_refused(self):
        for bad in (0, -1, 4, '2', 1.0, None):
            with self.assertRaises(PageNotFound, msg='page %r' % (bad,)):
                self.results.page(bad)
        for bad in (0, -5, 2.5, '10'):
            with self.assertRaises(ValueError, msg='per_page %r' % (bad,)):
                Paginator([1, 2, 3], per_page=bad)

    def test_an_empty_list_has_one_empty_page(self):
        nothing = Paginator([])
        self.assertEqual(nothing.num_pages, 1)
        self.assertEqual(nothing.page(1).items, [])
        self.assertFalse(nothing.page(1).has_next)
        with self.assertRaises(PageNotFound):
            nothing.page(2)

    def test_the_page_an_item_is_on(self):
        self.assertEqual([self.results.page_of(position) for position in (1, 10, 11, 20, 21, 25)],
                         [1, 1, 2, 2, 3, 3])
        for bad in (0, 26):
            with self.assertRaises(IndexError):
                self.results.page_of(bad)


if __name__ == '__main__':
    unittest.main()
