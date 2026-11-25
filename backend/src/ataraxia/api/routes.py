"""Application routes under /api/v1. CONTRACT STUBS: bodies are implemented in L03.

Every route except `client-config` depends on `require_owner`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ataraxia.api.schemas import (
    ActivityPage,
    ClientConfig,
    ClientEvent,
    DailySlot,
    ErrorBody,
    ExportDocument,
    FinishedUpdate,
    FlagUpdate,
    FollowUpRequest,
    Job,
    Lesson,
    LessonPage,
    LessonRequest,
    LessonState,
    Me,
    PreferencesUpdate,
    Progress,
    RatingUpdate,
    ReadingReport,
    SavedUpdate,
    Today,
)
from ataraxia.domain.subjects import SubjectId

bearer = HTTPBearer(auto_error=False)

ERRORS: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorBody},
    403: {"model": ErrorBody},
    422: {"model": ErrorBody},
}


def _todo() -> HTTPException:
    return HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "Not implemented")


def require_owner(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    """Return the owner's UID or raise 401/403."""
    raise _todo()


public = APIRouter(prefix="/api/v1")
router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_owner)], responses=ERRORS)


@public.get("/client-config", response_model=ClientConfig)
def client_config() -> ClientConfig:
    raise _todo()


@router.get("/me", response_model=Me)
def get_me() -> Me:
    raise _todo()


@router.patch("/me", response_model=Me)
def update_me(update: PreferencesUpdate) -> Me:
    raise _todo()


@router.get("/today", response_model=Today)
def get_today() -> Today:
    raise _todo()


@router.post(
    "/today/lesson",
    response_model=DailySlot,
    status_code=status.HTTP_202_ACCEPTED,
    responses={429: {"model": ErrorBody}},
)
def ensure_daily_lesson() -> DailySlot:
    """Queue today's daily lesson unless it exists or is already queued."""
    raise _todo()


@router.post(
    "/lessons/requests",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    responses={429: {"model": ErrorBody}},
)
def request_lesson(request: LessonRequest) -> Job:
    raise _todo()


@router.get("/lessons", response_model=LessonPage)
def list_lessons(
    saved: bool | None = None,
    subject: SubjectId | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> LessonPage:
    raise _todo()


@router.get("/lessons/{lesson_id}", response_model=Lesson, responses={404: {"model": ErrorBody}})
def get_lesson(lesson_id: str) -> Lesson:
    raise _todo()


@router.post(
    "/lessons/{lesson_id}/follow-ups",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorBody}, 429: {"model": ErrorBody}},
)
def request_follow_up(lesson_id: str, request: FollowUpRequest) -> Job:
    raise _todo()


@router.put("/lessons/{lesson_id}/saved", response_model=LessonState)
def set_saved(lesson_id: str, update: SavedUpdate) -> LessonState:
    raise _todo()


@router.put("/lessons/{lesson_id}/rating", response_model=LessonState)
def set_rating(lesson_id: str, update: RatingUpdate) -> LessonState:
    raise _todo()


@router.put("/lessons/{lesson_id}/finished", response_model=LessonState)
def set_finished(lesson_id: str, update: FinishedUpdate) -> LessonState:
    raise _todo()


@router.put("/lessons/{lesson_id}/flag", response_model=LessonState)
def set_flag(lesson_id: str, update: FlagUpdate) -> LessonState:
    raise _todo()


@router.post("/lessons/{lesson_id}/opened", response_model=LessonState)
def record_opened(lesson_id: str) -> LessonState:
    raise _todo()


@router.post("/lessons/{lesson_id}/reading", response_model=LessonState)
def record_reading(lesson_id: str, report: ReadingReport) -> LessonState:
    raise _todo()


@router.get("/jobs/{job_id}", response_model=Job, responses={404: {"model": ErrorBody}})
def get_job(job_id: str) -> Job:
    raise _todo()


@router.post(
    "/jobs/{job_id}/retry",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorBody}, 409: {"model": ErrorBody}, 429: {"model": ErrorBody}},
)
def retry_job(job_id: str) -> Job:
    raise _todo()


@router.get("/progress", response_model=Progress)
def get_progress() -> Progress:
    raise _todo()


@router.post("/activity", status_code=status.HTTP_204_NO_CONTENT)
def record_client_event(event: ClientEvent) -> None:
    raise _todo()


@router.get("/activity", response_model=ActivityPage)
def list_activity(
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> ActivityPage:
    raise _todo()


@router.get("/export", response_model=ExportDocument)
def export() -> ExportDocument:
    raise _todo()
