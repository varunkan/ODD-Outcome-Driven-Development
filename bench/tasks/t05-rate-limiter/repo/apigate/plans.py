"""Plans: what a customer has bought, and the request rate that comes with it."""

_UNITS = {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}


def parse_rate(text):
    """Turn "60/hour" into (60, 3600): a number of requests and the seconds they are spread over."""
    try:
        count, unit = text.strip().lower().split('/')
        count = int(count)
        seconds = _UNITS[unit.strip()]
    except (AttributeError, KeyError, ValueError):
        raise ValueError('not a rate: %r' % (text,)) from None
    if count < 1:
        raise ValueError('not a rate: %r' % (text,))
    return count, seconds


def _span(seconds):
    """Say a number of seconds the way the pricing page does: "hour", "30 minutes", "2.5 seconds"."""
    for unit in ('day', 'hour', 'minute', 'second'):
        size = _UNITS[unit]
        if seconds % size == 0:
            count = int(seconds // size)
            return unit if count == 1 else '%d %ss' % (count, unit)
    return '%g seconds' % seconds


class Plan:
    """A named plan: `limit` requests are included per `window` seconds. Without a limit the plan is unlimited."""

    def __init__(self, name, limit=None, window=None):
        if not isinstance(name, str) or not name.strip():
            raise ValueError('a plan needs a name')
        if limit is None:
            window = None
        else:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                raise ValueError('limit must be a whole number of at least 1')
            if isinstance(window, bool) or not isinstance(window, (int, float)) or not window > 0:
                raise ValueError('window must be a number of seconds greater than 0')
        self.name = name
        self.limit = limit
        self.window = window

    @classmethod
    def from_rate(cls, name, rate):
        """Plan.from_rate("free", "60/hour")"""
        return cls(name, *parse_rate(rate))

    @property
    def unlimited(self):
        return self.limit is None

    def describe(self):
        """The line shown on the pricing page."""
        if self.unlimited:
            return '%s: unlimited' % self.name
        noun = 'request' if self.limit == 1 else 'requests'
        return '%s: %d %s per %s' % (self.name, self.limit, noun, _span(self.window))

    def __eq__(self, other):
        if not isinstance(other, Plan):
            return NotImplemented
        return (self.name, self.limit, self.window) == (other.name, other.limit, other.window)

    def __hash__(self):
        return hash((self.name, self.limit, self.window))

    def __repr__(self):
        return 'Plan(%r, %r, %r)' % (self.name, self.limit, self.window)


PLANS = {
    'free': Plan.from_rate('free', '60/hour'),
    'pro': Plan.from_rate('pro', '600/minute'),
    'internal': Plan('internal'),
}


def plan_named(name):
    """The built-in plan with that name; ValueError when there is none."""
    try:
        return PLANS[name]
    except (KeyError, TypeError):
        raise ValueError('no such plan: %r' % (name,)) from None
