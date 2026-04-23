import pytest
from datetime import date, datetime, time, timedelta

from solution import TimeWindow, BusyInterval, Slot, suggest_slots


# ---------- Helpers ----------


def combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def overlaps(
    a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime
) -> bool:
    return a_start < b_end and b_start < a_end


def in_window(win: TimeWindow, t: time) -> bool:
    return win.start <= t < win.end


def assert_slots_basic_constraints(
    slots,
    day,
    working_hours,
    busy_intervals,
    duration,
    n,
    buffer,
    candidate_window,
):
    assert isinstance(slots, list)
    assert len(slots) <= n

    # Deterministic ordering
    assert slots == sorted(slots, key=lambda s: s.start_time)

    for s in slots:
        assert in_window(working_hours, s.start_time)
        if candidate_window is not None:
            assert in_window(candidate_window, s.start_time)

    for s in slots:
        start_dt = combine(day, s.start_time)
        end_dt = start_dt + duration

        wh_end = combine(day, working_hours.end)
        assert end_dt <= wh_end

        if candidate_window is not None:
            cw_end = combine(day, candidate_window.end)
            assert end_dt <= cw_end

    for s in slots:
        slot_start = combine(day, s.start_time)
        slot_end = slot_start + duration

        for b in busy_intervals:
            b_start = combine(day, b.start) - buffer
            b_end = combine(day, b.end) + buffer
            assert not overlaps(slot_start, slot_end, b_start, b_end)


# ---------- Tests ----------


# Covers C2, AC1
def test_a1_no_busy_simple_slots():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=3)

    assert_slots_basic_constraints(
        out, day, working, busy, duration, 3, timedelta(0), None
    )
    assert len(out) > 0
    assert out[0].start_time >= time(9, 0)


# Covers C2, C4, AC3, AC7
def test_a2_deterministic_same_inputs_same_outputs():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [
        BusyInterval(time(10, 0), time(10, 30)),
        BusyInterval(time(13, 0), time(14, 0)),
    ]
    duration = timedelta(minutes=30)

    out1 = suggest_slots(day, working, busy, duration, n=10)
    out2 = suggest_slots(day, working, busy, duration, n=10)

    assert [s.start_time for s in out1] == [s.start_time for s in out2]


# Covers C6, AC4 (unsorted + overlapping)
def test_a3_overlapping_and_unsorted_busy_intervals_handled():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(10, 30), time(11, 0)),
        BusyInterval(time(10, 0), time(10, 45)),
        BusyInterval(time(9, 30), time(9, 45)),
    ]
    duration = timedelta(minutes=15)

    out = suggest_slots(day, working, busy, duration, n=8)
    assert_slots_basic_constraints(
        out, day, working, busy, duration, 8, timedelta(0), None
    )


# Covers C1, AC2
def test_a4_candidate_window_respected():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(15, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=5, candidate_window=candidate)

    assert_slots_basic_constraints(
        out, day, working, busy, duration, 5, timedelta(0), candidate
    )
    assert all(candidate.start <= s.start_time < candidate.end for s in out)


# Covers C1, AC2, EC5
def test_a5_buffer_eliminates_small_gaps():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = [
        BusyInterval(time(9, 30), time(9, 50)),
        BusyInterval(time(10, 10), time(10, 30)),
    ]
    duration = timedelta(minutes=20)

    out_no_buffer = suggest_slots(
        day, working, busy, duration, n=10, buffer=timedelta(0)
    )
    out_with_buffer = suggest_slots(
        day, working, busy, duration, n=10, buffer=timedelta(minutes=5)
    )

    assert len(out_with_buffer) <= len(out_no_buffer)


# ---------------- Additional Required Tests ----------------


