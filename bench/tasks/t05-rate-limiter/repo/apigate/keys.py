"""API keys: who may call, and on which plan."""
from apigate.plans import Plan, plan_named


class UnknownKey(KeyError):
    """The key was never added to the store."""


class ApiKey:
    """One issued key. A revoked key stays in the store with `active` set to False."""

    def __init__(self, key, owner, plan):
        self.key = key
        self.owner = owner
        self.plan = plan
        self.active = True

    def __repr__(self):
        state = 'active' if self.active else 'revoked'
        return 'ApiKey(%r, owner=%r, plan=%r, %s)' % (self.key, self.owner, self.plan.name, state)


def _as_plan(plan):
    return plan if isinstance(plan, Plan) else plan_named(plan)


class KeyStore:
    """The keys that have been issued."""

    def __init__(self):
        self._keys = {}

    def add(self, key, owner, plan):
        """Issue `key` to `owner`. `plan` is a Plan or the name of a built-in plan."""
        if not isinstance(key, str) or not key:
            raise ValueError('an api key must be a non-empty string')
        if key in self._keys:
            raise ValueError('api key already in use: %s' % key)
        entry = ApiKey(key, owner, _as_plan(plan))
        self._keys[key] = entry
        return entry

    def lookup(self, key):
        try:
            return self._keys[key]
        except (KeyError, TypeError):
            raise UnknownKey(key) from None

    def revoke(self, key):
        self.lookup(key).active = False

    def restore(self, key):
        self.lookup(key).active = True

    def change_plan(self, key, plan):
        self.lookup(key).plan = _as_plan(plan)

    def keys_of(self, owner):
        """Every key issued to `owner`, revoked ones included, in alphabetical order."""
        return sorted(entry.key for entry in self._keys.values() if entry.owner == owner)

    def __contains__(self, key):
        return key in self._keys

    def __len__(self):
        return len(self._keys)
