"""Support desk tickets: intake, service targets, the queue and the weekly report."""
from .clock import format_time, parse_time
from .desk import DEFAULT_DESK, Desk
from .intake import classify, open_from_email, open_ticket
from .queue import TicketQueue
from .report import format_report, service_report
from .tickets import Ticket

__all__ = ['DEFAULT_DESK', 'Desk', 'Ticket', 'TicketQueue', 'classify', 'format_report', 'format_time',
           'open_from_email', 'open_ticket', 'parse_time', 'service_report']
