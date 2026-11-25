"""The worker records whether Claude is signed in, and the API reports it."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from support import make_world

from ataraxia.adapters.claude_cli import ClaudeCliGenerator, ClaudeCliLogin
from ataraxia.adapters.fake_generator import FakeLessonGenerator
from ataraxia.adapters.wikipedia import WikipediaIllustrations
from ataraxia.application.ports import GenerationError, LoginStatus
from ataraxia.bootstrap import claude_config, create_writer
from ataraxia.config import Settings
from ataraxia.worker.__main__ import LoginChecks

EXPIRES = datetime(2026, 12, 22, 20, 0, tzinfo=UTC)


class Probe:
    def __init__(self, *answers: LoginStatus | None) -> None:
        self.answers = list(answers)
        self.calls = 0

    def status(self) -> LoginStatus | None:
        self.calls += 1
        return self.answers.pop(0)


def test_today_reports_login_state_from_checks_and_calls(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    status = world.workers.status
    assert world.api.today.today().worker.claude_logged_in is None

    status.record_login(world.clock.now(), LoginStatus(logged_in=False))
    assert world.api.today.today().worker.claude_logged_in is False

    status.record_login(world.clock.now(), LoginStatus(logged_in=True, expires_at=EXPIRES))
    worker = world.api.today.today().worker
    assert worker.claude_logged_in is True and worker.login_expires_at == EXPIRES

    world.generator.errors.append(GenerationError("claude_auth", "Not logged in"))
    world.api.requests.request_subject("art")
    world.worker.step()
    assert world.api.today.today().worker.claude_logged_in is False

    world.worker.step()  # a timeout or other failure says nothing about the login
    world.api.requests.request_subject("music")
    world.worker.step()
    assert world.api.today.today().worker.claude_logged_in is True


def test_login_checks_run_at_start_and_then_on_an_interval(tmp_path: Path) -> None:
    world = make_world(tmp_path)
    clock = [0.0]
    probe = Probe(LoginStatus(logged_in=False), None, LoginStatus(logged_in=True))
    checks = LoginChecks(probe, world.workers.status, interval=600, monotonic=lambda: clock[0])

    checks.run_if_due()
    assert probe.calls == 1
    assert world.workers.status.get().logged_in is False
    clock[0] = 599
    checks.run_if_due()
    assert probe.calls == 1
    clock[0] = 600
    checks.run_if_due()  # could not tell: keep the last known state
    assert world.workers.status.get().logged_in is False
    clock[0] = 1200
    checks.run_if_due()
    assert world.workers.status.get().logged_in is True

    LoginChecks(None, world.workers.status).run_if_due()


def test_writer_follows_the_generator_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oat-secret")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/home/app/.claude")
    settings = Settings(database_path=tmp_path / "app.db", generator="claude")
    writer = create_writer(settings)
    assert isinstance(writer.generator, ClaudeCliGenerator)
    assert isinstance(writer.illustrations, WikipediaIllustrations)
    assert isinstance(writer.login, ClaudeCliLogin)
    config = claude_config(settings)
    assert config.oauth_token == "oat-secret"
    assert config.config_dir == "/home/app/.claude"
    assert "oat-secret" not in repr(settings)

    fake = create_writer(Settings(database_path=tmp_path / "app.db", generator="fake"))
    assert isinstance(fake.generator, FakeLessonGenerator) and fake.login is None
