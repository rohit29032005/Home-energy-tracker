"""Bounded-retry Kafka bridge for anomaly inference.

The worker consumes the existing `energy-usage` topic, calls the local model,
then emits a separate `anomaly-results` event. A message that fails repeatedly
is sent to `anomaly-processing-failures` before the offset is committed. This
prevents an infinite retry loop while keeping the failure observable.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer

from app.main import TelemetryInput, predict_telemetry

LOGGER = logging.getLogger("ml_inference.kafka")


class KafkaInferenceWorker:
    """Legacy topic worker with bounded message retries and broker reconnection."""

    def __init__(self, *, connection_retry_seconds: float | None = None) -> None:
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.max_attempts = int(os.getenv("KAFKA_MAX_PROCESSING_ATTEMPTS", "3"))
        self.connection_retry_seconds = connection_retry_seconds or float(
            os.getenv("KAFKA_CONNECTION_RETRY_SECONDS", "5")
        )
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.connection_retry_seconds <= 0:
            raise ValueError("connection_retry_seconds must be positive")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._consumer: KafkaConsumer | None = None
        self._state_lock = threading.Lock()
        self._connected = False
        self._connection_attempts = 0
        self._last_connection_error: str | None = None

    @property
    def status(self) -> dict[str, object]:
        """Small, non-secret state snapshot for the service health endpoint."""
        with self._state_lock:
            return {
                "running": self._thread is not None and self._thread.is_alive() and not self._stop.is_set(),
                "connected": self._connected,
                "connectionAttempts": self._connection_attempts,
                "lastConnectionError": self._last_connection_error,
            }

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="ml-kafka-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        consumer = self._consumer
        if consumer is not None:
            self._close_consumer(consumer)
        if self._thread is not None:
            self._thread.join(timeout=10)

    def _run(self) -> None:
        while not self._stop.is_set():
            consumer: KafkaConsumer | None = None
            producer: KafkaProducer | None = None
            try:
                consumer, producer = self._connect()
                self._consumer = consumer
                self._set_connected()
                LOGGER.info("Kafka inference worker connected to %s", self.bootstrap_servers)
                self._consume(consumer, producer)
            except Exception as exception:
                self._set_disconnected(exception)
                if not self._stop.is_set():
                    LOGGER.exception(
                        "Kafka inference worker connection failed; retrying in %s seconds",
                        self.connection_retry_seconds,
                    )
            finally:
                if producer is not None:
                    self._close_producer(producer)
                if consumer is not None:
                    self._close_consumer(consumer)
                if self._consumer is consumer:
                    self._consumer = None
                with self._state_lock:
                    self._connected = False
            if not self._stop.is_set():
                self._stop.wait(self.connection_retry_seconds)

    def _connect(self) -> tuple[KafkaConsumer, KafkaProducer]:
        with self._state_lock:
            self._connection_attempts += 1
        consumer = KafkaConsumer(
            "energy-usage",
            bootstrap_servers=self.bootstrap_servers,
            group_id="ml-inference-service",
            enable_auto_commit=False,
            auto_offset_reset="latest",
            value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
            consumer_timeout_ms=1000,
        )
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                retries=3,
                retry_backoff_ms=500,
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            )
        except Exception:
            # A partial connection must not leave a consumer thread/socket open
            # before the outer reconnect loop retries.
            self._close_consumer(consumer)
            raise
        return consumer, producer

    def _consume(self, consumer: KafkaConsumer, producer: KafkaProducer) -> None:
        while not self._stop.is_set():
            for message in consumer:
                if self._stop.is_set():
                    return
                self._process_message(message.value, producer)
                consumer.commit()

    def _set_connected(self) -> None:
        with self._state_lock:
            self._connected = True
            self._last_connection_error = None

    def _set_disconnected(self, exception: Exception) -> None:
        with self._state_lock:
            self._connected = False
            self._last_connection_error = type(exception).__name__

    @staticmethod
    def _close_consumer(consumer: KafkaConsumer) -> None:
        try:
            consumer.close(autocommit=False)
        except Exception:
            LOGGER.debug("Kafka consumer close failed during worker shutdown", exc_info=True)

    @staticmethod
    def _close_producer(producer: KafkaProducer) -> None:
        try:
            producer.close(timeout=5)
        except Exception:
            LOGGER.debug("Kafka producer close failed during worker shutdown", exc_info=True)

    def _process_message(self, event: dict, producer: KafkaProducer) -> None:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                payload = TelemetryInput.model_validate(event)
                prediction = predict_telemetry(payload).model_dump(by_alias=True, mode="json")
                prediction.update(
                    {
                        "eventId": event.get("eventId", str(uuid.uuid4())),
                        "sourceTopic": "energy-usage",
                        "processedAt": datetime.now(timezone.utc).isoformat(),
                    }
                )
                producer.send("anomaly-results", prediction).get(timeout=10)
                LOGGER.info("Published anomaly result for device %s", payload.device_id)
                return
            except Exception as exc:
                last_error = exc
                LOGGER.warning("Anomaly processing attempt %s/%s failed: %s", attempt, self.max_attempts, exc)
                if attempt < self.max_attempts:
                    time.sleep(min(attempt, 2))
        failure = {
            "event": event,
            "error": str(last_error),
            "attempts": self.max_attempts,
            "failedAt": datetime.now(timezone.utc).isoformat(),
        }
        producer.send("anomaly-processing-failures", failure).get(timeout=10)
        LOGGER.error("Sent permanently failing telemetry event to anomaly-processing-failures")
