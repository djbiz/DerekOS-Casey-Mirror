# DerekOS Master Brain Bridge

Supported scope: an installable Python operator surface for deterministic Phase 1 ingest, read-only canonical retrieval, managed Obsidian projection, governed candidate intake, review proposals, and readiness diagnostics. Later knowledge-extraction phases remain unfinished and are reported as prerequisites rather than faked.

## Install and verify

```bash
python -m pip install -e '.[dev]'
python -m compileall -q master_brain_bridge 01_INGEST/ingest.py ingest.py
python -m unittest discover -s 14_TESTS_AUDITS -p 'test_master_brain*.py' -v
python -m pip_audit
```

## Private inputs

`00_RAW_ARCHIVE/`, the canonical store, queue/review logs, and the Obsidian vault are private runtime data and are not supplied by a clean checkout. Configure them with environment variables (see `.env.example`):

- `MASTER_BRAIN_CANONICAL_STORE_PATH`
- `MASTER_BRAIN_CANDIDATE_QUEUE_PATH`
- `MASTER_BRAIN_REVIEW_LOG_PATH`
- `OBSIDIAN_VAULT_PATH`

The runtime does not load `.env` files implicitly.

## Operator commands

```bash
derekos doctor --json
derekos ingest --source-dir 00_RAW_ARCHIVE/chatgpt --output-dir 01_INGEST --json
derekos get MBK-EXAMPLE-001 --json
derekos search "canonical phrase" --json
derekos publish MBK-EXAMPLE-001
derekos publish-all --json
derekos intake path/inside/MasterBrain/Candidates/note.md --json
derekos intake-all --json
derekos review MBC-EXAMPLE --json
derekos review-all --json
```

Exit code `0` means complete success. Exit code `1` means failed prerequisites, command failure, or a structured partial bulk result with one or more failed items. `--log-level DEBUG` enables tracebacks in logs.

## Safety boundaries

Retrieval is read-only against the canonical JSONL store. Projection writes only managed notes under `MasterBrain/Published`. Candidate intake appends queue records only. Review appends auditable proposals and never mutates canon. Ingest stages and validates outputs before promoting generated artifacts so a failed run leaves previous outputs intact.
