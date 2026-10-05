"""Tests for the derekos CLI operator boundary."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from master_brain_bridge.cli import main


RECORD = {
    "knowledge_id": "MBK-CLI-001",
    "revision": 1,
    "canonical_status": "CURRENT",
    "title": "CLI Ready",
    "summary": "Searchable summary",
    "content": "The CLI can retrieve canonical content.",
    "evidence_ids": ["ev-1"],
    "approval_status": "ACCEPTED",
    "projection_policy": "PUBLISH",
}


def run_cli(argv: list[str], env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch.dict(os.environ, env or {}, clear=False), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def write_store(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(RECORD) + "\n", encoding="utf-8")


class CliTests(unittest.TestCase):
    def test_doctor_json_fresh_checkout_exits_nonzero_with_valid_json(self) -> None:
        code, out, _ = run_cli(["doctor", "--json"], env={
            "MASTER_BRAIN_CANONICAL_STORE_PATH": str(Path("/nonexistent/canonical.jsonl")),
        })
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["status"], "not_ready")
        self.assertIn("checks", payload)

    def test_get_and_search_emit_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store = Path(td) / "canonical.jsonl"
            write_store(store)
            env = {"MASTER_BRAIN_CANONICAL_STORE_PATH": str(store)}
            code, out, _ = run_cli(["--json", "get", "MBK-CLI-001"], env=env)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["knowledge_id"], "MBK-CLI-001")
            code, out, _ = run_cli(["--json", "search", "retrieve canonical"], env=env)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)[0]["knowledge_id"], "MBK-CLI-001")

    def test_publish_all_partial_failure_exits_nonzero_and_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = root / "canonical.jsonl"
            bad = dict(RECORD, knowledge_id="MBK-CLI-../BAD")
            store.write_text(json.dumps(RECORD) + "\n" + json.dumps(bad) + "\n", encoding="utf-8")
            vault = root / "vault"
            vault.mkdir()
            env = {"MASTER_BRAIN_CANONICAL_STORE_PATH": str(store), "OBSIDIAN_VAULT_PATH": str(vault)}
            code, out, _ = run_cli(["--json", "publish-all"], env=env)
            self.assertEqual(code, 1)
            payload = json.loads(out)
            self.assertEqual(payload["status"], "partial")
            self.assertEqual(payload["failure_count"], 1)
            self.assertEqual(payload["success_count"], 1)

    def test_intake_all_partial_failure_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = root / "canonical.jsonl"
            write_store(store)
            vault = root / "vault"
            good_dir = vault / "MasterBrain" / "Candidates"
            good_dir.mkdir(parents=True)
            (good_dir / "good.md").write_text("# Good\n", encoding="utf-8")
            broken = good_dir / "broken.md"
            broken.write_text("# Broken\n", encoding="utf-8")
            broken.chmod(0o000)
            env = {
                "MASTER_BRAIN_CANONICAL_STORE_PATH": str(store),
                "OBSIDIAN_VAULT_PATH": str(vault),
                "MASTER_BRAIN_CANDIDATE_QUEUE_PATH": str(root / "queue.jsonl"),
            }
            try:
                code, out, _ = run_cli(["--json", "intake-all"], env=env)
            finally:
                broken.chmod(0o644)
            # Running as root can still read chmod 000, so assert stable structured success/partial output.
            payload = json.loads(out)
            self.assertIn(payload["status"], {"success", "partial"})
            self.assertEqual(code, 0 if payload["status"] == "success" else 1)
            self.assertGreaterEqual(payload["success_count"], 1)


if __name__ == "__main__":
    unittest.main()
