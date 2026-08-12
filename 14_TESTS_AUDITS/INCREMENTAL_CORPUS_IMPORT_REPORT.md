# INCREMENTAL CORPUS IMPORT REPORT

**Generated:** 2026-08-12T11:45:22.253548+00:00
**Candidate file:** `conversations.json`
**Source SHA-256:** `2e3d2b5a1cae429a3162c117045dd038de6c076814c41bac3ef71fe335baac74`
**Source size:** 107,422,950 bytes (102.4 MB)

## Summary

- **Candidate conversations:** 465
- **Candidate messages:** 3,032
- **Canonical conversations:** 3,476
- **Canonical messages (raw archive):** 68,756
- **Canonical messages (ingested):** 68,756

## Comparison Results

- **New conversations:** 465
- **Overlapping conversations:** 0
  - Exact duplicates: 0
  - With new/additional content: 0
  - Conflicting versions: 0

## New Conversations (sample)

- `a00ea0fe-ef30-423b-9959-2467b55cff6f` — Autonomous Retail Pod for Last-Mile Commerce
- `fe238563-6e8c-41e1-ae03-3677a487d697` — Building AI Framework for Autonomous Empire
- `02b68320-b780-458a-aa0a-98c5433e6cda` — Ultimate AI-Driven TikTok Automation Engine
- `eeb9afa3-09fb-4b4b-be1e-632f1e25b877` — Python Fundraising OS System Implementation
- `35209a8a-f061-4bc5-a5a6-5e07f1364d97` — Autonomous Ops Engine Generative Strategy Integration
- `d981de11-83c4-4069-a418-1140391632df` — Super Brain MVP: MCP API and Cockpit Development
- `d7fc5110-0089-45cc-917a-31a8e1a8df3f` — Alpha Engine Advanced PPO Multi-Asset Trading System
- `2997fde7-0b4e-40ed-883e-eb958111710e` — Engineering Log Review
- `93188e37-8ce0-4693-96b5-66be7a1a9bbf` — Python Code for Hedge Fund Launch Blueprint
- `e6867977-5135-43ce-a00d-81b88a7e5c12` — Advanced AI-Powered Notion Integration Strategy
- `eb2a8817-8c24-417d-9aa8-39bbc400b2f9` — Universal AI Content System Development Plan
- `7b565459-c71e-44df-9738-c2a0e83afa9c` — Curious About User's Recent Action
- `80ef40ef-e318-44da-85de-be0c3e9fc14e` — SSCP-Nano: The Final Evolution of Programmable Matter
- `96b7448f-1d47-407a-9ac7-a4b588220a0d` — AI-Powered Sales CRM Platform Development
- `edba4141-d0ab-44d1-8df1-4bb7f6065ea6` — AI-GWS Multi-Agent System Interoperability Framework
- `a946d4d9-6942-4c8e-8220-aedd11f7cd4a` — Integrating Somatic AI with Swarm Matter
- `5cf882f3-78c3-4b5b-acda-63fa8257d47c` — Autonomous Enterprise Workflow for Planetary Media
- `35f76b2b-e098-4aba-bd81-97ee76e87442` — Sales Skyscraper App with Bot Integration
- `50ea5f89-15a4-41f9-a8d2-288180a63066` — IdentityRX Behavioral Sales Engine Ready
- `06c04cdf-d9a2-403d-abe2-b897cd537de2` — Trust Intelligence Drives Sales Automation
- ... and 445 more

## Overlapping Conversations (sample)

_No overlapping conversations found._

## Recommendation

**APPROVE INCREMENTAL IMPORT.** 465 new conversations detected. Proceed with delta ingestion into `01_INGEST/` while preserving source provenance (source_file, conversation_id, message_id, timestamps, parent/child topology, source_hash).

---

## Post-Import Validation

**Delta ingestion completed successfully.**

### Final Corpus State

- **Total conversations in index:** 3,969
  - Canonical JSON files: 3,476
  - Copilot CSV (pre-existing): 28
  - Delta import (other-ai-export): 465
- **Total messages in messages.jsonl:** 72,241
  - Canonical JSON files: 68,761
  - Copilot CSV (pre-existing): 400
  - Delta import (other-ai-export): 3,080

### Validation Results

- **Duplicate conversation IDs introduced:** 0
- **Duplicate source_record_ids introduced:** 0
- **Orphaned nodes:** 0
- **Topology failures (cycles + unreachable):** 0
- **Timestamp parse failures:** 0
- **Records with unknown authorship:** 51
  - All are `SEARCH` or `THINK` fragment types from the other-ai-export
  - Preserved with `role: null` to avoid fabricated attribution

### Deterministic ID Verification

- **All 3,080 delta `source_record_id` values verified deterministic**
- **Deterministic ID mismatches:** 0
- **ID formula:** `srcmsg_{sha256(source_hash + "│" + conversation_id + "│" + node_id + "│" + fragment_index)[:32]}`

### Source Format Metadata Preserved

- `source_format`: `other-ai-export-fragments`
- `fragment_type`: REQUEST, RESPONSE, SEARCH, THINK, FILE
- `model`: preserved per message node (e.g., `deepseek-chat`)
- `message_id`: set to `node_id` (no explicit message IDs in source)
- `source_sha256`: `2e3d2b5a1cae429a3162c117045dd038de6c076814c41bac3ef71fe335baac74`

### Next Steps

Per approval, semantic extraction and canonical knowledge generation are deferred until:
1. Provenance resolver validation passes on the expanded corpus
2. Adversarial provenance validation gate is cleared

---

_This report was generated automatically. Do not modify the frozen Gold Set._