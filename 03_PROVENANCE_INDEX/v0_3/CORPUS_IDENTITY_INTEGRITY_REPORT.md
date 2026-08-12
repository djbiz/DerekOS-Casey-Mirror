# Corpus Identity Integrity — Remediation Report

**Scope of this pass, per the Architecture Board's directive: identity remediation, corrected release, and blast-radius analysis only. Stops here.** No provenance index has been rebuilt from `CORPUS_RELEASE_002`. `provenance_index_v0_3.py` was not modified or re-tuned. No Resolver V0.6 work, out-of-sample challenge, or Conglomerate/canonicalization work was touched. `CORPUS_RELEASE_001` was not rewritten (SHA-256 verified unchanged before and after this pass).

## 1. Root cause, verified against immutable raw sources (not inferred from ingested output)

42 `message_id` values in `CORPUS_RELEASE_001` are not globally unique (2,985 duplicate records out of 72,241). Two distinct, independently confirmed causes:

**A. 39/42 IDs — the "other-ai-export" source's native per-conversation-scoped node keys were copied into the global `message_id` field unnamespaced.** Confirmed by reading `00_RAW_ARCHIVE/other-ai-export/conversations.json` directly: it contains 465 conversation objects, each with its own `mapping` dict whose keys are simple sequential integers (`"1"`, `"2"`, `"3"`, ...) - correct and unambiguous *within* that source's own structure (each conversation has a real, globally-unique `id`), but the ingest path (`01_INGEST/delta_ingest.py`) wrote the raw per-conversation node key directly into the global `message_id` field without combining it with the conversation ID. This is why `message_id: "2"` appears in 469 different conversations.

**B. 3/42 IDs — ChatGPT's own raw export can legitimately reuse one node UUID across multiple separate conversation records.** Confirmed directly in `00_RAW_ARCHIVE/chatgpt/conversations-023.json`: node id `bbb21829-9a84-455a-920e-2546e06a8e73` appears in three separately-exported conversations titled "Chess Business App Dev" / "iOS Chess Business App" / "Business Chess App Dev" - consistent with ChatGPT conversation branching/regeneration producing multiple export records that share a common history prefix (and therefore share early node UUIDs) before diverging. Not an ingest defect; a real property of the raw source.

**Conclusion: `message_id` alone was never a safe global key, for two structurally different reasons.** Even the weaker fallback of `(message_id, conversation_id)` is insufficient - see §3.

## 2. Canonical identifier established: `source_record_id` (no new scheme invented)

`source_record_id` already exists on every `CORPUS_RELEASE_001` record and is already computed deterministically from immutable source coordinates by all three ingest paths:
- `ingest.py` (ChatGPT): `srcmsg_` + sha256(`source_file`, `conversation_id`, `message_id`)[:32]
- `delta_ingest.py` (other-ai-export): `srcmsg_` + sha256(`source_sha256`, `conversation_id`, `node_id`, `fragment_index`)[:32]
- `copilot_csv_ingest.py`: deterministic hash of (`source_sha256`, `title`, `row_number`)

Verified directly: **72,241/72,241 records have a non-null `source_record_id`, and all 72,241 values are distinct - zero collisions.** This already satisfies the instruction's stated preference ("prefer the existing deterministic `source_record_id` where available"). No new ID-generation scheme was built.

## 3. Why `(message_id, conversation_id)` alone would still not have been safe

While building `CORPUS_RELEASE_002`, 48 `(message_id, conversation_id)` pairs were found to map to *more than one* `source_record_id` - all in the other-ai-export source, all differing only by `fragment_index`. This happens when one raw mapping node's content is split into multiple ingest fragments (e.g. a combined request/response node). `source_record_id`/`canonical_id` (which incorporates `fragment_index`) is the only field that resolves these uniquely; the compound pair would not have been.

## 4. CORPUS_RELEASE_002 built

`13_SOURCE_INDEX/corpus_releases/build_corpus_release_002_identity_repair.py` reads **only** `CORPUS_RELEASE_001` (not the live, actively-mutated `01_INGEST/messages.jsonl`, which has diverged since CORPUS_RELEASE_001 was frozen and would have mixed unrelated changes into this repair). It verifies the parent's SHA-256 before running, and applies exactly one transform: adds an explicit `canonical_id` field (alias of the pre-existing `source_record_id`) to every record. `message_id` is preserved byte-for-byte as platform-native source metadata - never overwritten, never destroyed.

