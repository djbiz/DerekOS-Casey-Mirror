"""Centralized environment-backed runtime configuration for Master Brain."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ENV_CANONICAL_STORE = "MASTER_BRAIN_CANONICAL_STORE_PATH"
ENV_CANDIDATE_QUEUE = "MASTER_BRAIN_CANDIDATE_QUEUE_PATH"
ENV_REVIEW_LOG = "MASTER_BRAIN_REVIEW_LOG_PATH"
ENV_OBSIDIAN_VAULT = "OBSIDIAN_VAULT_PATH"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RuntimeConfig:
    """Resolved paths used by operator commands.

    Defaults are repository-relative for fresh-checkout diagnostics, while
    environment variables remain the only runtime override source.
    """

    repo_root: Path
    raw_chatgpt_dir: Path
    ingest_output_dir: Path
    source_index_dir: Path
    thoughts_path: Path
    entities_path: Path
    relationships_path: Path
    timelines_path: Path
    canonical_candidates_path: Path
    extraction_report_path: Path
    canonical_store_path: Path
    candidate_queue_path: Path
    review_log_path: Path
    obsidian_vault_path: Path | None

    @classmethod
    def load(cls, env: Mapping[str, str] | None = None, *, root: Path | None = None) -> "RuntimeConfig":
        source = os.environ if env is None else env
        repo = (root or repository_root()).resolve(strict=False)
        canonical = Path(source.get(ENV_CANONICAL_STORE, repo / "10_CANONICAL_KNOWLEDGE" / "canonical_records.jsonl"))
        queue = Path(source.get(ENV_CANDIDATE_QUEUE, repo / "12_CONFLICTS" / "candidate_queue.jsonl"))
        review = Path(source.get(ENV_REVIEW_LOG, repo / "12_CONFLICTS" / "review_log.jsonl"))
        vault_raw = source.get(ENV_OBSIDIAN_VAULT)
        return cls(
            repo_root=repo,
            raw_chatgpt_dir=repo / "00_RAW_ARCHIVE" / "chatgpt",
            ingest_output_dir=repo / "01_INGEST",
            source_index_dir=repo / "13_SOURCE_INDEX",
            thoughts_path=repo / "02_EXTRACTED_THOUGHTS" / "thoughts.jsonl",
            entities_path=repo / "02_EXTRACTED_THOUGHTS" / "entities.jsonl",
            relationships_path=repo / "02_EXTRACTED_THOUGHTS" / "relationships.jsonl",
            timelines_path=repo / "02_EXTRACTED_THOUGHTS" / "timelines.jsonl",
            canonical_candidates_path=repo / "02_EXTRACTED_THOUGHTS" / "canonical_candidates.jsonl",
            extraction_report_path=repo / "02_EXTRACTED_THOUGHTS" / "extraction_report.json",
            canonical_store_path=canonical.expanduser().resolve(strict=False),
            candidate_queue_path=queue.expanduser().resolve(strict=False),
            review_log_path=review.expanduser().resolve(strict=False),
            obsidian_vault_path=Path(vault_raw).expanduser().resolve(strict=False) if vault_raw else None,
        )

    def redacted(self) -> dict[str, str | None]:
        return {
            ENV_CANONICAL_STORE: str(self.canonical_store_path),
            ENV_CANDIDATE_QUEUE: str(self.candidate_queue_path),
            ENV_REVIEW_LOG: str(self.review_log_path),
            ENV_OBSIDIAN_VAULT: str(self.obsidian_vault_path) if self.obsidian_vault_path else None,
            "RAW_CHATGPT_DIR": str(self.raw_chatgpt_dir),
            "INGEST_OUTPUT_DIR": str(self.ingest_output_dir),
            "SOURCE_INDEX_DIR": str(self.source_index_dir),
            "EXTRACTION_THOUGHTS_PATH": str(self.thoughts_path),
            "EXTRACTION_ENTITIES_PATH": str(self.entities_path),
            "EXTRACTION_RELATIONSHIPS_PATH": str(self.relationships_path),
            "EXTRACTION_TIMELINES_PATH": str(self.timelines_path),
            "EXTRACTION_CANONICAL_CANDIDATES_PATH": str(self.canonical_candidates_path),
            "EXTRACTION_REPORT_PATH": str(self.extraction_report_path),
        }