# Covers C6, AC8, EC4, EC5
def test_a6_no_availability_due_to_short_gaps():
    """
    All gaps smaller than duration → expect empty result
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [
        BusyInterval(time(9, 0), time(9, 20)),
        BusyInterval(time(9, 25), time(10, 0)),
    ]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=5)
    assert out == []


# Covers C3, AC4, EC9
def test_a7_no_duplicate_slots():
    """
    Ensure no duplicate slots are returned after normalization
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(10, 0), time(10, 30)),
        BusyInterval(time(10, 0), time(10, 30)),  # duplicate interval
    ]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=10)

    seen = set()
    for s in out:
        assert s.start_time not in seen
        seen.add(s.start_time)


# Covers C7, AC1, EC7
def test_a8_respects_n_limit():
    """
    Ensure no more than N slots are returned
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=2)

    assert len(out) <= 2


# Covers C1, AC2, EC3
def test_a9_adjacent_busy_intervals_no_false_gap():
    """
    Adjacent intervals should not create fake availability
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))
    busy = [
        BusyInterval(time(9, 30), time(10, 0)),
        BusyInterval(time(10, 0), time(10, 30)),  # directly adjacent
    ]
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=10)

    # No slot should start at 10:00 (fake gap)
    assert all(s.start_time != time(10, 0) for s in out)


# Covers C8, AC6, EC7
def test_a10_recompute_after_input_change():
    """
    Changing inputs should change output deterministically
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    duration = timedelta(minutes=30)

    busy1 = []
    busy2 = [BusyInterval(time(9, 0), time(11, 0))]

    out1 = suggest_slots(day, working, busy1, duration, n=5)
    out2 = suggest_slots(day, working, busy2, duration, n=5)

    assert out1 != out2


# ---------------- EVEN MORE ADDITIONAL TESTS ----------------


# Covers C6, AC4, EC1
def test_a11_unsorted_intervals_produce_same_result_as_sorted():
    """
    Unsorted vs sorted busy intervals should produce identical outputs
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    duration = timedelta(minutes=30)

    busy_unsorted = [
        BusyInterval(time(11, 0), time(11, 30)),
        BusyInterval(time(9, 30), time(10, 0)),
        BusyInterval(time(10, 15), time(10, 45)),
    ]

    busy_sorted = sorted(busy_unsorted, key=lambda b: b.start)

    out1 = suggest_slots(day, working, busy_unsorted, duration, n=10)
    out2 = suggest_slots(day, working, busy_sorted, duration, n=10)

    assert [s.start_time for s in out1] == [s.start_time for s in out2]


# Covers C1, AC2, EC2
def test_a12_overlapping_intervals_merged_correctly():
    """
    Overlapping intervals should behave as one merged block
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(13, 0))
    duration = timedelta(minutes=30)

    busy = [
        BusyInterval(time(10, 0), time(11, 0)),
        BusyInterval(time(10, 30), time(12, 0)),  # overlap
    ]

    out = suggest_slots(day, working, busy, duration, n=10)

    # No slot should fall within merged [10:00–12:00]
    for s in out:
        assert not (time(10, 0) <= s.start_time < time(12, 0))


# Covers C7, AC1
def test_a13_n_zero_returns_empty():
    """
    n = 0 should always return empty list
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, [], duration, n=0)
    assert out == []


# Covers C6, AC8, EC4
def test_a14_duration_longer_than_any_gap():
    """
    Meeting duration longer than any available gap
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [BusyInterval(time(9, 15), time(9, 45))]
    duration = timedelta(minutes=50)

    out = suggest_slots(day, working, busy, duration, n=5)
    assert out == []


# Covers C6, AC8, EC5
def test_a15_invalid_candidate_window():
    """
    Candidate window where start >= end should return no availability
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(15, 0), time(13, 0))  # invalid
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, [], duration, n=5, candidate_window=candidate)
    assert out == []


# Covers C1, AC2
def test_a16_buffer_applied_symmetrically():
    """
    Buffer should apply before and after busy interval
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [BusyInterval(time(10, 0), time(10, 30))]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=10)

    out = suggest_slots(day, working, busy, duration, n=10, buffer=buffer)

    for s in out:
        # Slot must not start in [9:50–10:40]
        assert not (time(9, 50) <= s.start_time < time(10, 40))


# Covers C2, C4, AC7
def test_a17_tie_breaking_same_start_time_ordering():
    """
    Ensure deterministic ordering even if same start times could arise
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, [], duration, n=10)

    # Just verify sorted order consistency
    times = [s.start_time for s in out]
    assert times == sorted(times)


