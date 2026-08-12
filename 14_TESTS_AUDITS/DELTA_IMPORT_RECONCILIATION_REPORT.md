# DELTA IMPORT RECONCILIATION REPORT

**Generated:** 2026-08-12T12:16:07.658227+00:00
**Source file:** `D:\Projects\VOX\DerekOS_Master_Brain\00_RAW_ARCHIVE\other-ai-export\conversations.json`
**Source SHA-256:** `2e3d2b5a1cae429a3162c117045dd038de6c076814c41bac3ef71fe335baac74`
**Source size:** 107,422,950 bytes
**Ingest version:** 2.0.0

## Summary

- **Previous conversations (canonical JSON files):** 3,476
- **Previous conversations (Copilot CSV, pre-existing):** 28
- **Total previous conversations in index:** 3,504
- **Imported conversations:** 465
- **Expected total conversations (JSON files only):** 3,941
- **Actual total conversations in index:** 3,969

- **Previous messages (canonical JSON files):** 68,761
- **Previous messages (Copilot CSV, pre-existing):** 400
- **Total previous messages in index:** 69,161
- **Imported source messages/fragments:** 3,080
- **Expected total messages (JSON files only):** 71,841
- **Actual total messages in index:** 72,241

## Validation

- **Duplicate conversation IDs introduced:** 0
- **Duplicate source_record_ids introduced:** 0
- **Orphaned nodes:** 0
- **Topology failures (cycles + unreachable):** 0
- **Timestamp parse failures:** 0
- **Records with unknown authorship:** 51
  - All unknown authorship records are `SEARCH` or `THINK` fragment types
  - These are system-generated fragments without a user/assistant role
  - They are preserved with `role: null` for completeness

## Deterministic Rerun Verification

- **All 3,080 delta `source_record_id` values verified deterministic** by recomputing from `source_hash + conversation_id + node_id + fragment_index`
- **Deterministic ID mismatches:** 0
- **messages.jsonl hash:** `f7ef56c8beac371727b5a06cd7fe245378f9bfe7c681532fca9363a7558841c0`
- **conversations_index.json hash:** `38900a639c42bacff9f142095a4c71ad5ccb1754bbb7622aaefa158b9b359585`

## Source Format Notes

- Source format: `other-ai-export-fragments`
- Fragment types observed: REQUEST (1,506), RESPONSE (1,523), SEARCH (43), THINK (6), FILE (2)
- Model field preserved per message node (e.g., `deepseek-chat`)
- No explicit message IDs in source; `message_id` set to `node_id`
- Root node has `message: None`; no records emitted for structural nodes
- Conversation timestamps: `inserted_at` / `updated_at` (no `create_time` at conversation level)

## Conversation Index Update

- Existing index entries preserved: 3,504 (includes 28 Copilot CSV conversations)
- New index entries appended: 465
- Total index entries after merge: 3,969
- No duplicate (conversation_id, source_file) pairs detected

## Post-Import Validation

- **Zero duplicate IDs introduced:** confirmed
- **Orphaned nodes:** 0
- **Topology failures:** 0
- **Timestamp parse failures:** 0
- **Deterministic rerun:** all `source_record_id` values reproduce exactly
- **Hash verification:** messages.jsonl and conversations_index.json hashes recorded above

## Next Steps

Per approval, semantic extraction and canonical knowledge generation are deferred until:
1. Provenance resolver validation passes on the expanded corpus
2. Adversarial provenance validation gate is cleared

The 465 conversations are now part of the provenance corpus only.
