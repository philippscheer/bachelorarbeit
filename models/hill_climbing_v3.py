import pickle
from loguru import logger

from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import (
    get_schedule_mark,
    is_valid_schedule,
    rebuild_available_offerings,
    preprocess,
    get_must_schedule_courses,
)


"""
Hill climbing v3 implementation from R. Feldman and M.C. Golumbic in Optimization Algorithms for Student Scheduling via Constraint Satisfiability

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


def schedule_course(schedule: list[Offering], available: list[Offering]) -> Offering | None:
    """
    Picks one offering that fits best into the schedule and returns this offering
    """
    if len(schedule) == 0:
        return sorted(available, key=lambda item: -item.mark)[0]

    schedule_marks: list[Offering, int] = [[a, get_schedule_mark([*schedule, a])] for a in available]
    try:
        return sorted(schedule_marks, key=lambda item: -item[1])[0][0]
    except Exception:
        return None


def build_schedule(offerings: list[Offering]) -> list[Offering] | None:
    offerings = list(reversed(offerings))

    schedule = get_must_schedule_courses(offerings)
    available_offerings = [o for o in offerings if o.courseId not in [s.courseId for s in schedule]]

    while True:
        available_offerings = rebuild_available_offerings(schedule, available_offerings, v3=True)
        next_valid_course = schedule_course(schedule, available_offerings)

        if is_valid_schedule(schedule, verbose=True) and len(schedule) == C.COURSE_COUNT_CONSTRAINT[1]:
            break

        if is_valid_schedule(schedule) and not next_valid_course:
            break

        if next_valid_course is None:
            return None

        logger.debug(f"{is_valid_schedule(schedule)=}, {len(available_offerings)} offerings remaining")
        schedule.append(next_valid_course)
        logger.debug(f"{schedule=}")

    return schedule


if __name__ == "__main__":
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        offerings: list[Offering] = pickle.load(f)

    offerings = preprocess(offerings)
    schedule = build_schedule(offerings)

    logger.success("found schedule")
    logger.success(f"{schedule=}")
    logger.success(f"{len(schedule)=}")
    logger.success(f"{is_valid_schedule(schedule)=}")
    logger.success(f"{get_schedule_mark(schedule)=}")
