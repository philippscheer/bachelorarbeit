import json
from pathlib import Path

import bachelorarbeit.constraints as C


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
