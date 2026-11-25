"""Runtime configuration shared by the API, worker, and tools."""

from pathlib import Path
from typing import Literal

from pydantic import Field
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
