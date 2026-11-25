"""Asking for lessons: new requests, follow-ups, today's daily lesson, and retries.

These only insert or requeue jobs; the worker does the preparation.
"""

from uuid import uuid4

from pydantic import JsonValue

from ataraxia.adapters.sqlite.jobs import JobRepository
from ataraxia.adapters.sqlite.lessons import LessonRepository
from ataraxia.application.errors import NotFoundError
from ataraxia.application.models import DailyCap, NewJob
from ataraxia.application.settings import OwnerTime, PreferencesService
from ataraxia.application.views import Job
from ataraxia.domain.activity import NewEvent
from ataraxia.domain.errors import InvalidInputError
from ataraxia.domain.jobs import JobKind
from ataraxia.domain.subjects import SubjectId


class LessonRequests:
    def __init__(
        self,
        jobs: JobRepository,
        lessons: LessonRepository,
        preferences: PreferencesService,
        lessons_per_day: int,
    ) -> None:
        self._jobs = jobs
        self._lessons = lessons
        self._preferences = preferences
        self._lessons_per_day = lessons_per_day

    def get(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise NotFoundError("No such job.")
        return job

    def request_surprise(self) -> Job:
        return self._create(self._preferences.owner_time(), "surprise")

    def request_subject(self, subject: SubjectId) -> Job:
        return self._create(self._preferences.owner_time(), "subject", subject=subject)

    def request_topic(self, topic: str) -> Job:
        return self._create(self._preferences.owner_time(), "topic", request_text=topic)

    def request_follow_up(
        self, lesson_id: str, *, direction: int | None, question: str | None
    ) -> Job:
        """Continue a lesson with one of its suggested directions or the owner's question.

        Raises `InvalidInputError` unless exactly one is given, and `NotFoundError`.
        """
        if (direction is None) == (question is None):
            raise InvalidInputError("direction", "Choose a direction or ask a question, not both.")
        parent = self._lessons.parent(lesson_id)
        if parent is None:
            raise NotFoundError("No such lesson.")
        request_text = question
        if direction is not None:
            if direction >= len(parent.go_deeper):
                raise InvalidInputError("direction", "This lesson has no such direction.")
            request_text = parent.go_deeper[direction].title
        return self._create(
            self._preferences.owner_time(),
            "follow_up",
            subject=parent.subject,
            request_text=request_text,
            parent_lesson_id=parent.id,
            direction_index=direction,
        )

    def ensure_daily(self) -> Job:
        """Today's daily job, created if there is none. Idempotent."""
        moment = self._preferences.owner_time()
        existing = self._jobs.daily_job(moment.today)
        if existing is not None:
            return existing
        return self._create(moment, "daily")

    def retry(self, job_id: str) -> Job:
        """Queue a failed job again with fresh attempts; every call still counts."""
        moment = self._preferences.owner_time()
        job = self.get(job_id)
        event = moment.event(
            "lesson.requested",
            subject=job.subject,
            data={"job_id": job.id, "kind": job.kind, "retry": True},
        )
        return self._jobs.retry(job_id, event, self._cap(moment))

    def _cap(self, moment: OwnerTime) -> DailyCap:
        return DailyCap(local_date=moment.today, limit=self._lessons_per_day)

    def _create(
        self,
        moment: OwnerTime,
        kind: JobKind,
        *,
        subject: SubjectId | None = None,
        request_text: str | None = None,
        parent_lesson_id: str | None = None,
        direction_index: int | None = None,
    ) -> Job:
        job = NewJob(
            id=str(uuid4()),
            kind=kind,
            local_date=moment.today,
            created_at=moment.now,
            subject=subject,
            request_text=request_text,
            parent_lesson_id=parent_lesson_id,
            direction_index=direction_index,
        )
        return self._jobs.create(job, requested_event(moment, job), self._cap(moment))


def requested_event(moment: OwnerTime, job: NewJob) -> NewEvent:
    """`lesson.requested` with the kind, subject, and the owner's words, if any."""
    data: dict[str, JsonValue] = {"job_id": job.id, "kind": job.kind}
    if job.kind == "topic":
        data["topic"] = job.request_text
    elif job.kind == "follow_up":
        data["parent_id"] = job.parent_lesson_id
        if job.direction_index is None:
            data["question"] = job.request_text
        else:
            data["direction"] = job.request_text
    return moment.event("lesson.requested", subject=job.subject, data=data)
