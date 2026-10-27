"""Contract tests for the isolated experimental REFIT Kafka side path."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ML_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(ML_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE_ROOT))

from app.refit_kafka_worker import RefitControlledKafkaWorker  # noqa: E402


class FakeResult:
    def as_dict(self) -> dict[str, object]:
        return {
            "refitProfileId": 1,
            "streamId": "replay-H1",
            "inputState": "accepted",
            "closedBins": [],
        }


class FakeEngine:
    model_version = "refit_controlled_v1-test"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def ingest(self, **kwargs: object) -> FakeResult:
        self.calls.append(kwargs)
        return FakeResult()


class FakeFuture:
    def get(self, timeout: int) -> None:
        assert timeout == 10


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, object]]] = []

    def send(self, topic: str, value: dict[str, object]) -> FakeFuture:
        self.sent.append((topic, value))
        return FakeFuture()


class PublishFailureFuture:
    def get(self, timeout: int) -> None:
        assert timeout == 10
        raise OSError("broker unavailable")


class PublishFailureProducer:
    """Producer double that fails every acknowledged Kafka publication."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, object]]] = []

    def send(self, topic: str, value: dict[str, object]) -> PublishFailureFuture:
        self.sent.append((topic, value))
        return PublishFailureFuture()


class SingleMessageConsumer:
    """Consumer double for asserting the worker's commit ordering locally."""

    def __init__(self, event: dict[str, object]) -> None:
        self._event = event
        self.commit_calls = 0

    def __iter__(self):
        return iter((type("Message", (), {"value": self._event})(),))

    def commit(self) -> None:
        self.commit_calls += 1


def valid_event() -> dict[str, object]:
    return {
        "eventId": "event-1",
        "refitProfileId": 1,
        "streamId": "replay-H1",
        "energyConsumed": 0.0004,
        "timestamp": "2026-01-01T00:00:08Z",
        "intervalSeconds": 8,
    }


class RefitKafkaWorkerTests(unittest.TestCase):
    def test_valid_replay_event_uses_dedicated_topics_and_explicit_profile(self) -> None:
        engine = FakeEngine()
        worker = RefitControlledKafkaWorker(
            engine,  # type: ignore[arg-type]
            max_attempts=1,
            input_topic="refit-controlled-replay",
            output_topic="refit-controlled-anomaly-results",
            failure_topic="refit-controlled-anomaly-failures",
        )
        producer = FakeProducer()

        worker._process_message(valid_event(), producer)

        self.assertEqual(len(engine.calls), 1)
        call = engine.calls[0]
        self.assertEqual(call["profile_id"], 1)
        self.assertEqual(call["stream_id"], "replay-H1")
        self.assertIsInstance(call["timestamp"], datetime)
        self.assertEqual(call["timestamp"].tzinfo, timezone.utc)  # type: ignore[union-attr]
        self.assertEqual([topic for topic, _ in producer.sent], ["refit-controlled-anomaly-results"])
        payload = producer.sent[0][1]
        self.assertEqual(payload["sourceTopic"], "refit-controlled-replay")
        self.assertEqual(payload["modelScope"], "experimental_controlled_perturbation_benchmark")
        self.assertNotIn("anomalyProbability", payload)

    def test_invalid_or_implicit_device_mapping_event_goes_only_to_dedicated_failure_topic(self) -> None:
        engine = FakeEngine()
        worker = RefitControlledKafkaWorker(
            engine,  # type: ignore[arg-type]
            max_attempts=1,
            input_topic="refit-controlled-replay",
            output_topic="refit-controlled-anomaly-results",
            failure_topic="refit-controlled-anomaly-failures",
        )
        producer = FakeProducer()
        event = valid_event()
        event.pop("refitProfileId")
        event["deviceId"] = 1

        worker._process_message(event, producer)

        self.assertEqual(engine.calls, [])
        self.assertEqual([topic for topic, _ in producer.sent], ["refit-controlled-anomaly-failures"])
        failure = producer.sent[0][1]
        self.assertEqual(failure["attempts"], 1)
        self.assertEqual(failure["sourceTopic"], "refit-controlled-replay")

    def test_non_string_stream_identifier_goes_only_to_dedicated_failure_topic(self) -> None:
        engine = FakeEngine()
        worker = RefitControlledKafkaWorker(
            engine,  # type: ignore[arg-type]
            max_attempts=1,
            input_topic="refit-controlled-replay",
            output_topic="refit-controlled-anomaly-results",
            failure_topic="refit-controlled-anomaly-failures",
        )
        producer = FakeProducer()
        event = valid_event()
        event["streamId"] = 1

        worker._process_message(event, producer)

        self.assertEqual(engine.calls, [])
        self.assertEqual([topic for topic, _ in producer.sent], ["refit-controlled-anomaly-failures"])

    def test_unacknowledged_output_and_failure_publication_leaves_input_uncommitted(self) -> None:
        """The input is committed only after the worker publishes an outcome.

        A result publication failure is retried by the message processor. Once
        the final failure-record publication also fails, that exception reaches
        the consume loop before its following consumer.commit() call.
        """
        engine = FakeEngine()
        worker = RefitControlledKafkaWorker(
            engine,  # type: ignore[arg-type]
            max_attempts=1,
            input_topic="refit-controlled-replay",
            output_topic="refit-controlled-anomaly-results",
            failure_topic="refit-controlled-anomaly-failures",
        )
        consumer = SingleMessageConsumer(valid_event())
        producer = PublishFailureProducer()

        with self.assertRaisesRegex(OSError, "broker unavailable"):
            worker._consume(consumer, producer)

        self.assertEqual(
            [topic for topic, _ in producer.sent],
            ["refit-controlled-anomaly-results", "refit-controlled-anomaly-failures"],
        )
        self.assertEqual(consumer.commit_calls, 0)

    def test_unacknowledged_failure_record_leaves_invalid_input_uncommitted(self) -> None:
        """An invalid event is likewise not committed when its failure record cannot publish."""
        engine = FakeEngine()
        worker = RefitControlledKafkaWorker(
            engine,  # type: ignore[arg-type]
            max_attempts=1,
            input_topic="refit-controlled-replay",
            output_topic="refit-controlled-anomaly-results",
            failure_topic="refit-controlled-anomaly-failures",
        )
        event = valid_event()
        event.pop("refitProfileId")
        consumer = SingleMessageConsumer(event)
        producer = PublishFailureProducer()

        with self.assertRaisesRegex(OSError, "broker unavailable"):
            worker._consume(consumer, producer)

        self.assertEqual([topic for topic, _ in producer.sent], ["refit-controlled-anomaly-failures"])
        self.assertEqual(consumer.commit_calls, 0)


if __name__ == "__main__":
    unittest.main()
