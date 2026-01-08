import os
import glob
import pickle
import argparse
import statistics
import pandas as pd

from tqdm import tqdm
from types import SimpleNamespace
from loguru import logger
from pathlib import Path

from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import get_schedule_mark, is_valid_schedule, preprocess

from hill_climbing_v1 import build_schedule as test_hill_climbing_v1
from hill_climbing_v3 import build_schedule as test_hill_climbing_v3
from ilp import solve_ilp as test_ilp
from ilp_gpu import solve_ilp as test_ilp_gpu
from offering_order import solve_offering_order as test_offering_order

from utils.print_schedule import print_schedule
from utils.profile import ProfileResult, profile
from utils.benchmark import write_benchmarks
from utils.load_constraints import load_constraints_from_file


logger.remove()
logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True, level="DEBUG")

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run scheduling algorithm tests."
    )
    parser.add_argument(
        "-r",
        "--rounds",
        type=int,
        help="Number of rounds every test runs",
        default=1,
    )
    parser.add_argument("--ilp", action="store_true", help="Run ILP tests")
    parser.add_argument("--ilp-gpu", action="store_true", help="Run ILP tests")
    parser.add_argument(
        "--hc", action="store_true", help="Run Hill Climbing tests (v1 and v3)"
    )
    parser.add_argument(
        "--oo", action="store_true", help="Run Offering Order test"
    )
    parser.add_argument(
        "--config", help="Config ID", default=None, required=False
    )
    parser.add_argument(
        "--print-schedule", action="store_true", help="Print the found schedule"
    )
    parser.add_argument(
        "--course-min",
        type=int,
        help="Minimum amount of courses to be scheduled (if omitted, dynamically calculated using ILP)",
    )
    parser.add_argument(
        "--course-max",
        type=int,
        help="Maximum amount of courses to be scheduled (if omitted, dynamically calculated using ILP)",
    )
    args = parser.parse_args()

    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        all_offerings: list[Offering] = pickle.load(f)

    logger.info("running tests on algorithms")

    tests = {
        k: v
        for k, v in {
            "ilp": test_ilp if args.ilp else None,
            "ilp_gpu": test_ilp_gpu if args.ilp_gpu else None,
            "offering_order": test_offering_order if args.oo else None,
            "hill_climbing_v1": test_hill_climbing_v1 if args.hc else None,
            "hill_climbing_v3": test_hill_climbing_v3 if args.hc else None,
        }.items()
        if v is not None
    }

    loops = args.rounds
    logger.info(f"running {loops} loops")

    config_files = (
        glob.glob(f"{CURRENT_PATH}/config/constraint*.json")
        if args.config is None
        else glob.glob(f"{CURRENT_PATH}/config/constraint_{args.config}_*.json")
    )

    logger.debug(f"found {len(config_files)} config files")

    with tqdm(
        config_files,
        desc="Benchmarking constraint config",
        position=1,
        leave=True,
    ) as pbar:
        for cfg_path in pbar:
            cfg_path = Path(cfg_path)
            cfg_name = cfg_path.stem  # e.g. constraint1

            cfg = load_constraints_from_file(cfg_path)
            offerings = preprocess(all_offerings)

            if args.course_min and args.course_max:
                C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
                    min=args.course_min, max=args.course_max
                )
                logger.info(
                    f"Set TOTAL_COURSE_COUNT_CONSTRAINT to {C.TOTAL_COURSE_COUNT_CONSTRAINT}"
                )

            elif args.course_min or args.course_max:
                logger.warning("both --course-min and --course-max must be set")
                exit(1)

            elif cfg.get("TOTAL_COURSE_COUNT_CONSTRAINT") is None:
                logger.warning(
                    "no course count constraint specified, testing max course count using ilp"
                )
                C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
                    min=1, max=999
                )
                logger.info(f"trying count {C.TOTAL_COURSE_COUNT_CONSTRAINT}")
                schedule = test_ilp(
                    offerings
                )  # might be the best schedule, but not the longest
                previous_schedule = None

                while is_valid_schedule(schedule, schedule_complete=True):
                    previous_schedule = schedule
                    C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
                        min=len(schedule) + 1, max=999
                    )
                    logger.info(
                        f"trying count {C.TOTAL_COURSE_COUNT_CONSTRAINT}"
                    )
                    schedule = test_ilp(offerings)
                    logger.info(f"result {schedule}")
                    logger.info(f"length {len(schedule)}")
                    logger.info(
                        f"is valid? {is_valid_schedule(schedule, schedule_complete=True)}"
                    )
                    logger.info(f"score: {get_schedule_mark(schedule)}")

                C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
                    min=len(previous_schedule), max=999
                )
                logger.success(
                    f"found longest ilp schedule with length {len(previous_schedule)})"
                )
                logger.success(
                    f"is valid? {is_valid_schedule(previous_schedule, schedule_complete=True)}"
                )
                C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
                    min=1, max=len(previous_schedule)
                )

            cfg_title = cfg.get("title", cfg_name)

            logger.info(f'running benchmark "{cfg_title}"')

            pbar.set_postfix_str(f"Benchmarking {cfg_title}")

            test_results = {
                "ilp": [],
                "offering_order": [],
                "hill_climbing_v1": [],
                "hill_climbing_v3": [],
            }

            ccc_min = C.TOTAL_COURSE_COUNT_CONSTRAINT.min
            ccc_max = C.TOTAL_COURSE_COUNT_CONSTRAINT.max + 1

            for i in range(ccc_min, ccc_max):
                C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
                    min=i, max=i
                )  # fix course count

                for alg_name, alg_fn in tests.items():
                    profiles: list[ProfileResult] = []
                    logger.info(f"running algo {alg_name} for {i} courses")
                    schedule: list[Offering] | None = None

                    for _ in range(loops):
                        pbar.set_postfix_str(
                            f"{cfg_title}, ccc {i}/{ccc_max-1}, run {_+1}/{loops}"
                        )

                        with profile() as profileResult:
                            schedule = alg_fn(offerings)

                        if _ == 0 and args.print_schedule:
                            print_schedule(schedule)

                        profiles.append(profileResult)

                    if loops == 1 and args.print_schedule:
                        logger.debug(f"measurement: {profiles[0]}")

                    all_measurements = [
                        m for p in profiles for m in p.mem_measurements
                    ]

                    logger.success(
                        f"schedule={[str(c.courseId) + ':' + c.groupId for c in (schedule or [])]}, is valid? {is_valid_schedule(schedule, schedule_complete=True)}, mark: {get_schedule_mark(schedule)}"
                    )

                    test_results[alg_name].append(
                        {
                            "courses": i,
                            "score": get_schedule_mark(schedule),
                            "valid": is_valid_schedule(
                                schedule, schedule_complete=True
                            ),
                            # run timings
                            "timings": [p.time_elapsed for p in profiles],
                            "timings_mean": statistics.mean(
                                p.time_elapsed for p in profiles
                            ),
                            "timings_median": statistics.median(
                                p.time_elapsed for p in profiles
                            ),
                            "timings_stdev": (
                                statistics.stdev(
                                    p.time_elapsed for p in profiles
                                )
                                if len(profiles) > 1
                                else 0
                            ),
                            # memory profiling
                            "memory_mean": statistics.mean(all_measurements),
                            "memory_median": statistics.median(
                                all_measurements
                            ),
                            "memory_stdev": (
                                statistics.stdev(all_measurements)
                                if len(all_measurements) > 1
                                else 0
                            ),
                            "memory_min": min(all_measurements),
                            "memory_max": max(all_measurements),
                            "memory_peak": max(p.mem_peak for p in profiles),
                        }
                    )

            frames = {}
            for method, records in test_results.items():
                frames[method] = pd.DataFrame(records)
            df = pd.concat(frames, axis=1)

            # try:
            #     df[("score_percent", "hill_climbing_v1_vs_ilp")] = (
            #         df[("hill_climbing_v1", "score")] / df[("ilp", "score")]
            #     )
            #     df[("score_percent", "hill_climbing_v3_vs_ilp")] = (
            #         df[("hill_climbing_v3", "score")] / df[("ilp", "score")]
            #     )
            #     df[("score_percent", "offering_order_vs_ilp")] = df[("offering_order", "score")] / df[("ilp", "score")]
            # except Exception:
            #     pass

            # write_benchmarks(df, cfg, cfg_name, cfg_title)
            # logger.success("wrote benchmarks")

    logger.success("done")
