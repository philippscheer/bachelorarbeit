import sys
import time
import pickle
import statistics
import pandas as pd
import json
import glob
from pathlib import Path
from loguru import logger
from tqdm import tqdm

from bachelorarbeit.config import RAW_DATA_DIR, REPORTS_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import (
    get_schedule_mark,
    is_valid_schedule,
    preprocess,
)

from hill_climbing_v1 import build_schedule as test_hill_climbing_v1
from ilp import solve_ilp as test_ilp
from offering_order import solve_offering_order as test_offering_order


def load_constraints_from_file(path: Path):
    with open(path, "r") as f:
        cfg = json.load(f)

    # Überschreibe die Constraints im constraints-Modul
    C.FIXED_TIME_CONSTRAINTS = cfg.get("FIXED_TIME_CONSTRAINTS", {})
    C.NON_FIXED_TIME_CONSTRAINTS = cfg.get("NON_FIXED_TIME_CONSTRAINTS", [])
    C.COURSE_PRIORITY_CONSTRAINTS = cfg.get("COURSE_PRIORITY_CONSTRAINTS", {})
    C.HOUR_LOAD_CONSTRAINT = tuple(cfg.get("HOUR_LOAD_CONSTRAINT", (0, 999)))
    C.COURSE_COUNT_CONSTRAINT = tuple(cfg.get("COURSE_COUNT_CONSTRAINT", (1, 999)))

    # convenience Variablen neu setzen
    C.HOURS_MUST_NOT_SCHEDULE = [hour for hour, priority in C.FIXED_TIME_CONSTRAINTS.items() if priority == -100]
    C.COURSE_MUST_NOT_SCHEDULE = [cid for cid, priority in C.COURSE_PRIORITY_CONSTRAINTS.items() if priority == -100]
    C.HOURS_FLEXIBLE = {hour: priority for hour, priority in C.FIXED_TIME_CONSTRAINTS.items() if abs(priority) < 100}

    return cfg


if __name__ == "__main__":
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        offerings: list[Offering] = pickle.load(f)

    offerings = preprocess(offerings)

    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.info("running tests on algorithms")

    tests = {
        "ilp": test_ilp,
        "offering_order": test_offering_order,
        "hill_climbing_v1": test_hill_climbing_v1,
    }

    loops = 5

    config_files = glob.glob("models/config/constraint*.json")

    for cfg_path in tqdm(config_files, desc="Benchmarking constraint configs"):
        cfg_path = Path(cfg_path)
        cfg_name = cfg_path.stem  # e.g. constraint1
        cfg = load_constraints_from_file(cfg_path)

        test_results = {"ilp": [], "offering_order": [], "hill_climbing_v1": []}

        for i in range(C.COURSE_COUNT_CONSTRAINT[0], C.COURSE_COUNT_CONSTRAINT[1] + 1):
            C.COURSE_COUNT_CONSTRAINT = (i, i)  # fix course count

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
                        "stdev": statistics.stdev(timings) if len(timings) > 1 else 0,
                    }
                )

        frames = {}
        for method, records in test_results.items():
            frames[method] = pd.DataFrame(records)
        df = pd.concat(frames, axis=1)

        try:
            df[("diff", "hill_vs_offering")] = df[("hill_climbing_v1", "score")] - df[("offering_order", "score")]
        except Exception:
            df[("diff", "hill_vs_offering")] = None

        out_path = REPORTS_DIR / f"benchmark_{cfg_name}.xlsx"
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            header_lines = [f"Benchmark Constraints {cfg_name}"]
            for k, v in cfg.items():
                header_lines.append(f"{k}: {v}")
            header_df = pd.DataFrame(header_lines, columns=["info"])
            header_df.to_excel(writer, sheet_name="results", index=False, header=False)

            startrow = len(header_lines) + 2
            df.to_excel(writer, sheet_name="results", startrow=startrow)

        logger.success(f"Wrote benchmark to {out_path}")
