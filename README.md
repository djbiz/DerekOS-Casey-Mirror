# DerekOS Master Brain Bridge

Supported scope: an installable Python operator surface for deterministic Phase 1 ingest, conservative semantic extraction, read-only canonical retrieval, managed Obsidian projection, governed candidate intake, review proposals, and readiness diagnostics.

The extraction model is an offline rules engine. It uses only role metadata and explicit source text markers, preserves exact provenance, derives stable content IDs, validates stage boundaries, and omits unsupported or ambiguous semantics instead of guessing.

## Install and verify

```bash
python -m pip install -e '.[dev]'
python -m compileall -q master_brain_bridge 01_INGEST/ingest.py ingest.py
python -m unittest discover -s 14_TESTS_AUDITS -p 'test_master_brain*.py' -v
python -m pip_audit
```

## Private inputs and runtime configuration

`00_RAW_ARCHIVE/`, the canonical store, queue/review logs, generated extraction artifacts, and the Obsidian vault are private runtime data and are not supplied by a clean checkout. Configure runtime paths with the existing four environment variables (see `.env.example`):

- `MASTER_BRAIN_CANONICAL_STORE_PATH`
- `MASTER_BRAIN_CANDIDATE_QUEUE_PATH`
- `MASTER_BRAIN_REVIEW_LOG_PATH`
- `OBSIDIAN_VAULT_PATH`

The runtime does not load `.env` files implicitly. Extraction stage artifacts are package-owned repo-relative files under `02_EXTRACTED_THOUGHTS/`; only the canonical store, queue, review log, and Obsidian vault have runtime overrides.

## Operator commands

```bash
derekos doctor --json
derekos ingest --source-dir 00_RAW_ARCHIVE/chatgpt --output-dir 01_INGEST --json
derekos extract-thoughts --json
derekos extract-entities --json
derekos extract-relationships --json
derekos extract-timelines --json
derekos extract-canonical --json
derekos extract-all --json
derekos get MBK-EXAMPLE-001 --json
derekos search "canonical phrase" --json
derekos intake-all --json
derekos review-all --json
derekos publish-all --json
```

Typical full local sequence:

```bash
derekos ingest --json
derekos extract-all --json
derekos intake-all --json
derekos review-all --json
derekos publish-all --json
```

Exit code `0` means complete success. Exit code `1` means failed prerequisites, validation failure, protected overwrite refusal, command failure, or a structured partial bulk result with one or more failed items. No command fabricates downstream files when prerequisites are absent or corrupt.

## Generated extraction artifacts

- `02_EXTRACTED_THOUGHTS/thoughts.jsonl`
- `02_EXTRACTED_THOUGHTS/entities.jsonl`
- `02_EXTRACTED_THOUGHTS/relationships.jsonl`
- `02_EXTRACTED_THOUGHTS/timelines.jsonl`
- `02_EXTRACTED_THOUGHTS/canonical_candidates.jsonl`
- `02_EXTRACTED_THOUGHTS/extraction_report.json`
- generated candidate notes under `MasterBrain/Candidates` inside the configured vault

The canonical stage atomically promotes only an extraction-owned canonical JSONL store. It refuses to replace a non-generated canonical store.

## Safety boundaries

Retrieval is read-only against the canonical JSONL store. Projection writes only managed notes under `MasterBrain/Published`. Candidate intake appends queue records only. Review appends auditable proposals and never mutates canon. Ingest and extraction stages validate temporary output before atomic promotion so a failed run leaves previous outputs intact.

## Docker

Build:

```bash
docker build -t derekos-casey-mirror .
```

Run with explicit mounts:

```bash
docker run --rm \
  -v "$PWD/00_RAW_ARCHIVE/chatgpt:/app/00_RAW_ARCHIVE/chatgpt:ro" \
  -v "$PWD/10_CANONICAL_KNOWLEDGE:/data/canonical" \
  -v "$PWD/12_CONFLICTS:/data/conflicts" \
  -v "/path/to/obsidian-vault:/data/obsidian" \
  derekos-casey-mirror doctor --json
```

Compose example:

```bash
docker compose run --rm derekos doctor --json
docker compose run --rm derekos extract-all --json
```

The image declares runtime mount points and `.dockerignore` excludes private archive, canonical, conflict, vault, cache, build, and VCS data from the build context.
