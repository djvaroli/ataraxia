"""Runtime configuration shared by the API and worker."""

from pydantic import RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read explicit Ataraxia environment variables, without ambient cloud setup."""

    model_config = SettingsConfigDict(env_prefix="ATARAXIA_")

    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")
