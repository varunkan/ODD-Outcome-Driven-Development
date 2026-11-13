import datetime as dt
import unittest

from helpdesk import TicketQueue, classify, open_from_email, open_ticket
from helpdesk import sla
from helpdesk.tickets import Ticket


def at(text):
    return dt.datetime.strptime(text, '%Y-%m-%d %H:%M')


class ClassifyTest(unittest.TestCase):
    def test_words_decide_the_priority(self):
        self.assertEqual(classify('Our shop is down'), 'urgent')
        self.assertEqual(classify('Payment failed', 'card declined'), 'high')
        self.assertEqual(classify('Question about invoices'), 'low')
        self.assertEqual(classify('Please change my address'), 'normal')

    def test_premium_goes_one_step_up(self):
        self.assertEqual(classify('Question about invoices', plan='premium'), 'normal')
        self.assertEqual(classify('Please change my address', plan='premium'), 'high')
        self.assertEqual(classify('Payment failed', plan='premium'), 'urgent')
        with self.assertRaises(ValueError):
            classify('anything', plan='gold')


class TargetTest(unittest.TestCase):
    def test_targets_count_desk_time(self):
        opened = at('2026-03-09 13:00')                                         # a Monday
        self.assertEqual(sla.due_at('high', opened), at('2026-03-10 11:00'))
        self.assertEqual(sla.due_at('normal', opened), at('2026-03-11 13:00'))
        self.assertEqual(sla.due_at('low', opened), at('2026-03-16 13:00'))
        with self.assertRaises(ValueError):
            sla.target_minutes('critical')

    def test_breach_and_minutes_left(self):
        ticket = Ticket(1, 'Printer error', 'ann@example.com', 'high', 'portal',
                        at('2026-03-09 13:00'), at('2026-03-10 11:00'))
        self.assertEqual(sla.minutes_left(ticket, at('2026-03-09 17:00')), 240)
        self.assertEqual(sla.minutes_left(ticket, at('2026-03-10 12:00')), -60)
        self.assertFalse(sla.is_breached(ticket, at('2026-03-10 10:59')))
        self.assertTrue(sla.is_breached(ticket, at('2026-03-10 11:01')))
        ticket.first_reply_at = at('2026-03-10 09:00')
        self.assertIsNone(sla.minutes_left(ticket, at('2026-03-10 12:00')))
        self.assertFalse(sla.is_breached(ticket, at('2026-03-12 12:00')))
        self.assertEqual(sla.first_reply_minutes(ticket), 360)


class IntakeTest(unittest.TestCase):
    def test_tickets_are_numbered_and_timed(self):
        queue = TicketQueue()
        first = open_ticket(queue, 'Payment failed', 'ann@example.com', dt.datetime(2026, 3, 9, 13, 0, 42))
        second = open_ticket(queue, 'Question about invoices', 'bo@example.com', at('2026-03-09 13:05'))
        self.assertEqual((first.number, second.number), (1, 2))
        self.assertEqual(first.opened_at, at('2026-03-09 13:00'))
        self.assertEqual(first.due_at, at('2026-03-10 11:00'))
        self.assertEqual(first.channel, 'portal')
        self.assertEqual(queue.get(2).priority, 'low')

    def test_requests_are_taken_when_the_desk_is_closed(self):
        queue = TicketQueue()
        ticket = open_ticket(queue, 'Please change my address', 'cy@example.com', at('2026-03-14 23:10'))
        self.assertEqual(ticket.opened_at, at('2026-03-14 23:10'))                 # a Saturday night
        self.assertGreater(ticket.due_at, ticket.opened_at)
        self.assertEqual(len(queue), 1)

    def test_email(self):
        queue = TicketQueue()
        raw = 'From: Dee Shop <dee@example.com>\r\nSubject: Refund for order 551\r\n\r\nI was charged twice.\r\n'
        ticket = open_from_email(queue, raw, at('2026-03-09 13:00'), plans={'dee@example.com': 'standard'})
        self.assertEqual((ticket.subject, ticket.customer, ticket.channel), ('Refund for order 551', 'dee@example.com',
                                                                              'email'))
        self.assertEqual(ticket.priority, 'high')
        with self.assertRaises(ValueError):
            open_ticket(queue, 'Hello', 'x@example.com', at('2026-03-09 13:00'), channel='fax')


if __name__ == '__main__':
    unittest.main()
