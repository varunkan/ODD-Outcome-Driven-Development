"""The front door: check the caller's key, then pass the request on to the handler."""
from apigate.keys import UnknownKey


class Request:
    """One incoming call: the API key it was sent with, and what it asks for."""

    def __init__(self, key, path, method='GET'):
        self.key = key
        self.path = path
        self.method = method

    def __repr__(self):
        return 'Request(%r, %r, %r)' % (self.key, self.path, self.method)


class Response:
    """What goes back to the caller. Header names and values are strings."""

    def __init__(self, status, body, headers=None):
        self.status = status
        self.body = body
        self.headers = dict(headers or {})

    @property
    def ok(self):
        return 200 <= self.status < 300

    def __repr__(self):
        return 'Response(%r, %r, %r)' % (self.status, self.body, self.headers)


class Gateway:
    """Answers requests for the keys in `keys`; `handler(request)` produces the body of a successful answer."""

    def __init__(self, keys, handler):
        self._keys = keys
        self._handler = handler
        self._stats = {}

    def handle(self, request):
        response = self._answer(request)
        self._stats[response.status] = self._stats.get(response.status, 0) + 1
        return response

    def _answer(self, request):
        try:
            entry = self._keys.lookup(request.key)
        except UnknownKey:
            return Response(401, 'unknown api key')
        if not entry.active:
            return Response(403, 'api key revoked')
        return Response(200, self._handler(request))

    def stats(self):
        """How many responses went out so far, by status: {200: 12, 401: 3}."""
        return dict(self._stats)
