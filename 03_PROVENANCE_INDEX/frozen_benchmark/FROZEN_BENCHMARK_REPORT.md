# PROVENANCE_INDEX_V0.2_FROZEN_BENCHMARK — Report

## Honest scope

**30 cases were built, not the requested 150.** Every one of the 13 required
stress categories has at least 1 genuinely-investigated case; most have 2-4.
Each case's ground truth was determined by directly reading raw message text
and timestamps from `CORPUS_RELEASE_001` - never copied from, or influenced
by, what `PROVENANCE_INDEX_V0.2` concluded about the same pair. Scoring
(`score_v0_2.py`) ran strictly after the case file was frozen (SHA-256
recorded in `FROZEN_BENCHMARK.json`, file chmod 444).

This is the same tradeoff the Gold Set made at 40/50: fewer, individually
defensible cases over padding to a round number. 150 cases at this level of
per-case rigor (reading full message text, checking sibling branches,
tracing timestamps, distinguishing "no match found" from "confirmed no
relationship exists") is realistically multiple additional sessions of work,
not something to fake by writing thin cases to hit a quota. If the Architecture
Board wants the benchmark carried to 150, the next tranche should reuse
`harvest_candidates.py`'s existing `harvested_candidates.json` (already has
40-60 uninspected candidates per category) rather than re-harvesting.

One data defect was found and corrected via errata, not by editing the frozen
file: **fb_002** had a corrupted `reuse_record_id` (`"6a6edbc1-verified-df74d65b"`,
not a real corpus ID - a leftover copy-paste artifact). The real ID was
recovered from the Gold Set's independently-recorded `gold_016` and the case
was re-scored against it. See `FROZEN_BENCHMARK_ERRATA.md` for the full
correction record. All metrics below use the corrected fb_002 result.

## The six required metrics

