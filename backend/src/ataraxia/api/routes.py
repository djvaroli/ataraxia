"""Application routes under /api/v1.

Every route except `client-config` depends on `require_owner`. Handlers translate
HTTP to use-case calls; errors become `ErrorBody` responses in `api.errors`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ataraxia.api.auth import authenticate
from ataraxia.api.schemas import (
    ClientConfig,
    ClientEvent,
    ErrorBody,
    FinishedUpdate,
    FlagUpdate,
    FollowUpRequest,
    LessonRequest,
    Me,
    PreferencesUpdate,
    RatingUpdate,
    ReadingReport,
    SavedUpdate,
    SubjectInfo,
    SubjectRequest,
    SurpriseRequest,
)
from ataraxia.application.views import (
    ActivityPage,
    DailySlot,
    ExportDocument,
    Job,
    Lesson,
    LessonPage,
    LessonState,
    Progress,
    Today,
)
from ataraxia.bootstrap import ApiServices
from ataraxia.domain.subjects import SUBJECTS, SubjectId

bearer = HTTPBearer(auto_error=False)

ERRORS: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorBody},
    403: {"model": ErrorBody},
    422: {"model": ErrorBody},
}
NOT_FOUND: dict[int | str, dict[str, object]] = {404: {"model": ErrorBody}}


def get_services(request: Request) -> ApiServices:
    """The services built at startup by the app's lifespan."""
    services = request.app.state.services
    if not isinstance(services, ApiServices):
        raise RuntimeError("The API started without its services")
    return services


Services = Annotated[ApiServices, Depends(get_services)]


def require_owner(
    request: Request,
    services: Services,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    """Return the owner's UID or raise 401/403."""
    token = None if credentials is None else credentials.credentials
    return authenticate(services.owner, request.headers, token)


public = APIRouter(prefix="/api/v1")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_owner)], responses=ERRORS)


@public.get("/client-config", response_model=ClientConfig)
def client_config(services: Services) -> ClientConfig:
    return services.client_config


def _me(services: ApiServices) -> Me:
    return Me(
        auth_mode=services.owner.mode,
        preferences=services.preferences.get(),
        catalog=[
            SubjectInfo(id=entry.id, label=entry.label, description=entry.description)
            for entry in SUBJECTS
        ],
        lessons_per_day=services.lessons_per_day,
    )


@router.get("/me", response_model=Me)
def get_me(services: Services) -> Me:
    return _me(services)


@router.patch("/me", response_model=Me)
def update_me(update: PreferencesUpdate, services: Services) -> Me:
    services.preferences.update(
        time_zone=update.time_zone,
        subjects=update.subjects,
        lesson_length=update.lesson_length,
        morning_lesson=update.morning_lesson,
        morning_hour=update.morning_hour,
    )
    return _me(services)


@router.get("/today", response_model=Today)
def get_today(services: Services) -> Today:
    return services.today.today()


@router.post(
    "/today/lesson",
    response_model=DailySlot,
    status_code=status.HTTP_202_ACCEPTED,
    responses={429: {"model": ErrorBody}},
)
def ensure_daily_lesson(services: Services) -> DailySlot:
    """Queue today's daily lesson unless it exists or is already queued."""
    services.requests.ensure_daily()
    return services.today.daily_slot()


@router.post(
    "/lessons/requests",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    responses={429: {"model": ErrorBody}},
)
def request_lesson(request: LessonRequest, services: Services) -> Job:
    if isinstance(request, SurpriseRequest):
        return services.requests.request_surprise()
    if isinstance(request, SubjectRequest):
        return services.requests.request_subject(request.subject)
    return services.requests.request_topic(request.topic)


@router.get("/lessons", response_model=LessonPage)
def list_lessons(
    services: Services,
    saved: bool | None = None,
    subject: SubjectId | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> LessonPage:
    return services.library.page(saved=saved, subject=subject, query=q, cursor=cursor, limit=limit)


@router.get("/lessons/{lesson_id}", response_model=Lesson, responses=NOT_FOUND)
def get_lesson(lesson_id: str, services: Services) -> Lesson:
    return services.library.get(lesson_id)


@router.post(
    "/lessons/{lesson_id}/follow-ups",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorBody}, 429: {"model": ErrorBody}},
)
def request_follow_up(lesson_id: str, request: FollowUpRequest, services: Services) -> Job:
    return services.requests.request_follow_up(
        lesson_id, direction=request.direction, question=request.question
    )


@router.put("/lessons/{lesson_id}/saved", response_model=LessonState, responses=NOT_FOUND)
def set_saved(lesson_id: str, update: SavedUpdate, services: Services) -> LessonState:
    return services.reading.set_saved(lesson_id, update.saved)


@router.put("/lessons/{lesson_id}/rating", response_model=LessonState, responses=NOT_FOUND)
def set_rating(lesson_id: str, update: RatingUpdate, services: Services) -> LessonState:
    return services.reading.set_rating(lesson_id, update.rating)


@router.put("/lessons/{lesson_id}/finished", response_model=LessonState, responses=NOT_FOUND)
def set_finished(lesson_id: str, update: FinishedUpdate, services: Services) -> LessonState:
    return services.reading.set_finished(lesson_id, update.finished)


@router.put("/lessons/{lesson_id}/flag", response_model=LessonState, responses=NOT_FOUND)
def set_flag(lesson_id: str, update: FlagUpdate, services: Services) -> LessonState:
    return services.reading.flag(lesson_id, update.note)


@router.post("/lessons/{lesson_id}/opened", response_model=LessonState, responses=NOT_FOUND)
def record_opened(lesson_id: str, services: Services) -> LessonState:
    return services.reading.record_open(lesson_id)


@router.post(
    "/lessons/{lesson_id}/reading",
    response_model=LessonState,
    responses={404: {"model": ErrorBody}, 409: {"model": ErrorBody}},
)
def record_reading(lesson_id: str, report: ReadingReport, services: Services) -> LessonState:
    """409 when the session ID was already used for another lesson."""
    return services.reading.record_reading(
        lesson_id, report.session_id, report.seconds, report.scroll
    )


@router.get("/jobs/{job_id}", response_model=Job, responses=NOT_FOUND)
def get_job(job_id: str, services: Services) -> Job:
    return services.requests.get(job_id)


@router.post(
    "/jobs/{job_id}/retry",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorBody}, 409: {"model": ErrorBody}, 429: {"model": ErrorBody}},
)
def retry_job(job_id: str, services: Services) -> Job:
    return services.requests.retry(job_id)


@router.get("/progress", response_model=Progress)
def get_progress(services: Services) -> Progress:
    return services.progress.progress()


@router.post("/activity", status_code=status.HTTP_204_NO_CONTENT)
def record_client_event(event: ClientEvent, services: Services) -> None:
    services.activity.record(event.type)


@router.get("/activity", response_model=ActivityPage)
def list_activity(
    services: Services,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> ActivityPage:
    return services.activity.page(cursor, limit)


@router.get("/export", response_model=ExportDocument)
def export(services: Services) -> ExportDocument:
    return services.export.export()
