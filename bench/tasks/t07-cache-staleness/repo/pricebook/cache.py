"""A small in-memory cache whose entries expire."""
import time

_MISSING = object()


class TTLCache:
    """Keeps a value for `ttl` seconds after it was put. `clock` returns the current time in seconds."""

    def __init__(self, ttl=300.0, clock=time.monotonic):
        if ttl <= 0:
            raise ValueError('ttl must be greater than zero')
        self._ttl = ttl
        self._clock = clock
        self._entries = {}

    def get(self, key, default=None):
        """The live value for key, or default when there is none or it has expired."""
        entry = self._entries.get(key)
        if entry is None:
            return default
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._entries[key]
            return default
        return value

    def put(self, key, value):
        """Keep value under key for the next `ttl` seconds."""
        self._entries[key] = (self._clock() + self._ttl, value)

    def discard(self, key):
        """Forget key. Does nothing when key is not held."""
        self._entries.pop(key, None)

    def clear(self):
        """Forget everything."""
        self._entries.clear()

    def __contains__(self, key):
        return self.get(key, _MISSING) is not _MISSING

    def __len__(self):
        now = self._clock()
        return sum(1 for expires_at, _ in self._entries.values() if now < expires_at)
