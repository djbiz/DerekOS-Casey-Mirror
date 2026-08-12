# Copilot Import Reconciliation Report

**Generated:** 2026-08-12T12:44:10.376416+00:00
**Source file:** `D:\Projects\VOX\DerekOS_Master_Brain\00_RAW_ARCHIVE\copilot\copilot-2026-08-12T11_59_49.315Z.csv`
**Source SHA-256:** `4d08d154ea75037b884b1799f47ec8d561629f80b2c8b4311affffa858713b98`
**Ingest version:** 1.0.0

Pre-import analysis: `14_TESTS_AUDITS/COPILOT_INCREMENTAL_CORPUS_IMPORT_REPORT.md` (read first - contains the Legacy Forge provenance-laundering finding this ingestion preserves rather than resolves).

## Summary

- **Messages in corpus before this run:** 74,921
- **Copilot messages imported:** 400
- **Messages in corpus after this run:** 75,321
- **Conversations imported:** 28 (of 28 found in the source file)

## Chronology reconstruction

- **Conversations where sorting by Time changed the original CSV row order:** 28 — confirms the pre-import finding that CSV row order is not reliably chronological. Every record's `source_csv_row_number` preserves its original position for full audit/reconstruction regardless of the reordering applied here.
- **Tie-break rule applied:** same-timestamp Human/AI pairs ordered Human-before-AI (a request logically precedes its response) — a disclosed heuristic, not a guarantee from the source data itself.

## Data quality

- **Empty-`Message` rows imported as-is (not dropped):** 29 — consistent with the "no silent drops" principle; these are real records (likely attachment-only shares) with legitimately empty text, not a parsing failure.
- **Unparseable timestamps:** 0
- **Duplicate `source_record_id`s (should be 0 on a clean run):** 0

## What this ingestion does NOT do

- **Does not assign `evidence_class`, `originator`, or any provenance judgment.** `Author=Human` is preserved verbatim as `source_author` and separately mapped to `role: "user"` for schema consistency only — neither field is treated as evidence of Derek authorship. That determination is the provenance resolver's job (`MASTER_BRAIN_BUILD_SPEC.md` §6, §12.7), identical to how ChatGPT's `role: user` is treated.
- **Does not resolve the Legacy Forge finding.** The traced lineage (ChatGPT-invented content -> pasted into Copilot -> polished) is preserved as-is in the ingested records; a future cross-source provenance pass links `origin_message_id`s back to the ChatGPT corpus (`14_TESTS_AUDITS/copilot_chatgpt_overlap.json` already has 38 candidate cross-source matches from the pre-import check, not yet formalized into `03_PROVENANCE_INDEX/`).
- **Does not begin SOP extraction or canonicalization.**

## Deterministic rerun verification

Re-running this script on the same source file produces identical `source_record_id` values for every row (stable hash of source SHA-256 + conversation title + row number) — existing records are matched and skipped, not duplicated.
