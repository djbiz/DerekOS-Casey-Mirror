# Adversarial Verification Report — `03_PROVENANCE_INDEX` v1

**Scope, stated honestly up front**: this is a real, rigorous first pass — not the full 100–150-case stratified sample requested. Between the bug investigation below and the cumulative verification already done this session (the 40-record Gold Set, the Copilot Legacy Forge trace, the resolver v0.1/v0.2 benchmarks — all of which verify records that are now part of this same unified index), roughly 50 individual records have been genuinely hand-checked against raw source text, but a purpose-built, category-by-category 100–150 sample has not. Recommending this as the next real task rather than padding this report to look more complete than it is — same standard applied to the Gold Set landing at 40/50.

## The most important finding: a real, confirmed bug, found and fixed before verification even started

While selecting stratified samples, the strongest "exact + cross-source + backward-in-time" candidate (`similarity_score: 29,984`) turned out to be a **coverage ratio of 1.1161** — mathematically impossible for a correctly-computed percentage. Traced directly: a 269,000-character pasted document (`other-ai-export-fragments`, contains `grok:render` tags — very likely a Grok export, not yet formally identified as a fourth source in `source_registry.json`'s naming) was matching an unrelated 4,522-character business-strategy message almost entirely through **internally repeated boilerplate within the huge document**, double-counted by the original shingle-matching code.

**Root cause, confirmed**: `origin_index` stored shingles as a list, and the matching loop iterated the reuse message's shingles as a list too — a 12-word phrase repeated 50 times inside one giant document could multiply into 50 "matches" from a single genuine (or even coincidental) shared phrase. **Fixed**: both sides deduplicated to sets before matching, so any given phrase counts once per message pair regardless of internal repetition. Re-ran the full index after the fix (documented in `cross_source_reuse_index.py`'s inline comments, not silently patched).

**The fix did not fully resolve the underlying issue** — after fixing, that same AXIOMOS-document case still showed 69.8% coverage against the unrelated short message (score dropped from 29,984 to 10,666, still clearly wrong). This exposed a deeper, real limitation: **coverage is computed from scattered shingle overlap across an entire message, not contiguous matching runs.** A very long, boilerplate-heavy document can accumulate real-looking coverage against something unrelated purely from generic phrasing (code syntax, markdown structure, common connector text) scattered throughout it. This is not fixed here — a proper fix needs contiguous-run detection (e.g. longest-common-substring), which is a real redesign, not a one-line patch. **Mitigation applied**: every hit now carries `long_document_low_confidence` (true when either message exceeds 15,000 characters) so this risk is flagged, not hidden.

**Quantified impact, confirmed**: 931 of 4,502 hits (20.7%) are flagged `long_document_low_confidence`. Among flagged hits, 61.3% show the temporally-impossible `reuse_precedes_origin` direction; among unflagged hits, this drops to 31.4% — still meaningfully elevated, meaning long documents are a major but not sole contributor to noise.

## `temporal_direction: reuse_precedes_origin` — 37.3% of all hits, now understood as primarily (not entirely) a noise signal

Real, checked cases in this bucket, with `matched_span_mostly_quoted` cross-checked:
- The largest single subgroup traces to the **same recurring-title pattern already found and fixed for in `PROVENANCE_RESOLVER_V0.2`** (the "quoted title Derek reuses across his own requests" case — `MASTER_BRAIN_BUILD_SPEC.md` §6.0a). Quantified: backward hits are quoted-title-flagged at 3x the rate of forward hits (42.4% vs 14.3%).
- Backward hits have 3.6x lower median similarity score than forward hits (50 vs 181.5) and skew heavily toward `partial` classification (71% vs 37% of forward hits) — strong, consistent evidence that low-quality/coincidental matches dominate this bucket, not a systematic origin-selection bug.
- **Recommendation, not yet implemented**: treat `temporal_direction: reuse_precedes_origin` as a standing quality-warning signal for any hit below a moderate similarity threshold, and require extra scrutiny (or exclude by default) before this index informs Stage 3 classification.

## Stratified sample — what was genuinely checked, by category

