# Phase 1 Ingest

The authoritative implementation now lives in `master_brain_bridge.ingest` and is exposed through `derekos ingest`. The historical `01_INGEST/ingest.py` script is a compatibility wrapper that delegates to the same code path.

The normalized message contract remains `schemas/message-1.1.0.schema.json` with deterministic `source_record_id` values and `ingest_version: 1.1.0`. Ingest reads operator-supplied `conversations-*.json` files from a private ChatGPT export directory, writes staged artifacts, validates message JSONL records, and only then promotes:

- `messages.jsonl`
- `conversations_index.json`
- `ingest_report.json`
- `checkpoint.json`
- `../13_SOURCE_INDEX/source_manifest.json`

Example:

```bash
derekos ingest --source-dir ../00_RAW_ARCHIVE/chatgpt --output-dir . --index-dir ../13_SOURCE_INDEX --json
```
