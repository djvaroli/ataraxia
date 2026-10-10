"""Construct infrastructure shared by the two process entry points."""

from redis.asyncio import Redis

from ataraxia.config import Settings


def create_redis(settings: Settings) -> Redis:
    """Create a lazy client with bounded connection and command waits."""
    return Redis.from_url(
        str(settings.redis_url),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
