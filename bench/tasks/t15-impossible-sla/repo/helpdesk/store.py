"""Saving the queue: one JSON object per line, one line per ticket, in ticket number order."""
import json
import os
import tempfile

from .queue import TicketQueue
from .tickets import Ticket


def dumps(queue):
    return ''.join(json.dumps(ticket.to_dict(), sort_keys=True) + '\n' for ticket in queue)


def loads(text):
    tickets = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            tickets.append(Ticket.from_dict(json.loads(line)))
        except ValueError as error:
            raise ValueError('line %d: %s' % (number, error)) from None
    return TicketQueue(tickets)


def save(queue, path):
    """Write the queue to path, replacing the file in one step so a crash never leaves half a file."""
    folder = os.path.dirname(os.path.abspath(path))
    handle, temporary = tempfile.mkstemp(dir=folder, prefix='.tickets-')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as out:
            out.write(dumps(queue))
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def load(path):
    """The queue saved at path; an empty queue when there is no file yet."""
    if not os.path.exists(path):
        return TicketQueue()
    with open(path, encoding='utf-8') as source:
        return loads(source.read())