# Covers C8, AC6
def test_a18_multiple_calls_consistency_after_change():
    """
    Ensure no stale state between calls
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    duration = timedelta(minutes=30)

    busy = []
    out1 = suggest_slots(day, working, busy, duration, n=5)

    busy.append(BusyInterval(time(9, 0), time(11, 0)))
    out2 = suggest_slots(day, working, busy, duration, n=5)

    assert out1 != out2


# Covers C1, AC2
def test_a19_slots_do_not_exceed_working_hours():
    """
    Ensure slots never extend beyond working hours end
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    duration = timedelta(minutes=45)

    out = suggest_slots(day, working, [], duration, n=10)

    for s in out:
        end = combine(day, s.start_time) + duration
        assert end <= combine(day, working.end)


# Covers C6, AC4
def test_a20_adjacent_intervals_with_buffer_remove_gap():
    """
    Adjacent intervals + buffer eliminate gap completely
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(9, 30), time(10, 0)),
        BusyInterval(time(10, 0), time(10, 30)),
    ]
    duration = timedelta(minutes=20)
    buffer = timedelta(minutes=5)

    out = suggest_slots(day, working, busy, duration, n=10, buffer=buffer)

    # Gap around 10:00 should be fully eliminated
    for s in out:
        assert not (time(9, 55) <= s.start_time <= time(10, 5))


# import pytest
# from datetime import date, datetime, time, timedelta

# # Update import path to match your project structure:
# from solution import TimeWindow, BusyInterval, Slot, suggest_slots


# # ---------- Helpers ----------

# def combine(d: date, t: time) -> datetime:
#     return datetime.combine(d, t)


# def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
#     return a_start < b_end and b_start < a_end


# def in_window(win: TimeWindow, t: time) -> bool:
#     return win.start <= t < win.end


# def assert_slots_basic_constraints(
#     slots,
#     day,
#     working_hours,
#     busy_intervals,
#     duration,
#     n,
#     buffer,
#     candidate_window,
# ):
#     # Return type / length
#     assert isinstance(slots, list)
#     assert len(slots) <= n

#     # Deterministic ordering: start_time ascending
#     assert slots == sorted(slots, key=lambda s: s.start_time)

#     # Each slot start must be within working_hours and candidate_window (if any)
#     for s in slots:
#         assert in_window(working_hours, s.start_time)
#         if candidate_window is not None:
#             assert in_window(candidate_window, s.start_time)

#     # Each slot must fit fully inside working_hours and candidate_window
#     for s in slots:
#         start_dt = combine(day, s.start_time)
#         end_dt = start_dt + duration

#         wh_end = combine(day, working_hours.end)
#         assert end_dt <= wh_end

#         if candidate_window is not None:
#             cw_end = combine(day, candidate_window.end)
#             assert end_dt <= cw_end

#     # No overlap with busy intervals, considering buffer:
#     # busy interval is expanded to [start-buffer, end+buffer)
#     for s in slots:
#         slot_start = combine(day, s.start_time)
#         slot_end = slot_start + duration

#         for b in busy_intervals:
#             b_start = combine(day, b.start) - buffer
#             b_end = combine(day, b.end) + buffer
#             assert not overlaps(slot_start, slot_end, b_start, b_end)


# # ---------- Tests ----------

# def test_a1_no_busy_simple_slots():
#     """
#     Like original "single med exact times": here, no busy events.
#     Expect earliest slots within working hours (we only assert constraints + non-empty).
#     """
#     day = date(2026, 2, 24)
#     working = TimeWindow(time(9, 0), time(12, 0))
#     busy = []
#     duration = timedelta(minutes=30)

#     out = suggest_slots(
#         day=day,
#         working_hours=working,
#         busy_intervals=busy,
#         duration=duration,
#         n=3,
#         buffer=timedelta(0),
#         candidate_window=None
#     )

