"""The monthly report the shop sends to its accountant, as a dictionary and as text."""
import calendar

from .money import format_amount


def _month_key(year, month):
    if not 1 <= month <= 12:
        raise ValueError('month must be 1 to 12, got %r' % (month,))
    return '%04d-%02d' % (year, month)


def monthly(ledger, year, month):
    """What happened in one month.

    income      the sum of the positive amounts dated in the month, in cents
    spending    the sum of the negative amounts dated in the month, as a positive number of cents
    net         income - spending
    by_category {category: signed sum of the month's amounts}, in category order
    entries     how many entries are dated in the month
    closing     {account: balance at the end of the month's last day}, for every account with an entry by then
    """
    key = _month_key(year, month)
    last_day = '%s-%02d' % (key, calendar.monthrange(year, month)[1])
    income = spending = count = 0
    by_category = {}
    closing = {}
    for entry in ledger.entries():
        if entry.date <= last_day:
            closing[entry.account] = closing.get(entry.account, 0) + entry.amount
        if entry.month != key:
            continue
        count += 1
        if entry.amount > 0:
            income += entry.amount
        else:
            spending -= entry.amount
        by_category[entry.category] = by_category.get(entry.category, 0) + entry.amount
    return {
        'month': key,
        'income': income,
        'spending': spending,
        'net': income - spending,
        'by_category': dict(sorted(by_category.items())),
        'entries': count,
        'closing': dict(sorted(closing.items())),
    }


def yearly(ledger, year):
    """The twelve monthly reports of a year, January first."""
    return [monthly(ledger, year, month) for month in range(1, 13)]


def render(report):
    """The report as the plain text that goes into the e-mail."""
    width = max([len(name) for name in report['by_category']] + [len(name) for name in report['closing']] + [12])
    lines = ['Report for %s (%d entries)' % (report['month'], report['entries']), '']
    for label in ('income', 'spending', 'net'):
        lines.append('%-*s %14s' % (width, label.capitalize(), format_amount(report[label], thousands=True)))
    if report['by_category']:
        lines += ['', 'By category']
        for name, amount in report['by_category'].items():
            lines.append('%-*s %14s' % (width, name, format_amount(amount, thousands=True)))
    if report['closing']:
        lines += ['', 'Closing balances']
        for name, amount in report['closing'].items():
            lines.append('%-*s %14s' % (width, name, format_amount(amount, thousands=True)))
    return '\n'.join(lines) + '\n'
