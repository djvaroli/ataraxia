"""Choose and connect implementations for the API, the worker, and the tools.

This is the only module that decides which adapters run.
"""

import random
from dataclasses import dataclass

from ataraxia.adapters.clock import SystemClock
from ataraxia.adapters.fake_generator import FakeLessonGenerator, NoIllustrations
from ataraxia.adapters.firebase import FirebaseVerifier, GoogleSigningKeys, SigningKeySource
from ataraxia.adapters.local_owner import LocalOwner
from ataraxia.adapters.sqlite.activity import ActivityRepository
from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.jobs import JobRepository
from ataraxia.adapters.sqlite.lessons import LessonRepository
from ataraxia.adapters.sqlite.migrations import schema_version
from ataraxia.adapters.sqlite.profile import ProfileRepository
from ataraxia.adapters.sqlite.status import WorkerStatusRepository
from ataraxia.api.auth import OwnerPolicy
from ataraxia.api.schemas import ClientConfig, FirebaseWebConfig
from ataraxia.application.library import LibraryService
from ataraxia.application.ports import Clock, IllustrationResolver, LessonGenerator
from ataraxia.application.progress import ProgressService
from ataraxia.application.reading import ReadingService
from ataraxia.application.records import ActivityService, ExportService
from ataraxia.application.requests import LessonRequests
from ataraxia.application.settings import PreferencesService
from ataraxia.application.today import TodayService
from ataraxia.application.worker import LessonWorker
from ataraxia.config import Settings

LOCAL_OWNER_UID = "local-owner"


class ConfigurationError(RuntimeError):
    """Settings that cannot run; the message names the variables to fix."""


def create_database(settings: Settings) -> Database:
    """Point at the configured SQLite file; nothing is opened until first use."""
    return Database(settings.database_path)


@dataclass(frozen=True)
class Repositories:
    profile: ProfileRepository
    lessons: LessonRepository
    jobs: JobRepository
    status: WorkerStatusRepository
    activity: ActivityRepository

    @classmethod
    def on(cls, database: Database) -> "Repositories":
        return cls(
            profile=ProfileRepository(database),
            lessons=LessonRepository(database),
            jobs=JobRepository(database),
            status=WorkerStatusRepository(database),
            activity=ActivityRepository(database),
        )


def create_preferences(
    repositories: Repositories, settings: Settings, clock: Clock
) -> PreferencesService:
    try:
        return PreferencesService(repositories.profile, clock, settings.default_time_zone)
    except ValueError as error:
        raise ConfigurationError(
            "ATARAXIA_DEFAULT_TIME_ZONE must be an IANA time zone such as Europe/Paris"
        ) from error


def create_export(
    repositories: Repositories, preferences: PreferencesService, database: Database
) -> ExportService:
    return ExportService(
        repositories.lessons,
        repositories.jobs,
        repositories.activity,
        preferences,
        lambda: schema_version(database),
    )


@dataclass(frozen=True)
class ApiServices:
    database: Database
    owner: OwnerPolicy
    client_config: ClientConfig
    lessons_per_day: int
    preferences: PreferencesService
    requests: LessonRequests
    reading: ReadingService
    library: LibraryService
    today: TodayService
    progress: ProgressService
    activity: ActivityService
    export: ExportService


