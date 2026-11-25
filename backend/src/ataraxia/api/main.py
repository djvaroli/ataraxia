"""HTTP application factory and infrastructure health endpoints."""

import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal, cast

from fastapi import Depends, FastAPI, Request, Response
from pydantic import BaseModel

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import SCHEMA_VERSION, migrate, schema_version
from ataraxia.api import routes
from ataraxia.bootstrap import create_database
from ataraxia.config import Settings

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Public health status without connection details or credentials."""

    status: Literal["ok", "unavailable"]


def get_database(request: Request) -> Database:
    """Obtain the process database; tests can override this dependency."""
    return cast(Database, request.app.state.database)


def create_app(database: Database | None = None) -> FastAPI:
    """Build the API; the database is opened and migrated at startup, not import."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.database = database or create_database(Settings())
        migrate(app.state.database)
        yield

    app = FastAPI(
        title="Ataraxia API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/api/health/live", response_model=HealthStatus)
    def live() -> HealthStatus:
        return HealthStatus(status="ok")

    @app.get(
        "/api/health/ready", response_model=HealthStatus, responses={503: {"model": HealthStatus}}
    )
    def ready(
        response: Response, database: Annotated[Database, Depends(get_database)]
    ) -> HealthStatus:
        try:
            current = schema_version(database)
        except sqlite3.Error:
            logger.warning("Readiness check could not read the database")
            current = -1
        if current != SCHEMA_VERSION:
            response.status_code = 503
            return HealthStatus(status="unavailable")
        return HealthStatus(status="ok")

    app.include_router(routes.public)
    app.include_router(routes.router)
    return app


app = create_app()
