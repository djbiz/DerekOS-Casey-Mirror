"""Compatibility wrapper for authoritative package ingest.

Run `derekos ingest` or import `master_brain_bridge.ingest.run_ingest` for the
supported operator surface. This wrapper is retained for historical scripts.
"""

from __future__ import annotations

from master_brain_bridge.ingest import *  # noqa: F401,F403 - compatibility surface
from master_brain_bridge.ingest import main


if __name__ == "__main__":
    raise SystemExit(main())
