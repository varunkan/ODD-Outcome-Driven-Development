import unittest

from paging.navigation import nearest_page, page_links, summary
from paging.paginator import PageNotFound, Paginator


class NavigationTests(unittest.TestCase):

    def test_links_show_the_ends_and_the_pages_around_the_current_one(self):
        results = Paginator(list(range(95)), per_page=10)     # 10 pages
        self.assertEqual(page_links(results, 5), [1, None, 3, 4, 5, 6, 7, None, 10])
        self.assertEqual(page_links(results, 1), [1, 2, 3, None, 10])
        self.assertEqual(page_links(results, 10), [1, None, 8, 9, 10])
        self.assertEqual(page_links(results, 5, around=0), [1, None, 5, None, 10])
        self.assertEqual(page_links(Paginator(list(range(25))), 2), [1, 2, 3])
        with self.assertRaises(PageNotFound):
            page_links(results, 11)

    def test_summary_names_the_items_on_the_page(self):
        results = Paginator(list(range(25)), per_page=10)
        self.assertEqual(summary(results.page(2)), 'Showing 11-20 of 25')
        self.assertEqual(summary(results.page(3)), 'Showing 21-25 of 25')
        self.assertEqual(summary(Paginator(list(range(21))).page(3)), 'Showing 21 of 21')
        self.assertEqual(summary(Paginator([]).page(1)), 'No results')

    def test_out_of_range_numbers_land_on_the_nearest_page(self):
        results = Paginator(list(range(25)), per_page=10)
        self.assertEqual(nearest_page(results, 99).number, 3)
        self.assertEqual(nearest_page(results, -4).number, 1)
        self.assertEqual(nearest_page(results, 2).number, 2)
        self.assertEqual(nearest_page(results, 'last').number, 1)


if __name__ == '__main__':
    unittest.main()
