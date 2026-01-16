from loguru import logger
from typing import TypeVar, Literal
from itertools import combinations
from collections import defaultdict
from datetime import datetime, time

from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

T = TypeVar("T")

Weekday = Literal[
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
]

# === Implicit constraints ===


def is_valid_schedule(
    schedule: list[Offering], schedule_complete: bool = False, verbose=False
):
    if schedule is None:
        return False

    # time in schedule overlaps
    if schedule_overlaps(schedule):
        verbose and logger.debug("schedule overlaps")
        return False

    if (
        C.HOUR_LOAD_CONSTRAINT.min is not None
        or C.HOUR_LOAD_CONSTRAINT.max is not None
    ):
        # hour load constraint
        min_hrs, max_hrs = daily_schedule_hours(schedule)
        if (
            C.HOUR_LOAD_CONSTRAINT.min is not None
            and min_hrs < C.HOUR_LOAD_CONSTRAINT.min
        ) or (
            C.HOUR_LOAD_CONSTRAINT.max is not None
            and max_hrs > C.HOUR_LOAD_CONSTRAINT.max
        ):
            verbose and logger.debug(
                f"schedule does not satisfy hour load constraint. "
                f"should be {C.HOUR_LOAD_CONSTRAINT.min} - {C.HOUR_LOAD_CONSTRAINT.max}, "
                f"is {min_hrs} - {max_hrs}"
            )
            return False

    if schedule_complete:
        # total course count constraint satisfied
        if (
            C.TOTAL_COURSE_COUNT_CONSTRAINT.min is not None
            and len(schedule) < C.TOTAL_COURSE_COUNT_CONSTRAINT.min
        ) or (
            C.TOTAL_COURSE_COUNT_CONSTRAINT.max is not None
            and len(schedule) > C.TOTAL_COURSE_COUNT_CONSTRAINT.max
        ):
            verbose and logger.debug(
                f"schedule does not satisfy total course count constraint, "
                f"should be {C.TOTAL_COURSE_COUNT_CONSTRAINT.min}-{C.TOTAL_COURSE_COUNT_CONSTRAINT.max}, is {len(schedule)}"
            )
            return False

        # zero or at least X courses scheduled per day
        if (
            C.DAILY_COURSE_COUNT_CONSTRAINT.min is not None
            or C.DAILY_COURSE_COUNT_CONSTRAINT.max is not None
        ):
            if not scheduled_enough_courses_per_day(
                schedule,
                C.DAILY_COURSE_COUNT_CONSTRAINT.min,
                C.DAILY_COURSE_COUNT_CONSTRAINT.max,
            ):
                verbose and logger.debug(
                    "scheduled either too few or too many daily courses"
                )
                return False

    # mandatory courses scheduled?
    scheduled_ids = {o.courseId for o in schedule}
    for cId in C.COURSE_MUST_SCHEDULE:
        if cId not in scheduled_ids:
            verbose and logger.debug("mandatory course not scheduled")
            return False

    for offering in schedule:
        if violates_hard_constraints(offering):
            verbose and logger.debug("schedule violates hard constraints")
            return False

    return True


# O(n log(n))
def schedule_overlaps(schedule: list[Offering]) -> bool:
    # 1. Collect all date ranges into a single list
    # Each range is a dict with "start" and "end" keys
    all_sessions = []
    for offering in schedule:
        all_sessions.extend(offering.dates)

    if not all_sessions:
        return False

    # 2. Sort sessions by start time - O(N log N)
    all_sessions.sort(key=lambda x: x["start"])

    # 3. Check adjacent sessions for overlap - O(N)
    # Since they are sorted, if session[i] overlaps with anything,
    # it must overlap with session[i-1].
    for i in range(1, len(all_sessions)):
        prev_session = all_sessions[i - 1]
        curr_session = all_sessions[i]

        # Overlap condition: current start is before previous end
        if curr_session["start"] < prev_session["end"]:
            return True

    return False


# O(n^2)
def __schedule_overlaps(schedule: list[Offering]):
    all_date_ranges = flatten([offering.dates for offering in schedule])
    for range1, range2 in combinations(all_date_ranges, 2):
        if dates_overlap(
            range1["start"], range1["end"], range2["start"], range2["end"]
        ):
            return True
    return False


# === Validate constraints ===


def scheduled_enough_courses_per_day(
    schedule: list[Offering], min_c: int | None, max_c: int | None
) -> bool:
    day_to_unique_courses = defaultdict(set)

    for offering in schedule:
        for date_entry in offering.dates:
            day = date_entry["start"].date()
            day_to_unique_courses[day].add(
                offering.courseId
            )  # Use set to avoid double-counting sessions

    for courses_on_day in day_to_unique_courses.values():
        count = len(courses_on_day)
        if min_c is not None and count < min_c:
            return False
        if max_c is not None and count > max_c:
            return False

    logger.debug(f"scheduled_enough_courses_per_day (min={min_c}, max={max_c})")
    return True


def flatten(xss: list[list[T]]) -> list[T]:
    return [x for xs in xss for x in xs]


def dates_overlap(
    start1: datetime, end1: datetime, start2: datetime, end2: datetime
):
    return start1 < end2 and end1 > start2


def times_overlap(
    start1: datetime, end1: datetime, start2: int, end2: int, weekday: Weekday
):
    if not is_on_day(start1, weekday):
        return False

    start1 = start1.time()
    end1 = end1.time()

    start2 = time(start2, 0)
    end2 = time(end2, 0)

    return start1 < end2 and end1 > start2


