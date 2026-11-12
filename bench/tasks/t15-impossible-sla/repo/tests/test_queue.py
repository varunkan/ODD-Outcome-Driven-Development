import datetime as dt
import os
import tempfile
import unittest

from helpdesk import TicketQueue, format_report, service_report
from helpdesk import store
from helpdesk.tickets import Ticket


def at(text):
    return dt.datetime.strptime(text, '%Y-%m-%d %H:%M')


def sample():
    return TicketQueue([
        Ticket(1, 'Printer error', 'ann@example.com', 'high', 'portal', at('2026-03-09 13:00'), at('2026-03-10 11:00')),
        Ticket(2, 'New user', 'bo@example.com', 'normal', 'email', at('2026-03-09 13:05'), at('2026-03-11 13:05')),
        Ticket(3, 'Login error', 'cy@example.com', 'high', 'phone', at('2026-03-09 14:00'), at('2026-03-10 12:00')),
    ])


class QueueTest(unittest.TestCase):
    def test_reply_and_close(self):
        queue = sample()
        queue.reply(1, at('2026-03-09 15:00'))
        queue.reply(1, at('2026-03-09 16:00'))
        self.assertEqual(queue.get(1).first_reply_at, at('2026-03-09 15:00'))
        self.assertEqual(queue.get(1).status, 'replied')
        queue.close(1, at('2026-03-09 16:30'))
        with self.assertRaises(ValueError):
            queue.reply(1, at('2026-03-09 17:00'))
        with self.assertRaises(ValueError):
            queue.reply(2, at('2026-03-09 12:00'))
        self.assertEqual([ticket.number for ticket in queue.open_tickets()], [3, 2])
        self.assertEqual(queue.next_number(), 4)

    def test_escalation_and_overdue(self):
        queue = sample()
        self.assertEqual([t.number for t in queue.due_within(at('2026-03-10 09:30'), 120)], [1])
        self.assertEqual([t.number for t in queue.due_within(at('2026-03-10 10:00'), 120)], [1, 3])
        self.assertEqual([t.number for t in queue.overdue(at('2026-03-10 11:30'))], [1])

    def test_store_round_trip(self):
        queue = sample()
        queue.reply(2, at('2026-03-10 09:00'))
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'tickets.jsonl')
            self.assertEqual(len(store.load(path)), 0)
            store.save(queue, path)
            again = store.load(path)
        self.assertEqual(list(again), list(queue))
        self.assertIn('"due_at": "2026-03-10 11:00"', store.dumps(queue).splitlines()[0])
        with self.assertRaises(ValueError) as caught:
            store.loads(store.dumps(queue) + '{"number": 9}\n')
        self.assertIn('line 4', str(caught.exception))


class ReportTest(unittest.TestCase):
    def test_weekly_figures(self):
        queue = sample()
        queue.reply(1, at('2026-03-09 15:00'))
        queue.reply(3, at('2026-03-10 13:00'))
        report = service_report(queue, at('2026-03-09 00:00'), at('2026-03-16 00:00'), now=at('2026-03-12 09:00'))
        self.assertEqual(report['high'], {'opened': 2, 'replied': 2, 'breached': 1, 'median_reply_minutes': 330})
        self.assertEqual(report['normal'], {'opened': 1, 'replied': 0, 'breached': 1, 'median_reply_minutes': None})
        self.assertEqual(report['urgent']['opened'], 0)
        text = format_report(report)
        self.assertIn('Service report 2026-03-09 00:00 to 2026-03-16 00:00', text)
        self.assertIn('330 min', text)


if __name__ == '__main__':
    unittest.main()