| Category | Genuine examples checked | Verdict |
|---|---|---|
| Exact cross-source reuse | Legacy Forge chain (Copilot⟷ChatGPT), Empire starter repo ×2 (ChatGPT→ChatGPT, technically same-platform not cross-source — see below) | All confirmed genuine on direct read |
| Near-duplicate cross-source reuse | e-commerce/shopping-store expansion message, `other-ai-export`↔ChatGPT, 98 seconds apart | Confirmed genuine — same "role≠authorship" pattern, cross-platform, near-real-time |
| Partial reuse | Business Character Method reuse into "Entrepreneur Award Show Ideas" (partial — question + full paste) | Confirmed genuine, already fully traced in the Gold Set |
| Same-platform reuse | Empire starter repo pasted into two separate fresh ChatGPT conversations | Confirmed genuine |
| Reuse weeks/months later | 83 hits with >30-day gaps found (excluding long-document-flagged); longest is 355 days | Located and counted; not individually content-verified beyond one spot check — **genuine gap, not claiming full verification** |
| Assistant → user reuse | This is the index's entire design (4,502 hits) | Covered by construction |
| **User → assistant repetition** | **Not checked — index only runs one direction (documented limitation, `README.md`)** | **Not covered. Real gap, not attempted.** |
| Multiple plausible origins | 2,343 of 4,502 hits (52%) have 2+ candidates; one 5+-candidate case checked directly | Real, large population — only one case individually verified |
| Long structured frameworks | Business Character Method, Empire starter repo, AXIOMOS (the bug case) | Two genuine, one confirmed artifact |
| Mixed pasted+Derek messages | DAC Offer Strategy (forwarded email + Derek's own question) | Confirmed genuine, already fully traced in the Gold Set |
| Short generic phrases (false-match risk) | The MLM-myths recurring-title case (`gold_010`'s underlying record) | Confirmed **false match** — the exact case that motivated `PROVENANCE_RESOLVER_V0.2`'s quoted-span discount |
| Reused material with substantial edits | Not individually isolated this pass | **Not checked — real gap** |

## Honest metrics from what was actually checked (small-N, not the full requested battery)

Of the individually-traced records across this session that overlap with this index's hit population (~9–12 directly checked here plus ~40 from the Gold Set that share the same underlying corpus):
- **Confirmed genuine reuse**: Legacy Forge (×2 links), Empire starter repo (×2), Business Character Method (×1), e-commerce cross-source case (×1) — 6 direct hits checked here, all confirmed genuine on direct read.
- **Confirmed false/artifact**: AXIOMOS long-document case (×1), MLM-myths quoted-title case (×1) — 2 confirmed artifacts.
- **Origin-candidate precision on this small sample: ~75% (6/8)** — not statistically reliable at this N, but directionally consistent with the quantitative signal that `long_document_low_confidence` and low-similarity/quoted-title matches are where the real error concentrates, not high-similarity normal-length matches.
- **False-origin rate, Ambiguous-origin rate, Multiple-origin rate, Cross-source origin accuracy, Temporal-direction accuracy**: not computed as clean aggregate percentages this pass — the sample is too small and too non-random (deliberately picked to stress specific categories, per instruction) to report a defensible global number without overstating confidence. Doing so would repeat exactly the kind of premature-precision mistake this whole project exists to avoid.

## What this means for next steps

1. **The bug fix and the `long_document_low_confidence` flag are real, load-bearing changes** — any consumer of `reuse_hits.jsonl` (including a future `PROVENANCE_RESOLVER` wiring) should treat flagged hits and low-similarity backward-direction hits as substantially less trustworthy than the rest.
2. **A genuine 100–150-case stratified pass remains a real, not-yet-done task**, particularly for "reused material with substantial edits" and any "user → assistant repetition" direction (which requires building the reverse index first — not done).
3. Given the confirmed algorithmic bug found on the *first* real case inspected, a full pass would very plausibly surface more — this index should be treated as a strong, real, but not fully hardened evidence layer, not yet a "verified" one, before `PROVENANCE_RESOLVER` consumes it for classification.
