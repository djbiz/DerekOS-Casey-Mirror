"""Tests for deterministic extraction stages."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge.candidate_intake import CandidateIntake
from master_brain_bridge.config import RuntimeConfig, repository_root
from master_brain_bridge.extraction import ExtractionError, ExtractionPipeline
from master_brain_bridge.ingest import run_ingest
from master_brain_bridge.repository import ReadOnlyCanonicalRepository


def write_export(source_dir: Path, text: str) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    export = [
        {
            "id": "conv-1",
            "conversation_id": "conv-1",
            "title": "Extraction Fixture",
            "create_time": 1700000000.0,
            "update_time": 1700000060.0,
            "current_node": "msg-2",
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
                "msg-2": {
                    "id": "msg-2",
                    "parent": "msg-1",
                    "message": {
                        "id": "message-2",
                        "author": {"role": "assistant", "name": None},
                        "create_time": 1700000060.0,
                        "content": {"content_type": "text", "parts": ["Acknowledged. Entity: DerekOS (technology)"]},
                    },
                },
            },
        }
    ]
    (source_dir / "conversations-000.json").write_text(json.dumps(export), encoding="utf-8")


def cfg(root: Path) -> RuntimeConfig:
    return RuntimeConfig(
        repo_root=repository_root(),
        raw_chatgpt_dir=root / "raw",
        ingest_output_dir=root / "ingest",
        source_index_dir=root / "index",
        thoughts_path=root / "extract" / "thoughts.jsonl",
        entities_path=root / "extract" / "entities.jsonl",
        relationships_path=root / "extract" / "relationships.jsonl",
        timelines_path=root / "extract" / "timelines.jsonl",
        canonical_candidates_path=root / "extract" / "canonical_candidates.jsonl",
        extraction_report_path=root / "extract" / "extraction_report.json",
        canonical_store_path=root / "canonical" / "canonical_records.jsonl",
        candidate_queue_path=root / "conflicts" / "candidate_queue.jsonl",
        review_log_path=root / "conflicts" / "review_log.jsonl",
        obsidian_vault_path=root / "vault",
    )


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ExtractionTests(unittest.TestCase):
    def test_run_all_is_deterministic_and_preserves_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = cfg(root)
            config.obsidian_vault_path.mkdir(parents=True)
            text = "Decision: Casey Mirror is the operator memory.\nEntity: Casey Mirror (product)\nEntity: Derek (person)\nrelationship: Casey Mirror | depends_on | Derek\ntimeline: 2024-01-02 | developed | Casey Mirror design was refined."
            write_export(config.raw_chatgpt_dir, text)
            run_ingest(config.raw_chatgpt_dir, config.ingest_output_dir, config.source_index_dir)
            pipeline = ExtractionPipeline(config)
            first = pipeline.run_all()
            first_thoughts = config.thoughts_path.read_text(encoding="utf-8")
            first_canon = config.canonical_store_path.read_text(encoding="utf-8")
            second = pipeline.run_all()
            self.assertTrue(first.ok)
            self.assertTrue(second.ok)
            self.assertEqual(first_thoughts, config.thoughts_path.read_text(encoding="utf-8"))
            self.assertEqual(first_canon, config.canonical_store_path.read_text(encoding="utf-8"))
            thoughts = read_jsonl(config.thoughts_path)
            self.assertEqual(thoughts[0]["originator"], "derek")
            self.assertEqual(thoughts[0]["evidence_class"], "D0")
            self.assertIn("source_record_id", thoughts[0]["source"])
            entities = read_jsonl(config.entities_path)
            self.assertEqual({e["name"] for e in entities}, {"Casey Mirror", "Derek", "DerekOS"})
            relationships = read_jsonl(config.relationships_path)
            self.assertEqual(len(relationships), 1)
            self.assertEqual(relationships[0]["type"], "depends_on")
            timelines = read_jsonl(config.timelines_path)
            self.assertTrue(any(item["event"] == "developed" for item in timelines))
            repo = ReadOnlyCanonicalRepository(config.canonical_store_path)
            self.assertGreaterEqual(len(repo.knowledge_ids), 1)

    def test_conservative_omission_without_explicit_entity_or_relationship(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = cfg(root)
            config.obsidian_vault_path.mkdir(parents=True)
            write_export(config.raw_chatgpt_dir, "Alice and Bob might be names, but no explicit entity marker exists.")
            run_ingest(config.raw_chatgpt_dir, config.ingest_output_dir, config.source_index_dir)
            pipeline = ExtractionPipeline(config)
            pipeline.extract_thoughts()
            entity_report = pipeline.extract_entities()
            relationship_report = pipeline.extract_relationships()
            self.assertEqual(entity_report.records_written, 1)  # assistant fixture explicitly names DerekOS
            self.assertEqual(relationship_report.records_written, 0)

    def test_corrupt_upstream_rejected_and_previous_output_survives(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = cfg(root)
            write_export(config.raw_chatgpt_dir, "Good thought")
            run_ingest(config.raw_chatgpt_dir, config.ingest_output_dir, config.source_index_dir)
            pipeline = ExtractionPipeline(config)
            pipeline.extract_thoughts()
            before = config.thoughts_path.read_bytes()
            (config.ingest_output_dir / "messages.jsonl").write_text("not json\n", encoding="utf-8")
            with self.assertRaises(ExtractionError):
                pipeline.extract_thoughts()
            self.assertEqual(before, config.thoughts_path.read_bytes())

    def test_refuses_to_overwrite_non_generated_canonical_store(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = cfg(root)
            config.obsidian_vault_path.mkdir(parents=True)
            write_export(config.raw_chatgpt_dir, "Decision: generated knowledge")
            run_ingest(config.raw_chatgpt_dir, config.ingest_output_dir, config.source_index_dir)
            config.canonical_store_path.parent.mkdir(parents=True)
            config.canonical_store_path.write_text(json.dumps({
                "knowledge_id": "MBK-HUMAN-001", "revision": 1, "canonical_status": "CURRENT",
                "title": "Human", "content": "Human managed.", "evidence_ids": []
            }) + "\n", encoding="utf-8")
            pipeline = ExtractionPipeline(config)
            pipeline.extract_thoughts()
            pipeline.extract_entities()
            pipeline.extract_relationships()
            pipeline.extract_timelines()
            with self.assertRaises(ExtractionError):
                pipeline.extract_canonical()
            self.assertIn("MBK-HUMAN-001", config.canonical_store_path.read_text(encoding="utf-8"))

    def test_candidate_notes_are_compatible_with_intake(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = cfg(root)
            config.obsidian_vault_path.mkdir(parents=True)
            write_export(config.raw_chatgpt_dir, "Decision: Candidate notes remain governed.")
            run_ingest(config.raw_chatgpt_dir, config.ingest_output_dir, config.source_index_dir)
            ExtractionPipeline(config).run_all()
            repo = ReadOnlyCanonicalRepository(config.canonical_store_path)
            intake = CandidateIntake(config.obsidian_vault_path, config.candidate_queue_path, repository=repo)
            result = intake.ingest_all()
            self.assertTrue(result.ok)
            self.assertGreaterEqual(len(result.successes), 1)
            queue = read_jsonl(config.candidate_queue_path)
            self.assertEqual(queue[0]["source_system"], "obsidian")
            self.assertEqual(queue[0]["proposed_operation"], "CREATE")


if __name__ == "__main__":
    unittest.main()
