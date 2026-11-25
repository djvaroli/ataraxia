"""Construct infrastructure shared by the two process entry points."""

from ataraxia.adapters.sqlite.database import Database
from ataraxia.config import Settings


def create_database(settings: Settings) -> Database:
    """Point at the configured SQLite file; nothing is opened until first use."""
    return Database(settings.database_path)
