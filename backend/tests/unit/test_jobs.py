"""Requests, limits, and the worker loop against a temporary database with fakes."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from support import World, count, event_types, make_world, prepare_lesson

from ataraxia.adapters.sqlite import rows
from ataraxia.application.errors import ConflictError, LimitReachedError, NotFoundError
from ataraxia.application.ports import GeneratedLesson, GenerationError, GenerationUsage
from ataraxia.domain.errors import InvalidInputError


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def calls(world: World) -> list[tuple[str, str | None]]:
    with world.api.database.connect() as connection:
        found = connection.execute(
            "SELECT job_id, outcome FROM generation_calls ORDER BY started_at"
        ).fetchall()
    return [(row["job_id"], row["outcome"]) for row in found]


class TestRequests:
    def test_request_creates_a_queued_job_and_one_event(self, world: World) -> None:
        job = world.api.requests.request_topic("how rivers shape borders")
        assert (job.status, job.kind, job.request_text) == ("queued", "topic", job.request_text)
        assert job.request_text == "how rivers shape borders"
        assert job.can_retry is False
        assert event_types(world) == ["lesson.requested"]

    def test_at_most_three_jobs_wait(self, world: World) -> None:
        for _ in range(3):
            world.api.requests.request_surprise()
        with pytest.raises(LimitReachedError) as refused:
            world.api.requests.request_surprise()
        assert refused.value.code == "too_many_waiting"
        assert count(world, "generation_jobs") == 3

    def test_daily_cap_counts_calls_and_queued_jobs(self, tmp_path: Path) -> None:
        world = make_world(tmp_path, max_lessons_per_day=3)
        prepare_lesson(world)
        prepare_lesson(world)
        world.api.requests.request_surprise()
        with pytest.raises(LimitReachedError) as refused:
            world.api.requests.request_surprise()
        assert refused.value.code == "daily_limit"
        allowance = world.api.today.allowance(world.api.preferences.owner_time())
        assert (allowance.used, allowance.remaining, allowance.waiting) == (2, 0, 1)

    def test_login_and_usage_limit_refusals_do_not_count(self, tmp_path: Path) -> None:
        world = make_world(tmp_path, max_lessons_per_day=1)
        world.generator.errors = [GenerationError("claude_auth", "Not logged in")]
        job = world.api.requests.request_surprise()
        world.worker.step()
        assert world.api.requests.get(job.id).status == "failed"
        assert world.api.today.allowance(world.api.preferences.owner_time()).used == 0
        world.api.requests.request_surprise()

    def test_daily_ensure_is_idempotent(self, world: World) -> None:
        first = world.api.requests.ensure_daily()
        second = world.api.requests.ensure_daily()
        assert first.id == second.id
        assert event_types(world) == ["lesson.requested"]

    def test_follow_up_continues_the_thread(self, world: World) -> None:
        parent_id = prepare_lesson(world, "history")
        job = world.api.requests.request_follow_up(parent_id, direction=1, question=None)
        parent = world.api.library.get(parent_id)
        assert job.subject == "history"
        assert job.parent_lesson_id == parent_id
        assert job.request_text == parent.go_deeper[1].title
        world.worker.step()
        child_id = world.api.requests.get(job.id).lesson_id
        assert child_id is not None
        child = world.api.library.get(child_id)
        assert (child.parent_id, child.thread_root_id, child.part) == (parent_id, parent_id, 2)
        assert [entry.id for entry in child.thread] == [parent_id, child_id]
        brief = world.generator.briefs[-1]
        assert brief.parent is not None and brief.parent.title == parent.title
        assert brief.direction == parent.go_deeper[1]

    @pytest.mark.parametrize(("direction", "question"), [(None, None), (0, "Why?")])
    def test_follow_up_needs_exactly_one_of_direction_or_question(
        self, world: World, direction: int | None, question: str | None
    ) -> None:
        parent_id = prepare_lesson(world)
        with pytest.raises(InvalidInputError):
            world.api.requests.request_follow_up(parent_id, direction=direction, question=question)

    def test_follow_up_of_a_missing_lesson(self, world: World) -> None:
        with pytest.raises(NotFoundError):
            world.api.requests.request_follow_up("missing", direction=0, question=None)

    def test_only_failed_jobs_can_be_retried(self, world: World) -> None:
        job = world.api.requests.request_surprise()
        with pytest.raises(ConflictError):
            world.api.requests.retry(job.id)
        with pytest.raises(NotFoundError):
            world.api.requests.retry("missing")


class TestWorker:
    def test_success_publishes_lesson_state_job_and_event(self, world: World) -> None:
        job = world.api.requests.request_subject("math")
        assert world.worker.step()
        done = world.api.requests.get(job.id)
        assert done.status == "succeeded" and done.attempts == 1 and done.lesson_id
        lesson = world.api.library.get(done.lesson_id)
        assert lesson.subject == "math" and lesson.part == 1
        assert lesson.thread_root_id == lesson.id
        assert lesson.state.read_seconds == 0
        assert event_types(world) == ["lesson.requested", "lesson.prepared"]
        assert calls(world) == [(job.id, "succeeded")]
        assert world.worker.step() is False

    def test_brief_carries_history_and_taste(self, world: World) -> None:
        liked = prepare_lesson(world, "art")
        world.api.reading.set_rating(liked, 1)
        world.api.requests.request_subject("art")
        world.worker.step()
        brief = world.generator.briefs[-1]
        title = world.api.library.get(liked).title
        assert brief.liked_titles == (title,)
        assert brief.recent_titles_in_subject == (title,)
        assert brief.length == "standard"

    def test_retryable_failure_retries_after_a_delay_then_fails_once(self, world: World) -> None:
        world.generator.errors = [
            GenerationError("claude_error", "boom"),
            GenerationError("claude_timeout", "slow"),
        ]
        job = world.api.requests.request_surprise()
        world.worker.step()
        waiting = world.api.requests.get(job.id)
        assert (waiting.status, waiting.attempts, waiting.error_code) == (
            "queued",
            1,
            "claude_error",
        )
        assert waiting.next_attempt_at == world.clock.now() + timedelta(seconds=30)
        assert world.worker.step() is False
        world.clock.advance(seconds=30)
        world.worker.step()
        failed = world.api.requests.get(job.id)
        assert (failed.status, failed.attempts, failed.error_code) == (
            "failed",
            2,
            "claude_timeout",
        )
        assert failed.can_retry and failed.error_message
        assert event_types(world).count("lesson.failed") == 1

    def test_retry_gives_two_fresh_attempts(self, world: World) -> None:
        world.generator.errors = [GenerationError("claude_auth", "Not logged in")]
        job = world.api.requests.request_surprise()
        world.worker.step()
        failed = world.api.requests.get(job.id)
        assert failed.error_message is not None
        assert "claude auth login" in failed.error_message
        retried = world.api.requests.retry(job.id)
        assert (retried.status, retried.attempts, retried.error_code) == ("queued", 0, None)
        world.worker.step()
        assert world.api.requests.get(job.id).status == "succeeded"
        assert len(calls(world)) == 2

    def test_usage_limit_waits_and_refunds_the_attempt(self, world: World) -> None:
        expiry = world.clock.now() + timedelta(days=300)
        world.generator.errors = [
            GenerationError("claude_usage_limit", "limit", GenerationUsage(login_expires_at=expiry))
        ] * 3
        job = world.api.requests.request_surprise()
        world.worker.step()
        waiting = world.api.requests.get(job.id)
        assert (waiting.status, waiting.attempts) == ("queued", 0)
        assert waiting.next_attempt_at == world.clock.now() + timedelta(minutes=30)
        assert world.api.today.worker(world.api.preferences.owner_time()).login_expires_at == expiry
        world.clock.advance(minutes=30)
        world.worker.step()
        assert world.api.requests.get(job.id).status == "queued"
        world.clock.advance(hours=24)
        world.worker.step()
        assert world.api.requests.get(job.id).error_code == "claude_usage_limit"
        assert world.api.requests.get(job.id).status == "failed"
        assert world.api.today.allowance(world.api.preferences.owner_time()).used == 0
        assert world.workers.status.get().last_error_code == "claude_usage_limit"

    def test_cap_reached_before_the_call_fails_without_calling(self, tmp_path: Path) -> None:
        world = make_world(tmp_path, max_lessons_per_day=1)
        world.api.requests.ensure_daily()
        world.worker.step()  # The daily lesson uses today's only call.
        # A queued job from before the cap was reached (inserted without the API's check).
        with world.api.database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO generation_jobs (id, kind, status, local_date, created_at,
                    queued_at, next_attempt_at)
                VALUES ('late', 'surprise', 'queued', ?, ?, ?, ?)
                """,
                (
                    world.clock.now().date().isoformat(),
                    *[rows.timestamp(world.clock.now())] * 3,
                ),
            )
        assert world.worker.step()
        late = world.api.requests.get("late")
        assert (late.status, late.error_code) == ("failed", "daily_limit")
        assert len(calls(world)) == 1
        assert len(world.generator.briefs) == 1

    def test_wrong_subject_is_invalid_output(self, world: World) -> None:
        def change_subject(generated: GeneratedLesson) -> GeneratedLesson:
            content = generated.content.model_copy(update={"subject": "music"})
            return replace(generated, content=content)

        world.generator.change = change_subject
        job = world.api.requests.request_subject("art")
        world.worker.step()
        assert world.api.requests.get(job.id).error_code == "invalid_output"
        assert count(world, "lessons") == 0

    def test_topic_lessons_may_choose_their_subject(self, world: World) -> None:
        job = world.api.requests.request_topic("why the trolley problem is hard")
        world.worker.step()
        lesson_id = world.api.requests.get(job.id).lesson_id
        assert lesson_id is not None
        assert world.api.library.get(lesson_id).request_text == "why the trolley problem is hard"
        assert world.generator.briefs[0].subject is None

    def test_failed_publication_leaves_nothing_half_written(
        self, world: World, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job = world.api.requests.request_surprise()

        def broken(*_: object) -> None:
            raise RuntimeError("disk full")

        monkeypatch.setattr(rows, "insert_event", broken)
        with pytest.raises(RuntimeError):
            world.worker.step()
        monkeypatch.undo()
        assert count(world, "lessons") == 0
        assert count(world, "lesson_state") == 0
        assert world.api.requests.get(job.id).status == "running"
        # The loop recovers after an error; the job gets its second attempt.
        assert world.worker.recover() == 1
        world.worker.step()
        assert world.api.requests.get(job.id).status == "succeeded"
        assert count(world, "lessons") == 1
        assert calls(world) == [(job.id, "interrupted"), (job.id, "succeeded")]

    def test_recovery_fails_jobs_without_attempts_left(self, world: World) -> None:
        first = world.api.requests.request_surprise()
        second = world.api.requests.request_surprise()
        with world.api.database.transaction() as connection:
            connection.execute(
                "UPDATE generation_jobs SET status = 'running', attempts = 1 WHERE id = ?",
                (first.id,),
            )
            connection.execute(
                "UPDATE generation_jobs SET status = 'running', attempts = 2 WHERE id = ?",
                (second.id,),
            )
        assert world.worker.recover() == 2
        requeued = world.api.requests.get(first.id)
        failed = world.api.requests.get(second.id)
        assert (requeued.status, requeued.error_code) == ("queued", "interrupted")
        assert (failed.status, failed.error_code) == ("failed", "interrupted")
        assert event_types(world).count("lesson.failed") == 1

    def test_morning_lesson_waits_for_the_hour_and_is_created_once(self, world: World) -> None:
        world.api.preferences.update(time_zone="America/Los_Angeles", morning_hour=8)
        # 15:00 UTC is 07:00 in Los Angeles.
        assert world.worker.ensure_morning_lesson() is False
        assert world.api.today.today().daily.status == "waiting"
        world.clock.advance(hours=1)
        assert world.worker.ensure_morning_lesson() is True
        assert world.worker.ensure_morning_lesson() is False
        assert world.api.today.today().daily.status == "queued"
        world.worker.step()
        slot = world.api.today.today().daily
        assert slot.status == "ready" and slot.lesson is not None

    def test_morning_lesson_off(self, world: World) -> None:
        world.api.preferences.update(morning_lesson=False)
        assert world.worker.ensure_morning_lesson() is False
        daily = world.api.today.today().daily
        assert (daily.status, daily.morning_hour) == ("not_scheduled", None)

    def test_unexpected_generator_errors_become_claude_error(self, world: World) -> None:
        def explode(_: GeneratedLesson) -> GeneratedLesson:
            raise KeyError("bug")

        world.generator.change = explode
        job = world.api.requests.request_surprise()
        world.worker.step()
        assert world.api.requests.get(job.id).error_code == "claude_error"
