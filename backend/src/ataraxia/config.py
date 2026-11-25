"""Runtime configuration shared by the API and worker."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read explicit Ataraxia environment variables, without ambient cloud setup."""

    model_config = SettingsConfigDict(env_prefix="ATARAXIA_")

    database_path: Path = Path("data/ataraxia.db")
