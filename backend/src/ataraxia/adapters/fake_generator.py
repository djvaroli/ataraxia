"""A deterministic lesson writer for development, tests, and the smoke check.

It returns a plausible sample lesson for any brief, with the Markdown features the
reader must render, so the whole loop runs without Claude. The same brief always
gives the same lesson.
"""

import hashlib
from collections.abc import Sequence

from ataraxia.application.ports import GeneratedLesson, GenerationUsage, LessonBrief
from ataraxia.domain.lessons import (
    Direction,
    FurtherItem,
    GlossaryEntry,
    Illustration,
    IllustrationRequest,
    LessonContent,
)
from ataraxia.domain.subjects import SubjectId, subject

PROMPT_VERSION = "fake-1"
MODEL = "fake"
WORDS_PER_MINUTE = 230

_SAMPLE_TOPICS: dict[SubjectId, tuple[str, ...]] = {
    "art": ("How Vermeer painted light", "The Bauhaus workshop", "Hokusai's Great Wave"),
    "history": ("The Silk Road's middlemen", "Why Rome split in two", "The Hanseatic League"),
    "film": ("Kurosawa's Rashomon", "The long take", "Italian neorealism"),
    "words": ("Words for small pleasures", "Words from the sea", "Words about time"),
    "geography": ("The Strait of Malacca", "Why the Nile matters", "The Arctic's new routes"),
    "science": ("How vaccines teach immunity", "Why the sky is blue", "Plate tectonics"),
    "math": ("Why primes never run out", "The pigeonhole principle", "Euler's formula"),
    "computing": ("How hash tables work", "Binary search", "Why caches are fast"),
    "philosophy": ("The ship of Theseus", "Hume on causation", "The trolley problem"),
    "literature": ("Reading Chekhov's stories", "The sonnet's turn", "Woolf's interior voice"),
    "music": ("How a fugue works", "The blues scale", "Listening to Steve Reich"),
}

_KEYWORDS: tuple[tuple[str, SubjectId], ...] = (
    ("paint", "art"),
    ("film", "film"),
    ("movie", "film"),
    ("word", "words"),
    ("war", "history"),
    ("empire", "history"),
    ("country", "geography"),
    ("river", "geography"),
    ("number", "math"),
    ("proof", "math"),
    ("algorithm", "computing"),
    ("computer", "computing"),
    ("program", "computing"),
    ("poem", "literature"),
    ("novel", "literature"),
    ("music", "music"),
    ("song", "music"),
    ("ethic", "philosophy"),
)


class FakeLessonGenerator:
    """Implements `LessonGenerator` without any external call."""

    def generate(self, brief: LessonBrief) -> GeneratedLesson:
        subject_id = brief.subject or _subject_for_topic(brief.topic or "")
        title = _title(brief, subject_id)
        body = _body(title, subject_id)
        words = len(body.split())
        content = LessonContent(
            subject=subject_id,
            title=title,
            hook=f"A short sample lesson on {title.lower()}, written without Claude so the "
            "app can be tried end to end.",
            reading_minutes=max(2, round(words / WORDS_PER_MINUTE)),
            body_markdown=body,
            key_ideas=[
                f"{title} is easier to follow with one concrete example.",
                "Separate what is documented from what is interpreted.",
                "Return to the idea a day later to keep it.",
            ],
            glossary=[
                GlossaryEntry(term="Sample", definition="A stand-in used to try something."),
                GlossaryEntry(term="Brief", definition="What the writer is asked to cover."),
            ],
            go_deeper=[
                Direction(
                    title="The people involved",
                    description=f"Who shaped {title.lower()} and what they wanted.",
                ),
                Direction(
                    title="A closer look",
                    description="One detail examined slowly, from first principles.",
                ),
                Direction(
                    title="What came next",
                    description="How the idea changed and where it shows up today.",
                ),
            ],
            further=[
                FurtherItem(title=f"An introduction to {title}", kind="book", creator="Various"),
                FurtherItem(title=subject(subject_id).label, kind="article"),
            ],
            illustrations=[
                IllustrationRequest(wikipedia_title=title, caption=f"Illustration for {title}")
            ],
            tags=[subject_id, "sample"],
        )
        return GeneratedLesson(
            content=content,
            usage=GenerationUsage(model=MODEL, duration_ms=0, input_tokens=0, output_tokens=0),
            prompt_version=PROMPT_VERSION,
        )


