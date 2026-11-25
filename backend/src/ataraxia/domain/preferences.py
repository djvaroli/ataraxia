"""The owner's settings and the rules a change must satisfy."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ataraxia.domain.calendar import is_time_zone
from ataraxia.domain.errors import InvalidInputError
from ataraxia.domain.lessons import LessonLength
from ataraxia.domain.subjects import SUBJECT_IDS, SubjectId

DEFAULT_MORNING_HOUR = 6


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    time_zone: str
    time_zone_confirmed: bool = Field(
        description="False until the owner or the browser has set the time zone."
    )
    subjects: list[SubjectId] = Field(description="Enabled subjects, in catalog order.")
    lesson_length: LessonLength
    morning_lesson: bool
    morning_hour: Annotated[int, Field(ge=0, le=23)]


def default_preferences(time_zone: str) -> Preferences:
    """Settings before the owner changes anything: every subject, standard length,
    and a morning lesson at 6. The zone is unconfirmed until the owner sets it."""
    return Preferences(
        time_zone=time_zone,
        time_zone_confirmed=False,
        subjects=list(SUBJECT_IDS),
        lesson_length="standard",
        morning_lesson=True,
        morning_hour=DEFAULT_MORNING_HOUR,
    )


def check_time_zone(name: str) -> str:
    if not is_time_zone(name):
        raise InvalidInputError("time_zone", "Use an IANA time zone such as Europe/Paris.")
    return name


def catalog_ordered(subjects: list[SubjectId]) -> list[SubjectId]:
    """Reject duplicates and an empty list; return the subjects in catalog order."""
    if not subjects:
        raise InvalidInputError("subjects", "Enable at least one subject.")
    if len(set(subjects)) != len(subjects):
        raise InvalidInputError("subjects", "Each subject may appear only once.")
    chosen = set(subjects)
    return [subject_id for subject_id in SUBJECT_IDS if subject_id in chosen]
