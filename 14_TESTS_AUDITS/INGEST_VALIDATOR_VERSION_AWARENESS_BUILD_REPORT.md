# Ingest Validator Version-Awareness — Build Report

**Date:** 2026-08-12
**Result:** PASS

## Changes made

- Preserved the immutable ChatGPT `1.1.0` schema unchanged.
- Added strict schemas for Copilot CSV `1.0.0` and other-AI fragments `2.0.0`.
- Added explicit `(ingest_version, source_format)` schema dispatch.
- Scoped the original Phase 1 count, graph, source-hash, report-hash, and pilot checks to the original ChatGPT `1.1.0` baseline.
- Added aggregate source-record uniqueness and known-profile checks.
- Reduced validator memory use by retaining graph link tuples rather than full message bodies.
- Added regression tests proving supported dispatch, unknown-version denial, cross-format denial, and extra-property denial.

## Why needed

The canonical message stream now contains independently versioned records from three source adapters. Applying the ChatGPT `1.1.0` contract to every record created false failures and obscured real schema defects.

## Tests and evidence

- Focused version-awareness tests: **4 passed**.
- Full reconciliation validator: **PASS**, all checks true.
- Validated profile inventory:
  - `1.1.0 | chatgpt-json`: 68,761
  - `2.0.0 | other-ai-export-fragments`: 3,080
  - `1.0.0 | copilot-csv`: 400
- Original ChatGPT graph, raw hashes, read-only custody, pilot compatibility, and filtered baseline report hash remain valid.
- No message, provenance record, manifest entry, ingest report, or raw source was rewritten by this maintenance.

## Remaining risks

- Each future adapter version requires a new immutable schema and explicit dispatch entry.
- The 305 MB mixed stream makes validation sensitive to machine memory pressure; bounded sampling validates structure while exact-key and identity checks still cover every record.

## Recommended next step

Proceed with Slice 2 fixture-tested one-way projection publishing. Do not enable production publication until a real accepted canonical record exists.
