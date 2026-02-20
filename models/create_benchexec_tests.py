import os
import glob
import pickle

from tqdm import tqdm
from types import SimpleNamespace
from loguru import logger
from pathlib import Path

from bachelorarbeit.config import RAW_DATA_DIR, PROJ_ROOT
from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import get_schedule_mark, is_valid_schedule, preprocess

from ilp import solve_ilp as ilp_benchmark

from utils.print_schedule import print_schedule
from utils.load_constraints import load_constraints_from_file


CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
ROUNDS = 50
TOOLS = ["ilp_test", "ilp_gpu_test", "offering_order_test", "hill_climbing_test"]
XML_BENCHMARK_START = """<?xml version="1.0"?>
<!DOCTYPE benchmark PUBLIC "+//IDN sosy-lab.org//DTD BenchExec benchmark 3.30//EN" "https://www.sosy-lab.org/benchexec/benchmark-3.30.dtd">
<benchmark tool="{{tool}}"
           displayName="{{tool}}_benchmarks"
           timelimit="15s"
           threads="1">

  <tasks>
    <include>{{constraint_path}}</include>
  </tasks>

  <columns>
  </columns>

  <resultfiles>.</resultfiles>
"""
XML_BENCHMARK_END = """</benchmark>"""


logger.remove()
logger.add(
    lambda msg: tqdm.write(msg, end=""),
    colorize=True,
    level="DEBUG",
)


def load_offerings() -> list[Offering]:
    logger.debug("loading offerings")
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    all_offerings = load_offerings()

    logger.info("testing scenarios for max amount of courses using ILP")

    config_files = glob.glob(f"{CURRENT_PATH}/config/constraint*.json")

    logger.debug(f"found {len(config_files)} config files")

    tests_complete = []

    with tqdm(
        config_files,
        desc="Benchmarking constraint config",
        position=1,
        leave=True,
    ) as pbar:
        for cfg_path in pbar:
            logger.debug(str(cfg_path))
            cfg_path = Path(cfg_path)
            cfg_name = cfg_path.stem  # e.g. constraint1
            pbar.set_description(cfg_name)

            # inefficient but prevents errors when the original offering objects
            # inside change for whatever reason
            cfg = load_constraints_from_file(cfg_path)
            all_offerings = load_offerings()
            offerings = preprocess(all_offerings)

            C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(min=1, max=999)
            logger.info(f"trying count {C.TOTAL_COURSE_COUNT_CONSTRAINT}")
            schedule = ilp_benchmark(
                offerings
            )  # might be the best schedule, but not the longest
            previous_schedule = None
            print_schedule(schedule)
            is_valid_schedule(schedule, schedule_complete=True, verbose=True)

            while is_valid_schedule(schedule, schedule_complete=True, verbose=True):
                logger.debug(f"trying schedule with len={len(schedule)+1}")
                previous_schedule = schedule
                C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
                    min=len(schedule) + 1, max=999
                )
                schedule = ilp_benchmark(offerings)
                logger.info(
                    f"found schedule with {len(schedule)} offerings, "
                    f"valid={is_valid_schedule(schedule, schedule_complete=True, verbose=True)}, "
                    f"score={get_schedule_mark(schedule)}"
                )

            min_len = 1
            max_len = len(previous_schedule)

            logger.success(
                f"found longest ilp schedule with length {max_len}, "
                f"valid={is_valid_schedule(previous_schedule, schedule_complete=True, verbose=True)}"
            )

            for tool in TOOLS:
                crafted_xml = XML_BENCHMARK_START.replace("{{tool}}", tool).replace(
                    "{{constraint_path}}", str(cfg_path)
                )
                for i in range(min_len, max_len + 1):
                    for j in range(ROUNDS):
                        crafted_xml += f'<rundefinition name="run_{str(j + 1).zfill(2)}_{str(i).zfill(2)}"> <option>{i}</option> </rundefinition>\n'
                crafted_xml += XML_BENCHMARK_END
                with open(
                    PROJ_ROOT / "benchexec" / "benchmarks" / f"{cfg_name}_{tool}.xml",
                    "w",
                ) as f:
                    f.write(crafted_xml)

    logger.success("done")
