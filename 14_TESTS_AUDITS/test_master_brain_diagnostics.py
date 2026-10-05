"""Tests for read-only diagnostics."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge.config import RuntimeConfig
from master_brain_bridge.diagnostics import run_diagnostics


def config_for(root: Path) -> RuntimeConfig:
    return RuntimeConfig(
        repo_root=root,
        raw_chatgpt_dir=root / "00_RAW_ARCHIVE" / "chatgpt",
        ingest_output_dir=root / "01_INGEST",
        source_index_dir=root / "13_SOURCE_INDEX",
        canonical_store_path=root / "10_CANONICAL_KNOWLEDGE" / "canonical_records.jsonl",
        candidate_queue_path=root / "12_CONFLICTS" / "candidate_queue.jsonl",
        review_log_path=root / "12_CONFLICTS" / "review_log.jsonl",
        obsidian_vault_path=root / "vault",
    )


class DiagnosticsTests(unittest.TestCase):
    def test_fresh_checkout_missing_private_inputs_reports_not_ready_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "01_INGEST" / "schemas").mkdir(parents=True)
            (root / "01_INGEST" / "schemas" / "message-1.1.0.schema.json").write_text("{}", encoding="utf-8")
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            report = run_diagnostics(config_for(root))
            after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))
            self.assertEqual(report.status, "not_ready")
            self.assertEqual(before, after)
            failures = {c.name for c in report.checks if c.status == "fail"}
            self.assertIn("canonical_store", failures)
            self.assertIn("raw_chatgpt_dir", failures)

    def test_valid_fixture_reports_ready(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = config_for(root)
            cfg.raw_chatgpt_dir.mkdir(parents=True)
            (cfg.raw_chatgpt_dir / "conversations-000.json").write_text("[]", encoding="utf-8")
            (root / "01_INGEST" / "schemas").mkdir(parents=True)
            (root / "01_INGEST" / "schemas" / "message-1.1.0.schema.json").write_text("{}", encoding="utf-8")
            cfg.canonical_store_path.parent.mkdir(parents=True)
            cfg.canonical_store_path.write_text(json.dumps({
                "knowledge_id": "MBK-READY-001",
                "revision": 1,
                "canonical_status": "CURRENT",
                "title": "Ready",
                "content": "Ready content.",
                "evidence_ids": [],
            }) + "\n", encoding="utf-8")
            cfg.obsidian_vault_path.mkdir()
            cfg.candidate_queue_path.parent.mkdir(parents=True)
            cfg.review_log_path.parent.mkdir(parents=True, exist_ok=True)
            for artifact in ("messages.jsonl", "conversations_index.json", "ingest_report.json"):
                (cfg.ingest_output_dir / artifact).write_text("{}\n", encoding="utf-8")
            report = run_diagnostics(cfg)
            self.assertEqual(report.status, "ready")


if __name__ == "__main__":
    unittest.main()
