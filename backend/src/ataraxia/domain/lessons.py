"""Lesson content and the rules it must satisfy before it is stored.

`LessonContent` is what the generator must return; its JSON schema is also given to
Claude as the required output shape. Limits are generous upper bounds that catch
broken output, not style targets; the targets live in the prompt.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ataraxia.domain.subjects import SubjectId

LessonLength = Literal["short", "standard", "long"]
FurtherKind = Literal["book", "film", "artwork", "music", "place", "article", "other"]

# Word-count targets given to the writer, at about 230 words a minute:
# roughly 5, 10-15, and 20 minutes of reading.
WORD_TARGETS: dict[LessonLength, tuple[int, int]] = {
    "short": (1000, 1300),
    "standard": (2300, 3200),
    "long": (4000, 5000),
}


class _Content(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GlossaryEntry(_Content):
    """A term worth keeping and a short definition."""

    term: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    definition: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
    ]


class Direction(_Content):
    """A suggested follow-up the reader can choose under "Go deeper"."""

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=80)]
    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=240)
    ]


class FurtherItem(_Content):
    """A book, film, work, or place to explore; the frontend builds search links."""

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
    creator: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] | None = None
    kind: FurtherKind
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=240)] | None = None


class IllustrationRequest(_Content):
    """An English Wikipedia article whose lead image would help the lesson."""

    wikipedia_title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    caption: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]


class LessonContent(_Content):
    """The complete lesson as written, before illustrations are resolved."""

    subject: SubjectId
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)]
    hook: Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=320)]
    reading_minutes: Annotated[int, Field(ge=2, le=30)]
    body_markdown: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=600, max_length=40000)
    ]
    key_ideas: Annotated[
        list[
            Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
        ],
        Field(min_length=3, max_length=5),
    ]
    glossary: Annotated[list[GlossaryEntry], Field(max_length=12)]
    go_deeper: Annotated[list[Direction], Field(min_length=3, max_length=3)]
    further: Annotated[list[FurtherItem], Field(max_length=5)]
    illustrations: Annotated[list[IllustrationRequest], Field(max_length=3)]
    tags: Annotated[
        list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]],
        Field(min_length=1, max_length=6),
    ]


class Illustration(_Content):
    """A resolved image: URL on upload.wikimedia.org and the article it came from."""

    image_url: str
    page_url: str
    title: str
    caption: str
    width: int | None = None
    height: int | None = None
