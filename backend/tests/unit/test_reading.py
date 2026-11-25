"""Reading actions, Library, Progress, settings, and export against temporary storage."""

from datetime import date, timedelta
from pathlib import Path

import pytest
from support import World, count, event_types, make_world, prepare_lesson

from ataraxia.application.errors import ConflictError, NotFoundError
from ataraxia.domain.errors import InvalidInputError

SESSION_A = "00000000-0000-4000-8000-00000000000a"
SESSION_B = "00000000-0000-4000-8000-00000000000b"


@pytest.fixture
def world(tmp_path: Path) -> World:
    return make_world(tmp_path)


def owner_events(world: World) -> list[str]:
    return [
        kind for kind in event_types(world) if kind not in ("lesson.requested", "lesson.prepared")
    ]


class TestLessonActions:
    def test_each_real_change_writes_exactly_one_event(self, world: World) -> None:
        lesson_id = prepare_lesson(world)
        reading = world.api.reading
        reading.set_saved(lesson_id, True)
        reading.set_saved(lesson_id, True)
        reading.set_rating(lesson_id, 1)
        reading.set_rating(lesson_id, 1)
        reading.set_rating(lesson_id, -1)
        reading.set_finished(lesson_id, True)
        reading.set_finished(lesson_id, True)
        reading.set_finished(lesson_id, False)
        reading.flag(lesson_id, "Date looks wrong")
        reading.flag(lesson_id, "Date looks wrong")
        state = reading.set_saved(lesson_id, False)
        assert owner_events(world) == [
            "lesson.saved",
            "lesson.rated",
            "lesson.rated",
            "lesson.finished",
            "lesson.unfinished",
            "lesson.flagged",
            "lesson.unsaved",
        ]
        assert (state.saved, state.saved_at, state.rating, state.finished_at) == (
            False,
            None,
            -1,
            None,
        )
        assert state.flagged

    def test_every_open_is_recorded_but_first_open_is_kept(self, world: World) -> None:
        lesson_id = prepare_lesson(world)
        first = world.api.reading.record_open(lesson_id).first_opened_at
        world.clock.advance(minutes=5)
        assert world.api.reading.record_open(lesson_id).first_opened_at == first
        assert owner_events(world) == ["lesson.opened", "lesson.opened"]

    def test_unknown_lesson(self, world: World) -> None:
        with pytest.raises(NotFoundError):
            world.api.reading.set_saved("missing", True)
        with pytest.raises(NotFoundError):
            world.api.reading.record_reading("missing", SESSION_A, 10, 0.1)
        assert count(world, "activity_events") == 0

    def test_reading_reports_keep_the_largest_values_per_session(self, world: World) -> None:
        lesson_id = prepare_lesson(world)
        reading = world.api.reading
        reading.record_reading(lesson_id, SESSION_A, 30, 0.2)
        reading.record_reading(lesson_id, SESSION_A, 60, 0.5)
        reading.record_reading(lesson_id, SESSION_A, 60, 0.5)
        reading.record_reading(lesson_id, SESSION_A, 30, 0.1)  # Late, smaller report.
        state = reading.record_reading(lesson_id, SESSION_B, 45, 0.4)
        assert (state.read_seconds, state.furthest_scroll) == (105, 0.5)
        assert count(world, "reading_sessions") == 2
        assert owner_events(world) == []

    def test_a_session_belongs_to_one_lesson(self, world: World) -> None:
        first = prepare_lesson(world, "art")
        second = prepare_lesson(world, "music")
        world.api.reading.record_reading(first, SESSION_A, 30, 0.2)
        with pytest.raises(ConflictError):
            world.api.reading.record_reading(second, SESSION_A, 40, 0.3)


class TestLibrary:
    def test_pagination_is_stable_for_equal_timestamps(self, world: World) -> None:
        ids = {prepare_lesson(world) for _ in range(5)}  # The clock does not move.
        seen: list[str] = []
        cursor = None
        while True:
            page = world.api.library.page(cursor=cursor, limit=2)
            seen += [item.id for item in page.items]
            cursor = page.next_cursor
            if cursor is None:
                break
        assert len(seen) == 5 and set(seen) == ids
        assert seen == sorted(seen, reverse=True)

    def test_newest_first_and_filters(self, world: World) -> None:
        art = prepare_lesson(world, "art")
        world.clock.advance(minutes=1)
        music = prepare_lesson(world, "music")
        world.api.reading.set_saved(art, True)
        assert [item.id for item in world.api.library.page().items] == [music, art]
        assert [item.id for item in world.api.library.page(saved=True).items] == [art]
        assert [item.id for item in world.api.library.page(saved=False).items] == [music]
        assert [item.id for item in world.api.library.page(subject="music").items] == [music]

    def test_search_matches_title_hook_and_tags_and_escapes_wildcards(self, world: World) -> None:
        world.api.requests.request_topic("100% of the 1_000 rivers")
        world.worker.step()
        world.api.requests.request_topic("Rivers in general")
        world.worker.step()
        assert len(world.api.library.page(query="RIVERS").items) == 2
        assert len(world.api.library.page(query="100%").items) == 1
        assert len(world.api.library.page(query="1_0").items) == 1
        assert len(world.api.library.page(query="%").items) == 1
        assert len(world.api.library.page(query="sample").items) == 2  # A tag.

    def test_bad_cursor(self, world: World) -> None:
        with pytest.raises(InvalidInputError):
            world.api.library.page(cursor="not-a-cursor")


