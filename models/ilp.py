import pulp
import pickle
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


def solve_ilp(offerings: list[Offering]) -> list[Offering]:
    model = pulp.LpProblem("CourseSelection", pulp.LpMaximize)

    # decision vars (0 or 1 for each possible course. 1 means picked, 0 means not picked)
    y = {c.courseId: pulp.LpVariable(f"y_{c.courseId}", cat="Binary") for c in offerings}

    for must_schedule_course_id in C.COURSE_MUST_SCHEDULE:
        model += y[must_schedule_course_id] == 1

    for must_schedule_course_id in C.COURSE_MUST_NOT_SCHEDULE:
        model += y[must_schedule_course_id] == 0

    # maximizing total mark
    model += pulp.lpSum(get_offering_mark(c) * y[c.courseId] for c in offerings)

    model += pulp.lpSum(y[c.courseId] for c in offerings) >= C.COURSE_COUNT_CONSTRAINT[0]
    model += pulp.lpSum(y[c.courseId] for c in offerings) <= C.COURSE_COUNT_CONSTRAINT[1]

    # implicit constraint: forbidden pairs - planpunkt
    # a user cannot take two of the same courses from planpunkt
    forbidden_pairs_planpunkt = [
        (c1.courseId, c2.courseId) for c1, c2 in combinations(offerings, 2) if c1.groupId == c2.groupId
    ]
    logger.debug(f"found {len(forbidden_pairs_planpunkt)} pairs forbidden by planpunkt")
    for i, j in forbidden_pairs_planpunkt:
        model += y[i] + y[j] <= 1

    # implicit constraint: forbidden pairs - overlaps
    forbidden_pairs_overlaps = [
        (c1.courseId, c2.courseId) for c1, c2 in combinations(offerings, 2) if schedule_overlaps([c1, c2])
    ]
    logger.debug(f"found {len(forbidden_pairs_overlaps)} pairs forbidden by overlap")
    for i, j in forbidden_pairs_overlaps:
        model += y[i] + y[j] <= 1

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
    logger.success(f"{is_valid_schedule(best_solution)=}")
    logger.success(f"{len(best_solution)=}")
    logger.success(f"{get_schedule_mark(best_solution)=}")
