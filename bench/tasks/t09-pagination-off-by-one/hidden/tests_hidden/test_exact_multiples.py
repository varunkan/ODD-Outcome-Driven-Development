"""Acceptance tests for the one-page-too-many report. Copied into the repository after the session ends."""
import unittest

from paging.navigation import nearest_page, page_links
from paging.paginator import PageNotFound, Paginator


def numbered(count, per_page):
    """A paginator over the items 1..count."""
    return Paginator(list(range(1, count + 1)), per_page=per_page)


class ExactMultipleTests(unittest.TestCase):
    """The reported case: the number of items is an exact multiple of the page size."""

    def setUp(self):
        self.results = numbered(20, 10)

    def test_page_count_has_no_extra_page(self):
        self.assertEqual(self.results.num_pages, 2)
        for count, per_page, pages in ((10, 10, 1), (30, 10, 3), (3, 1, 3), (1, 1, 1), (100, 25, 4), (6, 2, 3)):
            self.assertEqual(numbered(count, per_page).num_pages, pages,
                             msg='%d items at %d to a page' % (count, per_page))

    def test_the_page_after_the_last_one_does_not_exist(self):
        with self.assertRaises(PageNotFound):
            self.results.page(3)
        with self.assertRaises(PageNotFound):
            numbered(10, 10).page(2)
        with self.assertRaises(PageNotFound):
            numbered(3, 1).page(4)

    def test_last_page_is_the_last_page_with_items(self):
        last = self.results.last_page()
        self.assertEqual(last.number, 2)
        self.assertEqual(list(last.items), list(range(11, 21)))
        only = numbered(10, 10).last_page()
        self.assertEqual(only.number, 1)
        self.assertEqual(list(only.items), list(range(1, 11)))

    def test_last_page_has_no_next_page(self):
        self.assertTrue(self.results.page(1).has_next)
        self.assertFalse(self.results.page(2).has_next)
        self.assertFalse(numbered(10, 10).page(1).has_next)
        one_each = numbered(3, 1)
        self.assertEqual([one_each.page(number).has_next for number in (1, 2, 3)], [True, True, False])

    def test_pages_and_page_range_stop_at_the_last_page(self):
        self.assertEqual(list(self.results.page_range), [1, 2])
        pages = list(self.results.pages())
        self.assertEqual([page.number for page in pages], [1, 2])
        self.assertEqual([list(page.items) for page in pages], [list(range(1, 11)), list(range(11, 21))])
        self.assertEqual(list(numbered(10, 10).page_range), [1])
        self.assertEqual([list(page.items) for page in numbered(4, 2).pages()], [[1, 2], [3, 4]])

    def test_page_links_offer_no_page_above_the_last(self):
        self.assertEqual(list(page_links(self.results, 1)), [1, 2])
        self.assertEqual(list(page_links(self.results, 2)), [1, 2])
        self.assertEqual(list(page_links(numbered(10, 10), 1)), [1])
        self.assertEqual(list(page_links(numbered(30, 10), 2)), [1, 2, 3])

    def test_nearest_page_for_a_number_that_is_too_high_is_the_real_last_page(self):
        page = nearest_page(self.results, 99)
        self.assertEqual(page.number, 2)
        self.assertEqual(list(page.items), list(range(11, 21)))
        self.assertEqual(nearest_page(self.results, 3).number, 2)
        self.assertEqual(nearest_page(numbered(10, 10), 2).number, 1)


class NeighbourTests(unittest.TestCase):
    """One item fewer, one item more, and no items at all: these must stay as they are."""

    def test_one_item_short_of_a_multiple(self):
        results = numbered(19, 10)
        self.assertEqual(results.num_pages, 2)
        self.assertEqual(list(results.last_page().items), list(range(11, 20)))
        self.assertTrue(results.page(1).has_next)
        self.assertFalse(results.page(2).has_next)
        with self.assertRaises(PageNotFound):
            results.page(3)
        self.assertEqual(list(page_links(results, 1)), [1, 2])

    def test_one_item_over_a_multiple(self):
        results = numbered(21, 10)
        self.assertEqual(results.num_pages, 3)
        self.assertEqual(list(results.last_page().items), [21])
        self.assertTrue(results.page(2).has_next)
        self.assertFalse(results.page(3).has_next)
        self.assertEqual([page.number for page in results.pages()], [1, 2, 3])
        self.assertEqual(nearest_page(results, 99).number, 3)
        with self.assertRaises(PageNotFound):
            results.page(4)

    def test_fewer_items_than_one_page(self):
        results = numbered(3, 10)
        self.assertEqual(results.num_pages, 1)
        self.assertEqual(list(results.last_page().items), [1, 2, 3])
        self.assertFalse(results.page(1).has_next)

    def test_an_empty_list_keeps_its_one_empty_page(self):
        nothing = Paginator([], per_page=10)
        self.assertEqual(nothing.num_pages, 1)
        self.assertEqual(list(nothing.page(1).items), [])
        self.assertFalse(nothing.page(1).has_next)
        self.assertEqual(list(nothing.last_page().items), [])
        self.assertEqual(list(nothing.page_range), [1])
        with self.assertRaises(PageNotFound):
            nothing.page(2)


if __name__ == '__main__':
    unittest.main()
