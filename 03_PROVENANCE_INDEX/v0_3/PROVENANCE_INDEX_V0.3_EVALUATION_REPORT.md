# PROVENANCE_INDEX_V0.3 — Implementation + Evaluation Report

**V0.2 preserved unchanged.** `03_PROVENANCE_INDEX/v0_2/provenance_index_v0_2.py` was not edited - V0.3 imports its matching primitives rather than copying or modifying them. `03_PROVENANCE_INDEX/v0_2/reuse_hits.jsonl` was not regenerated.

**No tuning after evaluation.** The corpus-scale run (`provenance_index_v0_3.py`) completed once. The frozen 30-case benchmark was scored against that output exactly once (`score_v0_3.py`). The new 6-case tranche was frozen *before* this run and scored once after. `provenance_index_v0_3.py` was not modified after either scoring pass, including in response to the critical finding in §1 below - that finding is reported, not silently patched.

## 1. Critical finding: message_id is not globally unique — a pre-existing, corpus-wide defect, not a V0.3 regression

While investigating why several frozen-benchmark cases showed unexpected results, I found that **42 message_ids in `CORPUS_RELEASE_001` are not unique** - they are reused across 2 to 469 different conversations each (2,985 duplicate records total, out of 72,241). 39 of the 42 are small sequential integers (`"1"` through `"38"`, plus `"41"`) used exclusively by the `conversations.json` (other-ai-export) source, which appears to assign per-conversation turn-index integers instead of globally-unique IDs, unlike ChatGPT's UUID-style IDs and Copilot's `copilot_msg_*`-prefixed IDs. Three more (`bbb21829-...`, `bbb21052-...`, `bbb219df-...`) collide between `conversations-023.json` (ChatGPT) and `conversations.json` - a smaller, separate cross-source collision.

**This bug predates V0.3.** Both `provenance_index_v0_2.py` and `provenance_index_v0_3.py` build `by_id = {m["message_id"]: m for m in messages}` and passage IDs as `f"{message_id}#p{n}"` - a dict comprehension over a non-unique key silently keeps only the last-loaded record for any colliding ID. This corrupts the *origin* side of any hit whose candidate passage ID collides: the origin's timestamp, conversation, and indexed words used for span-matching can silently belong to the wrong conversation.

