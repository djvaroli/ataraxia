"""The owner's settings and the local calendar every other use case reads them for."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime

from pydantic import JsonValue

from ataraxia.adapters.sqlite.profile import ProfileRepository
from ataraxia.application.ports import Clock
from ataraxia.domain.activity import EventType, NewEvent
from ataraxia.domain.calendar import local_time
from ataraxia.domain.lessons import LessonLength
from ataraxia.domain.preferences import (
    Preferences,
    catalog_ordered,
    check_time_zone,
    default_preferences,
)
from ataraxia.domain.subjects import SubjectId


@dataclass(frozen=True)
class OwnerTime:
    """The current instant with the owner's settings and local date and hour."""

    now: datetime
    preferences: Preferences
    today: date = field(init=False)
    hour: int = field(init=False)

    def __post_init__(self) -> None:
        local = local_time(self.now, self.preferences.time_zone)
        object.__setattr__(self, "today", local.date())
        object.__setattr__(self, "hour", local.hour)

    def event(
        self,
        type: EventType,
        *,
        lesson_id: str | None = None,
        subject: SubjectId | None = None,
        data: Mapping[str, JsonValue] | None = None,
    ) -> NewEvent:
        return NewEvent(
            type=type,
            occurred_at=self.now,
            local_date=self.today,
            lesson_id=lesson_id,
            subject=subject,
            data=data or {},
        )


class PreferencesService:
    def __init__(self, profile: ProfileRepository, clock: Clock, default_time_zone: str) -> None:
        self._profile = profile
        self._clock = clock
        self._defaults = default_preferences(check_time_zone(default_time_zone))

    def get(self) -> Preferences:
        return self._profile.get() or self._defaults

    def owner_time(self) -> OwnerTime:
        return OwnerTime(now=self._clock.now(), preferences=self.get())

    def update(
        self,
        *,
        time_zone: str | None = None,
        subjects: list[SubjectId] | None = None,
        lesson_length: LessonLength | None = None,
        morning_lesson: bool | None = None,
        morning_hour: int | None = None,
    ) -> Preferences:
        """Apply the given fields. Setting the time zone confirms it, even when it is
        unchanged. Writes `settings.updated` with the changed fields' new values, and
        nothing when nothing changed. Raises `InvalidInputError`."""
        current = self.get()
        changes: dict[str, object] = {}
        if time_zone is not None:
            changes["time_zone"] = check_time_zone(time_zone)
            changes["time_zone_confirmed"] = True
        if subjects is not None:
            changes["subjects"] = catalog_ordered(subjects)
        if lesson_length is not None:
            changes["lesson_length"] = lesson_length
        if morning_lesson is not None:
            changes["morning_lesson"] = morning_lesson
        if morning_hour is not None:
            changes["morning_hour"] = morning_hour
        updated = Preferences.model_validate({**current.model_dump(), **changes})
        before = current.model_dump(mode="json")
        after = updated.model_dump(mode="json")
        changed: dict[str, JsonValue] = {
            name: value for name, value in after.items() if before[name] != value
        }
        if not changed:
            return current
        moment = OwnerTime(now=self._clock.now(), preferences=updated)
        self._profile.save(updated, moment.event("settings.updated", data=changed))
        return updated
