import json
from pathlib import Path
from itertools import product

CONFIG_DIR = Path(".")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Dimension 1: Fixed time constraints
fixed_time_options = {
    "high": {9: 100, 10: 100, 11: 75},
    "low": {7: -100, 8: -100, 18: -100, 19: -75},
    "mid": {9: 50, 10: -50, 11: 75, 20: -25},
}

# Dimension 2: Course priority constraints
# (simulieren gesperrte Kurse durch negative Priorität)
course_priority_options = {
    "few": {cid: -100 for cid in [""]},  # 0 Kurse gesperrt
    "some": {cid: -100 for cid in [""]},  # 5 Kurse gesperrt
    "many": {cid: -100 for cid in [""]},  # 20 Kurse gesperrt
}

# Dimension 3: Hour load constraint
hour_load_options = {
    "lax": (2, 50),
    "medium": (10, 35),
    "high": (15, 25),
}


def generate_config(fixed_time_key, course_priority_key, hour_load_key, idx):
    config = {
        "FIXED_TIME_CONSTRAINTS": fixed_time_options[fixed_time_key],
        "NON_FIXED_TIME_CONSTRAINTS": [],
        "COURSE_PRIORITY_CONSTRAINTS": course_priority_options[course_priority_key],
        "HOUR_LOAD_CONSTRAINT": hour_load_options[hour_load_key],
        "COURSE_COUNT_CONSTRAINT": (1, 13),
    }
    out_path = CONFIG_DIR / f"constraint_{idx:03d}.json"
    with open(out_path, "w") as f:
        json.dump(config, f, indent=4)
    return out_path


if __name__ == "__main__":
    idx = 1
    for fixed_time_key, course_priority_key, hour_load_key in product(
        fixed_time_options.keys(), course_priority_options.keys(), hour_load_options.keys()
    ):
        path = generate_config(fixed_time_key, course_priority_key, hour_load_key, idx)
        print(f"Generated {path} ({fixed_time_key}, {course_priority_key}, {hour_load_key})")
        idx += 1

    print(f"\n✅ Generated {idx-1} configuration files in {CONFIG_DIR}")
