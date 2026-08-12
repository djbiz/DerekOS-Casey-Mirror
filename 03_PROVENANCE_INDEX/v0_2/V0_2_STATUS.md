# PROVENANCE_INDEX_V0.2 — Status

## Built and validated against known cases

- Reads from `CORPUS_RELEASE_001` (frozen, `13_SOURCE_INDEX/corpus_releases/`, SHA-256 `66a20833...`), never the live mutable `01_INGEST/messages.jsonl`.
- `SIMILARITY_EDGE` / `DERIVATION_EDGE` / `INTELLECTUAL_ORIGIN` kept structurally distinct — `intellectual_origin: null`, `semantic_status: "UNREVIEWED"` unconditional on every record, same as v0.1.
- Passage-segmentation for messages >15,000 chars (2,500-word passages, 250-word overlap) — the real fix for the AXIOMOS-class bug, not just a warning flag.
- Contiguous/ordered span detection (diagonal-run grouping, not scattered shingle-count) — `longest_contiguous_span_words`, `number_of_matching_spans`, `span_dispersion` reported independently.
- Origin selection never picks by max similarity alone — chronologically-invalid candidates are filtered first; a hit with no valid earlier candidate becomes `edge_type: SIMILARITY_EDGE`, `reverse_match: true` rather than a false `DERIVATION_EDGE`.
- All twelve requested per-candidate fields present: `total_similarity`, `reuse_side_coverage`, `origin_side_coverage`, `longest_contiguous_span_words`, `number_of_matching_spans`, `span_dispersion`, `chronology_valid`, `length_ratio`, `boilerplate_repetition_penalty`, `exact_copy_indicator`, `cross_source`, `multiple_earlier_candidate_count`.

**Direct validation**: the AXIOMOS case (the confirmed bug from v0.1) now produces 12 passage-level hits, **all** correctly `SIMILARITY_EDGE`/`reverse_match: true` — the false `DERIVATION_EDGE` claim is gone. The Business Character Method case (known-good, verified multiple times this session) still correctly resolves `DERIVATION_EDGE`, 98% coverage, valid chronology. Both checked directly against `reuse_hits.jsonl`, not assumed.

**Run totals**: 6,052 hits over 34,131 origin passages (up from whole-message units due to segmentation) — 3,924 `DERIVATION_EDGE`, 2,128 `SIMILARITY_EDGE`/reverse-match (now honestly labeled instead of hidden inside the old 37.3% backward-direction rate).

## Known remaining imprecision, disclosed not hidden

One AXIOMOS passage hit shows `reuse_side_coverage: 1.0451` — still slightly over 1.0, a residual artifact of passage-boundary coverage accounting, not fully eliminated by this pass. Doesn't affect correctness of the `reverse_match` classification (still correctly rejected), but the coverage *number* on that specific record shouldn't be trusted at face value. Flagging rather than rounding away.

## NOT done in this pass — real gaps, not silently skipped

1. **The 150-case frozen, blind adversarial benchmark.** This is a genuinely large, separate undertaking (comparable in effort to the 40-record Gold Set, which took substantial dedicated work on its own) — not attempted here beyond the two direct case validations above. This is the explicit next task, not optional polish.
2. **`PROVENANCE_RESOLVER_V0.3`** (consuming this index as evidence, output schema `submitted_by`/`authored_by`/`reused_from`/`transformed_from`/`adoption_status`/`UNRESOLVED`) — not started.
3. **Wiring to Codex's 69-false-attribution findings** — I have no visibility into that work beyond confirming `08_MASTER_PLAN/reconstruction_pilots/conglomerate/` and `14_TESTS_AUDITS/CONGLOMERATE_DISCOVERY_CANDIDATE_EVIDENCE_V0.1.md` exist on disk; have not read or cross-referenced them against this index.
4. **`PROVENANCE_CORPUS_V1`** and **Conglomerate reconstruction V0.2** — correctly held, per instruction, exactly where Codex left it.
