"""The subject catalog: what lessons can be about and how each should be written."""

from dataclasses import dataclass
from typing import Literal, get_args

SubjectId = Literal[
    "art",
    "history",
    "film",
    "words",
    "geography",
    "science",
    "math",
    "computing",
    "philosophy",
    "literature",
    "music",
]
SUBJECT_IDS: tuple[SubjectId, ...] = get_args(SubjectId)


@dataclass(frozen=True)
class Subject:
    """A catalog entry. `guidance` is added to the writing prompt for this subject."""

    id: SubjectId
    label: str
    description: str
    guidance: str


SUBJECTS: tuple[Subject, ...] = (
    Subject(
        "art",
        "Art",
        "Paintings, sculpture, architecture, photography, and the people who made them",
        "Anchor the lesson in specific works: say what is actually in them and how to look "
        "at them, then why they mattered. Label interpretation as interpretation. Range "
        "across periods, regions, and media rather than defaulting to famous European "
        "painting. Request illustrations of the key works.",
    ),
    Subject(
        "history",
        "History",
        "Events, people, and turning points, and why they unfolded as they did",
        "Tell it as a story with real people, places, and dates, then step back to causes "
        "and consequences. Separate what is documented from what historians debate, and "
        "avoid single-cause explanations. Range across regions and eras.",
    ),
    Subject(
        "film",
        "Film",
        "Notable films and filmmakers, craft, and film history",
        "Usually center one notable film or filmmaker: context, what it does with "
        "image, sound, performance, and editing, and its influence. Do not reveal plot "
        "beyond the first act unless a clearly marked spoiler section comes first. Say what "
        "to watch for on a first viewing.",
    ),
    Subject(
        "words",
        "Words",
        "Useful, precise, or beautiful words and where they come from",
        "Teach a themed set of 5 to 8 words worth using in speech or writing. For each: "
        "pronunciation in plain respelling, part of speech, a precise definition, origin, "
        "register (formal, literary, everyday), and two natural example sentences. Put "
        "every taught word in the glossary. Prefer words an educated adult half-knows "
        "over obscure curiosities.",
    ),
    Subject(
        "geography",
        "Geography & geopolitics",
        "Places, landscapes, borders, resources, and how they shape power",
        "Make the place concrete: physical setting, people, economy, then the forces "
        "acting on it. For current geopolitics, describe the positions of the main actors "
        "fairly, separate facts from contested claims, and note that the situation may "
        "have changed since your knowledge was current.",
    ),
    Subject(
        "science",
        "Science",
        "Physics, biology, chemistry, earth and space, the mind and body",
        "Explain mechanisms, not just findings: what happens and how we know. Say what "
        "kind of evidence supports each claim (experiment, observation, model, consensus "
        "review) and where knowledge is uncertain or still debated. Use everyday analogies, "
        "then say where they break down.",
    ),
    Subject(
        "math",
        "Mathematics",
        "Ideas, proofs, and the intuition behind them",
        "Build intuition before notation. Include at least one worked example the reader "
        "can follow step by step. Use LaTeX math with $...$ inline and $$...$$ for display. "
        "Show why a result is true, not only that it is, and where it is used.",
    ),
    Subject(
        "computing",
        "Computer science",
        "Algorithms, systems, programming ideas, and computing history",
        "Explain the idea from first principles with a concrete example, and include a "
        "short code or pseudo-code block when it helps. Cover trade-offs and where the "
        "idea shows up in real systems. Assume a technically literate reader who may not "
        "know this area.",
    ),
    Subject(
        "philosophy",
        "Philosophy",
        "Big questions, arguments, and the thinkers behind them",
        "Present one question or idea through its strongest arguments and objections, in "
        "plain language, with concrete thought experiments. Attribute views accurately and "
        "keep the reader's own judgment open.",
    ),
    Subject(
        "literature",
        "Literature",
        "Novels, poems, plays, and the writers who made them",
        "Center a work, writer, or form. Quote only short public-domain passages, or "
        "paraphrase. Explain what makes the writing work, its context, and how to approach "
        "reading it. Avoid revealing endings unless marked.",
    ),
    Subject(
        "music",
        "Music",
        "Composers, genres, instruments, and how music works",
        "Describe sound concretely so the reader knows what to listen for, and name "
        "specific recordings or pieces to try. Cover the music's context and influence. "
        "Explain theory only as far as it helps listening.",
    ),
)

_BY_ID = {subject.id: subject for subject in SUBJECTS}


def subject(subject_id: SubjectId) -> Subject:
    """Look up a catalog entry; every `SubjectId` has one."""
    return _BY_ID[subject_id]
