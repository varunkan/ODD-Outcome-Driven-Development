"""The journal: an append-only file of JSON lines, one per event, that is the queue's only storage.

Every till has journals on disk written in this format, so the format is part of the interface. A line looks like:

    {"job": "inv-1", "event": "submitted", "kind": "charge_invoice", "payload": {...}, "at": 1700000000.0}
    {"job": "inv-1", "event": "started", "at": 1700000001.0}
    {"job": "inv-1", "event": "done", "output": {...}, "at": 1700000002.0}
    {"job": "inv-1", "event": "failed", "error": "ValueError: ...", "at": 1700000002.0}

Readers ignore keys they do not know.
"""

import json
import os

EVENTS = ('submitted', 'started', 'done', 'failed')


class Journal:
    def __init__(self, path):
        self.path = path

    def append(self, record):
        """Write one event and make it durable before returning."""
        if record.get('event') not in EVENTS:
            raise ValueError('unknown event %r' % (record.get('event'),))
        if not isinstance(record.get('job'), str) or not record['job']:
            raise ValueError('an event needs a job id')
        line = json.dumps(record, sort_keys=True, separators=(',', ':'))
        with open(self.path, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
            f.flush()
            os.fsync(f.fileno())

    def records(self):
        """Every event in the order written. A last line cut short by a crash is skipped; any other bad line raises."""
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding='utf-8') as f:
            lines = f.read().split('\n')
        out = []
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError:
                if number == len(lines):  # no newline after it: the write never finished
                    break
                raise ValueError('%s line %d is not JSON' % (self.path, number))
            if not isinstance(record, dict) or record.get('event') not in EVENTS:
                raise ValueError('%s line %d is not a journal event' % (self.path, number))
            out.append(record)
        return out

    def __len__(self):
        return len(self.records())
