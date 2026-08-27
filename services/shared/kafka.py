"""Async Kafka producer and consumer base classes.

Implements production patterns:
- Exponential backoff retry on publish failures
- Dead-letter queue (DLQ) for permanently failed messages
- Graceful consumer shutdown with signal handling
- Idempotent consumer support via event IDs
"""

from __future__ import annotations

import asyncio
import json
import signal
from abc import ABC, abstractmethod
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from services.shared.config import get_settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Producer
# ---------------------------------------------------------------------------

class KafkaProducer:
    """Async Kafka producer with retry and structured logging."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            max_in_flight_requests_per_connection=5,
        )
        await self._producer.start()
        logger.info("kafka_producer_started", servers=self._settings.kafka.bootstrap_servers)

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("kafka_producer_stopped")

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def publish(
        self,
        topic: str,
        value: dict[str, Any],
        key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Publish an event to Kafka with automatic retry.

        Args:
            topic: Kafka topic name.
            value: Event payload (will be JSON-serialized).
            key: Optional partition key for ordering guarantees.
            headers: Optional message headers.
        """
        if not self._producer:
            raise RuntimeError("KafkaProducer not started — call start() first")

        kafka_headers = [(k, v.encode("utf-8")) for k, v in (headers or {}).items()]

        await self._producer.send_and_wait(
            topic=topic,
            value=value,
            key=key,
            headers=kafka_headers if kafka_headers else None,
        )
        logger.info(
            "event_published",
            topic=topic,
            key=key,
            event_type=value.get("event_type", "unknown"),
        )


# ---------------------------------------------------------------------------
# Consumer Base Class
# ---------------------------------------------------------------------------

class KafkaConsumer(ABC):
    """Base class for Kafka event consumers.

    Subclasses must implement `handle_message`. The base class provides:
    - Graceful shutdown via signal handlers
    - Dead-letter queue routing for failed messages
    - Idempotency tracking via event IDs
    - Automatic offset commits after successful processing
    """

    def __init__(
        self,
        topics: list[str],
        consumer_group: str | None = None,
    ) -> None:
        self._settings = get_settings()
        self._topics = topics
        self._consumer_group = consumer_group or self._settings.kafka.consumer_group
        self._consumer: AIOKafkaConsumer | None = None
        self._producer: AIOKafkaProducer | None = None
        self._running = False
        self._processed_ids: set[str] = set()
        self._max_processed_cache = 10_000

    async def start(self) -> None:
        """Start the consumer and producer (for DLQ publishing)."""
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._settings.kafka.bootstrap_servers,
            group_id=self._consumer_group,
            auto_offset_reset=self._settings.kafka.auto_offset_reset,
            enable_auto_commit=self._settings.kafka.enable_auto_commit,
            session_timeout_ms=self._settings.kafka.session_timeout_ms,
            heartbeat_interval_ms=self._settings.kafka.heartbeat_interval_ms,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.kafka.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",
        )
        await self._consumer.start()
        await self._producer.start()
        self._running = True

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        logger.info(
            "kafka_consumer_started",
            topics=self._topics,
            group=self._consumer_group,
        )

    async def stop(self) -> None:
        """Gracefully stop the consumer."""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()
        logger.info("kafka_consumer_stopped", topics=self._topics)

    async def run(self) -> None:
        """Main consumer loop — poll and process messages."""
        if not self._consumer:
            raise RuntimeError("KafkaConsumer not started — call start() first")

        while self._running:
            try:
                async for msg in self._consumer:
                    if not self._running:
                        break

                    event_id = msg.headers[0][1].decode("utf-8") if msg.headers else None

                    # Idempotency check
                    if event_id and event_id in self._processed_ids:
                        logger.debug("duplicate_event_skipped", event_id=event_id)
                        await self._consumer.commit()
                        continue

                    try:
                        await self.handle_message(
                            topic=msg.topic,
                            key=msg.key.decode("utf-8") if msg.key else None,
                            value=msg.value,
                            headers={
                                h[0]: h[1].decode("utf-8") for h in (msg.headers or [])
                            },
                        )

                        # Track processed ID
                        if event_id:
                            self._processed_ids.add(event_id)
                            if len(self._processed_ids) > self._max_processed_cache:
                                # Evict oldest half
                                to_remove = list(self._processed_ids)[: self._max_processed_cache // 2]
                                for item in to_remove:
                                    self._processed_ids.discard(item)

                        await self._consumer.commit()

                    except Exception as exc:
                        logger.error(
                            "message_processing_failed",
                            topic=msg.topic,
                            event_id=event_id,
                            error=str(exc),
                        )
                        await self._send_to_dlq(msg, str(exc))
                        await self._consumer.commit()

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("consumer_loop_error", error=str(exc))
                await asyncio.sleep(1)

    @abstractmethod
    async def handle_message(
        self,
        topic: str,
        key: str | None,
        value: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        """Process a single message. Must raise on failure (for DLQ routing)."""
        ...

    async def _send_to_dlq(self, original_msg: Any, error: str) -> None:
        """Route a failed message to the dead-letter queue."""
        dlq_topic = f"{original_msg.topic}.dlq"
        try:
            await self._producer.send_and_wait(
                topic=dlq_topic,
                value=original_msg.value,
                key=original_msg.key,
                headers=[
                    ("original_topic", original_msg.topic.encode("utf-8")),
                    ("error", error.encode("utf-8")),
                    ("event_id", (original_msg.headers[0][1] if original_msg.headers else b"none")),
                ],
            )
            logger.warning("message_sent_to_dlq", original_topic=original_msg.topic, dlq_topic=dlq_topic)
        except Exception as exc:
            logger.error("dlq_publish_failed", error=str(exc))
