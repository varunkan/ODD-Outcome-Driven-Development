# One page too many when the results divide evenly

We use `paging` to split search results into pages of ten. Whenever the number of results is an exact multiple of the
page size, the paginator reports one page more than there is, and that extra page is empty:

```python
>>> from paging.paginator import Paginator
>>> results = Paginator(list(range(1, 21)), per_page=10)      # 20 results, 10 to a page
>>> results.num_pages
3
>>> results.last_page().items
[]
>>> results.page(2).has_next
True
```

Twenty results at ten to a page are two pages. As it is, "Last" opens a page that says "No results", page 2 offers a
"Next" link that leads to the same empty page, and the page links read 1 2 3. With 19 or with 21 results everything is
right.

What should happen:

- `Paginator(items, per_page).num_pages` counts only pages that have something on them: 2 for 20 items at 10 to a
  page, 1 for 10 items at 10 to a page, 3 for 3 items at 1 to a page.
- `page(number)` raises `paging.paginator.PageNotFound` for every number above `num_pages`, so `results.page(3)`
  raises here.
- `last_page()` is the last page that has items: here its `.number` is 2 and its `.items` are 11 to 20.
- `Page.has_next` is `False` on the last page and `True` on every page before it.
- `pages()` and `page_range` stop at the last page, so there is no empty page at the end.
- `paging.navigation.page_links(paginator, current)` offers no page above `num_pages`: `page_links(results, 1)` is
  `[1, 2]`.
- `paging.navigation.nearest_page(paginator, number)` gives the real last page for a number that is too high:
  `nearest_page(results, 99).number` is 2.
- An empty list stays as it is today: one page with nothing on it. Its `num_pages` is 1, `page(1).items` is `[]` and
  that page's `has_next` is `False`.
- Lists that do not divide evenly keep giving what they give today.
