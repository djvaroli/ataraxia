"""Streaks, totals, the per-subject breakdown, and recent days."""

from datetime import timedelta

from ataraxia.adapters.sqlite.lessons import LessonRepository
from ataraxia.application.settings import PreferencesService
from ataraxia.application.views import DayActivity, Progress, SubjectProgress
from ataraxia.domain.progress import streaks
from ataraxia.domain.subjects import SUBJECT_IDS

RECENT_DAYS = 84


class ProgressService:
    def __init__(self, lessons: LessonRepository, preferences: PreferencesService) -> None:
        self._lessons = lessons
        self._preferences = preferences

    def progress(self, days: int = RECENT_DAYS) -> Progress:
        """Days are the owner's local dates; the last `days` end with today."""
        today = self._preferences.owner_time().today
        first_day = today - timedelta(days=days - 1)
        counted = streaks(self._lessons.finished_dates(), today)
        totals = {row.subject: row for row in self._lessons.subject_totals()}
        finished = self._lessons.finished_per_day(first_day)
        seconds = self._lessons.read_seconds_per_day(first_day)
        subjects = []
        for subject_id in SUBJECT_IDS:
            row = totals.get(subject_id)
            subjects.append(
                SubjectProgress(
                    subject=subject_id,
                    lessons=row.lessons if row else 0,
                    finished=row.finished if row else 0,
                    read_minutes=row.read_seconds // 60 if row else 0,
                    liked=row.liked if row else 0,
                    disliked=row.disliked if row else 0,
                    last_finished_on=row.last_finished_on if row else None,
                )
            )
        recent = [first_day + timedelta(days=offset) for offset in range(days)]
        return Progress(
            current_streak=counted.current,
            longest_streak=counted.longest,
            lessons_total=sum(row.lessons for row in totals.values()),
            finished_total=sum(row.finished for row in totals.values()),
            saved_total=sum(row.saved for row in totals.values()),
            read_minutes_total=sum(row.read_seconds for row in totals.values()) // 60,
            subjects=subjects,
            days=[
                DayActivity(
                    date=day,
                    finished=finished.get(day, 0),
                    read_minutes=seconds.get(day, 0) // 60,
                )
                for day in recent
            ],
        )
