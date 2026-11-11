"""Split a list of items into numbered pages. Page numbers start at 1."""


class PageNotFound(LookupError):
    """Raised for a page number that is not a whole number or is not one of the pages."""


class Page:
    """One page of a paginated list."""

    def __init__(self, paginator, number, items):
        self.paginator = paginator
        self.number = number
        self.items = list(items)

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def __repr__(self):
        return '<Page %d of %d>' % (self.number, self.paginator.num_pages)

    @property
    def start_index(self):
        """Position of the first item on this page, counting from 1. 0 when the page is empty."""
        if not self.items:
            return 0
        return (self.number - 1) * self.paginator.per_page + 1

    @property
    def end_index(self):
        """Position of the last item on this page, counting from 1. 0 when the page is empty."""
        if not self.items:
            return 0
        return self.start_index + len(self.items) - 1

    @property
    def has_previous(self):
        return self.number > 1

    @property
    def has_next(self):
        return self.number * self.paginator.per_page <= self.paginator.count

    @property
    def previous_number(self):
        if not self.has_previous:
            raise PageNotFound('page %d is the first page' % self.number)
        return self.number - 1

    @property
    def next_number(self):
        if not self.has_next:
            raise PageNotFound('page %d is the last page' % self.number)
        return self.number + 1


class Paginator:
    """Pages over `items`, `per_page` to a page."""

    def __init__(self, items, per_page=10):
        if isinstance(per_page, bool) or not isinstance(per_page, int) or per_page < 1:
            raise ValueError('per_page must be a whole number of at least 1')
        self._items = list(items)
        self.per_page = per_page

    @property
    def count(self):
        """How many items there are in all."""
        return len(self._items)

    @property
    def num_pages(self):
        """How many pages there are. An empty list still has one page, with nothing on it."""
        return self.count // self.per_page + 1

    @property
    def page_range(self):
        """The page numbers, from 1 up to and including the last page."""
        return range(1, self.num_pages + 1)

    def validate_number(self, number):
        """Return `number` when it is the number of a page, otherwise raise `PageNotFound`."""
        if isinstance(number, bool) or not isinstance(number, int):
            raise PageNotFound('a page number must be a whole number, not %r' % (number,))
        if number < 1 or number > self.num_pages:
            raise PageNotFound('there is no page %d (pages run from 1 to %d)' % (number, self.num_pages))
        return number

    def page(self, number):
        """The page with that number."""
        number = self.validate_number(number)
        start = (number - 1) * self.per_page
        return Page(self, number, self._items[start:start + self.per_page])

    def first_page(self):
        return self.page(1)

    def last_page(self):
        return self.page(self.num_pages)

    def pages(self):
        """Every page, in order."""
        for number in self.page_range:
            yield self.page(number)

    def page_of(self, position):
        """The number of the page that holds the item at `position`. The first item is at position 1."""
        if isinstance(position, bool) or not isinstance(position, int):
            raise TypeError('a position must be a whole number')
        if position < 1 or position > self.count:
            raise IndexError('there is no item at position %d' % position)
        return (position - 1) // self.per_page + 1
