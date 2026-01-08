import pickle
from tqdm import tqdm
from loguru import logger
from typing import Generator
from itertools import product, combinations
from collections import defaultdict

from bachelorarbeit.config import RAW_DATA_DIR
from bachelorarbeit.dtypes import Offering
from bachelorarbeit.constraints import TOTAL_COURSE_COUNT_CONSTRAINT

from utils import (
    get_schedule_mark,
    preprocess,
)


# === helpers ===


def count_exact_k(group_sizes, k_max):
    """
    Calculate how many possible combinations of k Planpunkte there are
    """
    dp = [0] * (k_max + 1)
    dp[0] = 1
    for s in group_sizes:
        for k in range(k_max, 0, -1):
            dp[k] += dp[k - 1] * s
    dp[0] = 0
    return dp


def get_total_combinations(offering_sets: list[list[Offering]]) -> int:
    """
    Calculate how many possible schedules there are given a number of sets of offerings
    """
    sizes = list(map(lambda l: len(l), offering_sets))
    combs = count_exact_k(sizes, TOTAL_COURSE_COUNT_CONSTRAINT.max)
    total_offerings = 0
    for r in range(TOTAL_COURSE_COUNT_CONSTRAINT.min, TOTAL_COURSE_COUNT_CONSTRAINT.max + 1):
        total_offerings += combs[r]
    return total_offerings


def get_offering_sets(offerings: list[Offering]) -> list[list[Offering]]:
    """
    Group offerings by groupId (Planpunkt) and return a list of sets of courses which must be picked exclusively
    """
    offering_sets = []

    grouped: dict[str, list[Offering]] = defaultdict(list)
    for o in offerings:
        grouped[o.groupId].append(o)

    for groupId, offs in grouped.items():
        offering_sets.append(offs)

    return offering_sets


# === Brute force algo ===


def bruteforce_schedules(offering_sets: list[list[Offering]]) -> Generator[list[Offering], None, None]:
    total_combos = get_total_combinations(offering_sets)

    batch_size = 250_000
    batch_count = 0

    pbar = tqdm(total=total_combos, desc="Generating schedules", unit_scale=True)

    for r in range(TOTAL_COURSE_COUNT_CONSTRAINT.min, TOTAL_COURSE_COUNT_CONSTRAINT.max + 1):
        for subset in combinations(offering_sets, r):
            for schedule in product(*subset):
                yield schedule
                batch_count += 1
                if batch_count >= batch_size:
                    pbar.update(batch_count)
                    batch_count = 0

    if batch_count > 0:
        pbar.update(batch_count)
    pbar.close()


def find_best_schedule(offering_sets: list[list[Offering]]):
    all_schedules = bruteforce_schedules(offering_sets)
    best_schedule = next(all_schedules)
    best_schedule = (get_schedule_mark(best_schedule), best_schedule)
    for schedule in all_schedules:
        current_schedule_mark = get_schedule_mark(schedule)
        if current_schedule_mark > best_schedule[0]:
            best_schedule = (current_schedule_mark, schedule)
    return best_schedule[1]


if __name__ == "__main__":
    with open(RAW_DATA_DIR / "offerings.pkl", "rb") as f:
        offerings: list[Offering] = pickle.load(f)

    offerings = preprocess(offerings)
    offering_sets = get_offering_sets(offerings)

    logger.success("building schedules")
    best_schedule = find_best_schedule(offering_sets)

    with open(RAW_DATA_DIR / "best_schedule_bf.pkl", "wb") as f:
        pickle.dump(best_schedule, f)
    logger.success(f"write best schedule to {RAW_DATA_DIR / 'best_schedule_bf.pkl'} complete")
