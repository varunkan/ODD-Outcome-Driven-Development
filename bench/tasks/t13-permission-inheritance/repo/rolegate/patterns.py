"""Resource paths and the patterns rules use to name them.

A resource is a path of segments joined by '/', such as 'docs/finance/2026/q3.pdf'. No segment is empty, so there
is no leading, trailing or doubled slash. A pattern is written the same way and may use two wildcards, each as a
whole segment:

    *     exactly one segment          'docs/*'   matches 'docs/a'        but not 'docs/a/b' or 'docs'
    **    any number of segments, none included
                                       'docs/**'  matches 'docs', 'docs/a' and 'docs/a/b'

Anything else in a segment is literal: 'q*.pdf' matches only a file named exactly 'q*.pdf'.
"""

from functools import lru_cache

ONE = '*'
ANY = '**'


def split(path):
    """The segments of a resource path. ValueError when it is not one."""
    if not isinstance(path, str) or not path:
        raise ValueError('a path is a non-empty string, not %r' % (path,))
    segments = path.split('/')
    if any(not segment for segment in segments):
        raise ValueError('path %r has an empty segment' % path)
    return tuple(segments)


def check_resource(resource):
    segments = split(resource)
    if ONE in segments or ANY in segments:
        raise ValueError('a resource has no wildcards: %r' % resource)
    return resource


def check_pattern(pattern):
    split(pattern)
    return pattern


def matches(pattern, resource):
    """Whether `pattern` names `resource`."""
    return _match(split(pattern), split(resource))


@lru_cache(maxsize=4096)
def _match(pattern, resource):
    if not pattern:
        return not resource
    head, rest = pattern[0], pattern[1:]
    if head == ANY:
        # '**' takes nothing, or one more segment and stays in place.
        return _match(rest, resource) or (bool(resource) and _match(pattern, resource[1:]))
    if not resource:
        return False
    if head == ONE or head == resource[0]:
        return _match(rest, resource[1:])
    return False


def is_literal(pattern):
    """True when the pattern names exactly one resource."""
    return all(segment not in (ONE, ANY) for segment in split(pattern))
