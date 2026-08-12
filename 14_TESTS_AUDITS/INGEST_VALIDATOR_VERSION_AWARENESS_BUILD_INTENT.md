# Ingest Validator Version-Awareness — Build Intent

**Date:** 2026-08-12
**Scope:** Validator maintenance only

## Inspected

- The strict `message-1.1.0` schema and Phase 1 reconciliation validator.
- The current mixed-source message stream: 68,761 ChatGPT `1.1.0` records, 3,080 other-AI fragment `2.0.0` records, and 400 Copilot CSV `1.0.0` records.
- Exact key families and source-format markers for each version.

## Proposed change

- Preserve `message-1.1.0.schema.json` unchanged.
- Add strict, versioned schemas for Copilot `1.0.0` and other-AI fragments `2.0.0`.
- Dispatch validation by `(ingest_version, source_format)` and reject unknown combinations.
- Keep original Phase 1 graph/count/hash/provenance assertions scoped to ChatGPT `1.1.0` records.
- Add aggregate uniqueness and per-profile validation checks without changing any record.

## Files affected

- `01_INGEST/schemas/message-1.0.0-copilot.schema.json`
- `01_INGEST/schemas/message-2.0.0-fragment.schema.json`
- `14_TESTS_AUDITS/verify_phase1_reconciliation.py`
- `14_TESTS_AUDITS/test_ingest_validator_version_awareness.py`
- This Build Intent Report

## Risks and verification

The principal risk is making validation permissive. The fix instead keeps `additionalProperties: false`, requires source-format/version pairs, rejects unknown profiles, and tests cross-profile rejection. The full validator must pass without rewriting messages, provenance, the source manifest, or the ingestion report.

## Final change question

**Does this move VOX closer to becoming the AI Workforce Operating System?** Yes. It restores trustworthy validation across independently versioned source adapters without weakening provenance contracts.
