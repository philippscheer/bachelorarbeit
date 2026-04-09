#!/usr/bin/env python3
"""Transform results/*.json files into CSV reports matching the reports/csv/old/ format.

Algorithm block order in each result JSON (alphabetical XML filename order, 50 rounds each):
  0   -  49 : Hill Climbing v1
  50  -  99 : Hill Climbing v3
  100 - 149 : ILP GPU
  150 - 199 : ILP
  200 - 249 : Offering Order
"""

import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROUNDS = 50
ALGO_ORDER = [
    "hill_climbing_v1",
    "hill_climbing_v3",
    "ilp_gpu",
    "ilp",
    "offering_order",
]

RESULTS_DIR = Path(__file__).parents[1] / "results"
REPORTS_DIR = Path(__file__).parents[1] / "reports" / "csv"

FILE_PATTERN = re.compile(r"^(constraint_.+)_difficulty_(\d+)_result\.json$")


def load_groups(path: Path) -> dict[str, list]:
    """Load a result JSON and split into per-algorithm groups of ROUNDS entries."""
    entries = json.loads(path.read_text(encoding="utf-8"))
    groups = {}
    for i, algo in enumerate(ALGO_ORDER):
        start = i * ROUNDS
        end = start + ROUNDS
        groups[algo] = entries[start:end] if len(entries) > start else []
    return groups


def algo_stats(entries: list) -> dict:
    """Compute statistics for one algorithm's entries."""
    times = [e["time_elapsed"] for e in entries]
    mems = [e["mem_peak"] for e in entries]
    vrams = [e["vram_peak"] for e in entries if "vram_peak" in e]
    valid_scores = [e["score"] for e in entries if e.get("is_valid")]

    def mean(values):
        return statistics.mean(values) if values else None

    def stdev(values):
        if len(values) >= 2:
            return statistics.stdev(values)
        return 0.0 if len(values) == 1 else None

    # If no valid score exists for this (result, algorithm, difficulty),
    # force timing and memory fields to nan in the CSV output as well.
    if not valid_scores:
        return {
            "score": None,
            "time_mean": None,
            "time_stdev": None,
            "mem_mean": None,
            "mem_stdev": None,
            "vram_mean": None,
            "vram_stdev": None,
        }

    return {
        "score": mean(valid_scores),
        "time_mean": mean(times),
        "time_stdev": stdev(times),
        "mem_mean": mean(mems),
        "mem_stdev": stdev(mems),
        "vram_mean": mean(vrams),
        "vram_stdev": stdev(vrams),
    }


def fmt(value) -> str:
    """Format a value for CSV output, matching pandas fillna('nan') behaviour."""
    return "nan" if value is None else str(value)


def write_csvs(constraint_name: str, rows: list) -> None:
    """Write the three CSV files for one constraint."""
    rows.sort(key=lambda r: r["difficulty"])

    # ---- score ----
    score_path = REPORTS_DIR / f"score_diff__{constraint_name}.csv"
    with score_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "difficulty",
                "ILP",
                "ILP GPU",
                "Hill Climbing v1",
                "Hill Climbing v3",
                "Offering Order",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r["difficulty"],
                    fmt(r["ilp"]["score"]),
                    fmt(r["ilp_gpu"]["score"]),
                    fmt(r["hill_climbing_v1"]["score"]),
                    fmt(r["hill_climbing_v3"]["score"]),
                    fmt(r["offering_order"]["score"]),
                ]
            )

    # ---- timing ----
    timing_path = REPORTS_DIR / f"timing_diff__{constraint_name}.csv"
    with timing_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "difficulty",
                "ILP",
                "ILP stdev",
                "ILP GPU",
                "ILP GPU stdev",
                "Hill Climbing v1",
                "Hill Climbing v1 stdev",
                "Hill Climbing v3",
                "Hill Climbing v3 stdev",
                "Offering Order",
                "Offering Order stdev",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r["difficulty"],
                    fmt(r["ilp"]["time_mean"]),
                    fmt(r["ilp"]["time_stdev"]),
                    fmt(r["ilp_gpu"]["time_mean"]),
                    fmt(r["ilp_gpu"]["time_stdev"]),
                    fmt(r["hill_climbing_v1"]["time_mean"]),
                    fmt(r["hill_climbing_v1"]["time_stdev"]),
                    fmt(r["hill_climbing_v3"]["time_mean"]),
                    fmt(r["hill_climbing_v3"]["time_stdev"]),
                    fmt(r["offering_order"]["time_mean"]),
                    fmt(r["offering_order"]["time_stdev"]),
                ]
            )

    # ---- memory ----
    memory_path = REPORTS_DIR / f"memory_diff__{constraint_name}.csv"
    with memory_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "difficulty",
                "ILP",
                "ILP stdev",
                "ILP GPU",
                "ILP GPU stdev",
                "ILP GPU VRAM",
                "ILP GPU VRAM stdev",
                "Hill Climbing v1",
                "Hill Climbing v1 stdev",
                "Hill Climbing v3",
                "Hill Climbing v3 stdev",
                "Offering Order",
                "Offering Order stdev",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r["difficulty"],
                    fmt(r["ilp"]["mem_mean"]),
                    fmt(r["ilp"]["mem_stdev"]),
                    fmt(r["ilp_gpu"]["mem_mean"]),
                    fmt(r["ilp_gpu"]["mem_stdev"]),
                    fmt(r["ilp_gpu"]["vram_mean"]),
                    fmt(r["ilp_gpu"]["vram_stdev"]),
                    fmt(r["hill_climbing_v1"]["mem_mean"]),
                    fmt(r["hill_climbing_v1"]["mem_stdev"]),
                    fmt(r["hill_climbing_v3"]["mem_mean"]),
                    fmt(r["hill_climbing_v3"]["mem_stdev"]),
                    fmt(r["offering_order"]["mem_mean"]),
                    fmt(r["offering_order"]["mem_stdev"]),
                ]
            )


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    by_constraint: dict[str, list] = defaultdict(list)
    for path in RESULTS_DIR.glob("*_result.json"):
        m = FILE_PATTERN.match(path.name)
        if m:
            by_constraint[m.group(1)].append(path)

    print(
        f"Found {len(by_constraint)} constraints across "
        f"{sum(len(v) for v in by_constraint.values())} files."
    )

    for constraint_name, files in sorted(by_constraint.items()):
        rows = []
        for path in files:
            m = FILE_PATTERN.match(path.name)
            difficulty = int(m.group(2))
            groups = load_groups(path)
            row = {"difficulty": difficulty}
            for algo in ALGO_ORDER:
                row[algo] = algo_stats(groups[algo])
            rows.append(row)

        write_csvs(constraint_name, rows)
        print(f"  Written: {constraint_name} ({len(rows)} difficulties)")

    print("Done.")


if __name__ == "__main__":
    main()
