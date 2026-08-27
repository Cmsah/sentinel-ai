"""FastAPI dependency injection.

Provides database sessions, Redis clients, and Kafka producer/consumer
instances as request-scoped dependencies.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from services.shared.database import get_session, get_engine, close_db
from services.shared.redis import get_redis, close_redis
from services.shared.kafka import KafkaProducer


# Re-export the DB session dependency for use in route handlers
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for the request lifetime."""
    async for session in get_session():
        yield session


async def get_kafka_producer() -> AsyncGenerator[KafkaProducer, None]:
    """Yield a Kafka producer for publishing events."""
    from services.shared.config import get_settings
    settings = get_settings()
    # In production, this would be a singleton
    producer = KafkaProducer()
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()
