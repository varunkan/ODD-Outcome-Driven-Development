# Hold each API key to its plan

Every plan in `apigate.plans` says how many requests it includes ("free: 60 requests per hour"), and we print that on
the pricing page. Nothing enforces it. A key on the free plan can send as many requests as it likes, and last week one
did. The gateway has to hold each key to its plan.

## The limiter: `apigate.limiter.SlidingWindowLimiter`

A new module that can be used on its own, because we want the same limiter in front of the login form later.

- `SlidingWindowLimiter(limit, window, clock=None)` allows at most `limit` requests per key in any `window` seconds.
  `limit` is a whole number of at least 1 and `window` is a number of seconds greater than 0. Anything else raises
  `ValueError`.
- `clock` is a function that takes no arguments and returns the current time in seconds. When it is left out the
  limiter uses `time.monotonic`. The limiter reads the time from its clock on every call and from nowhere else.
- `allow(key)` returns `True` and counts the request when `key` has fewer than `limit` counted requests in the last
  `window` seconds. Otherwise it returns `False`, and the refused request is not counted: hammering on a full
  limiter must not push the wait further out.
- The window slides. A request counted at time `t` stops counting at exactly `t + window`. It is not a counter that
  starts again on the hour.
- `remaining(key)` is how many more requests `key` could make right now. Asking does not count as a request.
- `retry_after(key)` is the number of seconds until `key` may make its next request: `0.0` when it may make one now,
  otherwise the time until its oldest counted request leaves the window. Asking does not count as a request.
- `reset(key)` forgets everything `key` has done.
- Keys never share a count, and a key the limiter has not seen has the whole limit left.

```python
from apigate.limiter import SlidingWindowLimiter

limiter = SlidingWindowLimiter(2, 60, clock=clock)   # clock() returns 0.0 for now
limiter.allow("ann")          # True
limiter.allow("ann")          # True
limiter.allow("ann")          # False
limiter.remaining("ann")      # 0
limiter.retry_after("ann")    # 60.0
limiter.allow("bob")          # True
# once clock() returns 60.0:
limiter.allow("ann")          # True
```

## The gateway: `apigate.gateway.Gateway`

- `Gateway(keys, handler, clock=None)` takes the same optional `clock` and uses it for all of its limiting.
- Each API key is held to its plan: `plan.limit` requests per `plan.window` seconds, with the sliding window
  described above. The count is per API key, so two keys on the same plan do not share one.
- A request over the limit is answered with status `429`, the body `"rate limit exceeded"` and a `"Retry-After"`
  header: the seconds to wait, rounded up to a whole number, as a string such as `"7"`. The handler is not called,
  and the refused request is not counted against the key.
- A request that is let through carries two more headers on its `200`: `"X-RateLimit-Limit"`, the plan's limit, and
  `"X-RateLimit-Remaining"`, what the key has left in the window after this request. Both are strings.
- The key checks come first and stay as they are. An unknown key is answered `401` and a revoked key `403`, however
  many requests it has made.
- A plan without a limit (`limit` is `None`, like `PLANS["internal"]`) is never limited.
- `Gateway.stats()` counts `429` answers like any other status.

```python
from apigate.gateway import Gateway, Request
from apigate.keys import KeyStore
from apigate.plans import Plan

keys = KeyStore()
keys.add("k-123", "ann", Plan("trial", 3, 10))        # 3 requests per 10 seconds
gateway = Gateway(keys, lambda request: "hello", clock=clock)

gateway.handle(Request("k-123", "/orders")).headers["X-RateLimit-Remaining"]   # "2"
gateway.handle(Request("k-123", "/orders")).status                             # 200
gateway.handle(Request("k-123", "/orders")).status                             # 200
refused = gateway.handle(Request("k-123", "/orders"))
refused.status                                         # 429
refused.headers["Retry-After"]                         # "10" while clock() has not moved
gateway.stats()                                        # {200: 3, 429: 1}
```
