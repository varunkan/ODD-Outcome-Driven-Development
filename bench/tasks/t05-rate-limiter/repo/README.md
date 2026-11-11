# apigate

A small gateway that sits in front of a request handler. It checks the API key a request was sent with, knows which
plan that key is on, and passes the request on. Python 3, standard library only.

## What is in it

`apigate.plans`: what a customer has bought.

- `Plan(name, limit=None, window=None)`: `limit` requests are included per `window` seconds. A plan without a limit
  is unlimited.
- `Plan.from_rate("free", "60/hour")` builds one from a rate; `parse_rate("60/hour")` gives `(60, 3600)`.
- `PLANS`: the built-in plans by name: `free` (60 requests per hour), `pro` (600 requests per minute) and `internal`
  (unlimited). `plan_named(name)` looks one up.
- `Plan.describe()`: the line shown on the pricing page, such as `"free: 60 requests per hour"`.

`apigate.keys`: who may call.

- `KeyStore()`, then `add(key, owner, plan)` with a `Plan` or the name of a built-in plan.
- `lookup(key)` returns the `ApiKey` (`key`, `owner`, `plan`, `active`) and raises `UnknownKey` for a key that was
  never added. A revoked key is still found; its `active` is `False`.
- `revoke(key)`, `restore(key)`, `change_plan(key, plan)`, `keys_of(owner)`.

`apigate.gateway`: the front door.

- `Request(key, path, method="GET")` and `Response(status, body, headers=None)`. Header names and values are strings.
- `Gateway(keys, handler)`: `handle(request)` answers `401` for an unknown key and `403` for a revoked one.
  Otherwise it calls `handler(request)` and returns the result as the body of a `200`.
- `stats()`: how many responses went out so far, by status, such as `{200: 12, 401: 3}`.

The limits on the plans are shown to customers, but the gateway does not enforce them.

## Example

```python
from apigate.gateway import Gateway, Request
from apigate.keys import KeyStore

keys = KeyStore()
keys.add("k-123", "ann", "free")

gateway = Gateway(keys, lambda request: "you asked for " + request.path)
gateway.handle(Request("k-123", "/orders")).body      # "you asked for /orders"
gateway.handle(Request("nope", "/orders")).status     # 401
gateway.stats()                                       # {200: 1, 401: 1}
```

## Tests

```
python3 -m unittest
```
