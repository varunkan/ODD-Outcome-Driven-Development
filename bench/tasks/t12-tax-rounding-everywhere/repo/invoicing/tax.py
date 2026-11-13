"""How much tax a line carries."""
from .rates import check_rate


def line_tax(net, rate):
    """The tax in cents on a net amount in cents at `rate` percent (a string such as '20' or '7.5')."""
    check_rate(rate)
    return round(net * float(rate) / 100)