def create_owner_policy(
    settings: Settings, keys: SigningKeySource | None = None
) -> tuple[OwnerPolicy, ClientConfig]:
    """Raises `ConfigurationError` when firebase mode lacks its settings."""
    if settings.auth_mode == "local":
        return (
            OwnerPolicy("local", LocalOwner(LOCAL_OWNER_UID), LOCAL_OWNER_UID),
            ClientConfig(auth_mode="local", firebase=None),
        )
    required = {
        "ATARAXIA_OWNER_UID": settings.owner_uid,
        "ATARAXIA_FIREBASE_PROJECT_ID": settings.firebase_project_id,
        "ATARAXIA_FIREBASE_API_KEY": settings.firebase_api_key,
        "ATARAXIA_FIREBASE_AUTH_DOMAIN": settings.firebase_auth_domain,
        "ATARAXIA_FIREBASE_APP_ID": settings.firebase_app_id,
    }
    missing = [name for name, value in required.items() if not value.strip()]
    if missing:
        raise ConfigurationError(
            "Firebase sign-in needs "
            + ", ".join(missing)
            + " (or ATARAXIA_AUTH_MODE=local for development on this machine)"
        )
    verifier = FirebaseVerifier(settings.firebase_project_id, keys or GoogleSigningKeys())
    return (
        OwnerPolicy("firebase", verifier, settings.owner_uid),
        ClientConfig(
            auth_mode="firebase",
            firebase=FirebaseWebConfig(
                api_key=settings.firebase_api_key,
                auth_domain=settings.firebase_auth_domain,
                project_id=settings.firebase_project_id,
                app_id=settings.firebase_app_id,
            ),
        ),
    )


def create_api_services(
    settings: Settings,
    *,
    clock: Clock | None = None,
    keys: SigningKeySource | None = None,
) -> ApiServices:
    """Raises `ConfigurationError` for settings the API cannot run with."""
    clock = clock or SystemClock()
    database = create_database(settings)
    repositories = Repositories.on(database)
    owner, client_config = create_owner_policy(settings, keys)
    preferences = create_preferences(repositories, settings, clock)
    limit = settings.max_lessons_per_day
    return ApiServices(
        database=database,
        owner=owner,
        client_config=client_config,
        lessons_per_day=limit,
        preferences=preferences,
        requests=LessonRequests(
            repositories.jobs, repositories.lessons, preferences, lessons_per_day=limit
        ),
        reading=ReadingService(repositories.lessons, preferences),
        library=LibraryService(repositories.lessons),
        today=TodayService(
            repositories.jobs,
            repositories.lessons,
            repositories.status,
            preferences,
            lessons_per_day=limit,
        ),
        progress=ProgressService(repositories.lessons, preferences),
        activity=ActivityService(repositories.activity, preferences),
        export=create_export(repositories, preferences, database),
    )


def create_generator(settings: Settings) -> LessonGenerator:
    if settings.generator == "claude":
        raise ConfigurationError(
            "ATARAXIA_GENERATOR=claude arrives in L04; use ATARAXIA_GENERATOR=fake for now"
        )
    return FakeLessonGenerator()


@dataclass(frozen=True)
class WorkerServices:
    database: Database
    worker: LessonWorker
    status: WorkerStatusRepository


def create_worker(
    settings: Settings,
    *,
    clock: Clock | None = None,
    generator: LessonGenerator | None = None,
    illustrations: IllustrationResolver | None = None,
    rng: random.Random | None = None,
) -> WorkerServices:
    """Raises `ConfigurationError` for settings the worker cannot run with."""
    clock = clock or SystemClock()
    database = create_database(settings)
    repositories = Repositories.on(database)
    preferences = create_preferences(repositories, settings, clock)
    worker = LessonWorker(
        repositories.jobs,
        repositories.lessons,
        repositories.status,
        preferences,
        generator or create_generator(settings),
        illustrations or NoIllustrations(),
        rng or random.Random(),
        lessons_per_day=settings.max_lessons_per_day,
    )
    return WorkerServices(database=database, worker=worker, status=repositories.status)


@dataclass(frozen=True)
class ToolServices:
    database: Database
    progress: ProgressService
    export: ExportService


def create_tools(settings: Settings, *, clock: Clock | None = None) -> ToolServices:
    clock = clock or SystemClock()
    database = create_database(settings)
    repositories = Repositories.on(database)
    preferences = create_preferences(repositories, settings, clock)
    return ToolServices(
        database=database,
        progress=ProgressService(repositories.lessons, preferences),
        export=create_export(repositories, preferences, database),
    )
