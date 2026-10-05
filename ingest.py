#!/usr/bin/env python3
"""Compatibility wrapper for DerekOS Master Brain Phase 1 ingest.

The older root-level pipeline has been retired so all entry points produce the
same normalized message contract as `01_INGEST/ingest.py` and `derekos ingest`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from master_brain_bridge.ingest import IngestReport, main, run_ingest


def ingest_all(source_dir: Path, output_dir: Path, limit: int | None = None) -> dict[str, Any]:
    """Backward-compatible API delegating to the authoritative package ingest.

    `limit` is accepted for call compatibility but unsupported because partial
    deterministic ingest products are not promoted.
    """

    if limit is not None:
        raise ValueError("limit is no longer supported; ingest promotes only complete validated outputs")
    report = run_ingest(source_dir=source_dir, output_dir=output_dir, index_dir=output_dir.parent / "13_SOURCE_INDEX")
    return report.to_dict()


if __name__ == "__main__":
    raise SystemExit(main())
