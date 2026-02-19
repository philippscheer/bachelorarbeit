import json
from typing import Literal
from types import SimpleNamespace


P = 100


FIXED_TIME_CONSTRAINTS: list[
    tuple[
        Literal["monday", "tuesday", "wednesday", "thursday", "saturday", "sunday"],
        int,
        int,
        int,
    ]
] = [("monday", 7, 10, -P)]

COURSE_PRIORITY_CONSTRAINTS = {1: -P}

HOUR_LOAD_CONSTRAINT = SimpleNamespace(min=None, max=None)
TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(min=2, max=13)
DAILY_COURSE_COUNT_CONSTRAINT = SimpleNamespace(min=None, max=None)

COURSE_MUST_NOT_SCHEDULE = [
    int(courseId)
    for courseId, priority in COURSE_PRIORITY_CONSTRAINTS.items()
    if priority == -100
]
COURSE_MUST_SCHEDULE = [
    int(courseId)
    for courseId, priority in COURSE_PRIORITY_CONSTRAINTS.items()
    if priority == 100
]
