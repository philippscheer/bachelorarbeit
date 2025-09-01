from typing import Literal
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Offering:
    courseId: int
    groupId: Literal[
        "adp",
        "bis",
        "blp",
        "dke",
        "fbwl",
        "fm",
        "gb",
        "jub",
        "m",
        "mak",
        "mgm",
        "mik",
        "rn",
        "s",
        "swa",
        "winf",
        "wpr",
        "zuwi",
    ]
    dates: list[dict[Literal["start", "end"], datetime]]
    ects: int
    mark: int = None

    def __hash__(self):
        return self.courseId

    def __eq__(self, other):
        return self.courseId == other.courseId

    def __str__(self):
        return (
            f"Offering(groupId={self.groupId}, "
            f"courseId={self.courseId}, "
            f"mark={self.mark}, "
            f"dates={len(self.dates)}, "
            f"ects={self.ects})"
        )

    def __repr__(self):
        return self.__str__()


if __name__ == "__main__":
    o1 = Offering(
        courseId=1, groupId="adp", dates=[{"start": datetime.now(), "end": datetime.now() + timedelta(hours=1)}], ects=1
    )
    print(o1)
