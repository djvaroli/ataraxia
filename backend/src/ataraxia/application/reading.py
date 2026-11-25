"""Owner actions on a lesson: open, read, save, rate, finish, and flag.

Repeating an action with the same value changes nothing and records nothing.
"""

from collections.abc import Callable

from ataraxia.adapters.sqlite.lessons import LessonRepository
from ataraxia.application.errors import NotFoundError
from ataraxia.application.settings import OwnerTime, PreferencesService
from ataraxia.application.views import LessonState, Rating
from ataraxia.domain.activity import EventType, NewEvent
from ataraxia.domain.subjects import SubjectId


class ReadingService:
    def __init__(self, lessons: LessonRepository, preferences: PreferencesService) -> None:
        self._lessons = lessons
        self._preferences = preferences

    def set_saved(self, lesson_id: str, saved: bool) -> LessonState:
        kind: EventType = "lesson.saved" if saved else "lesson.unsaved"
        return self._apply(
            lesson_id, kind, {}, lambda event: self._lessons.set_saved(lesson_id, saved, event)
        )

    def set_rating(self, lesson_id: str, rating: Rating) -> LessonState:
        return self._apply(
            lesson_id,
            "lesson.rated",
            {"rating": rating},
            lambda event: self._lessons.set_rating(lesson_id, rating, event),
        )

    def set_finished(self, lesson_id: str, finished: bool) -> LessonState:
        kind: EventType = "lesson.finished" if finished else "lesson.unfinished"
        return self._apply(
            lesson_id,
            kind,
            {},
            lambda event: self._lessons.set_finished(lesson_id, finished, event),
        )

    def flag(self, lesson_id: str, note: str) -> LessonState:
        return self._apply(
            lesson_id,
            "lesson.flagged",
            {"note": note},
            lambda event: self._lessons.set_flag(lesson_id, note, event),
        )

    def record_open(self, lesson_id: str) -> LessonState:
        return self._apply(
            lesson_id,
            "lesson.opened",
            {},
            lambda event: self._lessons.record_open(lesson_id, event),
        )

    def record_reading(
        self, lesson_id: str, session_id: str, seconds: int, scroll: float
    ) -> LessonState:
        """Upsert one reader visit's cumulative totals. No event is written.

        Raises `NotFoundError`, or `ConflictError` for another lesson's session.
        """
        moment = self._preferences.owner_time()
        state = self._lessons.record_reading(
            lesson_id, session_id, seconds, scroll, moment.now, moment.today
        )
        if state is None:
            raise NotFoundError("No such lesson.")
        return state

    def _apply(
        self,
        lesson_id: str,
        kind: EventType,
        data: dict[str, int | str],
        change: Callable[[NewEvent], LessonState | None],
    ) -> LessonState:
        subject = self._subject(lesson_id)
        moment: OwnerTime = self._preferences.owner_time()
        state = change(moment.event(kind, lesson_id=lesson_id, subject=subject, data=data))
        if state is None:
            raise NotFoundError("No such lesson.")
        return state

    def _subject(self, lesson_id: str) -> SubjectId:
        subject = self._lessons.subject_of(lesson_id)
        if subject is None:
            raise NotFoundError("No such lesson.")
        return subject
