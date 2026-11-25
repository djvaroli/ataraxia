"""Weighted choice of the subject for daily and "Surprise me" lessons."""

import random
from collections.abc import Iterable, Sequence

from ataraxia.domain.subjects import SubjectId

RECENT_PENALTY = 0.15
RATING_STEP = 0.25
MIN_RATING_FACTOR = 0.4
MAX_RATING_FACTOR = 2.0


def subject_weights(
    enabled: Sequence[SubjectId],
    recent_subjects: Sequence[SubjectId],
    ratings: Iterable[tuple[SubjectId, int]],
) -> list[float]:
    """Weight each enabled subject, in the order given.

    `recent_subjects` are the subjects of the latest lessons, newest first; only the
    last two count. `ratings` are (subject, rating) pairs from the last 60 days, where
    a rating is -1, 0, or 1.
    """
    net: dict[SubjectId, int] = {}
    for subject_id, rating in ratings:
        net[subject_id] = net.get(subject_id, 0) + rating
    last_two = set(recent_subjects[:2])
    weights = []
    for subject_id in enabled:
        factor = 1 + RATING_STEP * net.get(subject_id, 0)
        weight = min(MAX_RATING_FACTOR, max(MIN_RATING_FACTOR, factor))
        if subject_id in last_two:
            weight *= RECENT_PENALTY
        weights.append(weight)
    return weights


def choose_subject(
    enabled: Sequence[SubjectId],
    recent_subjects: Sequence[SubjectId],
    ratings: Iterable[tuple[SubjectId, int]],
    rng: random.Random,
) -> SubjectId:
    """Pick one enabled subject at random using `subject_weights`."""
    if not enabled:
        raise ValueError("At least one subject must be enabled")
    weights = subject_weights(enabled, recent_subjects, ratings)
    return rng.choices(list(enabled), weights=weights, k=1)[0]
