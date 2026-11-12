"""When the support desk is staffed.

Ops own the opening hours below and the holiday list in holidays.py; nothing else in the package decides them. All
times are naive local datetimes in the desk's own time zone.

Desk time is the time during which someone is on the desk. Service targets are counted in desk time: a target of
60 minutes set at 17:30 on a Friday runs out at 08:30 on the Monday.
"""
import datetime as dt

from .holidays import HOLIDAYS

OPENS = dt.time(8, 0)
CLOSES = dt.time(18, 0)
WORKDAYS = frozenset(range(5))  # Monday (0) to Friday (4)

_DAY = dt.timedelta(days=1)
_SEARCH_DAYS = 366


class Desk:
    """Opening hours of a desk: the same hours on every workday; closed at night, at weekends and on holidays."""

    def __init__(self, opens=OPENS, closes=CLOSES, workdays=WORKDAYS, holidays=()):
        if not opens < closes:
            raise ValueError('the desk must open before it closes')
        workdays = frozenset(workdays)
        if not workdays or not workdays <= set(range(7)):
            raise ValueError('workdays are weekday numbers, Monday 0 to Sunday 6')
        self.opens = opens
        self.closes = closes
        self.workdays = workdays
        self.holidays = frozenset(holidays)

    def __repr__(self):
        return 'Desk(%s-%s, workdays=%s, %d holidays)' % (
            self.opens.strftime('%H:%M'), self.closes.strftime('%H:%M'), sorted(self.workdays), len(self.holidays))

    def is_workday(self, day):
        """True when the desk opens at all on day (a date)."""
        return day.weekday() in self.workdays and day not in self.holidays

    def is_open(self, moment):
        """True when someone is on the desk at moment: a workday, from opening time up to, not including, closing."""
        return self.is_workday(moment.date()) and self.opens <= moment.time() < self.closes

    def opening(self, day):
        return dt.datetime.combine(day, self.opens)

    def closing(self, day):
        return dt.datetime.combine(day, self.closes)

    def next_open(self, moment):
        """moment itself when the desk is open then, otherwise the first opening time after it."""
        if self.is_open(moment):
            return moment
        day = moment.date()
        if self.is_workday(day) and moment.time() < self.opens:
            return self.opening(day)
        for _ in range(_SEARCH_DAYS):
            day += _DAY
            if self.is_workday(day):
                return self.opening(day)
        raise ValueError('the desk does not open within a year after %s' % moment)

    def previous_close(self, moment):
        """The last closing time at or before moment (moment itself is never returned while the desk is open)."""
        day = moment.date()
        if self.is_workday(day) and moment >= self.closing(day):
            return self.closing(day)
        for _ in range(_SEARCH_DAYS):
            day -= _DAY
            if self.is_workday(day):
                return self.closing(day)
        raise ValueError('the desk was not open within a year before %s' % moment)

    def add_working_minutes(self, start, minutes):
        """The moment at which `minutes` of desk time have gone by since start.

        Time while the desk is closed does not count. When start falls while the desk is closed, counting starts at
        the next opening; zero minutes gives that opening. When the minutes run out exactly at closing time, the
        closing time is returned.
        """
        if minutes < 0:
            raise ValueError('minutes must be zero or more')
        moment = self.next_open(start)
        left = dt.timedelta(minutes=minutes)
        while True:
            closing = self.closing(moment.date())
            if moment + left <= closing:
                return moment + left
            left -= closing - moment
            moment = self.next_open(closing)

    def working_minutes_between(self, start, end):
        """Whole minutes of desk time from start to end; 0 when end is not after start."""
        if end <= start:
            return 0
        total = dt.timedelta()
        moment = self.next_open(start)
        while moment < end:
            closing = self.closing(moment.date())
            total += min(closing, end) - moment
            moment = self.next_open(closing)
        return int(total.total_seconds() // 60)

    def open_days(self, first, last):
        """The workdays from first to last, both dates included."""
        days = []
        day = first
        while day <= last:
            if self.is_workday(day):
                days.append(day)
            day += _DAY
        return days


DEFAULT_DESK = Desk(holidays=HOLIDAYS)
