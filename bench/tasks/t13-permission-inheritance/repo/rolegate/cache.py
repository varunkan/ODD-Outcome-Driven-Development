"""The decision cache: (user, action, resource) -> Decision, least recently used out first."""

from collections import OrderedDict


class DecisionCache:
    def __init__(self, capacity=10000):
        if capacity < 1:
            raise ValueError('capacity is at least 1')
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
        self._entries = OrderedDict()
        self._by_user = {}

    def get(self, key):
        try:
            decision = self._entries[key]
        except KeyError:
            self.misses += 1
            return None
        self._entries.move_to_end(key)
        self.hits += 1
        return decision

    def put(self, key, decision):
        if key in self._entries:
            self._entries.move_to_end(key)
        self._entries[key] = decision
        self._by_user.setdefault(key[0], set()).add(key)
        while len(self._entries) > self.capacity:
            old, _ = self._entries.popitem(last=False)
            self._forget(old)

    def drop_user(self, user):
        for key in self._by_user.pop(user, ()):
            self._entries.pop(key, None)

    def clear(self):
        self._entries.clear()
        self._by_user.clear()

    def users(self):
        return sorted(self._by_user)

    def __len__(self):
        return len(self._entries)

    def __contains__(self, key):
        return key in self._entries

    def _forget(self, key):
        keys = self._by_user.get(key[0])
        if keys is not None:
            keys.discard(key)
            if not keys:
                del self._by_user[key[0]]
