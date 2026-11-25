"""The activity record and the complete export, for later analysis."""

from collections.abc import Callable

from ataraxia.adapters.sqlite.activity import ActivityRepository
from ataraxia.adapters.sqlite.jobs import JobRepository
from ataraxia.adapters.sqlite.lessons import LessonRepository
from ataraxia.application.settings import PreferencesService
from ataraxia.application.views import ActivityPage, ExportDocument
from ataraxia.domain.activity import EventType
from ataraxia.domain.errors import InvalidInputError


class ActivityService:
    def __init__(self, activity: ActivityRepository, preferences: PreferencesService) -> None:
        self._activity = activity
        self._preferences = preferences

    def record(self, event_type: EventType) -> None:
        """Record an event the client reports, such as `app.opened`."""
        self._activity.append(self._preferences.owner_time().event(event_type))

    def page(self, cursor: str | None, limit: int) -> ActivityPage:
        """Events oldest first; the cursor is the last event ID of the previous page."""
        after = None
        if cursor is not None:
            if not cursor.isdigit():
                raise InvalidInputError("cursor", "This page cursor is not valid.")
            after = int(cursor)
        found = self._activity.page(after, limit + 1)
        items = found[:limit]
        return ActivityPage(
            items=items, next_cursor=str(items[-1].id) if len(found) > limit else None
        )


class ExportService:
    def __init__(
        self,
        lessons: LessonRepository,
        jobs: JobRepository,
        activity: ActivityRepository,
        preferences: PreferencesService,
        schema_version: Callable[[], int],
    ) -> None:
        self._lessons = lessons
        self._jobs = jobs
        self._activity = activity
        self._preferences = preferences
        self._schema_version = schema_version

    def export(self) -> ExportDocument:
        """Every durable table except the worker's status row."""
        moment = self._preferences.owner_time()
        return ExportDocument(
            schema_version=self._schema_version(),
            exported_at=moment.now,
            preferences=moment.preferences,
            lessons=self._lessons.all_lessons(),
            jobs=self._jobs.all_jobs(),
            calls=self._jobs.all_calls(),
            events=self._activity.all_events(),
            reading_sessions=self._lessons.reading_sessions(),
        )
