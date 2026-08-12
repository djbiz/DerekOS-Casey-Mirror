# CANONICAL CORPUS BASELINE HISTORY V0.1

**Purpose:** Establish a clean audit trail of how the Master Brain corpus grew, so every agent can answer "Why are there N records today?" without guessing.

**Current filesystem state (verified 2026-08-12):**
- `messages.jsonl`: **72,241 records**
- `conversations_index.json`: **3,969 conversations**

---

## Corpus Evolution

### Baseline A — Original ChatGPT Export

- **Source:** `00_RAW_ARCHIVE/chatgpt/conversations-000.json` through `conversations-034.json`
- **Files:** 35 canonical JSON files
- **Source SHA-256:** per-file hashes recorded in `13_SOURCE_INDEX/source_manifest.json`
- **Ingestion script:** `01_INGEST/ingest.py` v1.1.0
- **Schema:** canonical ChatGPT mapping-tree export
- **Totals:**
  - Conversations: **3,476**
  - Messages: **68,761**

### Baseline B — After Copilot CSV Import

- **Added source:** `00_RAW_ARCHIVE/copilot/copilot-2026-08-12T11_59_49.315Z.csv`
- **Source SHA-256:** `4d08d154ea75037b884b1799f47ec8d561629f80b2c8b4311affffa858713b98`
- **Ingestion script:** `01_INGEST/copilot_csv_ingest.py` v1.0.0
- **Adapter:** `copilot-csv`
- **Schema notes:** Flat CSV with `Conversation, Time, Author, Message`; no native IDs; `Author` preserved as `source_author` and mapped to `role` for schema consistency only
- **Deterministic ID scheme:** `copilot_conv_{sha256(source_hash + "│" + conversation_title)[:32]}` and `copilot_msg_{sha256(source_hash + "│" + conversation_title + "│" + row_number)[:32]}`
- **Conversations imported:** **28** (27 named + 1 synthetic for 10 rows sharing empty title)
- **Messages imported:** **400**
- **New totals:**
  - Conversations: **3,504**
  - Messages: **69,161**

### Baseline C — After Other-AI Delta Import

- **Added source:** `00_RAW_ARCHIVE/other-ai-export/conversations.json`
- **Source SHA-256:** `2e3d2b5a1cae429a3162c117045dd038de6c076814c41bac3ef71fe335baac74`
- **Ingestion script:** `01_INGEST/delta_ingest.py` v2.0.0
- **Adapter:** `other-ai-export-fragments`
- **Schema notes:** Array-of-conversations format with `mapping` nodes containing `message.fragments[{type, content}]`; fragment types observed: `REQUEST`, `RESPONSE`, `SEARCH`, `THINK`, `FILE`; `model` preserved per node
- **Deterministic ID scheme:** `srcmsg_{sha256(source_hash + "│" + conversation_id + "│" + node_id + "│" + fragment_index)[:32]}`
- **Conversations imported:** **465**
- **Records imported:** **3,080** (one per fragment)
- **New totals:**
  - Conversations: **3,969**
  - Messages: **72,241**

---

## Source File Inventory

| Source File | Format | Conversations | Messages | SHA-256 |
|-------------|--------|---------------|----------|---------|
| `conversations-000.json` through `conversations-034.json` | canonical-chatgpt | 3,476 | 68,761 | per-file in source_manifest.json |
| `copilot-2026-08-12T11_59_49.315Z.csv` | copilot-csv | 28 | 400 | `4d08d154ea75037b884b1799f47ec8d561629f80b2c8b4311affffa858713b98` |
| `conversations.json` | other-ai-export-fragments | 465 | 3,080 | `2e3d2b5a1cae429a3162c117045dd038de6c076814c41bac3ef71fe335baac74` |
| **Total** | | **3,969** | **72,241** | |

---

## Authorship Coverage

| Source Format | User/Request | Assistant/Response | System/Unknown | Total Unknown-Role |
|---------------|--------------|-------------------|----------------|-------------------|
| canonical-chatgpt | included | included | — | — |
| copilot-csv | `Human` → `role: user` | `AI` → `role: assistant` | — | — |
| other-ai-export-fragments | `REQUEST` → `role: user` | `RESPONSE` → `role: assistant` | `SEARCH`, `THINK`, `FILE` → `role: null` | **51** |

**Note on 51 unknown-role records:** These are `SEARCH` (43), `THINK` (6), and `FILE` (2) fragments from the other-AI export. They are non-authorial provenance events by default. They must not later become `D0`/`A0` merely because they contain substantive text. Recommended future classification: `T0 = tool/search/thought/execution trace`.

---

## The 75,321 Discrepancy

During the Other-AI delta import, a failed rerun of `delta_ingest.py` duplicated the 3,080 delta records, producing a transient state of **75,321 messages** in `messages.jsonl`. The subsequent deduplication pass (`14_TESTS_AUDITS/dedup_ingest.py`) removed the duplicates, restoring the correct count of **72,241**.

The Copilot import reconciliation report (`COPILOT_IMPORT_RECONCILIATION_REPORT.md`) captured one intermediate snapshot of this transient state:
- Messages before Copilot import: 74,921
- Copilot messages imported: 400
- Messages after Copilot import: 75,321

Another agent subsequently reported the 75,321 figure without re-verifying the current filesystem. **The current canonical filesystem state is 72,241 messages, 3,969 conversations.**

---

## Cross-Source Provenance Notes

- **Copilot ↔ ChatGPT overlap:** 38 candidate cross-source matches identified in `14_TESTS_AUDITS/copilot_chatgpt_overlap.json`. The flagship case is the "Legacy Forge Shared Business Context" document, verified to be ChatGPT-invented content pasted into Copilot and polished — not Derek-supplied facts.
- **Other-AI ↔ ChatGPT overlap:** Not yet analyzed. The other-AI export uses DeepSeek models and contains Pain2Book, autonomous empire, video creation, pricing, and affiliate system conversations.
- **Cross-source reuse index:** `14_TESTS_AUDITS/cross_source_reuse_index.json` contains Copilot origin references; other-AI cross-source tracing is pending.

---

## Deterministic ID Verification

| Source | ID Scheme | Verified Deterministic |
|--------|-----------|------------------------|
| canonical-chatgpt | `srcmsg_{sha256(source_file + "│" + conversation_id + "│" + message_id)[:32]}` | Yes (original ingest) |
| copilot-csv | `copilot_conv_{sha256(source_hash + "│" + conversation_title)[:32]}` and `copilot_msg_{sha256(source_hash + "│" + conversation_title + "│" + row_number)[:32]}` | Yes (per reconciliation report) |
| other-ai-export-fragments | `srcmsg_{sha256(source_hash + "│" + conversation_id + "│" + node_id + "│" + fragment_index)[:32]}` | Yes (3,080/3,080 verified) |

---

## Next Steps

Per approved lane boundaries:
- **Semantic extraction:** NOT started
- **Provenance classification:** NOT started
- **Canonical knowledge generation:** NOT started
- **Next gate:** Adversarial provenance validation / provenance index verification

The corpus is complete at Baseline C. Do not advance totals without reconciling against the current filesystem first.
