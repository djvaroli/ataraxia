"""Fakes and builders shared by the unit tests."""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ataraxia.adapters.fake_generator import FakeLessonGenerator, NoIllustrations
from ataraxia.adapters.sqlite.migrations import migrate
from ataraxia.application.ports import (
    GeneratedLesson,
    GenerationError,
    LessonBrief,
)
from ataraxia.application.worker import LessonWorker
from ataraxia.bootstrap import (
    ApiServices,
    WorkerServices,
    create_api_services,
    create_worker,
)
from ataraxia.config import Settings
from ataraxia.domain.subjects import SubjectId

START = datetime(2026, 11, 24, 15, 0, tzinfo=UTC)


class FixedClock:
    def __init__(self, now: datetime = START) -> None:
        self.current = now

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


@dataclass
class ScriptedGenerator:
    """Fails with the queued errors first, then writes fake lessons; records briefs."""

    errors: list[GenerationError] = field(default_factory=list)
    briefs: list[LessonBrief] = field(default_factory=list)
    change: Callable[[GeneratedLesson], GeneratedLesson] | None = None

    def generate(self, brief: LessonBrief) -> GeneratedLesson:
        self.briefs.append(brief)
        if self.errors:
            raise self.errors.pop(0)
        generated = FakeLessonGenerator().generate(brief)
        return self.change(generated) if self.change else generated


def local_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_path": tmp_path / "app.db",
        "auth_mode": "local",
        "max_lessons_per_day": 8,
    }
    values.update(overrides)
    return Settings.model_validate(values)


@dataclass
class World:
    """API services and a worker sharing one temporary database and clock."""

    settings: Settings
    clock: FixedClock
    generator: ScriptedGenerator
    api: ApiServices
    workers: WorkerServices

    @property
    def worker(self) -> LessonWorker:
        return self.workers.worker


def make_world(tmp_path: Path, **overrides: object) -> World:
    settings = local_settings(tmp_path, **overrides)
    clock = FixedClock()
    generator = ScriptedGenerator()
    api = create_api_services(settings, clock=clock)
    migrate(api.database)
    workers = create_worker(
        settings,
        clock=clock,
        generator=generator,
        illustrations=NoIllustrations(),
        rng=random.Random(7),
    )
    return World(settings, clock, generator, api, workers)


def event_types(world: World) -> list[str]:
    with world.api.database.connect() as connection:
        found = connection.execute("SELECT type FROM activity_events ORDER BY id").fetchall()
    return [row["type"] for row in found]


def count(world: World, table: str) -> int:
    with world.api.database.connect() as connection:
        return int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0])


def prepare_lesson(world: World, subject: SubjectId = "art") -> str:
    """Request a subject lesson and run the worker once; return the lesson ID."""
    job = world.api.requests.request_subject(subject)
    assert world.worker.step()
    finished = world.api.requests.get(job.id)
    assert finished.lesson_id is not None, finished
    return finished.lesson_id
