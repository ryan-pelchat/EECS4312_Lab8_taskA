## Student Name: Ryan Pelchat
## Student ID: 218431957

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from typing import List, Optional
from zoneinfo import ZoneInfo

# ---------------- Data Models ----------------


@dataclass(frozen=True)
class TimeWindow:
    start: time
    end: time


@dataclass(frozen=True)
class BusyInterval:
    start: time
    end: time


@dataclass(frozen=True)
class Slot:
    start_time: time


class InfeasibleSchedule(Exception):
    pass


# ---------------- Helpers ----------------

ONTARIO_TZ = ZoneInfo("America/Toronto")


def _is_weekend(d: date) -> bool:
    return d.weekday() >= 5


def _is_ontario_holiday(d: date) -> bool:
    """
    Minimal deterministic Ontario holiday set (no external deps).
    Covers major fixed + computed holidays.
    """
    year = d.year

    # Fixed-date holidays
    fixed = {
        date(year, 1, 1),  # New Year's Day
        date(year, 7, 1),  # Canada Day
        date(year, 12, 25),  # Christmas
    }

    if d in fixed:
        return True

    # Helper: nth weekday of month
    def nth_weekday(month, weekday, n):
        first = date(year, month, 1)
        shift = (weekday - first.weekday()) % 7
        return first + timedelta(days=shift + 7 * (n - 1))

    # Helper: last weekday of month
    def last_weekday(month, weekday):
        if month == 12:
            last = date(year, 12, 31)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        shift = (last.weekday() - weekday) % 7
        return last - timedelta(days=shift)

    holidays = {
        nth_weekday(2, 0, 3),  # Family Day (3rd Monday Feb)
        last_weekday(5, 0),  # Victoria Day (last Monday May)
        nth_weekday(9, 0, 1),  # Labour Day (1st Monday Sep)
        nth_weekday(10, 0, 2),  # Thanksgiving (2nd Monday Oct)
    }

    # Civic Holiday (1st Monday Aug)
    holidays.add(nth_weekday(8, 0, 1))

    return d in holidays


def _to_datetime(d: date, t: time) -> datetime:
    return datetime.combine(d, t).replace(tzinfo=ONTARIO_TZ)


def _align_to_5_minutes(dt: datetime) -> datetime:
    minute_mod = dt.minute % 5
    if minute_mod != 0 or dt.second != 0 or dt.microsecond != 0:
        dt += timedelta(minutes=(5 - minute_mod))
        dt = dt.replace(second=0, microsecond=0)
    return dt


def _merge_intervals(intervals):
    if not intervals:
        return []
    intervals.sort()
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return merged


# ---------------- Core Function ----------------


