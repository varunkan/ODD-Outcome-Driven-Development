# paging

Splits a list into numbered pages and helps to show them: page links, a "Showing 11-20 of 45" line, the page an
item is on. Python 3, standard library only.

## What is in it

`paging.paginator`: the pages.

- `Paginator(items, per_page=10)`: `count` is the number of items, `num_pages` the number of pages and `page_range`
  the page numbers. Page numbers start at 1.
- `page(number)` returns a `Page`. It raises `PageNotFound` for a number that is not a whole number or is not one of
  the pages.
- `first_page()`, `last_page()`, and `pages()`, which goes through every page in order.
- `page_of(position)`: the number of the page that holds the item at `position`. The first item is at position 1.
- An empty list has one page, with nothing on it.
- `Page`: `number`, `items`, `has_previous`, `has_next`, `previous_number`, `next_number`, and `start_index` and
  `end_index`, the positions of its first and last item.

`paging.navigation`: showing them.

- `page_links(paginator, current, around=2)`: the page numbers to offer as links: the first page, the last page and
  the pages around the current one. `None` marks a gap.
- `summary(page)`: a line such as `"Showing 11-20 of 45"`, or `"No results"` for an empty page.
- `nearest_page(paginator, number)`: the page for a number that may be out of range, such as one typed into the
  address bar. Too low gives the first page, too high the last.

## Example

```python
from paging.navigation import page_links, summary
from paging.paginator import Paginator

results = Paginator(["result %d" % n for n in range(1, 96)], per_page=10)    # 95 results
results.num_pages                # 10
page = results.page(5)
page.items[0]                    # "result 41"
page.has_next                    # True
summary(page)                    # "Showing 41-50 of 95"
page_links(results, 5)           # [1, None, 3, 4, 5, 6, 7, None, 10]
```

## Tests

```
python3 -m unittest
```
