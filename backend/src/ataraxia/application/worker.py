"""Preparing lessons: recovery, the morning lesson, and one job at a time.

The generator call happens outside any transaction. Starting an attempt (cap check,
attempt count, call row) and publishing its result are each one transaction.
"""

import logging
import random
from datetime import timedelta
from uuid import uuid4

from ataraxia.adapters.sqlite.jobs import JobRepository
from ataraxia.adapters.sqlite.lessons import LessonRepository
from ataraxia.adapters.sqlite.status import WorkerStatusRepository
from ataraxia.application.models import DailyCap, NewJob, ParentRecord, PendingJob, Publication
from ataraxia.application.ports import (
    GeneratedLesson,
    GenerationError,
    GenerationUsage,
    IllustrationResolver,
    LessonBrief,
    LessonGenerator,
    ParentLesson,
)
from ataraxia.application.requests import requested_event
from ataraxia.application.settings import OwnerTime, PreferencesService
from ataraxia.domain.activity import NewEvent
from ataraxia.domain.choice import choose_subject
from ataraxia.domain.jobs import JobErrorCode, after_failure
from ataraxia.domain.lessons import Illustration

logger = logging.getLogger(__name__)

TASTE_WINDOW = timedelta(days=60)
RECENT_IN_SUBJECT = 40
RECENT_OVERALL = 15
TASTE_TITLES = 8


