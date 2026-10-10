"""Infrastructure health endpoints; owner-only application routes follow in A02."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal, cast

from fastapi import Depends, FastAPI, Request, Response
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from ataraxia.bootstrap import create_redis
from ataraxia.config import Settings


class HealthStatus(BaseModel):
    """Public health status without connection details or credentials."""

    status: Literal["ok", "unavailable"]


def get_redis(request: Request) -> Redis:
    """Obtain the process client; tests can override this dependency."""
    return cast(Redis, request.app.state.redis)


def create_app() -> FastAPI:
    """Build the API without connecting to Redis at import time."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with create_redis(Settings()) as redis:
            app.state.redis = redis
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
    async def live() -> HealthStatus:
        return HealthStatus(status="ok")

    @app.get(
        "/api/health/ready", response_model=HealthStatus, responses={503: {"model": HealthStatus}}
    )
    async def ready(
        response: Response, redis: Annotated[Redis, Depends(get_redis)]
    ) -> HealthStatus:
        try:
            async with asyncio.timeout(3):
                await redis.ping()
        except (RedisError, TimeoutError):
            response.status_code = 503
            return HealthStatus(status="unavailable")
        return HealthStatus(status="ok")

    return app


app = create_app()
