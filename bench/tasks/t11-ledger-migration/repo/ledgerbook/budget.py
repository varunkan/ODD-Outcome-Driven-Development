"""Monthly spending limits per category, and how much of each has been used."""


class Budget:
    def __init__(self, limits):
        """`limits` is {category: monthly limit in cents}; a limit is a whole number of cents, zero or more."""
        checked = {}
        for category, limit in dict(limits).items():
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValueError('the limit for %r must be a whole number of cents, zero or more' % (category,))
            checked[category] = limit
        self.limits = dict(sorted(checked.items()))

    def spent(self, ledger, category, year, month):
        """What the category used in the month, in cents: money out counts up, refunds into it count down."""
        key = '%04d-%02d' % (year, month)
        total = 0
        for entry in ledger.entries(category=category):
            if entry.date.startswith(key):
                total -= entry.amount
        return total

    def remaining(self, ledger, category, year, month):
        """The limit minus what was spent; negative when the category is over its limit."""
        return self.limits[category] - self.spent(ledger, category, year, month)

    def over(self, ledger, year, month):
        """[(category, spent, limit)] for every category that spent more than its limit in the month."""
        found = []
        for category, limit in self.limits.items():
            used = self.spent(ledger, category, year, month)
            if used > limit:
                found.append((category, used, limit))
        return found
