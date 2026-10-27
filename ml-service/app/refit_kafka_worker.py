"""Bounded-retry Kafka bridge for the explicit REFIT experimental stream.

The worker uses dedicated topics and is disabled by default.  It never consumes
the existing Wokwi `energy-usage` topic and never emits to `anomaly-results`,
so it cannot accidentally inject uncalibrated REFIT benchmark scores into the
legacy alert service.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from kafka import KafkaConsumer, KafkaProducer

from app.refit_controlled import RefitControlledEngine, RefitControlledError


LOGGER = logging.getLogger("ml_inference.refit_kafka")


class RefitControlledKafkaWorker:
    """Bridge explicit replay events through an isolated experimental topic path."""

    def __init__(
        self,
        engine: RefitControlledEngine,
        *,
        bootstrap_servers: str | None = None,
        max_attempts: int | None = None,
        input_topic: str | None = None,
        output_topic: str | None = None,
        failure_topic: str | None = None,
        connection_retry_seconds: float | None = None,
    ) -> None:
        self.engine = engine
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.max_attempts = max_attempts or int(os.getenv("KAFKA_MAX_PROCESSING_ATTEMPTS", "3"))
        self.input_topic = input_topic or os.getenv("REFIT_CONTROLLED_INPUT_TOPIC", "refit-controlled-replay")
        self.output_topic = output_topic or os.getenv(
            "REFIT_CONTROLLED_OUTPUT_TOPIC", "refit-controlled-anomaly-results"
        )
        self.failure_topic = failure_topic or os.getenv(
            "REFIT_CONTROLLED_FAILURE_TOPIC", "refit-controlled-anomaly-failures"
        )
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
        self._thread = threading.Thread(
            target=self._run, name="refit-controlled-kafka-worker", daemon=True
        )
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
                LOGGER.info(
                    "Experimental REFIT Kafka worker connected to %s (input=%s, output=%s)",
                    self.bootstrap_servers,
                    self.input_topic,
                    self.output_topic,
                )
                self._consume(consumer, producer)
            except Exception as exception:
                self._set_disconnected(exception)
                if not self._stop.is_set():
                    LOGGER.exception(
                        "Experimental REFIT Kafka worker connection failed; retrying in %s seconds",
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
            self.input_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id="refit-controlled-inference-service",
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
            # Do not leak a partially initialized consumer on broker flaps.
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
            LOGGER.debug("Experimental REFIT consumer close failed during worker shutdown", exc_info=True)

    @staticmethod
    def _close_producer(producer: KafkaProducer) -> None:
        try:
            producer.close(timeout=5)
        except Exception:
            LOGGER.debug("Experimental REFIT producer close failed during worker shutdown", exc_info=True)

    def _process_message(self, event: dict[str, Any], producer: Any) -> None:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = self.engine.ingest(**self._parse_event(event))
                payload = {
                    "eventId": event.get("eventId", str(uuid.uuid4())),
                    "sourceTopic": self.input_topic,
                    "processedAt": datetime.now(timezone.utc).isoformat(),
                    "modelVersion": self.engine.model_version,
                    "modelScope": "experimental_controlled_perturbation_benchmark",
                    "result": result.as_dict(),
                }
                producer.send(self.output_topic, payload).get(timeout=10)
                LOGGER.info("Published experimental REFIT result for stream %s", payload["result"]["streamId"])
                return
            except Exception as exc:
                last_error = exc
                LOGGER.warning(
                    "Experimental REFIT processing attempt %s/%s failed: %s",
                    attempt,
                    self.max_attempts,
                    exc,
                )
                if attempt < self.max_attempts:
                    time.sleep(min(attempt, 2))
        failure = {
            "event": event,
            "error": str(last_error),
            "attempts": self.max_attempts,
            "failedAt": datetime.now(timezone.utc).isoformat(),
            "sourceTopic": self.input_topic,
            "modelScope": "experimental_controlled_perturbation_benchmark",
        }
        producer.send(self.failure_topic, failure).get(timeout=10)
        LOGGER.error("Sent permanently failing REFIT replay event to %s", self.failure_topic)

    @staticmethod
    def _parse_event(event: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(event, dict):
            raise RefitControlledError("REFIT replay Kafka payload must be a JSON object")
        required = {"refitProfileId", "streamId", "energyConsumed", "timestamp", "intervalSeconds"}
        missing = sorted(required - set(event))
        if missing:
            raise RefitControlledError("REFIT replay Kafka payload is missing " + ", ".join(missing))
        unknown = sorted(set(event) - required - {"eventId"})
        if unknown:
            raise RefitControlledError("REFIT replay Kafka payload has unsupported field(s): " + ", ".join(unknown))
        try:
            timestamp = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise RefitControlledError("REFIT replay Kafka timestamp is invalid") from exc
        if timestamp.tzinfo is None:
            raise RefitControlledError("REFIT replay Kafka timestamp must include a timezone")
        try:
            profile_id = int(event["refitProfileId"])
            interval_seconds = int(event["intervalSeconds"])
            energy_kwh = float(event["energyConsumed"])
        except (TypeError, ValueError) as exc:
            raise RefitControlledError("REFIT replay Kafka numeric field is invalid") from exc
        if not math.isfinite(energy_kwh):
            raise RefitControlledError("REFIT replay Kafka energyConsumed must be finite")
        stream_id = event["streamId"]
        if not isinstance(stream_id, str):
            raise RefitControlledError("REFIT replay Kafka streamId must be a string")
        return {
            "profile_id": profile_id,
            "stream_id": stream_id,
            "energy_kwh": energy_kwh,
            "timestamp": timestamp.astimezone(timezone.utc),
            "interval_seconds": interval_seconds,
        }
