"""Unit contracts for broker reconnection without requiring a Kafka broker."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ML_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from app.kafka_worker import KafkaInferenceWorker  # noqa: E402
from app.refit_kafka_worker import RefitControlledKafkaWorker  # noqa: E402


class FakeConsumer:
    def __init__(self) -> None:
        self.closed = False

    def __iter__(self):
        return iter(())

    def commit(self) -> None:
        return None

    def close(self, autocommit: bool) -> None:
        assert autocommit is False
        self.closed = True


class FakeProducer:
    def __init__(self) -> None:
        self.closed = False

    def close(self, timeout: int) -> None:
        assert timeout == 5
        self.closed = True


class LegacyReconnectWorker(KafkaInferenceWorker):
    def __init__(self) -> None:
        super().__init__(connection_retry_seconds=0.001)
        self.connect_calls = 0
        self.created_consumer: FakeConsumer | None = None
        self.created_producer: FakeProducer | None = None

    def _connect(self):
        self.connect_calls += 1
        if self.connect_calls == 1:
            raise OSError("broker unavailable")
        self.created_consumer = FakeConsumer()
        self.created_producer = FakeProducer()
        self._stop.set()
        return self.created_consumer, self.created_producer


class RefitReconnectWorker(RefitControlledKafkaWorker):
    def __init__(self) -> None:
        super().__init__(object(), connection_retry_seconds=0.001)  # type: ignore[arg-type]
        self.connect_calls = 0
        self.created_consumer: FakeConsumer | None = None
        self.created_producer: FakeProducer | None = None

    def _connect(self):
        self.connect_calls += 1
        if self.connect_calls == 1:
            raise OSError("broker unavailable")
        self.created_consumer = FakeConsumer()
        self.created_producer = FakeProducer()
        self._stop.set()
        return self.created_consumer, self.created_producer


class KafkaReconnectTests(unittest.TestCase):
    def test_legacy_worker_retries_a_broker_connection_failure_instead_of_exiting(self) -> None:
        worker = LegacyReconnectWorker()

        worker._run()

        self.assertEqual(worker.connect_calls, 2)
        self.assertTrue(worker.created_consumer is not None and worker.created_consumer.closed)
        self.assertTrue(worker.created_producer is not None and worker.created_producer.closed)
        self.assertFalse(worker.status["connected"])
        self.assertIsNone(worker.status["lastConnectionError"])

    def test_refit_worker_retries_a_broker_connection_failure_instead_of_exiting(self) -> None:
        worker = RefitReconnectWorker()

        worker._run()

        self.assertEqual(worker.connect_calls, 2)
        self.assertTrue(worker.created_consumer is not None and worker.created_consumer.closed)
        self.assertTrue(worker.created_producer is not None and worker.created_producer.closed)
        self.assertFalse(worker.status["connected"])
        self.assertIsNone(worker.status["lastConnectionError"])

    def test_legacy_connect_closes_a_consumer_if_producer_creation_fails(self) -> None:
        consumer = FakeConsumer()
        worker = KafkaInferenceWorker(connection_retry_seconds=0.001)

        with patch("app.kafka_worker.KafkaConsumer", return_value=consumer), patch(
            "app.kafka_worker.KafkaProducer", side_effect=OSError("producer unavailable")
        ):
            with self.assertRaises(OSError):
                worker._connect()

        self.assertTrue(consumer.closed)

    def test_refit_connect_closes_a_consumer_if_producer_creation_fails(self) -> None:
        consumer = FakeConsumer()
        worker = RefitControlledKafkaWorker(object(), connection_retry_seconds=0.001)  # type: ignore[arg-type]

        with patch("app.refit_kafka_worker.KafkaConsumer", return_value=consumer), patch(
            "app.refit_kafka_worker.KafkaProducer", side_effect=OSError("producer unavailable")
        ):
            with self.assertRaises(OSError):
                worker._connect()

        self.assertTrue(consumer.closed)


if __name__ == "__main__":
    unittest.main()
