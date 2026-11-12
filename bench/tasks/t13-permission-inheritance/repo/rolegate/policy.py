"""The policy: roles, the rules on each role, and which users hold which roles.

Everything that changes the policy tells its subscribers, so that whoever keeps derived state (the resolver's
cache) can drop what the change made wrong. A subscriber is called as fn(kind, role=..., user=...) with kind one of
'role', 'rule', 'parents', 'user', after the change is made.
"""

from .model import make_rule
from .roles import RoleGraph, UnknownRole


def _check_user(user):
    if not isinstance(user, str) or not user.strip() or user != user.strip():
        raise ValueError('a user name is a non-empty string without surrounding spaces, not %r' % (user,))
    return user


class Policy:
    def __init__(self):
        self.graph = RoleGraph()
        self._rules = {}
        self._users = {}
        self._subscribers = []

    # -- roles -----------------------------------------------------------------------------------------------------

    def add_role(self, role, parents=()):
        self.graph.add(role, parents)
        self._rules[role] = []
        self._tell('role', role=role)

    def remove_role(self, role):
        holders = self.users_with(role)
        if holders:
            raise ValueError('role %r is held by %s' % (role, ', '.join(holders)))
        self.graph.remove(role)
        del self._rules[role]
        self._tell('role', role=role)

    def set_parents(self, role, parents):
        self.graph.set_parents(role, parents)
        self._tell('parents', role=role)

    def roles(self):
        return self.graph.roles()

    # -- rules -----------------------------------------------------------------------------------------------------

    def add_rule(self, role, effect, action, pattern):
        rule = make_rule(effect, action, pattern)
        rules = self._rules_of(role)
        if rule not in rules:
            rules.append(rule)
        self._tell('rule', role=role)
        return rule

    def remove_rule(self, role, rule):
        rules = self._rules_of(role)
        try:
            rules.remove(rule)
        except ValueError:
            raise KeyError('role %r has no rule %s' % (role, rule)) from None
        self._tell('rule', role=role)

    def rules(self, role):
        """The rules on the role itself, in the order they were added; not the inherited ones."""
        return list(self._rules_of(role))

    # -- users -----------------------------------------------------------------------------------------------------

    def assign(self, user, role):
        _check_user(user)
        self._rules_of(role)
        held = self._users.setdefault(user, [])
        if role not in held:
            held.append(role)
        self._tell('user', user=user)

    def unassign(self, user, role):
        held = self._users.get(user, [])
        if role not in held:
            raise KeyError('user %r does not hold %r' % (user, role))
        held.remove(role)
        if not held:
            del self._users[user]
        self._tell('user', user=user)

    def roles_of(self, user):
        """The roles assigned to the user, in the order assigned; not the inherited ones."""
        return list(self._users.get(user, ()))

    def users(self):
        return sorted(self._users)

    def users_with(self, role):
        """The users the role is assigned to directly."""
        return sorted(user for user, held in self._users.items() if role in held)

    # -- subscribers -----------------------------------------------------------------------------------------------

    def subscribe(self, fn):
        self._subscribers.append(fn)

    def unsubscribe(self, fn):
        self._subscribers.remove(fn)

    def _tell(self, kind, role=None, user=None):
        for fn in list(self._subscribers):
            fn(kind, role=role, user=user)

    def _rules_of(self, role):
        try:
            return self._rules[role]
        except KeyError:
            raise UnknownRole(role) from None

    # -- plain data ------------------------------------------------------------------------------------------------

    def to_dict(self):
        roles = {}
        for role in self._topological():
            roles[role] = {'parents': list(self.graph.parents(role)),
                           'rules': [[r.effect, r.action, r.pattern] for r in self._rules[role]]}
        return {'roles': roles, 'users': {user: list(held) for user, held in sorted(self._users.items())}}

    @classmethod
    def from_dict(cls, data):
        policy = cls()
        pending = dict(data.get('roles', {}))
        while pending:
            ready = [r for r, spec in pending.items() if all(p in policy.graph for p in spec.get('parents', []))]
            if not ready:
                raise ValueError('roles with unknown parents or a cycle: %s' % ', '.join(sorted(pending)))
            for role in ready:
                spec = pending.pop(role)
                policy.add_role(role, spec.get('parents', []))
                for effect, action, pattern in spec.get('rules', []):
                    policy.add_rule(role, effect, action, pattern)
        for user, held in data.get('users', {}).items():
            for role in held:
                policy.assign(user, role)
        return policy

    def _topological(self):
        done, order = set(), []

        def visit(role):
            if role in done:
                return
            done.add(role)
            for parent in self.graph.parents(role):
                visit(parent)
            order.append(role)
        for role in self.graph.roles():
            visit(role)
        return order
