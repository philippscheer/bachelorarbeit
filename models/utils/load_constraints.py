import json
from types import SimpleNamespace

from loguru import logger
from pathlib import Path

import bachelorarbeit.constraints as C


def load_constraints_from_file(path: Path):
    logger.info(f"load constraints from {path}")

    with open(path, "r") as f:
        cfg = json.load(f)

    # Überschreibe die Constraints im constraints-Modul
    C.FIXED_TIME_CONSTRAINTS = cfg.get("FIXED_TIME_CONSTRAINTS", [])
    C.COURSE_PRIORITY_CONSTRAINTS = cfg.get("COURSE_PRIORITY_CONSTRAINTS", {})

    C.HOUR_LOAD_CONSTRAINT = SimpleNamespace(
        min=cfg.get("HOUR_LOAD_CONSTRAINT", {}).get("min", None),
        max=cfg.get("HOUR_LOAD_CONSTRAINT", {}).get("max", None),
    )

    C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
        min=cfg.get("TOTAL_COURSE_COUNT_CONSTRAINT", {}).get("min"),
        max=cfg.get("TOTAL_COURSE_COUNT_CONSTRAINT", {}).get("max"),
    )

    C.DAILY_COURSE_COUNT_CONSTRAINT = SimpleNamespace(
        min=cfg.get("DAILY_COURSE_COUNT_CONSTRAINT", {}).get("min"),
        max=cfg.get("DAILY_COURSE_COUNT_CONSTRAINT", {}).get("max"),
    )

    # convenience Variablen neu setzen
    C.COURSE_MUST_SCHEDULE = [
        int(cid)
        for cid, priority in C.COURSE_PRIORITY_CONSTRAINTS.items()
        if priority == 100
    ]
    C.COURSE_MUST_NOT_SCHEDULE = [
        int(cid)
        for cid, priority in C.COURSE_PRIORITY_CONSTRAINTS.items()
        if priority == -100
    ]

    return cfg