def suggest_slots(
    day: date,
    working_hours: TimeWindow,
    busy_intervals: List[BusyInterval],
    duration: timedelta,
    n: int,
    buffer: timedelta = timedelta(0),
    candidate_window: Optional[TimeWindow] = None,
) -> List[Slot]:

    # ---- Basic validation ----
    if n <= 0 or duration.total_seconds() <= 0:
        return []

    # Enforce 5-minute factor duration
    if (duration.total_seconds() // 60) % 5 != 0:
        return []

    # Skip weekends & holidays
    if _is_weekend(day) or _is_ontario_holiday(day):
        return []

    # ---- Build working window ----
    start_dt = _to_datetime(day, working_hours.start)
    end_dt = _to_datetime(day, working_hours.end)

    if candidate_window:
        start_dt = max(start_dt, _to_datetime(day, candidate_window.start))
        end_dt = min(end_dt, _to_datetime(day, candidate_window.end))

    if start_dt >= end_dt:
        return []

    # ---- Respect current system time ----
    now = datetime.now(ONTARIO_TZ)
    if day == now.date():
        start_dt = max(start_dt, now)

    # ---- Normalize busy intervals with buffer ----
    normalized = []
    for b in busy_intervals:
        s = _to_datetime(day, b.start) - buffer
        e = _to_datetime(day, b.end) + buffer
        normalized.append((s, e))

    merged_busy = _merge_intervals(normalized)

    # ---- Compute free gaps ----
    free_gaps = []
    cursor = start_dt

    for s, e in merged_busy:
        if e <= cursor:
            continue
        if s > cursor:
            free_gaps.append((cursor, min(s, end_dt)))
        cursor = max(cursor, e)
        if cursor >= end_dt:
            break

    if cursor < end_dt:
        free_gaps.append((cursor, end_dt))

    # ---- Generate slots (5-minute grid) ----
    slots: List[Slot] = []
    step = timedelta(minutes=5)

    for gap_start, gap_end in free_gaps:
        current = _align_to_5_minutes(gap_start)

        while current + duration <= gap_end:
            slots.append(Slot(start_time=current.timetz().replace(tzinfo=None)))

            if len(slots) >= n:
                return sorted(slots, key=lambda s: s.start_time)

            current += step

    # ---- Requirement: notify if no availability ----
    if not slots:
        return []

    return sorted(slots, key=lambda s: s.start_time)


# """
# Task A: Appointment Timeslot Recommender (Stub)

# In this lab, you will design and implement an Appointment Slot Recommender using an LLM assistant
# as your primary programming collaborator.

# You are asked to implement a Python module that recommends available meeting slots within a
# defined working window.

# The system must:
#   • Accept working hours (start and end time).
#   • Accept a list of existing busy intervals.
#   • Accept a required meeting duration.
#   • Accept an optional buffer time between meetings.
#   • Optionally restrict suggestions to a candidate time window.
#   • Return chronologically ordered appointment slots that satisfy all constraints.

# The system must ensure that:
#   • Suggested slots fall within working hours.
#   • Suggested slots do not overlap busy intervals.
#   • Buffer time is respected when evaluating availability.
#   • Output ordering is deterministic under identical inputs.

# The module must preserve the following invariants:
#   • Returned slots must be at least as long as the required duration.
#   • No returned slot may violate buffer constraints.
#   • The returned list must reflect the current system state.

# The system must correctly handle non-trivial scenarios such as:
#   • Adjacent busy intervals.
#   • Very small gaps between meetings.
#   • Buffers eliminating otherwise valid availability.
#   • Overlapping or unsorted busy intervals.
#   • A meeting duration longer than any available gap.
#   • No availability within the working window.

# Output:
#   The output consists of the next N valid appointment suggestions in chronological order.
#   Behavior must be deterministic under ties (if any).

# See the lab handout for full requirements.
# """

# from dataclasses import dataclass
# from datetime import date, datetime, timedelta, time
# from typing import List, Optional, Tuple


# # ---------------- Data Models ----------------

# @dataclass(frozen=True)
# class TimeWindow:
#     """
#     A daily time window.
#     Assumption (unless stated otherwise in handout): non-wrapping window where start < end.
#     """
#     start: time
#     end: time


# @dataclass(frozen=True)
# class BusyInterval:
#     """
#     A busy interval on the given day.
#     Invariant: start < end
#     """
#     start: time
#     end: time


# @dataclass(frozen=True)
# class Slot:
#     """
#     A recommended appointment slot.

#     start_time is a time-of-day within the working window.
#     Deterministic ordering: sort by start_time ascending.
#     """
#     start_time: time


# class InfeasibleSchedule(Exception):
#     """Raised when no valid slots can be produced (if required by handout)."""
#     pass


# # ---------------- Core Function ----------------

# def suggest_slots(
#     day: date,
#     working_hours: TimeWindow,
#     busy_intervals: List[BusyInterval],
#     duration: timedelta,
#     n: int,
#     buffer: timedelta = timedelta(0),
#     candidate_window: Optional[TimeWindow] = None
# ) -> List[Slot]:
#     """
#     Suggest up to the next n valid appointment slots (start times) for the given day.

#     Args:
#         day: the calendar day for which to suggest slots.
#         working_hours: the allowed working window for meetings (start < end).
#         busy_intervals: list of busy time intervals (may be overlapping / unsorted).
#         duration: required meeting length (must be > 0).
#         n: maximum number of slot suggestions to return (n >= 0).
#         buffer: optional buffer time required between meetings (buffer >= 0).
#         candidate_window: optional extra restriction on suggestions (must lie within this window too).

#     Returns:
#         A list of Slot objects, sorted by start_time ascending, deterministic under identical inputs.
#         If no suitable time slots are available, return an empty list.

#     Notes:
#         - Suggested slots must fall within working_hours (and candidate_window if provided).
#         - Suggested slots must not overlap busy_intervals, considering buffer time.
#         - You are free to choose internal representation; inputs use time-of-day.
#         - See lab handout for required slot granularity (e.g., 5-min/15-min steps), if any.
#     """

#     ##################################################################
#     # TODO: Implement as per lab handout requirements and constraints.
#     ##################################################################

#     raise NotImplementedError("suggest_slots has not been implemented yet")
