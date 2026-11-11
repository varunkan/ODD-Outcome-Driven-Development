# scheduler

Helpers for booking one room over one day. Python 3, standard library only.

## What is in it

`scheduler.intervals`: spans of time, in whole minutes since midnight.

- `Interval(start, end)` covers `start` up to, but not including, `end`. 09:00 to 10:00 is `Interval(540, 600)` and
  is sixty minutes long.
- `parse_time("09:30")` gives `570`; `format_time(570)` gives `"09:30"`.
- `overlaps(a, b)`: do two intervals have time in common?
- `merge(intervals)`: join intervals that overlap, or that follow each other without a gap, into blocks.
- `gaps(intervals, window)`: the free intervals left inside a window.
- `total_minutes(intervals)`: minutes covered, with shared time counted once.

`scheduler.bookings`: one day's bookings for one room.

- `Schedule(opens="08:00", closes="18:00")`
- `book(title, start, end)` adds a booking. It raises `BookingConflict` when the room is taken at that time and
  `ValueError` when the times fall outside opening hours.
- `cancel(title)`, `bookings()`, `conflicts(start, end)`
- `busy_blocks()`: booked time as `("HH:MM", "HH:MM")` pairs, joined into blocks.
- `free_slots(minimum=1)`: unbooked time inside opening hours.
- `first_free(minutes, after=None)`: the earliest free slot of a given length, or `None`.

## Example

```python
from scheduler.bookings import Schedule

room = Schedule()
room.book("Standup", "09:00", "09:30")
room.book("Lunch talk", "13:00", "14:00")
room.free_slots(minimum=60)     # [("09:30", "13:00"), ("14:00", "18:00")]
room.first_free(90)             # ("09:30", "11:00")
```

## Tests

```
python3 -m unittest
```