class LessonWorker:
    def __init__(
        self,
        jobs: JobRepository,
        lessons: LessonRepository,
        status: WorkerStatusRepository,
        preferences: PreferencesService,
        generator: LessonGenerator,
        illustrations: IllustrationResolver,
        rng: random.Random,
        lessons_per_day: int,
    ) -> None:
        self._jobs = jobs
        self._lessons = lessons
        self._status = status
        self._preferences = preferences
        self._generator = generator
        self._illustrations = illustrations
        self._rng = rng
        self._lessons_per_day = lessons_per_day

    def recover(self) -> int:
        """Requeue or fail jobs a previous worker left running; returns how many."""
        moment = self._preferences.owner_time()
        return self._jobs.recover(
            moment.now,
            lambda job_id: moment.event(
                "lesson.failed", data={"job_id": job_id, "error_code": "interrupted"}
            ),
        )

    def ensure_morning_lesson(self) -> bool:
        """Queue today's daily job once the morning hour has passed, if enabled.

        Past days are not caught up. Returns True when a job was created.
        """
        moment = self._preferences.owner_time()
        preferences = moment.preferences
        if not preferences.morning_lesson or moment.hour < preferences.morning_hour:
            return False
        if self._jobs.daily_job(moment.today) is not None:
            return False
        job = NewJob(id=str(uuid4()), kind="daily", local_date=moment.today, created_at=moment.now)
        return self._jobs.create(job, requested_event(moment, job), cap=None).id == job.id

    def step(self) -> bool:
        """Attempt the oldest ready job. Returns False when there was nothing to do."""
        moment = self._preferences.owner_time()
        job = self._jobs.next_ready(moment.now)
        if job is None:
            return False
        call_id = str(uuid4())
        cap = DailyCap(local_date=moment.today, limit=self._lessons_per_day)
        refused = _failed_event(moment, job, "daily_limit")
        if not self._jobs.start(job, call_id, moment.now, cap, refused):
            logger.info("Job %s refused: daily limit", job.id)
            return True
        attempts = job.attempts + 1
        parent = (
            None if job.parent_lesson_id is None else self._lessons.parent(job.parent_lesson_id)
        )
        logger.info("Job %s attempt %d started", job.id, attempts)
        try:
            brief = self._brief(moment, job, parent)
            generated = self._generate(brief)
        except GenerationError as error:
            self._fail_attempt(job, call_id, attempts, error.code, error.usage)
            return True
        images = self._resolve(generated)
        finished = self._preferences.owner_time()
        lesson_id = str(uuid4())
        publication = Publication(
            lesson_id=lesson_id,
            job=job,
            call_id=call_id,
            content=generated.content,
            illustrations=images,
            local_date=finished.today,
            created_at=finished.now,
            model=generated.usage.model,
            prompt_version=generated.prompt_version,
            parent=parent,
        )
        event = finished.event(
            "lesson.prepared",
            lesson_id=lesson_id,
            subject=generated.content.subject,
            data={
                "job_id": job.id,
                "kind": job.kind,
                "model": generated.usage.model,
                "reading_minutes": generated.content.reading_minutes,
            },
        )
        self._jobs.publish(publication, generated.usage, event)
        self._status.record_call(finished.now, None, generated.usage)
        logger.info("Job %s succeeded", job.id)
        return True

    def _generate(self, brief: LessonBrief) -> GeneratedLesson:
        """Call the generator and enforce the subject rule. Raises `GenerationError`."""
        try:
            generated = self._generator.generate(brief)
        except GenerationError:
            raise
        except Exception as error:
            # A generator bug must not leave the job running until the next restart.
            # The type only: messages can contain lesson text.
            logger.error("Lesson generator failed unexpectedly: %s", type(error).__name__)
            raise GenerationError("claude_error", "Unexpected generator failure") from error
        if brief.kind != "topic" and generated.content.subject != brief.subject:
            raise GenerationError(
                "invalid_output", "Lesson subject differs from the brief", generated.usage
            )
        return generated

    def _resolve(self, generated: GeneratedLesson) -> list[Illustration]:
        try:
            return self._illustrations.resolve(generated.content.illustrations)
        except Exception as error:
            logger.error(
                "Illustration lookup failed (%s); publishing without images", type(error).__name__
            )
            return []

    def _fail_attempt(
        self,
        job: PendingJob,
        call_id: str,
        attempts: int,
        code: JobErrorCode,
        usage: GenerationUsage,
    ) -> None:
        moment = self._preferences.owner_time()
        decision = after_failure(code, attempts, job.queued_at, moment.now)
        self._jobs.record_failure(
            job,
            call_id,
            code,
            usage,
            decision,
            moment.now,
            _failed_event(moment, job, code),
        )
        self._status.record_call(moment.now, code, usage)
        logger.info("Job %s attempt %d failed: %s", job.id, attempts, code)

    def _brief(
        self, moment: OwnerTime, job: PendingJob, parent: ParentRecord | None
    ) -> LessonBrief:
        """Everything the writer needs. Raises `GenerationError` if the parent is gone."""
        preferences = moment.preferences
        since = moment.now - TASTE_WINDOW
        subject = job.subject
        if job.kind in ("daily", "surprise"):
            subject = choose_subject(
                preferences.subjects,
                self._lessons.recent_subjects(2),
                self._lessons.ratings_since(since),
                self._rng,
            )
        parent_lesson = None
        direction = None
        question = None
        if job.kind == "follow_up":
            if parent is None:
                raise GenerationError("invalid_output", "The parent lesson is missing")
            parent_lesson = ParentLesson(
                title=parent.title,
                subject=parent.subject,
                body_markdown=parent.body_markdown,
                key_ideas=tuple(parent.key_ideas),
            )
            if job.direction_index is not None:
                direction = parent.go_deeper[job.direction_index]
            else:
                question = job.request_text
        return LessonBrief(
            kind=job.kind,
            local_date=moment.today,
            length=preferences.lesson_length,
            subject=subject,
            topic=job.request_text if job.kind == "topic" else None,
            parent=parent_lesson,
            direction=direction,
            question=question,
            recent_titles_in_subject=(
                tuple(self._lessons.recent_titles(subject, RECENT_IN_SUBJECT)) if subject else ()
            ),
            recent_titles=tuple(self._lessons.recent_titles(None, RECENT_OVERALL)),
            liked_titles=tuple(self._lessons.rated_titles(1, since, TASTE_TITLES)),
            disliked_titles=tuple(self._lessons.rated_titles(-1, since, TASTE_TITLES)),
        )


def _failed_event(moment: OwnerTime, job: PendingJob, code: JobErrorCode) -> NewEvent:
    return moment.event(
        "lesson.failed",
        subject=job.subject,
        data={"job_id": job.id, "kind": job.kind, "error_code": code},
    )
