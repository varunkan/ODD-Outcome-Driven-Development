"""Rules and decisions."""

from collections import namedtuple

from .patterns import check_pattern, matches

ALLOW = 'allow'
DENY = 'deny'
EFFECTS = (ALLOW, DENY)
ANY_ACTION = '*'


class Rule(namedtuple('Rule', 'effect action pattern')):
    """`effect` is 'allow' or 'deny'; `action` a verb such as 'read', or '*' for every action; `pattern` a resource
    pattern (see patterns.py)."""

    __slots__ = ()

    def applies(self, action, resource):
        return (self.action == ANY_ACTION or self.action == action) and matches(self.pattern, resource)

    def __str__(self):
        return '%s %s %s' % (self.effect, self.action, self.pattern)


def make_rule(effect, action, pattern):
    if effect not in EFFECTS:
        raise ValueError('effect is allow or deny, not %r' % (effect,))
    if not isinstance(action, str) or not action or '/' in action or action != action.strip():
        raise ValueError('bad action %r' % (action,))
    return Rule(effect, action, check_pattern(pattern))


class Decision(namedtuple('Decision', 'allowed effect role rule')):
    """What a check came to. `effect` is the effect of the rule that decided, `role` the role that rule is on, and
    `rule` the Rule; all three are None when no rule matched, and then `allowed` is False."""

    __slots__ = ()

    def __str__(self):
        if self.rule is None:
            return 'refused: no rule matches'
        return '%s by %r: %s' % ('allowed' if self.allowed else 'refused', self.role, self.rule)


NO_MATCH = Decision(False, None, None, None)
