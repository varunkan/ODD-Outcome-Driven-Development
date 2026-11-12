"""Answers "may this user do this action on this resource?" from a policy, with a cache in front."""

from .cache import DecisionCache
from .model import ALLOW, NO_MATCH, Decision
from .patterns import check_resource


class Resolver:
    """Reads a Policy and keeps itself up to date by subscribing to it.

    `computed` counts the decisions worked out from the policy rather than taken from the cache.
    """

    def __init__(self, policy, cache=None):
        self.policy = policy
        self.cache = cache if cache is not None else DecisionCache()
        self.computed = 0
        self._compiled = {}
        policy.subscribe(self._changed)

    def close(self):
        self.policy.unsubscribe(self._changed)

    # -- questions -------------------------------------------------------------------------------------------------

    def check(self, user, action, resource):
        return self.explain(user, action, resource).allowed

    def explain(self, user, action, resource):
        check_resource(resource)
        key = (user, action, resource)
        decision = self.cache.get(key)
        if decision is None:
            decision = self._decide(user, action, resource)
            self.computed += 1
            self.cache.put(key, decision)
        return decision

    def filter(self, user, action, resources):
        """The resources, of those given, the user may do `action` on, in the order given. For listing pages, which
        ask about hundreds of resources at once: the user's rules are gathered once and kept."""
        rules = self._rules_for(user)
        allowed = []
        for resource in resources:
            check_resource(resource)
            for role, rule in rules:
                if rule.applies(action, resource):
                    if rule.effect == ALLOW:
                        allowed.append(resource)
                    break
        return allowed

    def roles(self, user):
        """Every role the user has: the assigned ones in order, each followed by what it inherits, each role once."""
        seen, order = set(), []
        for assigned in self.policy.roles_of(user):
            for role in self.policy.graph.ancestors(assigned):
                if role not in seen:
                    seen.add(role)
                    order.append(role)
        return order

    # -- inside ----------------------------------------------------------------------------------------------------

    def _decide(self, user, action, resource):
        for role in self.roles(user):
            for rule in self.policy.rules(role):
                if rule.applies(action, resource):
                    return Decision(rule.effect == ALLOW, rule.effect, role, rule)
        return NO_MATCH

    def _rules_for(self, user):
        rules = self._compiled.get(user)
        if rules is None:
            rules = [(role, rule) for role in self.roles(user) for rule in self.policy.rules(role)]
            self._compiled[user] = rules
        return rules

    def _changed(self, kind, role=None, user=None):
        if user is not None:
            affected = [user]
        elif kind == 'role':
            affected = []  # a new role is held by nobody yet, and a role still held cannot be removed
        else:
            affected = self.policy.users_with(role)
        for name in affected:
            self.cache.drop_user(name)
            self._compiled.pop(name, None)