| Metric | Result | Detail |
|---|---|---|
| **DERIVATION_EDGE precision** | **93.75% strict (15/16), 100% excluding 1 UNRESOLVED-ground-truth case (15/15)** | fb_011 is the one ambiguous case: my own ground truth for it is `UNRESOLVED` (a title carries over, but the requested body doesn't exist yet to compare), and V0.2 called it `DERIVATION_EDGE` anyway. This is not a *confirmed* false positive - I couldn't confidently call it either way myself - but it is a real instance of V0.2 expressing more confidence than the underlying evidence supports. Excluding that one genuinely-undecidable case, precision is a clean 15/15. |
| **DERIVATION_EDGE recall** | **100% (15/15)** | Every case where my independent judgment was `derived_from_candidate: YES` was correctly resolved as `DERIVATION_EDGE` by V0.2, including the corrected fb_002 (Business Character Method, exact 98% coverage match). |
| **False-origin rate** | **0% (0/30)** | Zero cases where V0.2 asserted a relationship to a candidate my independent judgment says is not the true origin, and zero cases where V0.2 fabricated a match in a no-corpus-origin control (external_no_corpus_origin ×2, derek_text_resembling_ai ×2, no_match_control ×2, independently_written_same_concept ×2 - all 8 correctly produced zero hits). |
| **Chronology violations** | **0 found (0/5 reverse-chronology-relevant cases)** | All 5 cases with a genuine reverse-chronology relationship (fb_001, fb_015, fb_016, fb_017, fb_018) were correctly marked `chronology_valid: false` by V0.2 and correctly demoted to `SIMILARITY_EDGE` rather than being force-assigned a backwards `DERIVATION_EDGE`. |
| **SIMILARITY_EDGE incorrectly promoted to DERIVATION_EDGE** (critical safety requirement) | **0 confirmed violations out of 14 cases where ground truth is a definite NO.** 1 additional case (fb_011) where ground truth is itself UNRESOLVED and V0.2 asserted DERIVATION_EDGE without hedging. | This is the metric the Architecture Board explicitly flagged as the safety-critical one: *"a similarity relationship must never become INTELLECTUAL_ORIGIN merely because it has the highest similarity score."* Across every case where I could independently confirm no derivation occurred, V0.2 never wrongly promoted it. The one open question is fb_011, where the honest answer is "unknown" on both sides - not a demonstrated failure. |
| **Correct multi-origin handling** | **1/2 clearly demonstrated, 1/2 inconclusive** | fb_021: V0.2 found `multiple_earlier_candidate_count: 3`, correctly picked the chronologically-valid, longest-span candidate → `DERIVATION_EDGE`. fb_022: V0.2 found only 1 candidate total for this reuse text (`multiple_earlier_candidate_count: 1`), whereas my case note speculated "several plausible candidates" existed elsewhere in the corpus's many review-writing conversations. I did not exhaustively verify that a second candidate actually clears V0.2's similarity threshold - so this is genuinely inconclusive, not a confirmed miss. Flagging rather than claiming either a pass or a failure. |
| **Long-document false-match rate** | **0% (0/63 hits)** | The frozen benchmark's long-document case (the AXIOMOS-class 269,000-character document, `fb_015`) now produces 63 hits in `CORPUS_RELEASE_001` (grown from the 12 spot-checked informally in `V0_2_STATUS.md`, since the corpus release is a later, larger snapshot) - every single one correctly resolves to `SIMILARITY_EDGE`/`reverse_match: true`, none promoted to a false `DERIVATION_EDGE`. This is the strongest and largest-sample confirmation yet that the passage-segmentation redesign actually fixed the root bug that drove the whole v0.1→v0.2 rebuild. |

## Headline finding: the directional-bias gap is real and reproducible, not a v0.1 artifact

Cases fb_016, fb_017, fb_018 (three separate same-conversation instances) and
fb_020 (the confirmed 3-hop chain) demonstrate the same structural gap
identified during the earlier reverse-chronology investigation: **V0.2 only
ever indexes assistant-role text as a candidate origin.** When Derek pastes
raw external content and the assistant reformats it moments later in the same
conversation, V0.2 correctly refuses to call it `DERIVATION_EDGE` (good - no
false attribution) but has no mechanism to positively identify that the
*user's own earlier message* is the true origin. It sees only a
`SIMILARITY_EDGE`/`reverse_match: true` and stops there. This is safe
(no wrong attribution is asserted) but incomplete (a real, findable
relationship goes unrepresented). fb_020's chain case is the sharpest example:
the true intellectual origin is external marketing copy, but V0.2's edges only
ever connect assistant-authored text to later reuses - it cannot see the
initial Derek-pastes-external-copy step at all.

This is a scope gap, not a defect requiring a V0.3 patch under this
benchmark's rules - documented per the Architecture Board's standing
instruction not to tune V0.2 against this benchmark. It is a design input for
`PROVENANCE_RESOLVER_V0.3` and any future bidirectional-origin-indexing work.

## What this benchmark does NOT establish

- **Not a statistically powered estimate.** 30 cases (15 in the DERIVATION_EDGE
  precision/recall denominators) means single-case swings move the percentages
  by several points. Treat these as directionally strong, not tight confidence
  intervals.
- **fb_022's multi-origin question is unresolved**, not passed.
- **fb_019 (reverse_chronology_cross_conv)** and **fb_011 (heavily_edited)**
  both have `UNRESOLVED` ground truth by design - genuine abstention, not a
  scoring gap.
- No Resolver-level (`INTELLECTUAL_ORIGIN`) evaluation is included - this
  benchmark scores `PROVENANCE_INDEX_V0.2` only, per the Architecture Board's
  explicit instruction to hold `PROVENANCE_RESOLVER_V0.3` for a separate pass.

## Files

- `frozen_benchmark_cases.jsonl` - 30 frozen ground-truth cases, chmod 444.
- `FROZEN_BENCHMARK.json` - freeze marker, SHA-256, category counts.
- `FROZEN_BENCHMARK_ERRATA.md` - fb_002 correction record (append-only).
- `score_v0_2.py` / `scoring_raw_results.json` - raw per-case comparison against `03_PROVENANCE_INDEX/v0_2/reuse_hits.jsonl`.
- `compute_metrics.py` / `metrics_computed.json` - the six metrics, machine-computed from the scored results.
