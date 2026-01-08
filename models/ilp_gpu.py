import pulp
import pickle
from loguru import logger

from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering

from utils import (
    get_schedule_mark,
    is_valid_schedule,
    preprocess,
)
from models.ilp import create_model


def solve_ilp(offerings: list[Offering]) -> list[Offering]:
    model, y = create_model(offerings)

    model.solve(pulp.CUOPT())
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
