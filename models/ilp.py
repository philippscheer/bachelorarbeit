import pulp
import pickle
from collections import defaultdict
from loguru import logger
from itertools import combinations

from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import (
    get_schedule_mark,
    get_offering_mark,
    is_valid_schedule,
    schedule_overlaps,
    preprocess,
)


def create_model(offerings: list[Offering]) -> tuple[pulp.LpProblem, dict[int, pulp.LpVariable]]:
    model = pulp.LpProblem("CourseSelection", pulp.LpMaximize)

    # decision vars (0 or 1 for each possible course. 1 means picked, 0 means not picked)
    y = {c.courseId: pulp.LpVariable(f"y_{c.courseId}", cat="Binary") for c in offerings}

    for must_schedule_course_id in C.COURSE_MUST_SCHEDULE:
        model += y[must_schedule_course_id] == 1

    # maximizing total mark
    model += pulp.lpSum(get_offering_mark(c) * y[c.courseId] for c in offerings)

    # 1. constraint: respect total course count constraint
    model += pulp.lpSum(y[c.courseId] for c in offerings) >= C.TOTAL_COURSE_COUNT_CONSTRAINT.min
    model += pulp.lpSum(y[c.courseId] for c in offerings) <= C.TOTAL_COURSE_COUNT_CONSTRAINT.max

    # 2. constraint: may only select one course per group
    group_map = defaultdict(list)
    for i, off in enumerate(offerings):
        group_map[off.groupId].append(off.courseId)

    for gid, gIds in group_map.items():
        # Sum of selected courses in this group must be <= 1
        model += pulp.lpSum(y[gId] for gId in gIds) <= 1

    # 3. constraint: daily courses constraint (0 or >= N)
    if C.DAILY_COURSE_COUNT_CONSTRAINT.min is not None or C.DAILY_COURSE_COUNT_CONSTRAINT.max is not None:
        days_map = defaultdict(list)
        for i, off in enumerate(offerings):
            for date in off.dates:
                days_map[date["start"].date()].append(off.courseId)

        for day, cIds in days_map.items():
            u_d = pulp.LpVariable(f"used_{day}", cat="Binary")

            day_sum = pulp.lpSum(y[cId] for cId in cIds)

            if C.DAILY_COURSE_COUNT_CONSTRAINT.min:
                model += day_sum >= C.DAILY_COURSE_COUNT_CONSTRAINT.min * u_d
                model += day_sum <= 100 * u_d

            if C.DAILY_COURSE_COUNT_CONSTRAINT.max:
                model += day_sum <= C.DAILY_COURSE_COUNT_CONSTRAINT.max * u_d

    # implicit constraint: forbidden pairs - overlaps
    forbidden_pairs_overlaps = [
        (c1.courseId, c2.courseId) for c1, c2 in combinations(offerings, 2) if schedule_overlaps([c1, c2])
    ]
    logger.debug(f"found {len(forbidden_pairs_overlaps)} pairs forbidden by overlap")
    for i, j in forbidden_pairs_overlaps:
        model += y[i] + y[j] <= 1

    return model, y


def solve_ilp(offerings: list[Offering]) -> list[Offering]:
    model, y = create_model(offerings)
    model.solve()
    if pulp.LpStatus[model.status] != "Optimal":
        logger.warning("model status is not optimal!")

    return [[o for o in offerings if o.courseId == cid][0] for cid, var in y.items() if pulp.value(var) > 0.5]


if __name__ == "__main__":
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        offerings: list[Offering] = pickle.load(f)

    offerings = preprocess(offerings)

    best_solution = solve_ilp(offerings)
    logger.success("found solution")
    logger.success(f"{best_solution=}")
    logger.success(f"{is_valid_schedule(best_solution, schedule_complete=True)=}")
    logger.success(f"{len(best_solution)=}")
    logger.success(f"{get_schedule_mark(best_solution)=}")
