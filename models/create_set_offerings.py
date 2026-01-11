import pickle
import sys
import random
from loguru import logger

from types import SimpleNamespace
from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import (
    violates_hard_constraints,
    times_overlap,
    is_valid_schedule,
    rebuild_available_offerings,
    preprocess,
    get_must_schedule_courses,
)
from utils.print_schedule import print_schedule


def get_offering_mark(offering: Offering):
    mark = 0

    # punish too many offerings
    mark += min(70, max(0, (10 - len(offering.dates)) * 5))

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


"""
Hill climbing implementation from R. Feldman and M.C. Golumbic in Optimization Algorithms for Student Scheduling via Constraint Satisfiability

Algorithm:

In each state (iteration in loop), we determine which states can be reached (by scheduling one course) and estimate the mark of each state and pick the one with the highest mark.
This is the new state, the loop starts again.
We stop when a state which is a valid schedule is reached.
    (A valid schedule is any schedule that satisfies all requirements)


Adaptations:
- Because we don't differentiate between mandatory and electives, there is only one group.
    Because we don't pick a group, we also don't have to pick a course from the group and an offering from the course.
    We can pick an offering directly from all offerings.
- Stopping on a valid schedule would mean that always the minimum course count constraint would be satisfied.
    When scheduling one more course leads to a better schedule, we continue scheduling


Constraints are encoded in the following way:
- Fixed time constraints:
    dict[int, int]:
        key: hour of the day
        value: priority P ranging from -100 (blocked) to +100 (must schedule)

- Course priorities:
    dict[str, int]:
        key: course id (mapped planpunkt from vvz, would translate to a group by paper terminology)
        value: priority P ranging from -100 (blocked) to +100 (must schedule)

- Hour load:
    tuple[int, int]:
        hour load per week: (min, max)

- Course count constraint:
    tuple[int, int]:
        min and max amount of courses scheduled to build a valid schedule
"""


def schedule_course(
    schedule: list[Offering], available: list[Offering]
) -> Offering | None:
    """
    Picks one offering that fits best into the schedule and returns this offering
    """
    if len(schedule) == 0:
        return sorted(available, key=lambda item: -item.mark)[0]

    schedule_marks: list[Offering, int] = [
        [a, get_schedule_mark([*schedule, a])] for a in available
    ]
    try:
        return sorted(schedule_marks, key=lambda item: -item[1])[0][0]
    except Exception:
        return None


def build_schedule(offerings: list[Offering]) -> list[Offering] | None:
    schedule = get_must_schedule_courses(offerings)
    available_offerings = [
        o for o in offerings if o.courseId not in [s.courseId for s in schedule]
    ]

    while True:
        available_offerings = rebuild_available_offerings(
            schedule, available_offerings
        )
        next_valid_course = schedule_course(schedule, available_offerings)

        if (
            is_valid_schedule(schedule, schedule_complete=False)
            and len(schedule) == C.TOTAL_COURSE_COUNT_CONSTRAINT.max
        ):
            break

        if (
            is_valid_schedule(schedule, schedule_complete=False)
            and not next_valid_course
        ):
            break

        if next_valid_course is None:
            return None

        logger.debug(
            f"picked {next_valid_course.courseId}, "
            f"valid={is_valid_schedule(schedule, schedule_complete=False)}, "
            f"{len(available_offerings)} offerings remaining"
        )
        schedule.append(next_valid_course)
        logger.debug(f"{schedule=}")

    return schedule


if __name__ == "__main__":
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        offerings: list[Offering] = pickle.load(f)

    C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
        min=int(sys.argv[1]), max=int(sys.argv[1])
    )
    C.COURSE_MUST_NOT_SCHEDULE = [int(x) for x in sys.argv[2].split(",")]

    offerings = preprocess(offerings)
    schedule = build_schedule(offerings)

    logger.success("found schedule")
    print_schedule(schedule)
    logger.success(f"{len(schedule)=}")
    logger.success(f"{is_valid_schedule(schedule, schedule_complete=True)=}")
    logger.success(f"{get_schedule_mark(schedule)=}")

    import json

    print(
        json.dumps(
            {
                "COURSE_PRIORITY_CONSTRAINTS": {
                    str(o.courseId): 100 for o in schedule
                }
            },
            indent=4,
        )
    )
