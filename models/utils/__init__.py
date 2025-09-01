from loguru import logger
from typing import TypeVar
from itertools import combinations
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