```
CORPUS_RELEASE_002: 72,241 records (all preserved, none dropped)
parent: CORPUS_RELEASE_001 (sha256 verified unchanged before build)
canonical_id: 72,241/72,241 distinct (100% unique)
message_id: preserved unmodified on every record
```

`test_corpus_identity_integrity.py` (also in `13_SOURCE_INDEX/corpus_releases/`) validates: canonical IDs globally unique, `message_id` preserved vs. parent, and documents that `message_id` alone would not resolve uniquely (48 pairs, §3) - confirming why `canonical_id` is required. **All 5 applicable checks pass.** The suite also includes coverage-ratio/chronology/chain-reference checks that will run against a *rebuilt* index's output - they currently skip (no index has been built from `CORPUS_RELEASE_002` yet, correctly, per the stop condition).

## 5. Blast-radius analysis

### 5a. Provenance index artifacts (mine, all three generations - same bug, inherited unmodified across versions)

| Artifact | Total hits/candidates | Touching a colliding ID |
|---|---|---|
| v0.1 `reuse_hits.jsonl` | 4,502 | 1,226 (27.2%) |
| v0.1 `origin_candidates.jsonl` | 18,797 | 10,458 (55.6%) |
| v0.1 `reuse_chains.jsonl` | 276 | 0 (0.0%) |
| v0.2 `reuse_hits.jsonl` | 6,052 | 2,588 (42.8%) |
| v0.3 `reuse_hits.jsonl` | 19,495 | 6,215 (31.9%) |