**Verified impact, not estimated:**
- **42.76% of V0.2's 6,052 hits** and **31.88% of V0.3's 19,495 hits** touch at least one colliding ID on either side.
- Directly confirmed on `fbv3_006` (my own new-tranche negative control): the reported hit shows `origin_side_coverage: 2.628` - mathematically impossible for a real coverage ratio (same category of red flag as the `1.1161` value that first exposed the v0.1 AXIOMOS bug), and its `origin_conversation_id` resolves to a conversation with no real relationship to the reuse message - a direct product of the `message_id: "1"` collision, not a real 862-shingle match.
- Directly confirmed on `fb_015` (the frozen benchmark's flagship AXIOMOS long-document case): both its `reuse_record_id` (`"1"`) and `candidate_origin_record_id` (`"6"`) are colliding IDs. The AXIOMOS *conclusion* (large document, correctly demoted to `SIMILARITY_EDGE`, no false `DERIVATION_EDGE`) still held in both the V0.2 and V0.3 evaluations, but the **specific hit counts I reported for it** (V0.2: "63 hits, 0/63 false match"; V0.3: "112 candidates") **should not be trusted at face value** - some unknown fraction of those hits may belong to unrelated conversations that happen to share a small-integer ID with the true AXIOMOS document.

**What this means for trust in either index's output:** aggregate, corpus-wide statistics (total hit counts, DERIVATION_EDGE vs SIMILARITY_EDGE split, actor-pair breakdowns in §3) are still directionally meaningful, but **any specific hit whose origin or reuse ID is one of these 42 values must be treated as unverified until re-derived with a corrected key.** The real fix belongs at the ingest layer (`message_id` needs to be namespaced, e.g. `f"{source_file}:{conversation_id}:{message_id}"`, for the `conversations.json` source specifically) and a fresh corpus release, not a patch inside the index. Flagging this for the ingest lane rather than fixing it here - out of scope for this pass, and fixing it now would mean re-running V0.3 after already scoring it, which the Architecture Board's instruction to evaluate once, not iteratively, rules out.

## 2. Corpus-scale run results

```
72,241 messages | 45,783 origin passages indexed (direction-neutral, vs V0.2's assistant-only ~34,131)
19,495 total hits: 11,505 DERIVATION_EDGE, 7,990 SIMILARITY_EDGE/reverse-match
1,103 multi-hop chains reconstructed, covering 9,326 of the 11,505 DERIVATION_EDGEs
6,166 cross-source hits | 9,417 cross-actor hits | 3,205 exact-copy hits
```

**The core design hypothesis is validated at real scale.** V0.2 could only ever produce `assistant -> derek` edges. V0.3's `DERIVATION_EDGE` actor-pair breakdown:

| Origin actor -> Reuse actor | Count |
|---|---|
| chatgpt_assistant -> chatgpt_assistant | 3,597 |
| chatgpt_assistant -> derek | 2,846 |
| **derek -> derek** | **2,810** |
| **derek -> chatgpt_assistant** | **1,009** |
| **derek -> other_ai_assistant** | **719** |
| chatgpt_assistant -> other_ai_assistant | 393 |
| copilot_assistant -> copilot_assistant | 33 |
| derek -> copilot_assistant | 28 |
| other_ai_assistant -> derek | 26 |
| other_ai_assistant -> other_ai_assistant | 26 |
| copilot_assistant -> derek | 8 |
| chatgpt_assistant -> copilot_assistant | 5 |
| copilot_assistant -> other_ai_assistant | 2 |
| copilot_assistant -> chatgpt_assistant | 1 |

The three bolded rows (4,566 edges) are directions **V0.2's design could never produce under any circumstance** - `derek -> X` edges require a `role: user` passage in the origin index, which V0.2 explicitly excludes. This is real, corpus-scale confirmation that Derek's own earlier messages are legitimate, frequent derivation origins - not a rare edge case. (Some fraction of these are subject to the §1 caveat if either side touches a colliding ID; the actor-pair counts themselves are unaffected since `actor_of()` is computed from each hit's own correctly-populated `role`/`source_file`, not from the corrupted `by_id` lookup.)

## 3. Frozen 30-case benchmark evaluation (run once)

Raw per-case comparison: `frozen_benchmark/scoring_raw_results_v0_3.json`.

**A real, unanticipated scoring artifact, not a defect: chain-vs-root scoring.** 9 of the 30 frozen cases (fb_006, fb_007, fb_008, fb_009, fb_010, fb_013, fb_014, fb_018, fb_019) show `v03_found_this_pair: false` under a literal (`reuse_id`, `origin_id`) match. I investigated each rather than assuming either "V0.3 regressed" or "the benchmark is wrong":

- **fb_007/008/009/010, fb_006, fb_013/014 (7 cases)**: V0.3 did not miss these - it found a **more precise, nearer chronological origin** than the frozen case names. Example, verified directly: fb_007's frozen case names the original assistant-authored "Savvy Shopper Reviews Style Guide" (`b02cedd8`, markdown-formatted) as the origin. V0.3 instead resolved it to `aaa23ec4` - Derek's own plain-text repost of the same guide, posted ~3 hours after the original and ~9 hours before fb_007's reuse, with a 741-word contiguous span. V0.3 correctly identified the *nearer* real intermediate copy in the reuse chain rather than jumping straight to the root. The same pattern held on manual verification for fb_006 (chained to fb_005's own message), fb_009, fb_010, and fb_013/014. This means the frozen benchmark's ground truth, written before chain reconstruction existed, encodes *a* valid origin but not always the *nearest* one - a real, useful distinction V0.3 newly exposes, not a flaw in either system. `derived_from_candidate: YES` / `true_corpus_origin: YES` still holds for all 7; only the specific named `candidate_origin_record_id` is coarser than what V0.3 can now report.
- **fb_018, fb_019 (2 cases)**: `SIMILARITY_EDGE`, `chronology_valid: false` - V0.3 correctly refused to treat a later message as an origin, matching the frozen ground truth (`derived_from_candidate: NO` / `UNRESOLVED`) exactly. Not a discrepancy at all.

**Two real errata found in my own frozen ground truth while investigating the above** (documented in `FROZEN_BENCHMARK_ERRATA.md`, frozen file left unedited per the append-only rule):
1. (Previously documented) fb_002's `reuse_record_id` was a corrupted, non-existent ID.
2. **(New)** fb_013 and fb_014's relative chronological order was reversed in my original case notes - fb_014 (`21:43:20`) is actually ~11 minutes *earlier* than fb_013 (`21:54:29`), not later as I wrote. V0.3's evaluation is what surfaced this - it resolved fb_013 as derived from fb_014, which only made sense once I checked the real timestamps and found my own note backwards.

**Direct, uncomplicated matches (no chain-refinement or collision caveats):** fb_003, fb_004, fb_005, fb_012, fb_021, fb_022 all resolved to `DERIVATION_EDGE` with the exact expected origin, chronology valid. fb_015 (AXIOMOS) still correctly resolved to `SIMILARITY_EDGE`/`reverse_match` (safe outcome preserved) but see §1's caveat on its hit-count details. fb_001, fb_016, fb_017 correctly stayed `SIMILARITY_EDGE` for the *named* backwards pair (matching frozen ground truth `derived_from_candidate: NO` for that specific pairing) - confirming §3's core design change didn't accidentally start over-promoting these; V0.3's actual improvement on this pattern is that it can now *also* find the true forward edge from the same underlying text elsewhere in the corpus (§2's `derek -> X` edges), which the pairwise per-case scoring format doesn't directly surface. fb_011, fb_023-030 (external/no-match/control cases) all resolved identically to V0.2 - no change, as expected since none of these involve a reverse-direction relationship.

**No false `DERIVATION_EDGE` promotions observed** across any of the 30 cases - the safety-critical behavior validated in the V0.2 report held under V0.3's much larger candidate pool.

## 4. New 6-case tranche evaluation (run once, frozen before this run)

Raw comparison: `frozen_benchmark_v0_3/scoring_v0_3_output.txt`.

- **fbv3_001, fbv3_002 (the headline reverse-direction cases)**: both involve `candidate_origin_record_id` values of `"1"` / `"3"` - colliding IDs (§1). V0.3's reported result for these specific pairs is **not usable evidence either way** - it's corrupted by the same ID-collision bug, not a genuine miss or hit. My own independent verification (93.3% and near-identical shingle coverage, done by direct text comparison before V0.3 ran, described in the design doc §4a and the tranche's case notes) stands on its own as evidence the underlying relationship is real; V0.3 simply cannot currently report on it correctly because of the upstream ID defect. This is an important, honest caveat on what would otherwise be the single best demonstration case for V0.3's core new capability.
- **fbv3_003**: matched exactly as expected - `DERIVATION_EDGE`, chronology valid, span 862, correctly assigned to `chain_01096`.
- **fbv3_004**: did not match the literal expected pair, but for the same good reason as §3's chain-refinement cases - V0.3 chained it to fbv3_003's message (a nearer, ~8-hour-closer, equally-strong candidate) instead of the more distant root. A correct, more precise answer, not a miss.
- **fbv3_005 (voice-convergence control)**: zero hits, as expected - correctly did not treat the one-shingle stock-phrase overlap as similarity.
- **fbv3_006 (scattered-overlap control)**: one `SIMILARITY_EDGE` hit, correctly *not* promoted to `DERIVATION_EDGE` (the safety property held), but the hit's own numbers are corrupted by the `message_id: "1"` collision (§1) - coincidentally another direct confirmation of that bug, not a real 862-shingle relationship to the message it names.

## 5. Summary

- Direction-neutral discovery, actor tagging, and multi-hop chain reconstruction all work as designed and are validated at corpus scale with real numbers, not just the small frozen benchmark.
- Chain reconstruction is *more* accurate than the original frozen benchmark's pairwise ground truth in several cases - an unanticipated, positive result.
- No false `DERIVATION_EDGE` promotions found in either evaluation.
- **The message_id collision bug (§1) is the most important finding in this report** - a pre-existing, corpus-wide defect affecting roughly a third to two-fifths of all hits in both V0.2 and V0.3's output, discovered because V0.3's larger candidate pool made it visible. It needs an ingest-layer fix and a fresh corpus release before either index's per-hit origin details can be fully trusted at scale. Not fixed in this pass, per the instruction to evaluate once and not iterate - reported clearly instead.
- No canonicalization, Conglomerate conclusions, Resolver changes, or `integration_strength`/authorship/adoption computation were performed, per instruction.