class TestProgress:
    def test_streaks_use_the_local_date_at_finishing(self, world: World) -> None:
        world.api.preferences.update(time_zone="America/Los_Angeles")
        # 15:00 UTC on 24 November is 07:00 on the 24th in Los Angeles.
        first = prepare_lesson(world)
        world.api.reading.set_finished(first, True)
        # 07:30 UTC on the 26th is still the evening of the 25th in Los Angeles.
        world.clock.advance(hours=40, minutes=30)
        second = prepare_lesson(world)
        world.api.reading.set_finished(second, True)
        world.api.reading.record_reading(second, SESSION_A, 600, 1.0)
        progress = world.api.progress.progress()
        assert (progress.current_streak, progress.longest_streak) == (2, 2)
        assert progress.finished_total == 2 and progress.read_minutes_total == 10
        assert progress.days[-1].date == date(2026, 11, 25)
        assert (progress.days[-1].finished, progress.days[-1].read_minutes) == (1, 10)
        assert len(progress.days) == 84
        art = next(row for row in progress.subjects if row.subject == "art")
        assert (art.lessons, art.finished, art.last_finished_on) == (2, 2, date(2026, 11, 25))
        assert len(progress.subjects) == 11
        # The streak survives until the end of the next local day.
        world.clock.advance(days=1)
        assert world.api.progress.progress().current_streak == 2
        world.clock.advance(days=1)
        assert world.api.progress.progress().current_streak == 0


class TestToday:
    def test_unfinished_and_other_jobs(self, world: World) -> None:
        opened = prepare_lesson(world)
        world.api.reading.record_open(opened)
        finished = prepare_lesson(world)
        world.api.reading.record_open(finished)
        world.api.reading.set_finished(finished, True)
        pending = world.api.requests.request_surprise()
        today = world.api.today.today()
        assert [lesson.id for lesson in today.unfinished] == [opened]
        assert [job.id for job in today.jobs] == [pending.id]
        world.workers.status.heartbeat(world.clock.now() - timedelta(seconds=10))
        assert world.api.today.today().worker.online is True
        world.clock.advance(seconds=21)
        assert world.api.today.today().worker.online is False
        world.clock.advance(days=15)
        assert world.api.today.today().unfinished == []


class TestSettings:
    def test_change_writes_one_event_with_new_values(self, world: World) -> None:
        defaults = world.api.preferences.get()
        assert defaults.time_zone == "UTC" and not defaults.time_zone_confirmed
        updated = world.api.preferences.update(
            time_zone="Europe/Paris", subjects=["music", "art"], morning_hour=7
        )
        assert updated.subjects == ["art", "music"] and updated.time_zone_confirmed
        world.api.preferences.update(morning_hour=7, subjects=["art", "music"])
        export = world.api.export.export()
        assert [event.type for event in export.events] == ["settings.updated"]
        assert export.events[0].data == {
            "time_zone": "Europe/Paris",
            "time_zone_confirmed": True,
            "subjects": ["art", "music"],
            "morning_hour": 7,
        }

    def test_setting_the_same_zone_confirms_it(self, world: World) -> None:
        assert world.api.preferences.update(time_zone="UTC").time_zone_confirmed
        assert event_types(world) == ["settings.updated"]

    def test_invalid_zone(self, world: World) -> None:
        with pytest.raises(InvalidInputError):
            world.api.preferences.update(time_zone="Nowhere/Special")


class TestExport:
    def test_export_contains_every_durable_table(self, world: World) -> None:
        lesson_id = prepare_lesson(world)
        world.api.reading.record_reading(lesson_id, SESSION_A, 30, 0.2)
        world.api.preferences.update(lesson_length="long")
        document = world.api.export.export()
        assert document.schema_version == 2
        assert document.preferences.lesson_length == "long"
        assert [lesson.id for lesson in document.lessons] == [lesson_id]
        assert document.lessons[0].thread[0].id == lesson_id
        assert len(document.jobs) == 1 and len(document.calls) == 1
        assert [session.id for session in document.reading_sessions] == [SESSION_A]
        assert [event.type for event in document.events] == [
            "lesson.requested",
            "lesson.prepared",
            "settings.updated",
        ]
