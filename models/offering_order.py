import json
import pickle
from typing import List, Dict
from loguru import logger

from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import (
    get_schedule_mark,
    get_offering_mark,
    is_valid_schedule,
    preprocess,
)


def offering_order_algorithm(groups: dict[str, List[Offering]], update_marks: bool = False) -> List[Offering]:
    """
    Implementation of the offering ordering algorithm.

    :param groups: dictionary groupId -> list of offerings
    :param update_marks: if True, implement the "update marks" version,
                         otherwise preprocess version.
    :return: list of selected offerings forming the schedule

    C1(Offering1, Offering2, Offering3)
    C2(Offering4, Offering5)
    """
    # Step 1: preprocess all offerings with evaluation f(offering)
    for g, offerings in groups.items():
        for o in offerings:
            o.mark = get_offering_mark(o)

    # Step 2: order offerings in each course/group
    for g, offerings in groups.items():
        offerings.sort(key=lambda o: (-o.mark, len(offerings)))

    # Step 3: order groups themselves by first offering value
    group_order = sorted(
        groups.items(),
        key=lambda item: (-item[1][0].mark if item[1] else -9999, len(item[1])),
    )

    logger.debug("group_order=" + json.dumps(group_order, default=str, indent=4))

    def forward_check_backtrack(groups, schedule=None, group_index=0, min_courses=1, max_courses=10):
        """
        Forward checking backtracking algorithm to create a valid schedule with course count limits.

        groups: list[list[groupId, list[Offering]]]
        schedule: list of selected offerings
        group_index: current index of group being scheduled
        min_courses: minimum number of courses required
        max_courses: maximum number of courses allowed
        """
        if schedule is None:
            schedule = []

        # If we've scheduled all groups, check if the final schedule is valid and course count is within limits
        if group_index >= len(groups):
            if min_courses <= len(schedule) <= max_courses and is_valid_schedule(schedule):
                return schedule
            else:
                return None

        group_id, offerings = groups[group_index]

        for offering in offerings:
            # Forward checking: check compatibility with the current (partial) schedule
            if is_valid_schedule(schedule + [offering], ignore_length=True):
                if len(schedule) + 1 > max_courses:
                    continue
                schedule.append(offering)
                result = forward_check_backtrack(groups, schedule, group_index + 1, min_courses, max_courses)
                if result:  # Found a valid schedule
                    return result
                # Backtrack
                schedule.pop()

        # No valid offering found in this group, skip to next group
        result = forward_check_backtrack(groups, schedule, group_index + 1, min_courses, max_courses)

        if result and len(result) >= min_courses:
            return result

        return None

    return forward_check_backtrack(
        group_order, min_courses=C.COURSE_COUNT_CONSTRAINT[0], max_courses=C.COURSE_COUNT_CONSTRAINT[1]
    )


def solve_offering_order(offerings):
    groups = {}
    for offering in offerings:
        groups[offering.groupId] = [*groups.get(offering.groupId, []), offering]
    return offering_order_algorithm(groups, update_marks=False)


if __name__ == "__main__":
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        offerings: list[Offering] = pickle.load(f)

    offerings = preprocess(offerings)

    # print(f"{groups=}")
    schedule = solve_offering_order(offerings)
    logger.success("found schedule")
    logger.success(f"{schedule=}")
    logger.success(f"{len(schedule)=}")
    logger.success(f"{is_valid_schedule(schedule, verbose=True)=}")
    logger.success(f"{get_schedule_mark(schedule)=}")
