# Provenance Gold Set v1 — Errata

**`provenance_gold_set_v1.jsonl` is immutable and remains unchanged (verified byte-identical before and after this document was written).** This errata records two labels that later provenance evidence proved incorrect. The corrected labels live in `provenance_gold_set_v1_1.jsonl`, derived from v1 with only these two records changed. This is append-only history, not a rewrite: the original v1 adjudication is preserved as the historical record; the correction is a new, linked, superseding adjudication — matching the Evidence Truth / Adjudication Truth distinction in `MASTER_BRAIN_BUILD_SPEC.md` §6.0h.

Both corrections were discovered as a side effect of building `PROVENANCE_RESOLVER_V0.1`'s Stage 1 (exhaustive cross-corpus shingle index) — **before** any Stage 3 classification or benchmark scoring ran. This is why they qualify as legitimate corrections rather than post-hoc tuning: the new evidence was found during tool construction, independent of and prior to any resolver's graded output.

---

## Correction 1: `gold_019`

| Field | v1 (original) | v1.1 (corrected) |
|---|---|---|
| `evidence_class` | `P0` | `P0` (unchanged) |
| `submitted_by` | `derek` | `derek` (unchanged) |
| `original_author` | `unknown` | `assistant` |
| `origin_message_id` | `null` | `02170d3e-daf5-41f3-a576-d749873d00d6` |
| `origin_conversation_id` | `null` | `66e00b26-a02c-8006-b369-2b291de52cff` |
| `provenance_certainty` | `PC1` | `PC4` |

**Record**: "LinkedIn Title Enhancement" (`aaa2f22e-d78d-45e8-97a1-5fe5906d2480`, 2024-09-13T18:35:48Z) — Derek pastes a LinkedIn headline and asks the assistant to add a phrase to it.

**Exact origin found**: "Remote Hiring Benefits" (`02170d3e-daf5-41f3-a576-d749873d00d6`, conversation `66e00b26-a02c-8006-b369-2b291de52cff`, **2024-09-11T01:39:03Z**, two days earlier) — an assistant message proposing "Tweaked Version: **Helping Aspiring Entrepreneurs Build Financial Freedom** 🤑 | Chief Fun Officer | Social Media Expert 📱 | Business Mentor 💡 | Professional Connector 🤝 | Peak Performance Coach 🚀" — verbatim match to what Derek later pastes.

**Evidence method**: `PROVENANCE_RESOLVER_V0.1` Stage 1 shingle index (12-word rolling window overlap against every assistant message in the full corpus, `14_TESTS_AUDITS/provenance_resolver_v0_1/stage1_evidence.py`). Match confirmed by direct read of both messages in `01_INGEST/messages.jsonl`.

**Why the original adjudication missed it**: the v1 label was built during the 10-record pilot phase, before the exhaustive Stage-1 shingle index existed. The manual cross-corpus search performed at the time was a targeted keyword/title search (looking for terms like "linkedin," "headline"), not an exhaustive text-overlap search — it did not check this specific short (222-character) message against the full 35,000+ assistant-message corpus. `PROVENANCE_RESOLVER_V0.1`'s Stage 1 does that exhaustively, which is precisely why it found what a targeted manual search missed.

---

## Correction 2: `gold_037`

| Field | v1 (original) | v1.1 (corrected) |
|---|---|---|
| `evidence_class` | `UNRESOLVED` | `P0` |
| `originator` | `unresolved` | `assistant` |
| `submitted_by` | (not set) | `derek` |
| `origin_message_id` | `null` | `4df2be21-cf21-474f-af92-6676e3e17fe6` |
| `origin_conversation_id` | `null` | `692ddf57-7e08-8328-86b7-5845d98f13d0` — *(see note below: actual conversation is "Flowla for DAC Funding")* |
| `provenance_certainty` | `PC1` | `PC4` |
| `requires_review` | `true` | `false` |

**Record**: "Empire Blueprint Enhancement" (`bbb21242-c081-42a4-b39b-df1a93fa0d58`, 2025-05-25T23:44:30Z) — a `role: user` message reading in unmistakable assistant voice ("Let me know your city, and I can even help scout ideal locations..."), which v1 deliberately left `UNRESOLVED` after a genuine but non-exhaustive manual search found nothing.

**Exact origin found**: "Flowla for DAC Funding" (`4df2be21-cf21-474f-af92-6676e3e17fe6`, **2025-05-25T06:37:26Z**, ~17 hours earlier the same day) — `role: assistant`, word-for-word identical opening ("Opening a real physical location can be a *power move*—but only if the timing, purpose, and economics make sense...") through the full structured breakdown.

**Evidence method**: same Stage 1 shingle index. Origin verified by direct read of the source message in `01_INGEST/messages.jsonl` — confirmed `role: assistant`, confirmed verbatim text match.

**Why the original adjudication missed it**: the v1-era manual cross-corpus search (`14_TESTS_AUDITS/find_reused_passages.py`, run once during Gold Set construction) capped its output at the top 200 matches by match strength across the *entire* candidate pool, sorted globally. This specific match did not rank high enough to appear in that capped list — not because the match is weak (it isn't; full-message verbatim overlap), but because many other, unrelated matches in the corpus had numerically higher shingle counts (longer messages produce more matching shingles) and crowded out this one's visibility in a global top-200 cut. `PROVENANCE_RESOLVER_V0.1`'s Stage 1 evidence-package builder runs a fresh, per-message lookup for each of the 40 Gold Set records individually rather than relying on a single globally-capped list, so it did not have this blind spot.

**This is the third confirmed instance of the same pattern** (after Business Character Method and the two Empire-starter-repo reuses already in v1): Derek pasting the assistant's own earlier response into a freshly-started conversation, presumably to continue work with a clean context window.

---

## What did not change

No other v1 record is touched. In particular, `gold_020` (the "9 Things I've learned" listicle, the one genuine resolver disagreement from the v0.1 benchmark) is **not** corrected here — there is no located source evidence for it either way, so per this errata's own standard ("independent source evidence proves the benchmark was wrong," not a re-argued judgment call), it stays as adjudicated in v1 pending `PROVENANCE_RESOLVER_V0.2`'s investigation (see `BENCHMARK_REPORT_V0.2.md`).

---

## Correction 3 (errata addendum, 2026-08-12): `gold_037` origin conversation ID

While cross-checking `PROVENANCE_RESOLVER_V0.1` against v1.1, the recorded
`origin_conversation_id` for `gold_037` (`692ddf57-7e08-8328-86b7-5845d98f13d0`,
"Empire starter repo breakdown") was found to be **incorrect**. The origin
message `4df2be21-cf21-474f-af92-6676e3e17fe6` resides in conversation
`68326864-d084-8006-bf19-fb8192c961ad` ("Flowla for DAC Funding") — verified
directly in `01_INGEST/messages.jsonl`. `provenance_gold_set_v1_1.jsonl` was
updated to the verified ID. The frozen v1 set remains unchanged.

---

## Freeze status (2026-08-12)

**Gold Set v1.1 is now frozen as the corrected benchmark** (see `FROZEN_V1_1.json`).
Frozen v1 and this errata are preserved permanently as historical evidence of
what changed — nothing in v1 or in this document's earlier corrections is
mutated. Benchmarks may be scored against v1 (historical) or v1.1 (corrected);
both are immutable. Future verified cases go to v1.2+ or
`PROVENANCE_ADVERSARIAL_SET_V1`.
