"""Browsing stored lessons."""

import base64
import binascii
import json
from datetime import datetime

from ataraxia.adapters.sqlite.lessons import Cursor, LessonRepository
from ataraxia.application.errors import NotFoundError
from ataraxia.application.views import Lesson, LessonPage
from ataraxia.domain.errors import InvalidInputError
from ataraxia.domain.subjects import SubjectId


class LibraryService:
    def __init__(self, lessons: LessonRepository) -> None:
        self._lessons = lessons

    def get(self, lesson_id: str) -> Lesson:
        lesson = self._lessons.get(lesson_id)
        if lesson is None:
            raise NotFoundError("No such lesson.")
        return lesson

    def page(
        self,
        *,
        saved: bool | None = None,
        subject: SubjectId | None = None,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> LessonPage:
        """Newest first. `query` matches title, hook, or tags, ignoring ASCII case."""
        after = None if cursor is None else decode_cursor(cursor)
        found = self._lessons.page(
            saved=saved,
            subject=subject,
            query=query.strip() if query else None,
            after=after,
            limit=limit + 1,
        )
        items = found[:limit]
        more = len(found) > limit
        return LessonPage(
            items=items,
            next_cursor=encode_cursor((items[-1].created_at, items[-1].id)) if more else None,
        )


def encode_cursor(position: Cursor) -> str:
    raw = json.dumps([position[0].isoformat(), position[1]]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> Cursor:
    """Raises `InvalidInputError` for anything `encode_cursor` did not produce."""
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        created_at, lesson_id = json.loads(raw)
        moment = datetime.fromisoformat(created_at)
        if not isinstance(lesson_id, str) or moment.tzinfo is None:
            raise ValueError("bad cursor")
    except (binascii.Error, ValueError, TypeError) as error:
        raise InvalidInputError("cursor", "This page cursor is not valid.") from error
    return moment, lesson_id
