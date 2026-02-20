import sys
import pulp

from loguru import logger
from types import SimpleNamespace

from utils.load_constraints import load_constraints_from_file
from utils.profile import profile

from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import preprocess, load_offerings
from models.ilp import create_model


def solve_ilp(offerings: list[Offering]) -> list[Offering]:
    model, solver, y = create_model(offerings)

    model.solve(pulp.CUOPT(msg=False))
    if pulp.LpStatus[model.status] != "Optimal":
        logger.warning("model status is not optimal!")

    return [
        [o for o in offerings if o.courseId == cid][0]
        for cid, var in y.items()
        if pulp.value(var) > 0.5
    ]


def solve_ilp_model(model, solver, y, offerings):
    model.solve(pulp.CUOPT(msg=False))
    if pulp.LpStatus[model.status] != "Optimal":
        logger.warning("model status is not optimal!")

    return [
        [o for o in offerings if o.courseId == cid][0]
        for cid, var in y.items()
        if pulp.value(var) > 0.5
    ]


if __name__ == "__main__":
    # ran by benchexec. the first argument is the constraint file, so load constraint, build model, solve
    # constraint loading not included in benchmark
    load_constraints_from_file(sys.argv[1])
    num_courses = int(sys.argv[2])
    C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(min=num_courses, max=num_courses)

    # preprocessing not included in benchmarks
    offerings = load_offerings()
    offerings = preprocess(offerings)

    with profile(sys.argv[1], sys.argv[2]):
        best_solution = solve_ilp(offerings)
