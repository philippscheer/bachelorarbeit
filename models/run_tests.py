import sys
import time
import pickle
import statistics
import pandas as pd
from loguru import logger

from bachelorarbeit.config import RAW_DATA_DIR, REPORTS_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints

from utils import (
    get_schedule_mark,
    get_offering_mark,
    is_valid_schedule,
    preprocess,
)

from hill_climbing_v1 import build_schedule as test_hill_climbing_v1
from ilp import solve_ilp as test_ilp
from offering_order import solve_offering_order as test_offering_order

if __name__ == "__main__":
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        offerings: list[Offering] = pickle.load(f)

    offerings = preprocess(offerings)

    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.info("running tests on algorithms")

    test_results = {"ilp": [], "offering_order": [], "hill_climbing_v1": []}

    tests = {
        "ilp": test_ilp,
        "offering_order": test_offering_order,
        "hill_climbing_v1": test_hill_climbing_v1,
    }

    loops = 5

    for i in range(1, 13):
        bachelorarbeit.constraints.COURSE_COUNT_CONSTRAINT = [i, i]

        for alg_name, alg_fn in tests.items():
            timings = []

            logger.info(f"running algo {alg_name} for {i} courses")
            schedule = None

            for _ in range(loops):
                start = time.perf_counter_ns()
                schedule = alg_fn(offerings)
                timings.append(time.perf_counter_ns() - start)

            test_results[alg_name].append(
                {
                    "courses": i,
                    "score": get_schedule_mark(schedule),
                    "valid": is_valid_schedule(schedule),
                    "timings": timings,
                    "mean": statistics.mean(timings),
                    "stdev": statistics.stdev(timings),
                }
            )

    with open(RAW_DATA_DIR / "benchmark.pkl", "wb") as f:
        pickle.dump(test_results, f)

    frames = {}
    for method, records in test_results.items():
        frames[method] = pd.DataFrame(records)
    df = pd.concat(frames, axis=1)
    df.to_excel(REPORTS_DIR / "benchmark.xlsx")
