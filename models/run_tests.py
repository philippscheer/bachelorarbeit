import os
import sys
import glob
import pickle
import statistics
import pandas as pd

from pathlib import Path
from loguru import logger
from tqdm import tqdm

from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import get_schedule_mark, is_valid_schedule, preprocess

from hill_climbing_v1 import build_schedule as test_hill_climbing_v1
from hill_climbing_v3 import build_schedule as test_hill_climbing_v3
from ilp import solve_ilp as test_ilp
from offering_order import solve_offering_order as test_offering_order

from utils.profile import ProfileResult, profile
from utils.benchmark import write_benchmarks
from utils.load_constraints import load_constraints_from_file


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
        "hill_climbing_v3": test_hill_climbing_v3,
    }

    loops = int(os.environ("LOOPS", 50))
    logger.info(f"running {loops} loops")

    config_files = glob.glob("models/config/constraint*.json")

    with tqdm(config_files, desc="Benchmarking constraint config", position=1, leave=True) as pbar:
        for cfg_path in pbar:
            cfg_path = Path(cfg_path)
            cfg_name = cfg_path.stem  # e.g. constraint1

            cfg = load_constraints_from_file(cfg_path)

            if cfg.get("COURSE_COUNT_CONSTRAINT") is None:
                logger.warning("no course count constraint specified, testing max course count using ilp")
                C.COURSE_COUNT_CONSTRAINT = (1, 999)
                logger.info(f"trying count {C.COURSE_COUNT_CONSTRAINT}")
                schedule = test_ilp(offerings)  # might be the best schedule, but not the longest
                previous_schedule = None

                while is_valid_schedule(schedule):
                    previous_schedule = schedule
                    C.COURSE_COUNT_CONSTRAINT = (len(schedule) + 1, 999)
                    logger.info(f"trying count {C.COURSE_COUNT_CONSTRAINT}")
                    schedule = test_ilp(offerings)
                    logger.info(f"result {schedule}")
                    logger.info(f"length {len(schedule)}")
                    logger.info(f"is valid? {is_valid_schedule(schedule)}")
                    logger.info(f"score: {get_schedule_mark(schedule)}")

                C.COURSE_COUNT_CONSTRAINT = (len(previous_schedule), 999)
                logger.success(f"found longest ilp schedule with length {len(previous_schedule)})")
                logger.success(f"is valid? {is_valid_schedule(previous_schedule)}")
                C.COURSE_COUNT_CONSTRAINT = (1, len(previous_schedule))

            cfg_title = cfg.get("title", cfg_name)

            pbar.set_postfix_str(f"Benchmarking {cfg_title}")

            test_results = {"ilp": [], "offering_order": [], "hill_climbing_v1": [], "hill_climbing_v3": []}

            ccc_min = C.COURSE_COUNT_CONSTRAINT[0]
            ccc_max = C.COURSE_COUNT_CONSTRAINT[1] + 1

            for i in range(ccc_min, ccc_max):
                C.COURSE_COUNT_CONSTRAINT = (i, i)  # fix course count

                for alg_name, alg_fn in tests.items():
                    profiles: list[ProfileResult] = []
                    logger.info(f"running algo {alg_name} for {i} courses")
                    schedule: list[Offering] | None = None

                    for _ in range(loops):
                        pbar.set_postfix_str(f"{cfg_title}, ccc {i}/{ccc_max-1}, run {_+1}/{loops}")

                        with profile() as profileResult:
                            schedule = alg_fn(offerings)
                        profiles.append(profileResult)

                    all_measurements = [m for p in profiles for m in p.mem_measurements]

                    logger.success(
                        f"schedule={[str(c.courseId) + ':' + c.groupId for c in (schedule or [])]}, is valid? {is_valid_schedule(schedule)}"
                    )

                    test_results[alg_name].append(
                        {
                            "courses": i,
                            "score": get_schedule_mark(schedule),
                            "valid": is_valid_schedule(schedule),
                            # run timings
                            "timings": [p.time_elapsed for p in profiles],
                            "timings_mean": statistics.mean(p.time_elapsed for p in profiles),
                            "timings_median": statistics.median(p.time_elapsed for p in profiles),
                            "timings_stdev": (
                                statistics.stdev(p.time_elapsed for p in profiles) if len(profiles) > 1 else 0
                            ),
                            # memory profiling
                            "memory_mean": statistics.mean(all_measurements),
                            "memory_median": statistics.median(all_measurements),
                            "memory_stdev": statistics.stdev(all_measurements) if len(all_measurements) > 1 else 0,
                            "memory_min": min(all_measurements),
                            "memory_max": max(all_measurements),
                            "memory_peak": max(p.mem_peak for p in profiles),
                        }
                    )

            frames = {}
            for method, records in test_results.items():
                frames[method] = pd.DataFrame(records)
            df = pd.concat(frames, axis=1)

            try:
                df[("score_percent", "hill_climbing_v1_vs_ilp")] = (
                    df[("hill_climbing_v1", "score")] / df[("ilp", "score")]
                )
                df[("score_percent", "hill_climbing_v3_vs_ilp")] = (
                    df[("hill_climbing_v3", "score")] / df[("ilp", "score")]
                )
                df[("score_percent", "offering_order_vs_ilp")] = df[("offering_order", "score")] / df[("ilp", "score")]
            except Exception:
                pass

            write_benchmarks(df, cfg, cfg_name, cfg_title)
            logger.success("wrote benchmarks")
