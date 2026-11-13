# Back-to-back bookings are refused as conflicts

We use the `scheduler` package to book the meeting room. A booking that starts exactly when another one ends is
refused:

```python
from scheduler.bookings import Schedule

room = Schedule(opens="08:00", closes="18:00")
room.book("Standup", "09:00", "10:00")
room.book("Design review", "10:00", "11:00")   # BookingConflict: clashes with: Standup
```

Standup is over at 10:00, so the room is free from 10:00 on. The same happens the other way round: with Standup
booked, `room.book("Prep", "08:00", "09:00")` is refused as well. The schedule even refuses its own suggestion: with
only Standup booked, `room.first_free(60)` returns `("08:00", "09:00")`, and booking exactly that slot fails.

What should happen:

- `Schedule.book(title, start, end)` accepts a booking that only touches other bookings, at its start, at its end,
  or at both. Times that really overlap, even by a single minute, must still raise `BookingConflict`.
- `Schedule.conflicts(start, end)` returns only the bookings that really overlap the given times, so
  `room.conflicts("10:00", "11:00")` is an empty list when only Standup is booked. (Each booking it returns has a
  `.title`.)
- `scheduler.intervals.overlaps(a, b)` is false for two `Interval(start, end)` values (whole minutes since midnight)
  that only touch, in whichever order they are passed, and true as soon as they share a minute.
- A slot returned by `Schedule.first_free(minutes)` can always be booked. (It returns a `(start, end)` pair of
  `"HH:MM"` strings, or `None` when no slot of that length is left.)
- `Schedule.busy_blocks()` shows back-to-back bookings as one block: `[("09:00", "11:00")]` for Standup followed by
  Design review.
