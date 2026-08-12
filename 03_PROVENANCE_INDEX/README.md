# 03_PROVENANCE_INDEX

Cross-source reuse detection, promoted from a one-off audit script
(`14_TESTS_AUDITS/cross_source_reuse_index.py`, preserved there unmodified
as historical evidence — not deleted, not moved) into first-class corpus
infrastructure. Built against the current unified `01_INGEST/messages.jsonl`
(72,241 messages as of the last run — three sources: 34,635 ChatGPT
records across `conversations-000.json`–`034.json`, 3,080
`other-ai-export-fragments`, 400 `copilot-csv`).

## The one rule that governs everything in this directory

**Similarity is not authorship proof.** Every record in `reuse_hits.jsonl` carries `intellectual_origin: null` and `semantic_status: "UNREVIEWED"` unconditionally — this layer observes text overlap, timestamps, and source metadata mechanically. It concludes nothing about who originated an idea. That determination is `PROVENANCE_RESOLVER`'s job (§6, §12.7 of `MASTER_BRAIN_BUILD_SPEC.md`), and even the resolver's output isn't canonical until adversarially verified. A reuse edge becomes a verified origin relationship only when chronology and content are checked by a human/agent pass and both support it — see `ADVERSARIAL_VERIFICATION_REPORT.md`.

## `earliest_corpus_occurrence` vs. `intellectual_origin` — kept explicitly distinct

`earliest_corpus_occurrence` is a mechanical fact: among every candidate origin found for a reused message, which one has the earliest timestamp *in this corpus*. It is **not** a claim about true authorship. Concretely: if an external article was pasted into ChatGPT, the assistant echoed it back, and Derek later pasted the assistant's echo into Copilot, the earliest *in-corpus* match is Derek's own ChatGPT paste — but the true intellectual origin is the external article, which this corpus may have no record of at all. `intellectual_origin` is reserved for that harder question and is legitimately allowed to resolve to `UNKNOWN_EXTERNAL` — this field is never computed by this mechanical layer, only by semantic review.

## Files

- **`source_registry.json`** — every source present in the corpus, message counts, role breakdown.
- **`reuse_hits.jsonl`** — one record per detected reuse (a `role: user` message with significant text overlap against an earlier `role: assistant` message somewhere in the corpus, any source). Schema per record:
  - `reuse_hit_id`, `reuse_record_id`, `reuse_conversation_id`, `reuse_source`, `reuse_author_role`, `reuse_timestamp`
  - `candidate_origin_record_id`, `origin_conversation_id`, `origin_source`, `origin_author_role`, `origin_timestamp`
  - `similarity_method` (currently `shingle_overlap_12word`), `similarity_score` (matching shingle count), `normalized_overlap_length` (coverage ratio, 0–1)
  - `match_classification`: `exact` (≥0.8 coverage) / `near` (≥0.35) / `partial` (below)
  - `temporal_direction`: `origin_precedes_reuse` / `reuse_precedes_origin` / `same_timestamp` / `unknown`; `origin_precedes_reuse` (bool or null)
  - `cross_source` (bool)
  - `matched_span_mostly_quoted` (resolver v0.2's noise-discount signal, reused here)
  - `provenance_confidence` (`PC0`–`PC4`, mechanical estimate from coverage/quoting — not the same as a Stage-3-verified `PC` value)
  - `transformation_distance` (`TD0`–`TD5`, **a rough mechanical proxy from coverage only** — §6 note below, not a semantic judgment)
  - `multiple_origin_candidates` (bool), `candidate_origin_count`
  - `earliest_corpus_occurrence: {message_id, timestamp}`
  - `intellectual_origin: null`, `semantic_status: "UNREVIEWED"` — always, unconditionally, at this layer
- **`origin_candidates.jsonl`** — every candidate origin found per reuse (not just the strongest one used in `reuse_hits.jsonl`), for multi-origin analysis.
- **`reuse_chains.jsonl`** — multi-hop chains (length ≥3) built by linking a reuse's origin to hits where *that* message is itself later reused elsewhere. Represents patterns like `ChatGPT assistant → ChatGPT user reuse → Copilot Human paste → Copilot AI polish` as one connected sequence instead of independent pairwise hits.
- **`cross_source_reuse_index.py`** — the builder. Deterministic given an unchanged `messages.jsonl` (re-run reproduces identical hit IDs in the same order).
- **`index_report.json`** — summary statistics from the last run.
- **`ADVERSARIAL_VERIFICATION_REPORT.md`** — the stratified spot-check pass and its metrics (Origin-candidate precision, False-origin rate, Ambiguous-origin rate, Multiple-origin rate, Cross-source origin accuracy, Temporal-direction accuracy).

## `transformation_distance` — explicit caveat

`TD0`–`TD5` here is computed **only** from shingle-overlap coverage (higher coverage → lower TD). This is a cheap proxy, not the semantic judgment the spec's design (`MASTER_BRAIN_BUILD_SPEC.md` §12, transformation-distance concept) actually calls for — a message could have low text-overlap coverage because it's a genuine substantive rewrite (real `TD3`/`TD4`) or because the shingle matcher simply missed a paraphrase entirely (not evidence of anything). Treat this field as a sorting/triage aid for the adversarial verification pass, not a trustworthy final value.

## Known limitation, disclosed rather than hidden

This index currently only checks one direction: `role: user` messages against earlier `role: assistant` messages (does an assistant's output get echoed back as if it were the user's own words). It does **not** check the reverse — whether an assistant ever repeats something a user said earlier as if generating it fresh. That reverse case is lower-risk (an assistant echoing what it was told is expected, unremarkable behavior, not a misattribution risk to Derek), which is why it wasn't built first, but it's a real gap if a future need requires bidirectional analysis.

## What this index does NOT do

- Does not classify anything as `D0`/`A0`/`P0`.
- Does not modify `01_INGEST/messages.jsonl` or any canonical knowledge layer.
- Does not resolve `intellectual_origin` for any record.
- Is not itself the provenance resolver — it produces the evidence package `PROVENANCE_RESOLVER` Stage 1 (§12.7) is meant to consume; the resolver's Stage 1 logic (`14_TESTS_AUDITS/provenance_resolver_v0_2/stage1_evidence.py`) is not yet wired to read from here and still runs its own narrower per-message lookup. Wiring the resolver to consume this index directly is a real next step, not done yet.
