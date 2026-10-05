"""Tests for authoritative staged ingest."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge.ingest import IngestError, run_ingest
from ingest import ingest_all as root_ingest_all


def write_conversation_export(source_dir: Path, *, text: str = "Hello") -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    export = [
        {
            "id": "conv-1",
            "conversation_id": "conv-1",
            "title": "Fixture",
            "create_time": 1700000000.0,
            "update_time": 1700000010.0,
            "current_node": "msg-1",
            "mapping": {
                "root": {"id": "root", "message": None, "parent": None},
                "msg-1": {
                    "id": "msg-1",
                    "parent": "root",
                    "message": {
                        "id": "message-1",
                        "author": {"role": "user", "name": None},
                        "create_time": 1700000000.0,
                        "content": {"content_type": "text", "parts": [text]},
                    },
                },
            },
        }
    ]
    (source_dir / "conversations-000.json").write_text(json.dumps(export), encoding="utf-8")


class IngestTests(unittest.TestCase):
    def test_run_ingest_writes_schema_valid_deterministic_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "raw" / "chatgpt"
            output = root / "out"
            index = root / "index"
            write_conversation_export(source)
            first = run_ingest(source, output, index)
            first_messages = (output / "messages.jsonl").read_text(encoding="utf-8")
            second = run_ingest(source, output, index)
            self.assertEqual(first.status, "PASS")
            self.assertEqual(first.messages_sha256, second.messages_sha256)
            self.assertEqual(first_messages, (output / "messages.jsonl").read_text(encoding="utf-8"))
            record = json.loads(first_messages.splitlines()[0])
            self.assertEqual(record["ingest_version"], "1.1.0")
            self.assertEqual(record["branch"], "main")
            self.assertTrue((index / "source_manifest.json").is_file())

    def test_failed_staged_ingest_leaves_previous_output_intact(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            output = root / "out"
            index = root / "index"
            write_conversation_export(source, text="good")
            run_ingest(source, output, index)
            before = (output / "messages.jsonl").read_bytes()
            (source / "conversations-000.json").write_text("not json", encoding="utf-8")
            with self.assertRaises(IngestError):
                run_ingest(source, output, index)
            self.assertEqual(before, (output / "messages.jsonl").read_bytes())

    def test_root_compatibility_wrapper_delegates_to_authoritative_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            output = root / "out"
            write_conversation_export(source)
            report = root_ingest_all(source, output)
            self.assertEqual(report["status"], "PASS")
            self.assertTrue((output / "messages.jsonl").exists())

    def test_historical_wrapper_cli_delegates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            output = root / "out"
            index = root / "index"
            write_conversation_export(source)
            proc = subprocess.run(
                [sys.executable, "01_INGEST/ingest.py", "--source-dir", str(source), "--output-dir", str(output), "--index-dir", str(index), "--json"],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertEqual(json.loads(proc.stdout)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
