"""HTTP application factory and infrastructure health endpoints."""

import logging
import sqlite3
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Request, Response
from pydantic import BaseModel

from ataraxia.adapters.sqlite.database import Database
from ataraxia.adapters.sqlite.migrations import SCHEMA_VERSION, migrate, schema_version
from ataraxia.api import routes
from ataraxia.api.errors import install_error_handlers
from ataraxia.bootstrap import ApiServices, create_api_services
from ataraxia.config import Settings

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Public health status without connection details or credentials."""

    status: Literal["ok", "unavailable"]


def get_database(request: Request) -> Database:
    return routes.get_services(request).database


def from_environment() -> ApiServices:
    return create_api_services(Settings())


def create_app(build: Callable[[], ApiServices] = from_environment) -> FastAPI:
    """Build the API. Settings are read, checked, and the database migrated at
    startup, not here, so the OpenAPI schema can be exported without configuration."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        services = build()
        migrate(services.database)
        if services.owner.mode == "local":
            logger.warning(
                "Local mode: no sign-in; only requests to localhost from this machine are served"
            )
        app.state.services = services
        yield

    app = FastAPI(
        title="Ataraxia API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    install_error_handlers(app)

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
