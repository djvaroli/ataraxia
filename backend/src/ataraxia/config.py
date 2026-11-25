"""Runtime configuration shared by the API, worker, and tools."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

AuthMode = Literal["firebase", "local"]
GeneratorChoice = Literal["fake", "claude"]


class Settings(BaseSettings):
    """Read explicit Ataraxia environment variables, without ambient cloud setup.

    Empty strings mean "not set", so Compose can pass optional variables through.
    """

    model_config = SettingsConfigDict(env_prefix="ATARAXIA_")

    database_path: Path = Path("data/ataraxia.db")
    auth_mode: AuthMode = "firebase"
    owner_uid: str = ""
    firebase_project_id: str = ""
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_app_id: str = ""
    default_time_zone: str = "UTC"
    max_lessons_per_day: int = Field(default=8, ge=1, le=100)
    generator: GeneratorChoice = "fake"
    claude_executable: str = "/usr/local/bin/claude"
    claude_model: str = "opus"
    claude_timeout_seconds: float = Field(default=600, ge=30, le=1800)
    # Claude Code's own variable names, read without the ATARAXIA_ prefix.
    claude_config_dir: str = Field(default="", validation_alias="CLAUDE_CONFIG_DIR")
    claude_oauth_token: SecretStr = Field(
        default=SecretStr(""), validation_alias="CLAUDE_CODE_OAUTH_TOKEN"
    )
