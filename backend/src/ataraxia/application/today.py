"""The Today screen: the daily lesson's slot, other work, and what can still be asked."""

from datetime import timedelta

from ataraxia.adapters.sqlite.jobs import JobRepository
from ataraxia.adapters.sqlite.lessons import LessonRepository
from ataraxia.adapters.sqlite.status import WorkerStatusRepository
from ataraxia.application.settings import OwnerTime, PreferencesService
from ataraxia.application.views import (
    Allowance,
    DailySlot,
    DailySlotStatus,
    Job,
    Today,
    WorkerStatus,
)
from ataraxia.domain.jobs import WAITING_LIMIT

UNFINISHED_WINDOW = timedelta(days=14)
UNFINISHED_LIMIT = 5
WORKER_ONLINE_WITHIN = timedelta(seconds=30)


class TodayService:
    def __init__(
        self,
        jobs: JobRepository,
        lessons: LessonRepository,
        status: WorkerStatusRepository,
        preferences: PreferencesService,
        lessons_per_day: int,
    ) -> None:
        self._jobs = jobs
        self._lessons = lessons
        self._status = status
        self._preferences = preferences
        self._lessons_per_day = lessons_per_day

    def today(self) -> Today:
        moment = self._preferences.owner_time()
        jobs = self._jobs.jobs_on(moment.today)
        others = [
            job
            for job in jobs
            if job.kind != "daily" and job.status in ("queued", "running", "failed")
        ]
        return Today(
            local_date=moment.today,
            daily=self.daily_slot(moment),
            jobs=others,
            unfinished=self._lessons.unfinished(moment.now - UNFINISHED_WINDOW, UNFINISHED_LIMIT),
            allowance=self.allowance(moment),
            worker=self.worker(moment),
        )

    def daily_slot(self, moment: OwnerTime | None = None) -> DailySlot:
        """The daily lesson's state. Without a job, `waiting` until the morning hour
        when the morning lesson is on, otherwise `not_scheduled`."""
        moment = moment or self._preferences.owner_time()
        preferences = moment.preferences
        morning_hour = preferences.morning_hour if preferences.morning_lesson else None
        job = self._jobs.daily_job(moment.today)
        if job is None:
            waiting = morning_hour is not None and moment.hour < morning_hour
            return DailySlot(
                status="waiting" if waiting else "not_scheduled",
                lesson=None,
                job=None,
                morning_hour=morning_hour,
            )
        lesson = None
        if job.lesson_id is not None:
            lesson = self._lessons.summaries([job.lesson_id]).get(job.lesson_id)
        return DailySlot(
            status=_slot_status(job),
            lesson=lesson,
            job=job,
            morning_hour=morning_hour,
        )

    def allowance(self, moment: OwnerTime) -> Allowance:
        usage = self._jobs.usage(moment.today)
        return Allowance(
            used=usage.used,
            limit=self._lessons_per_day,
            remaining=max(0, self._lessons_per_day - usage.used - usage.queued),
            waiting=usage.queued + usage.running,
            waiting_limit=WAITING_LIMIT,
        )

    def worker(self, moment: OwnerTime) -> WorkerStatus:
        record = self._status.get()
        online = (
            record.heartbeat_at is not None
            and moment.now - record.heartbeat_at < WORKER_ONLINE_WITHIN
        )
        return WorkerStatus(
            online=online,
            heartbeat_at=record.heartbeat_at,
            login_expires_at=record.login_expires_at,
        )


def _slot_status(job: Job) -> DailySlotStatus:
    return "ready" if job.status == "succeeded" else job.status
