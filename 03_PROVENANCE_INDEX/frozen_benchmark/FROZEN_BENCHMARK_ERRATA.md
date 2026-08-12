# PROVENANCE_INDEX_V0.2_FROZEN_BENCHMARK — Errata

Per `MASTER_BRAIN_BUILD_SPEC.md` §6.0h (Evidence Truth vs. Adjudication Truth):
frozen benchmark files are never edited in place. Corrections are recorded here
and superseded fields are tracked explicitly, the same pattern already used for
`gold_037` in the Gold Set errata.

## Correction 1 — fb_002 `reuse_record_id` was corrupted

- **Frozen value** (`frozen_benchmark_cases.jsonl`, unedited): `reuse_record_id: "6a6edbc1-verified-df74d65b"`
- **Defect**: this is not a real corpus message ID — it does not exist in `CORPUS_RELEASE_001`. It appears to be a copy-paste artifact from pre-compaction work (a fragment of the conversation ID `6a6edbc1...` concatenated with the literal word `verified` and a fragment of the true message ID `df74d65b...`).
- **Correct value** (verified against `14_TESTS_AUDITS/provenance_gold_set_v1.jsonl` gold_016, which independently records the same case): `reuse_record_id: "df74d65b-86c1-4612-b691-21eb68edd205"`
- **Discovered**: during scoring (`score_v0_2.py`), when the corrupted ID produced a spurious "V0.2 found no hit" result for a case that had been extensively hand-verified as a confirmed derivation (the "Business Character Method" case, `thought_pilot_0003`).
- **Corrected scoring result**: re-run against the real ID confirms V0.2 (`reuse_hits.jsonl`, `rh2_002988`) correctly resolves this as `DERIVATION_EDGE`, `chronology_valid: true`, `exact_copy_indicator: true`, `reuse_side_coverage: 0.9809` — an exact match with fb_002's ground truth (`derived_from_candidate: YES`, `true_corpus_origin: YES`, `intellectual_origin: assistant`).
- **Effect on metrics**: fb_002 is excluded from the raw `score_v0_2.py` output (`v02_found_any_hit: false` there is an artifact of the bad ID, not a V0.2 miss) and counted using the corrected result below in `FROZEN_BENCHMARK_REPORT.md`. This is a data-entry bug in my own case file, not a V0.2 defect — flagging it as such rather than either silently fixing the frozen file or silently letting it inflate V0.2's apparent miss rate.

## Correction 2 — fb_013 / fb_014 chronological order was reversed in my original notes

- **Frozen values** (`frozen_benchmark_cases.jsonl`, unedited): fb_013's note calls it the first occurrence and fb_014 "a second reuse... ~11 minutes later."
- **Defect**: verified directly against `CORPUS_RELEASE_001` timestamps: fb_013 (`aaa21a91-13d6-43c7-b9e0-650e2e1e6d5a`) is `2024-03-27T21:54:29`, fb_014 (`aaa2c7ca-7941-4c51-aa2b-db4c8a105c3d`) is `2024-03-27T21:43:20` — **fb_014 is actually ~11 minutes earlier than fb_013**, the reverse of what my original note says. This was my own error when writing the frozen case, not a V0.3 finding, but it was V0.3's evaluation run that surfaced it: V0.3 (correctly, per its own chronology-first rule) resolved fb_013 as derived from fb_014, not from the ultimate origin message, which only made sense once I checked the real timestamps and found my own note had the order backwards.
- **Effect on scoring**: fb_013/fb_014's `derived_from_candidate: YES` / `true_corpus_origin: YES` ground truth is still correct (both really are derived from the same origin chain), but the specific `candidate_origin_record_id` each case names is the *root* of the chain, not the nearest link — see the V0.3 evaluation report's discussion of chain-vs-root scoring for why this affects several cases, not just these two.

No other corrections identified as of this pass.
