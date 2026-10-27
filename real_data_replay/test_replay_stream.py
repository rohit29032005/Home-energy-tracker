"""Standard-library tests for the real-data replay engine.

The HTTP test uses an in-process loopback server, never the project gateway or
Docker stack. It verifies a confirmed 503 rejection is logged and retried once
before a 201 acceptance.
"""

from __future__ import annotations

import csv
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from real_data_replay import replay_stream


class RetryHandler(BaseHTTPRequestHandler):
    requests = 0
    seen_token = ""

    def do_POST(self) -> None:  # noqa: N802 - required BaseHTTPRequestHandler name.
        type(self).requests += 1
        type(self).seen_token = self.headers.get("X-Device-Token", "")
        content_length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(content_length)
        status = 503 if type(self).requests == 1 else 201
        self.send_response(status)
        self.end_headers()
        self.wfile.write(b"retry" if status == 503 else b"")

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        del format, args


class ReplayStreamTest(unittest.TestCase):
    def test_retries_confirmed_503_then_accepts_201(self) -> None:
        RetryHandler.requests = 0
        RetryHandler.seen_token = ""
        server = ThreadingHTTPServer(("127.0.0.1", 0), RetryHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                failed_path = Path(directory) / "failed_requests.csv"
                with failed_path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=replay_stream.FAILED_REQUEST_COLUMNS)
                    writer.writeheader()
                    result = replay_stream.send_with_retries(
                        endpoint=f"http://127.0.0.1:{server.server_port}/api/v1/ingestion",
                        device_token="test-token",
                        correlation_id="test-correlation-id",
                        payload={"deviceId": 1, "energyConsumed": 0.1, "timestamp": "2026-01-01T00:00:00Z"},
                        timeout_seconds=2,
                        max_attempts=2,
                        backoff_seconds=0,
                        retry_uncertain_transport=False,
                        failure_writer=writer,
                        failure_log_base={
                            "run_id": "test",
                            "loop_index": "0",
                            "sequence": "1",
                            "event_id": "fixture:1:1",
                            "household_id": "1",
                            "device_id": "1",
                            "source_timestamp_utc": "2014-01-01T00:00:00Z",
                            "replay_timestamp_utc": "2026-01-01T00:00:00Z",
                        },
                    )
                with failed_path.open("r", encoding="utf-8", newline="") as handle:
                    failures = list(csv.DictReader(handle))
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=2)

        self.assertTrue(result.accepted)
        self.assertEqual(result.attempts, 2)
        self.assertEqual(result.final_http_status, 201)
        self.assertEqual(RetryHandler.requests, 2)
        self.assertEqual(RetryHandler.seen_token, "test-token")
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["http_status"], "503")
        self.assertEqual(failures[0]["retryable"], "true")

    def test_current_timestamps_are_monotonic_per_device(self) -> None:
        record = replay_stream.RawReplayRecord(
            household_id="1",
            source_filename="fixture.csv",
            source_row_number="2",
            source_unix=1_400_000_000,
            source_timestamp_utc="2014-05-13T16:53:20Z",
            interval_seconds=8,
            energy_consumed_kwh=0.001,
            solar_interference_documented=False,
            known_source_caveat="",
        )
        last_by_device: dict[int, float] = {}
        first, first_adjusted = replay_stream.payload_timestamp(
            record=record,
            timeline_offset=0,
            loop_index=0,
            loop_span_seconds=10,
            timestamp_mode="current",
            replay_start_epoch=1_700_000_000,
            speed=100,
            current_epoch=1_700_000_000,
            device_id=1,
            last_payload_epoch_by_device=last_by_device,
        )
        second, second_adjusted = replay_stream.payload_timestamp(
            record=record,
            timeline_offset=0,
            loop_index=0,
            loop_span_seconds=10,
            timestamp_mode="current",
            replay_start_epoch=1_700_000_000,
            speed=100,
            current_epoch=1_700_000_000,
            device_id=1,
            last_payload_epoch_by_device=last_by_device,
        )
        self.assertFalse(first_adjusted)
        self.assertTrue(second_adjusted)
        self.assertLess(first, second)


if __name__ == "__main__":
    unittest.main()