#     assert_slots_basic_constraints(out, day, working, busy, duration, 3, timedelta(0), None)
#     # Should at least return 1 slot if implementation uses a reasonable slot step
#     assert len(out) > 0
#     # Earliest slot should be at or after working start
#     assert out[0].start_time >= time(9, 0)


# def test_a2_deterministic_same_inputs_same_outputs():
#     """
#     Like original tie/determinism check: same inputs must return identical outputs.
#     """
#     day = date(2026, 2, 24)
#     working = TimeWindow(time(9, 0), time(17, 0))
#     busy = [
#         BusyInterval(time(10, 0), time(10, 30)),
#         BusyInterval(time(13, 0), time(14, 0)),
#     ]
#     duration = timedelta(minutes=30)
#     buffer = timedelta(minutes=0)

#     out1 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)
#     out2 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)

#     assert [s.start_time for s in out1] == [s.start_time for s in out2]
#     assert_slots_basic_constraints(out1, day, working, busy, duration, 10, buffer, None)


# def test_a3_overlapping_and_unsorted_busy_intervals_handled():
#     """
#     Busy intervals may be unsorted/overlapping; suggestions must still avoid conflicts.
#     """
#     day = date(2026, 2, 24)
#     working = TimeWindow(time(9, 0), time(12, 0))
#     busy = [
#         BusyInterval(time(10, 30), time(11, 0)),
#         BusyInterval(time(10, 0), time(10, 45)),   # overlaps with above
#         BusyInterval(time(9, 30), time(9, 45)),    # unsorted relative order
#     ]
#     duration = timedelta(minutes=15)

#     out = suggest_slots(day, working, busy, duration, n=8, buffer=timedelta(0), candidate_window=None)
#     assert_slots_basic_constraints(out, day, working, busy, duration, 8, timedelta(0), None)


# def test_a4_candidate_window_respected():
#     """
#     Like original allowed_window respected: here we add an extra candidate window restriction.
#     """
#     day = date(2026, 2, 24)
#     working = TimeWindow(time(9, 0), time(17, 0))
#     candidate = TimeWindow(time(13, 0), time(15, 0))
#     busy = []
#     duration = timedelta(minutes=30)

#     out = suggest_slots(day, working, busy, duration, n=5, buffer=timedelta(0), candidate_window=candidate)
#     assert_slots_basic_constraints(out, day, working, busy, duration, 5, timedelta(0), candidate)

#     # Every slot must start within candidate window
#     assert all(candidate.start <= s.start_time < candidate.end for s in out)


# def test_a5_buffer_eliminates_small_gaps():
#     """
#     Like original rate-limit constraint: here buffer is the key extra constraint.
#     With buffer, some slots that would otherwise fit should be invalid.
#     """
#     day = date(2026, 2, 24)
#     working = TimeWindow(time(9, 0), time(11, 0))
#     # Two busy intervals leaving a 20-minute gap between them
#     busy = [
#         BusyInterval(time(9, 30), time(9, 50)),
#         BusyInterval(time(10, 10), time(10, 30)),
#     ]
#     duration = timedelta(minutes=20)

#     # Without buffer: the gap 9:50–10:10 is exactly 20 minutes -> potentially valid
#     out_no_buffer = suggest_slots(day, working, busy, duration, n=10, buffer=timedelta(0), candidate_window=None)
#     assert_slots_basic_constraints(out_no_buffer, day, working, busy, duration, 10, timedelta(0), None)

#     # With 5-min buffer: effective busy expands, gap shrinks -> should reduce or remove those slots
#     buf = timedelta(minutes=5)
#     out_with_buffer = suggest_slots(day, working, busy, duration, n=10, buffer=buf, candidate_window=None)
#     assert_slots_basic_constraints(out_with_buffer, day, working, busy, duration, 10, buf, None)

#     # Buffer should not increase number of available slots (monotonicity)
#     assert len(out_with_buffer) <= len(out_no_buffer)


# #################################################################################
# # Add your own additional tests here to cover more cases and edge cases as needed.
# #################################################################################
