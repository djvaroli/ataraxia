"""The export, stats, and backup command line."""

import io
import json
import sqlite3
from pathlib import Path

import pytest
from support import World, make_world, prepare_lesson

from ataraxia.adapters.sqlite.migrations import SCHEMA_VERSION
from ataraxia.tools.__main__ import main


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    world = make_world(tmp_path)
    monkeypatch.setenv("ATARAXIA_DATABASE_PATH", str(world.settings.database_path))
    return world


def test_export_to_stdout_and_file(world: World, tmp_path: Path) -> None:
    lesson_id = prepare_lesson(world)
    out = io.StringIO()
    assert main(["export"], stdout=out) == 0
    document = json.loads(out.getvalue())
    assert [lesson["id"] for lesson in document["lessons"]] == [lesson_id]
    assert document["schema_version"] == SCHEMA_VERSION
    target = tmp_path / "export.json"
    assert main(["export", "--output", str(target)]) == 0
    assert json.loads(target.read_text())["lessons"][0]["id"] == lesson_id


def test_stats(world: World) -> None:
    lesson_id = prepare_lesson(world, "music")
    world.api.reading.set_finished(lesson_id, True)
    out = io.StringIO()
    assert main(["stats"], stdout=out) == 0
    text = out.getvalue()
    assert "Lessons 1, finished 1" in text
    music = next(line for line in text.splitlines() if line.startswith("Music"))
    assert music.split()[1:3] == ["1", "1"]
    assert len([line for line in text.splitlines() if line.startswith("2026-")]) == 14


def test_backup_copies_and_never_overwrites(
    world: World, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lesson_id = prepare_lesson(world)
    target = tmp_path / "backups" / "copy.db"
    assert main(["backup", str(target)]) == 0
    copy = sqlite3.connect(target)
    try:
        assert copy.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        assert copy.execute("SELECT id FROM lessons").fetchone()[0] == lesson_id
    finally:
        copy.close()
    before = target.read_bytes()
    assert main(["backup", str(target)]) == 1
    assert "already exists" in capsys.readouterr().err
    assert target.read_bytes() == before
    assert sorted(path.name for path in target.parent.iterdir()) == ["copy.db"]


def test_missing_database_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATARAXIA_DATABASE_PATH", str(tmp_path / "absent.db"))
    assert main(["stats"]) == 1
    assert not (tmp_path / "absent.db").exists()


def test_help_and_usage_errors() -> None:
    with pytest.raises(SystemExit) as shown:
        main(["--help"])
    assert shown.value.code == 0
    with pytest.raises(SystemExit) as wrong:
        main(["unknown"])
    assert wrong.value.code == 2
