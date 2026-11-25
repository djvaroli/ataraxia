"""Pure rules: subject weighting, streaks, failure handling, settings, fake content."""

import random
from collections import Counter
from datetime import UTC, date, datetime, timedelta

import pytest

from ataraxia.adapters.fake_generator import FakeLessonGenerator
from ataraxia.application.ports import LessonBrief, ParentLesson
from ataraxia.domain.calendar import local_date
from ataraxia.domain.choice import choose_subject, subject_weights
from ataraxia.domain.errors import InvalidInputError
from ataraxia.domain.jobs import (
    RETRY_DELAY,
    USAGE_LIMIT_DELAY,
    Fail,
    Requeue,
    after_failure,
)
from ataraxia.domain.lessons import Direction, LessonContent
from ataraxia.domain.preferences import catalog_ordered, check_time_zone, default_preferences
from ataraxia.domain.progress import streaks
from ataraxia.domain.subjects import SUBJECT_IDS, SubjectId

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=UTC)


class TestSubjectChoice:
    def test_weights_follow_ratings_and_recent_subjects(self) -> None:
        weights = subject_weights(
            ["art", "history", "film", "words"],
            ["film", "words", "art"],
            [("art", 1), ("art", 1), ("history", -1), ("words", 1)],
        )
        # art: 1 + 0.25 * 2 = 1.5, not among the last two lessons.
        # history: 1 - 0.25 = 0.75.
        # film: 1.0, but used by one of the last two lessons.
        # words: 1.25, also recent.
        assert weights == pytest.approx([1.5, 0.75, 0.15, 1.25 * 0.15])

    def test_rating_factor_is_clamped(self) -> None:
        many_likes: list[tuple[SubjectId, int]] = [("art", 1)] * 10
        many_dislikes: list[tuple[SubjectId, int]] = [("history", -1)] * 10
        assert subject_weights(["art", "history"], [], many_likes + many_dislikes) == [2.0, 0.4]

    def test_choice_is_reproducible_and_avoids_recent_subjects(self) -> None:
        enabled = list(SUBJECT_IDS)
        first = [choose_subject(enabled, [], [], random.Random(3)) for _ in range(5)]
        second = [choose_subject(enabled, [], [], random.Random(3)) for _ in range(5)]
        assert first == second
        rng = random.Random(11)
        picks = Counter(choose_subject(["art", "history"], ["art"], [], rng) for _ in range(2000))
        # Expected share of art: 0.15 / 1.15, about 13 percent.
        assert 150 < picks["art"] < 380

    def test_choice_needs_an_enabled_subject(self) -> None:
        with pytest.raises(ValueError):
            choose_subject([], [], [], random.Random(1))


class TestStreaks:
    def test_current_streak_may_end_yesterday(self) -> None:
        today = date(2026, 11, 24)
        days = [today - timedelta(days=offset) for offset in (1, 2, 3)]
        assert streaks(days, today).current == 3
        assert streaks([*days, today], today).current == 4

    def test_gap_breaks_the_current_streak_but_not_the_longest(self) -> None:
        today = date(2026, 11, 24)
        days = [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 22)]
        result = streaks(days, today)
        assert result.current == 0
        assert result.longest == 3

    def test_empty_history(self) -> None:
        result = streaks([], date(2026, 11, 24))
        assert (result.current, result.longest) == (0, 0)

    def test_local_date_follows_the_owner_zone(self) -> None:
        # 07:30 UTC on the 25th is still the evening of the 24th in Los Angeles.
        moment = datetime(2026, 11, 25, 7, 30, tzinfo=UTC)
        assert local_date(moment, "America/Los_Angeles") == date(2026, 11, 24)
        assert local_date(moment, "Asia/Tokyo") == date(2026, 11, 25)


class TestFailures:
    def test_retryable_error_requeues_once(self) -> None:
        assert after_failure("claude_error", 1, NOW, NOW) == Requeue(NOW + RETRY_DELAY)
        assert after_failure("claude_timeout", 2, NOW, NOW) == Fail()

    def test_final_errors_fail_at_once(self) -> None:
        assert after_failure("claude_auth", 1, NOW, NOW) == Fail()
        assert after_failure("daily_limit", 1, NOW, NOW) == Fail()

    def test_usage_limit_waits_without_using_an_attempt_for_a_day(self) -> None:
        later = NOW + timedelta(hours=23)
        assert after_failure("claude_usage_limit", 2, NOW, later) == Requeue(
            later + USAGE_LIMIT_DELAY, refund=True
        )
        assert after_failure("claude_usage_limit", 1, NOW, NOW + timedelta(hours=24)) == Fail()


class TestPreferences:
    def test_defaults(self) -> None:
        defaults = default_preferences("UTC")
        assert defaults.subjects == list(SUBJECT_IDS)
        assert defaults.lesson_length == "standard"
        assert (defaults.morning_lesson, defaults.morning_hour) == (True, 6)
        assert not defaults.time_zone_confirmed

    def test_subjects_are_returned_in_catalog_order(self) -> None:
        assert catalog_ordered(["music", "art", "math"]) == ["art", "math", "music"]

    @pytest.mark.parametrize("subjects", [[], ["art", "art"]])
    def test_subjects_must_be_unique_and_present(self, subjects: list[SubjectId]) -> None:
        with pytest.raises(InvalidInputError):
            catalog_ordered(subjects)

    @pytest.mark.parametrize("zone", ["Mars/Base", "", "../etc/passwd", "localtime", "Factory"])
    def test_unknown_time_zones_are_refused(self, zone: str) -> None:
        with pytest.raises(InvalidInputError):
            check_time_zone(zone)

    def test_iana_zone_is_accepted(self) -> None:
        assert check_time_zone("America/Los_Angeles") == "America/Los_Angeles"


class TestFakeGenerator:
    @pytest.mark.parametrize("subject_id", SUBJECT_IDS)
    def test_every_subject_produces_valid_content(self, subject_id: SubjectId) -> None:
        brief = LessonBrief(
            kind="subject",
            local_date=date(2026, 11, 24),
            length="standard",
            subject=subject_id,
        )
        generated = FakeLessonGenerator().generate(brief)
        content = LessonContent.model_validate(generated.content.model_dump())
        assert content.subject == subject_id
        assert "## " in content.body_markdown and "> " in content.body_markdown
        if subject_id == "math":
            assert "$$" in content.body_markdown
        if subject_id == "computing":
            assert "```python" in content.body_markdown

    def test_same_brief_gives_the_same_lesson(self) -> None:
        brief = LessonBrief(
            kind="topic",
            local_date=date(2026, 11, 24),
            length="short",
            subject=None,
            topic="how rivers shape borders",
        )
        first = FakeLessonGenerator().generate(brief)
        assert first == FakeLessonGenerator().generate(brief)
        assert first.content.subject == "geography"

    def test_follow_up_title_names_the_direction(self) -> None:
        brief = LessonBrief(
            kind="follow_up",
            local_date=date(2026, 11, 24),
            length="standard",
            subject="art",
            parent=ParentLesson("The Bauhaus workshop", "art", "Body", ("Idea",)),
            direction=Direction(title="The people", description="Who taught there and why."),
        )
        assert FakeLessonGenerator().generate(brief).content.title == (
            "The Bauhaus workshop: The people"
        )
