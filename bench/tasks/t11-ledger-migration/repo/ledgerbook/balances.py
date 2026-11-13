"""Account balances: the sum of the amounts booked to an account, optionally up to and including a date."""


def _counts(entry, until):
    return until is None or entry.date <= until


def balance(entries, account, until=None):
    """The balance of one account in cents. An account with no entries has a balance of 0."""
    return sum(entry.amount for entry in entries if entry.account == account and _counts(entry, until))


def balances(entries, until=None):
    """{account: balance} for every account that has an entry, in account order."""
    totals = {}
    for entry in entries:
        if _counts(entry, until):
            totals[entry.account] = totals.get(entry.account, 0) + entry.amount
    return dict(sorted(totals.items()))


def net_worth(entries, until=None):
    """The sum of every account's balance."""
    return sum(balances(entries, until).values())