Code-level cause, confirmed in all three: `03_PROVENANCE_INDEX/{v0_1,v0_2,v0_3}/*.py` each build `by_id = {m["message_id"]: m for m in messages}` (v0.1's `cross_source_reuse_index.py:97`, v0.2's `provenance_index_v0_2.py:207`, v0.3's `provenance_index_v0_3.py:152`, and a duplicate root-level copy of the v0.1 script) - a bare-key dict comprehension that silently keeps only the last-loaded record for any colliding id. This is the exact mechanism that produced the mathematically-impossible `origin_side_coverage: 2.628` value that first surfaced this bug during V0.3's evaluation.

### 5b. My two frozen benchmarks

- **`frozen_benchmark/frozen_benchmark_cases.jsonl` (30 cases, V0.2 benchmark)**: 1 case affected - `fb_015` (the AXIOMOS long-document case), whose `reuse_record_id` (`"1"`) and `candidate_origin_record_id` (`"6"`) are both colliding IDs. The case's *qualitative conclusion* (large document, correctly demoted to `SIMILARITY_EDGE`, no false promotion) is not in question, but the specific hit-count claims made about it ("0/63 false match" in the V0.2 evaluation) are unverifiable at face value.
- **`frozen_benchmark_v0_3/frozen_benchmark_v0_3_cases.jsonl` (6 cases, V0.3 tranche)**: 3 of 6 cases affected - `fbv3_001`, `fbv3_002` (both use colliding origin IDs `"1"`/`"3"`), and `fbv3_006` (a negative control whose reported hit was directly confirmed to be a collision artifact, not a real match). This is the majority of that tranche, including its intended headline case.

### 5c. Gold Set - clean

`provenance_gold_set_v1.jsonl` and `_v1_1.jsonl` (40 records each): **0 affected.** Neither `message_id` nor `origin_message_id` on any record touches a colliding ID.

### 5d. Resolver lane (Codex, `14_TESTS_AUDITS/`) - the most severe exposure found

This is not my lane and nothing here was modified, but the exposure is severe enough to require reporting in full, especially given the Architecture Board's explicit concern about the V0.6 out-of-sample challenge:

- **`PROVENANCE_OUT_OF_SAMPLE_SET_V1.jsonl` (163 records) - 159 affected (97.5%).** Nearly the entire out-of-sample set is built from other-ai-export records carrying colliding `message_id` values.
- **`FROZEN_ADJUDICATION_V1.jsonl` and `FROZEN_OUT_OF_SAMPLE_ADJUDICATION_V1.jsonl`** - the frozen ground-truth labels V0.6 scoring reads directly - carry a field named `origin_record_id` that is in fact populated from bare `message_id` (`finalize_adjudication_v1.py:332,344`; `freeze_out_of_sample_adjudication_v1.py:32,41-45`), with **zero** `origin_conversation_id` occurrences anywhere in either file. The field name implies a safe canonical id; it isn't one.
- **`PROVENANCE_ADVERSARIAL_SET_V1.jsonl` (230 records) - 11 directly affected (4.8%)**, but a second, structural issue is more concerning: `build_adversarial_set_v1.py`'s final dedup pass (`chosen_by_id`, lines 320-326) keys on bare `message_id` - meaning records from *different* conversations that happen to share a colliding id would be silently treated as duplicates and **dropped from the benchmark population itself**, not just misattributed. This can bias which 230 cases exist at all, not only what's said about them.
- **`build_adjudication_bundle.py` and `build_out_of_sample_bundles_v1.py`** show a partial, incomplete mitigation: a conversation-aware `resolve()` helper exists, but its coverage is gated on `ingest_version == "2.0.0"` - records from the other-ai-export source (the dominant source of colliding ids) may not carry that version tag and would fall through to the unsafe bare-id path. Someone on that lane had already noticed part of this problem; the fix didn't fully close it.
- **Resolver stage1/stage2 evidence pipelines** (`provenance_resolver_v0_1/stage1_evidence.py`, `stage2_segment.py`, and their `v0_2` counterparts, plus the top-level `provenance_resolver_v0_1.py:490-497` / `v0_2.py:619-622`) independently build bare-`message_id`-keyed lookup dicts used to resolve gold-set records during benchmark scoring runs.
- **Confirmed clean**: `provenance_resolver_v0_3.py` through `v0_6.py` themselves only read fields off an already-scoped dict passed to them - no new bare-id dict construction in the resolver classification code proper. The exposure is in the *data feeding* those versions (the frozen adjudication/out-of-sample files above), not in v0.3-v0.6's own logic.

### 5e. Clean, no action needed

`01_INGEST/` (only assigns/computes ids, never looks up by bare `message_id`), `02_EXTRACTED_THOUGHTS/` (no `message_id` references), `13_SOURCE_INDEX/corpus_releases/freeze_release.py`, `master_brain_bridge/`, `08_MASTER_PLAN/` docs (narrative mentions only).

## 6. Marking affected evaluations superseded (not deleted, not edited in place)

Per instruction, no frozen file is edited. A marker file records which prior evaluations are affected:

- `03_PROVENANCE_INDEX/frozen_benchmark/SUPERSEDED_DUE_TO_IDENTITY_COLLISION.json` - flags `fb_015`'s hit-count claims in `FROZEN_BENCHMARK_REPORT.md` (V0.2) and the corresponding entry in `PROVENANCE_INDEX_V0.3_EVALUATION_REPORT.md` (V0.3).
- `03_PROVENANCE_INDEX/frozen_benchmark_v0_3/SUPERSEDED_DUE_TO_IDENTITY_COLLISION.json` - flags `fbv3_001`, `fbv3_002`, `fbv3_006`'s V0.3 scoring results.

Both frozen case files themselves remain byte-identical; the marker files are new, separate, additive records - not modifications.

## 7. What happens next (not performed in this pass)

Per the Architecture Board's gate: **Corpus identity integrity (this report) → corrected frozen release (done, §4) → rebuilt provenance index → index validation (`test_corpus_identity_integrity.py`'s §5-6 checks) → V0.6 out-of-sample challenge → `PROVENANCE_CORPUS_V1`.** This pass stops after the first two stages plus this blast-radius analysis, as instructed. In particular:

- The 4,566 previously-invisible directional edges (`derek->derek`, `derek->chatgpt_assistant`, `derek->other_ai_assistant`) reported in the V0.3 evaluation remain a real, positive architectural finding supporting direction-neutral discovery - but those exact counts should be re-derived from a `CORPUS_RELEASE_002`-based rebuild before being treated as established, since roughly a third of V0.3's hits touch a colliding id.
- The Resolver's out-of-sample challenge should not run against the current `PROVENANCE_OUT_OF_SAMPLE_SET_V1.jsonl` / `FROZEN_OUT_OF_SAMPLE_ADJUDICATION_V1.jsonl` given 97.5% exposure - that is a decision and a rebuild for the Resolver lane, not performed here.
- `provenance_index_v0_3.py` was not modified in response to any of this - the code that needs to change (swap `by_id`'s key from `message_id` to `canonical_id`, and read `canonical_id` throughout instead of `message_id`) is straightforward but is explicitly deferred to the "rebuilt provenance index" gate, not bundled into this remediation pass.
