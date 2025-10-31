from typing import Literal


P = 100


FIXED_TIME_CONSTRAINTS: list[
    tuple[Literal["monday", "tuesday", "wednesday", "thursday", "saturday", "sunday"], int, int, int]
] = [
    ["monday", 7, 10, -P]
    # 7: -100,  # fully block hour 7:00-8:00
    # 8: -100,  # fully block hour 8:00-9:00
    # # 9: -100,  # fully block hour 9:00-10:00
    # # 10: -100,  # fully block hour 9:00-10:00
    # # 11: -100,  # fully block hour 9:00-10:00
    # 9: 50,
    # 10: 75,
    # 11: 75,
    # 18: -50,
    # 19: -50,
    # 20: -75,
]

NON_FIXED_TIME_CONSTRAINTS = [
    # {
    #     "hour_start": 14,
    #     "hour_end": 17,
    #     "days_required": 3,
    #     "priority": -50
    # }  # Avoid late afternoon in 3+ days
]

COURSE_PRIORITY_CONSTRAINTS = {1: -P}

HOUR_LOAD_CONSTRAINT = (0, 45)

COURSE_COUNT_CONSTRAINT = (2, 13)


COURSE_MUST_NOT_SCHEDULE = [
    int(courseId) for courseId, priority in COURSE_PRIORITY_CONSTRAINTS.items() if priority == -100
]
COURSE_MUST_SCHEDULE = [int(courseId) for courseId, priority in COURSE_PRIORITY_CONSTRAINTS.items() if priority == 100]
