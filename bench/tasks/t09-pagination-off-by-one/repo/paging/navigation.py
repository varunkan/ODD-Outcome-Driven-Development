"""Helpers for showing a paginated list: page links, a summary line, forgiving page lookup."""

GAP = None


def page_links(paginator, current, around=2):
    """The page numbers to offer as links while `current` is shown.

    The first page, the last page and up to `around` pages on each side of the current one. `None` marks a gap:
    with 10 pages, `page_links(paginator, 5)` is `[1, None, 3, 4, 5, 6, 7, None, 10]`.
    """
    current = paginator.validate_number(current)
    if around < 0:
        raise ValueError('around must not be negative')
    last = paginator.num_pages
    shown = {1, last}
    shown.update(number for number in range(current - around, current + around + 1) if 1 <= number <= last)
    links = []
    previous = 0
    for number in sorted(shown):
        if number - previous > 1:
            links.append(GAP)
        links.append(number)
        previous = number
    return links


def summary(page):
    """A line such as "Showing 11-20 of 45". "No results" when the page is empty."""
    if not page.items:
        return 'No results'
    total = page.paginator.count
    if page.start_index == page.end_index:
        return 'Showing %d of %d' % (page.start_index, total)
    return 'Showing %d-%d of %d' % (page.start_index, page.end_index, total)


def nearest_page(paginator, number):
    """The page for a number that may be out of range, such as one typed into the address bar.

    A number below 1 gives the first page and a number that is too high gives the last page. Anything that is not
    a whole number gives the first page.
    """
    if isinstance(number, bool) or not isinstance(number, int):
        return paginator.first_page()
    return paginator.page(max(1, min(number, paginator.num_pages)))
