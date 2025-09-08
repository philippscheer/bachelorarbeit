from loguru import logger
from typing import TypeVar
from itertools import combinations
from collections import defaultdict
from datetime import datetime, time
from functools import lru_cache

from bachelorarbeit.dtypes import Offering
from bachelorarbeit.constraints import (
    FIXED_TIME_CONSTRAINTS,
    NON_FIXED_TIME_CONSTRAINTS,
    COURSE_PRIORITY_CONSTRAINTS,
    HOUR_LOAD_CONSTRAINT,
    COURSE_COUNT_CONSTRAINT,
    HOURS_MUST_NOT_SCHEDULE,
    COURSE_MUST_NOT_SCHEDULE,
    HOURS_FLEXIBLE,
)


T = TypeVar("T")


# === Implicit constraints ===


def is_valid_schedule(schedule: list[Offering], ignore_length: bool = False, verbose=False):
    if schedule_overlaps(schedule):
        if verbose:
            logger.debug("schedule overlaps")
        return False

    if not ignore_length and (len(schedule) < COURSE_COUNT_CONSTRAINT[0] or len(schedule) > COURSE_COUNT_CONSTRAINT[1]):
        if verbose:
            logger.debug("schedule does not satisfy course count constraint")
        return False

    if not ignore_length:
        min_hrs, max_hrs = weekly_schedule_hours(schedule)
        if min_hrs < HOUR_LOAD_CONSTRAINT[0] or max_hrs > HOUR_LOAD_CONSTRAINT[1]:
            if verbose:
                logger.debug("schedule does not satisfy hour load constraint")
            return False

    for offering in schedule:
        if violates_hard_constraints(offering):
            if verbose:
                logger.debug("schedule violates hard constraints")
            return False

    return True


def schedule_overlaps(schedule: list[Offering]):
    all_date_ranges = flatten([offering.dates for offering in schedule])
    for range1, range2 in combinations(all_date_ranges, 2):
        if dates_overlap(range1["start"], range1["end"], range2["start"], range2["end"]):
            return True
    return False


# === Validate constraints ===


def flatten(xss: list[list[T]]) -> list[T]:
    return [x for xs in xss for x in xs]


def dates_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime):
    return start1 < end2 and end1 > start2


def times_overlap(start1: datetime, end1: datetime, start2: int, end2: int):
    start1 = start1.time()
    end1 = end1.time()

    start2 = time(start2, 0)
    end2 = time(end2, 0)

    return start1 < end2 and end1 > start2


def violates_fixed_time(start: datetime, end: datetime):
    for hour in HOURS_MUST_NOT_SCHEDULE:
        if times_overlap(start, end, hour, hour + 1):
            return True
    return False


@lru_cache(maxsize=500)
def violates_hard_constraints(offering: Offering):
    if offering.courseId in COURSE_MUST_NOT_SCHEDULE:
        logger.debug("course id not allowed")
        return True

    for date in offering.dates:
        if violates_fixed_time(date["start"], date["end"]):
            logger.debug("violates fixed time")
            return True

    return False


def weekly_schedule_hours(schedule: list[Offering]) -> tuple[float, float]:
    """
    Returns (min_hours, max_hours) the schedule takes up in one week (Mo-Fr),
    counting parallel sessions only once.
    """
    week_intervals = defaultdict(list)  # (year, week) -> list of (start, end)

    for offering in schedule:
        for session in offering.dates:
            start = session["start"]
            end = session["end"]

            # only count Mo - Fr
            if start.weekday() > 4 or end.weekday() > 4:
                continue

            year, week, _ = start.isocalendar()
            week_intervals[(year, week)].append((start, end))

    week_hours = {}
    for week, intervals in week_intervals.items():
        merged = merge_intervals(intervals)
        total_hours = sum((end - start).total_seconds() / 3600 for start, end in merged)
        week_hours[week] = total_hours

    if not week_hours:
        return (0.0, 0.0)

    totals = week_hours.values()
    return (min(totals), max(totals))


def merge_intervals(intervals: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """
    Merge overlapping intervals and return a list of disjoint intervals.
    Courses at the same time do not count twice to the hour load constraint
    """
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    for current_start, current_end in intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:  # overlap
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


# === Calculate mark ===


@lru_cache(maxsize=500)
def get_offering_mark(offering: Offering):
    mark = 0
    mark += COURSE_PRIORITY_CONSTRAINTS.get(offering.groupId, 0)
    for date in offering.dates:
        for hour, mark_change in HOURS_FLEXIBLE.items():
            if times_overlap(date["start"], date["end"], hour, hour + 1):
                mark += mark_change
    return mark


def get_schedule_mark(schedule: list[Offering]):
    mark = 0
    for offering in schedule:
        if violates_hard_constraints(offering):
            return None
        mark += get_offering_mark(offering)
    return mark


def rebuild_available_offerings(schedule: list[Offering], available_offerings: list[Offering]) -> list[Offering]:
    taken_group_ids = list(set(map(lambda offering: offering.groupId, schedule)))
    taken_course_ids = list(map(lambda o: o.courseId, schedule))

    def _filter_available_offerings(previously_available_offering: Offering):
        if previously_available_offering.courseId in taken_course_ids:
            return False

        if previously_available_offering.groupId in taken_group_ids:
            return False

        if not is_valid_schedule([*schedule, previously_available_offering], ignore_length=True):
            return False

        return True

    return list(filter(_filter_available_offerings, available_offerings))


def preprocess(offerings: list[Offering]) -> list[Offering]:
    """
    Filter the offerings by variable inconsistency as mentioned on p357
    """
    logger.info(f"preprocessing {len(offerings)} offerings")
    keep_offerings = [
        offering for offering in offerings if offering.groupId is not None and not violates_hard_constraints(offering)
    ]

    for i, offering in enumerate(keep_offerings):
        keep_offerings[i].mark = get_offering_mark(offering)

    logger.success(f"preprocessed offerings, keep {len(keep_offerings)}")
    return keep_offerings
