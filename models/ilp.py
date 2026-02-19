import sys
import pulp
from types import SimpleNamespace
from loguru import logger
from collections import defaultdict

from bachelorarbeit.dtypes import Offering
import bachelorarbeit.constraints as C

from utils import (
    get_offering_mark,
    preprocess,
    load_offerings,
)
from utils.load_constraints import load_constraints_from_file


def create_model(
    offerings: list[Offering],
) -> tuple[pulp.LpProblem, dict[int, pulp.LpVariable]]:
    model = pulp.LpProblem("CourseSelection", pulp.LpMaximize)

    # decision vars (0 or 1 for each possible course. 1 means picked, 0 means not picked)
    y = {
        c.courseId: pulp.LpVariable(f"y_{c.courseId}", cat="Binary") for c in offerings
    }

    for must_schedule_course_id in C.COURSE_MUST_SCHEDULE:
        model += y[must_schedule_course_id] == 1

    # maximizing total mark
    model += pulp.lpSum(get_offering_mark(c) * y[c.courseId] for c in offerings)

    # 1. constraint: respect total course count constraint
    model += (
        pulp.lpSum(y[c.courseId] for c in offerings)
        >= C.TOTAL_COURSE_COUNT_CONSTRAINT.min
    )
    model += (
        pulp.lpSum(y[c.courseId] for c in offerings)
        <= C.TOTAL_COURSE_COUNT_CONSTRAINT.max
    )

    # 2. constraint: may only select one course per group
    group_map = defaultdict(list)
    for i, off in enumerate(offerings):
        group_map[off.groupId].append(off.courseId)

    for gid, gIds in group_map.items():
        # Sum of selected courses in this group must be <= 1
        model += pulp.lpSum(y[gId] for gId in gIds) <= 1

    # 3. constraint: daily hour load constraint
    # map: day -> list of (course_id, hours_that_day)
    if C.HOUR_LOAD_CONSTRAINT.min is not None or C.HOUR_LOAD_CONSTRAINT.max is not None:
        hours_per_day_map = defaultdict(list)
        for off in offerings:
            for date_info in off.dates:
                start = date_info["start"]
                end = date_info["end"]
                duration_hours = (end - start).total_seconds() / 3600.0

                hours_per_day_map[start.date()].append((off.courseId, duration_hours))

        for day, contributions in hours_per_day_map.items():
            # u_d: Is the student at uni at all on this day?
            u_d = pulp.LpVariable(f"used_day_{day}", cat="Binary")

            # Calculate total hours for this day based on selected courses
            day_hour_sum = pulp.lpSum(y[cid] * hrs for cid, hrs in contributions)

            # Minimum load: If day is used (u_d=1), must be >= min.
            # If not used (u_d=0), sum must be 0.
            if C.HOUR_LOAD_CONSTRAINT.min is not None:
                model += day_hour_sum >= C.HOUR_LOAD_CONSTRAINT.min * u_d
                # Big-M constraint to ensure u_d is 1 if any course is picked
                # 24 hours is a safe upper bound for a single day
                model += day_hour_sum <= 24 * u_d

            # Maximum load: Total hours cannot exceed max (applies regardless of u_d)
            if C.HOUR_LOAD_CONSTRAINT.max is not None:
                model += day_hour_sum <= C.HOUR_LOAD_CONSTRAINT.max * u_d

    # 3. Optimized Timeline Logic
    timeline = defaultdict(list)
    for off in offerings:
        for date_info in off.dates:
            start = date_info["start"]
            end = date_info["end"]
            day = start.date()
            timeline[day].append((start, end, off.courseId))

    for day, sessions in timeline.items():
        # Get all unique split points
        times = sorted(list(set([s[0] for s in sessions] + [s[1] for s in sessions])))

        for i in range(len(times) - 1):
            slot_start = times[i]
            slot_end = times[i + 1]

            # Identify which courses are active in this specific slot
            active_vars = []
            for start, end, cid in sessions:
                # STRICT inequality is safer for time slots to avoid
                # "touching" intervals counting as overlaps
                if start < slot_end and end > slot_start:
                    active_vars.append(y[cid])

            # CRITICAL FIX:
            # 1. Only add constraint if strictly necessary ( > 1 course)
            # 2. Use explicit summation to avoid generator weirdness in backend
            if len(active_vars) > 1:
                # This creates a "Clique" constraint which is very GPU friendly
                model += (pulp.lpSum(active_vars) <= 1, f"overlap_{day}_{i}")

    solver = pulp.PULP_CBC_CMD(msg=False)
    return model, solver, y


def solve_ilp(offerings: list[Offering]) -> list[Offering]:
    model, solver, y = create_model(offerings)
    model.solve(solver)

    if pulp.LpStatus[model.status] != "Optimal":
        logger.warning(f"MODEL STATUS NOT OPTIMAL: {pulp.LpStatus[model.status]}")
    else:
        logger.success(f"MODEL STATUS: {pulp.LpStatus[model.status]}")

    return [
        [o for o in offerings if o.courseId == cid][0]
        for cid, var in y.items()
        if pulp.value(var) > 0.5
    ]


def solve_ilp_model(model, solver, y, offerings):
    model.solve(solver)

    if pulp.LpStatus[model.status] != "Optimal":
        logger.warning(f"model status is '{pulp.LpStatus[model.status]}' != Optimal")

    return [
        [o for o in offerings if o.courseId == cid][0]
        for cid, var in y.items()
        if pulp.value(var) > 0.5
    ]


if __name__ == "__main__":
    # ran by benchexec. the first argument is the constraint file, so load constraint, build model, solve
    load_constraints_from_file(sys.argv[1])
    num_courses = int(sys.argv[2])
    C.TOTAL_COURSE_COUNT_CONSTRAINT = SimpleNamespace(min=num_courses, max=num_courses)

    offerings = load_offerings()
    offerings = preprocess(offerings)

    best_solution = solve_ilp(offerings)
