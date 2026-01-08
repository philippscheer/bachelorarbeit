import datetime


from loguru import logger

from bachelorarbeit.dtypes import Offering
from models.utils import get_offering_mark, get_schedule_mark, is_valid_schedule


def print_schedule(schedule: list[Offering]):
    logger.debug(
        f"Schedule (Mark: {get_schedule_mark(schedule)}, valid? {is_valid_schedule(schedule, schedule_complete=True)}):"
    )
    for offering in schedule:
        print_offering(offering)


def print_offering(offering: Offering):
    logger.debug(
        f"  Offering {offering.groupId} (LV-ID {offering.courseId}, {offering.ects} ECTS, Mark: {get_offering_mark(offering)})"
    )
    for date in offering.dates:
        logger.debug(f"    {_format(date['start'])} - {date['end'].strftime('%H:%M')}")


def _format(d: datetime.datetime):
    day = d.strftime("%A")

    return f"{day}{' ' * (10 - len(day))}{d.strftime('%d.%m %H:%M')}"
