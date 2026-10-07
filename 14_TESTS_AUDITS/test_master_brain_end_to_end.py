"""Synthetic ingest-to-publish operator workflow tests."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from master_brain_bridge.cli import main
from master_brain_bridge.config import repository_root


def run_cli(argv: list[str], root: Path, env: dict[str, str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with (
        patch("master_brain_bridge.config.repository_root", return_value=root),
        patch.dict(os.environ, env, clear=False),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def prepare_checkout(root: Path) -> None:
    (root / "01_INGEST" / "schemas").mkdir(parents=True)
    shutil.copy(repository_root() / "01_INGEST" / "schemas" / "message-1.1.0.schema.json", root / "01_INGEST" / "schemas" / "message-1.1.0.schema.json")
    shutil.copytree(repository_root() / "schemas", root / "schemas")
    (root / "13_SOURCE_INDEX").mkdir()


def write_export(root: Path) -> None:
    source_dir = root / "00_RAW_ARCHIVE" / "chatgpt"
    source_dir.mkdir(parents=True)
    export = [
        {
            "id": "conv-e2e",
            "conversation_id": "conv-e2e",
            "title": "E2E",
            "create_time": 1700000000.0,
            "update_time": 1700000100.0,
            "current_node": "msg-user",
            "mapping": {
                "root": {"id": "root", "message": None, "parent": None},
                "msg-user": {
                    "id": "msg-user",
                    "parent": "root",
                    "message": {
                        "id": "message-user",
                        "author": {"role": "user", "name": None},
                        "create_time": 1700000000.0,
                        "content": {"content_type": "text", "parts": ["Decision: Synthetic Master Brain extraction publishes governed knowledge.\nEntity: Master Brain (product)"]},
                    },
                },
            },
        }
    ]
    (source_dir / "conversations-000.json").write_text(json.dumps(export), encoding="utf-8")


class EndToEndTests(unittest.TestCase):
    def test_synthetic_ingest_extract_intake_review_publish_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prepare_checkout(root)
            write_export(root)
            vault = root / "vault"
            vault.mkdir()
            env = {
                "MASTER_BRAIN_CANONICAL_STORE_PATH": str(root / "10_CANONICAL_KNOWLEDGE" / "canonical_records.jsonl"),
                "MASTER_BRAIN_CANDIDATE_QUEUE_PATH": str(root / "12_CONFLICTS" / "candidate_queue.jsonl"),
                "MASTER_BRAIN_REVIEW_LOG_PATH": str(root / "12_CONFLICTS" / "review_log.jsonl"),
                "OBSIDIAN_VAULT_PATH": str(vault),
            }
            for command in (["--json", "ingest"], ["--json", "extract-all"], ["--json", "intake-all"], ["--json", "review-all"], ["--json", "publish-all"]):
                code, out, err = run_cli(command, root, env)
                self.assertEqual(code, 0, command + [out, err])
                self.assertTrue(out.strip())
            self.assertTrue((root / "01_INGEST" / "messages.jsonl").is_file())
            self.assertTrue((root / "02_EXTRACTED_THOUGHTS" / "thoughts.jsonl").is_file())
            self.assertTrue(Path(env["MASTER_BRAIN_CANDIDATE_QUEUE_PATH"]).is_file())
            self.assertTrue(Path(env["MASTER_BRAIN_REVIEW_LOG_PATH"]).is_file())
            canonical_records = [json.loads(line) for line in Path(env["MASTER_BRAIN_CANONICAL_STORE_PATH"]).read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(canonical_records[0]["canonical_status"], "CURRENT")
            self.assertTrue((vault / "MasterBrain" / "Published" / f"{canonical_records[0]['knowledge_id']}.md").is_file())
            code, out, _ = run_cli(["--json", "doctor"], root, env)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "ready")

    def test_missing_ingest_prerequisite_exits_one_without_downstream_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            prepare_checkout(root)
            vault = root / "vault"
            vault.mkdir()
            env = {
                "MASTER_BRAIN_CANONICAL_STORE_PATH": str(root / "10_CANONICAL_KNOWLEDGE" / "canonical_records.jsonl"),
                "MASTER_BRAIN_CANDIDATE_QUEUE_PATH": str(root / "12_CONFLICTS" / "candidate_queue.jsonl"),
                "MASTER_BRAIN_REVIEW_LOG_PATH": str(root / "12_CONFLICTS" / "review_log.jsonl"),
                "OBSIDIAN_VAULT_PATH": str(vault),
            }
            code, out, _ = run_cli(["--json", "extract-all"], root, env)
            self.assertEqual(code, 1)
            payload = json.loads(out)
            self.assertEqual(payload["status"], "error")
            self.assertFalse((root / "02_EXTRACTED_THOUGHTS" / "thoughts.jsonl").exists())
            self.assertFalse(Path(env["MASTER_BRAIN_CANONICAL_STORE_PATH"]).exists())


if __name__ == "__main__":
    unittest.main()