class NoIllustrations:
    """Implements `IllustrationResolver` by never finding an image."""

    def resolve(self, requests: Sequence[IllustrationRequest]) -> list[Illustration]:
        return []


def _subject_for_topic(topic: str) -> SubjectId:
    lowered = topic.lower()
    for keyword, subject_id in _KEYWORDS:
        if keyword in lowered:
            return subject_id
    return "science"


def _title(brief: LessonBrief, subject_id: SubjectId) -> str:
    if brief.parent is not None:
        step = brief.direction.title if brief.direction else (brief.question or "Further")
        return _clip(f"{brief.parent.title}: {step}")
    if brief.topic:
        return _clip(brief.topic[:1].upper() + brief.topic[1:])
    seen = set(brief.recent_titles_in_subject) | set(brief.recent_titles)
    topics = _SAMPLE_TOPICS[subject_id]
    start = int(hashlib.sha256(brief.local_date.isoformat().encode()).hexdigest(), 16)
    for offset in range(len(topics)):
        candidate = topics[(start + offset) % len(topics)]
        if candidate not in seen:
            return candidate
    return f"{topics[start % len(topics)]}, again"


def _clip(text: str) -> str:
    text = " ".join(text.split())
    if len(text) < 3:
        text = f"On {text}"
    return text if len(text) <= 120 else text[:117].rstrip() + "..."


def _body(title: str, subject_id: SubjectId) -> str:
    sections = [
        f"## Where {title.lower()} begins",
        "Every good lesson starts with something concrete. Picture a specific place, a "
        "specific person, or a specific object, and ask what is going on in it. This "
        "sample lesson stands in for one Claude would write, so the reader, the Library, "
        "and the activity record can be tried before the real writer is connected.",
        "## Three things to notice",
        "- What happened, in what order, and who was there.\n"
        "- What the evidence is, and how sure we can be about it.\n"
        "- Why it still matters, and where it shows up today.",
        "> A lesson is reading material, not a reference. When a claim looks wrong, flag "
        "it so it can be checked later.",
        "## A closer look",
        "The details are where understanding forms. A date, a measurement, a line of "
        "dialogue, or a brushstroke can carry more than a page of summary, because it "
        "gives the mind something to hold on to. Slow down here and look at one detail "
        "from several sides before moving on.",
    ]
    if subject_id == "math":
        sections += [
            "## A worked example",
            "The sum of the first $n$ odd numbers is a perfect square:",
            "$$1 + 3 + 5 + \\dots + (2n - 1) = n^2$$",
            "Check it for $n = 4$: $1 + 3 + 5 + 7 = 16 = 4^2$.",
        ]
    if subject_id == "computing":
        sections += [
            "## In code",
            "```python\n"
            "def binary_search(items: list[int], target: int) -> int:\n"
            "    low, high = 0, len(items) - 1\n"
            "    while low <= high:\n"
            "        middle = (low + high) // 2\n"
            "        if items[middle] == target:\n"
            "            return middle\n"
            "        if items[middle] < target:\n"
            "            low = middle + 1\n"
            "        else:\n"
            "            high = middle - 1\n"
            "    return -1\n"
            "```",
        ]
    sections += [
        "## What to take away",
        "Ideas stick when they are connected to something you already know. Before "
        "closing this lesson, think of one place where you have met this idea before, "
        "and one question you would like answered next. The Go deeper suggestions below "
        "are a place to start.",
    ]
    return "\n\n".join(sections)
