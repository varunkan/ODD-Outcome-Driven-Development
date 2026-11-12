"""Policies on disk: one JSON file, {"format": 1, "roles": {...}, "users": {...}} (see Policy.to_dict)."""

import json
import os
import tempfile

from .policy import Policy

FORMAT = 1


def save(policy, path):
    """Write the policy so that a crash leaves either the old file or the new one, never half of one."""
    data = dict(policy.to_dict(), format=FORMAT)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix='.policy-', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write('\n')
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if data.get('format', FORMAT) != FORMAT:
        raise ValueError('%s is policy format %r; this version reads %d' % (path, data.get('format'), FORMAT))
    return Policy.from_dict(data)
