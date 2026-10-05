"""Tests for durable JSONL storage helpers."""

from __future__ import annotations

import threading
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge.storage import BulkResult, PathConfinementError, append_jsonl, ensure_relative_to, read_jsonl


class StorageTests(unittest.TestCase):
    def test_append_jsonl_is_durable_and_readable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "queue" / "items.jsonl"
            append_jsonl(path, {"id": "one", "value": 1})
            append_jsonl(path, {"id": "two", "value": 2})
            self.assertEqual([r["id"] for r in read_jsonl(path)], ["one", "two"])

    def test_concurrent_appends_do_not_interleave_records(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "items.jsonl"
            def worker(i: int) -> None:
                append_jsonl(path, {"id": i, "text": "x" * 100})
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            records = read_jsonl(path)
            self.assertEqual(len(records), 20)
            self.assertEqual({r["id"] for r in records}, set(range(20)))

    def test_path_confinement_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            root.mkdir()
            with self.assertRaises(PathConfinementError):
                ensure_relative_to(Path(td) / "outside.jsonl", root)

    def test_bulk_result_is_structured_and_list_like(self) -> None:
        result = BulkResult("demo")
        result.add_success({"id": "ok"})
        result.add_failure("bad", ValueError("nope"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "ok")
        self.assertEqual(result.status, "partial")
        self.assertFalse(result.ok)
        self.assertEqual(result.to_dict()["failure_count"], 1)


if __name__ == "__main__":
    unittest.main()