def violates_fixed_time(start: datetime, end: datetime):
    for dayHourCombo in C.FIXED_TIME_CONSTRAINTS:
        if abs(dayHourCombo[3]) == C.P and times_overlap(
            start, end, dayHourCombo[1], dayHourCombo[2], dayHourCombo[0]
        ):
            return True
    return False


def is_on_day(dt: datetime, day: Weekday) -> bool:
    return dt.strftime("%A").lower() == day.lower()


def violates_hard_constraints(
    offering: Offering, verbose: bool = False, ignore_must_schedule: bool = True
):
    if (
        not ignore_must_schedule
        and offering.courseId not in C.COURSE_MUST_SCHEDULE
    ):
        logger.debug("mandatory course id not scheduled")
        return True

    if offering.courseId in C.COURSE_MUST_NOT_SCHEDULE:
        logger.debug("course id not allowed")
        return True

    for date in offering.dates:
        if violates_fixed_time(date["start"], date["end"]):
            verbose and logger.debug("violates fixed time")
            return True

    return False


def daily_schedule_hours(schedule: list[Offering]) -> tuple[float, float]:
    """
    Returns (min_hours, max_hours) per active day (Mo-Fr).
    - Counts parallel sessions only once (merges overlaps).
    - Ignores days with 0 scheduled courses.
    """
    day_intervals = defaultdict(list)  # date -> list of (start, end)

    for offering in schedule:
        for session in offering.dates:
            start = session["start"]
            end = session["end"]

            # Only count Mo - Fr (Monday=0, Friday=4)
            if start.weekday() > 4:
                continue

            # Group by calendar date (e.g., 2023-10-12)
            day_intervals[start.date()].append((start, end))

    daily_totals = []

    for day, intervals in day_intervals.items():
        # merge_intervals must be available in your scope (from previous code)
        merged = merge_intervals(intervals)

        # Calculate total duration in hours for this day
        total_seconds = sum(
            (end - start).total_seconds() for start, end in merged
        )
        hours = total_seconds / 3600.0

        if hours > 0:
            daily_totals.append(hours)

    if not daily_totals:
        return (0.0, 0.0)

    return (min(daily_totals), max(daily_totals))


def merge_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
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


def get_offering_mark(offering: Offering):
    mark = 0
    mark += C.COURSE_PRIORITY_CONSTRAINTS.get(offering.courseId, 0)
    for date in offering.dates:
        for weekday, hour_start, hour_end, mark_change in [
            c for c in C.FIXED_TIME_CONSTRAINTS if abs(c[3]) != C.P
        ]:
            if times_overlap(
                date["start"], date["end"], hour_start, hour_end, weekday
            ):
                mark += mark_change
    return mark


def get_schedule_mark(schedule: list[Offering]):
    if schedule is None:
        return None

    mark = 0
    for offering in schedule:
        if violates_hard_constraints(offering):
            return None
        mark += get_offering_mark(offering)
    return mark


def rebuild_available_offerings(
    schedule: list[Offering],
    available_offerings: list[Offering],
    v3: bool = False,
) -> list[Offering]:
    taken_group_ids = list(
        set(map(lambda offering: offering.groupId, schedule))
    )
    taken_course_ids = list(map(lambda o: o.courseId, schedule))

    def _filter_available_offerings(previously_available_offering: Offering):
        if previously_available_offering.courseId in taken_course_ids:
            return False

        if previously_available_offering.groupId in taken_group_ids:
            return False

        if not is_valid_schedule(
            [*schedule, previously_available_offering], schedule_complete=False
        ):
            return False

        return True

    available_offerings = list(
        filter(_filter_available_offerings, available_offerings)
    )
    return (
        available_offerings[(len(available_offerings) - 1) // 2 :]
        if v3
        else available_offerings
    )


def preprocess(offerings: list[Offering]) -> list[Offering]:
    """
    Filter the offerings by variable inconsistency as mentioned on p357.
    Return offerings sorted by mark (highest first)
    """
    logger.info(f"preprocessing {len(offerings)} offerings")
    logger.info(f"{C.DAILY_COURSE_COUNT_CONSTRAINT=}")
    logger.info(f"{C.TOTAL_COURSE_COUNT_CONSTRAINT=}")
    logger.info(f"{C.COURSE_PRIORITY_CONSTRAINTS=}")
    logger.info(f"{C.COURSE_MUST_SCHEDULE=}")
    logger.info(f"{C.COURSE_MUST_NOT_SCHEDULE=}")
    logger.info(f"{C.FIXED_TIME_CONSTRAINTS=}")
    logger.info(f"{C.HOUR_LOAD_CONSTRAINT=}")

    keep_offerings = [
        offering
        for offering in offerings
        if offering.groupId is not None
        and not violates_hard_constraints(offering)
    ]

    for i, offering in enumerate(keep_offerings):
        keep_offerings[i].mark = get_offering_mark(offering)

    must_schedule = get_must_schedule_courses(keep_offerings)
    if schedule_overlaps(must_schedule):
        logger.error(
            f"sanitfy check failed: must schedule courses {[o.courseId for o in must_schedule]} overlap"
        )
        raise Exception("insane")

    logger.success(f"preprocessed offerings, keep {len(keep_offerings)}")
    return sorted(keep_offerings, key=lambda o: -o.mark)


def get_must_schedule_courses(offerings: list[Offering]) -> list[Offering]:
    must_schedule: list[Offering] = []
    for offerId in C.COURSE_MUST_SCHEDULE:
        offers = [o for o in offerings if o.courseId == offerId]
        if len(offers) < 1:
            logger.error(
                f"sanitfy check failed: must schedule course {offerId} violates hard constraints (could not find course with id)"
            )
            raise Exception("insane")
        must_schedule.append(offers[0])
    return must_schedule
