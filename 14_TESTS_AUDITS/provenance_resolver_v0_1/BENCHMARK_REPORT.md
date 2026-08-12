# PROVENANCE_RESOLVER_V0.1 — Benchmark Report

Run against the frozen `provenance_gold_set_v1.jsonl` (40 records). Stage 3 (semantic classification) was performed by a **separate, fresh agent with no access to the gold labels** — it read only `stage3_input_bundle.json` (raw text + Stage 1/2 mechanical evidence) and the spec's classification rules, and was explicitly instructed not to search for or read any "gold"-named file. This independence is what makes the numbers below a real measurement rather than the resolver grading its own homework.

## Headline result: does not yet clear the precision bar

**D0 precision: 17/18 = 94.4%** — below the required **≥98%** threshold (spec §12.7). **The resolver is not yet trusted for automatic Derek-origin attribution at scale, per your own stated policy.** One disagreement in an 18-item D0 prediction set swings precision by ~6 points — this sample is too small to measure 98% reliably either way, but on this specific benchmark, it does not clear the bar as measured.

## Confusion matrix (gold → predicted evidence_class)

| GOLD \ PRED | A0 | D0 | MIXED | P0 | UNRESOLVED | X0 |
|---|---|---|---|---|---|---|
| **A0** | 5 | 0 | 0 | 0 | 0 | 0 |
| **D0** | 0 | 17 | 0 | 0 | 1 | 0 |
| **MIXED** | 0 | 0 | 3 | 0 | 0 | 0 |
| **P0** | 0 | 1 | 2 | 3 | 1 | 0 |
| **UNRESOLVED** | 0 | 0 | 1 | 1 | 0 | 0 |
| **X0** | 0 | 0 | 0 | 0 | 0 | 5 |

Exact evidence_class match: 33/40 (82%). Full agreement including `adoption_status`/`provenance_certainty` would be a stricter, lower number — this matrix is evidence_class only, the headline classification.

## The four safety metrics

| Metric | Value | Cases |
|---|---|---|
| **False Derek Attribution Rate** | 1/22 = 4.5% | `gold_020` |
| **False Assistant Attribution Rate** | 0/18 = 0.0% | none |
| **P0 Miss Rate** | 1/7 = 14.3% | `gold_020` (same case) |
| **Bad Abstention Rate** | see below — both directions, neither clearly "bad" on inspection | `gold_037`, `gold_040` (over-confident by raw count); `gold_010`, `gold_022` (under-confident by raw count) |

## Two important findings that are NOT resolver errors — they're corrections to the frozen gold set

**This is the most significant result of this benchmark run**, more important than the headline precision number:

### `gold_019` (LinkedIn headline) — gold label was wrong

My gold label: `P0`, `original_author: "unknown"`, `origin_message_id: null` — I searched for a source during Gold Set construction and didn't find one.

The resolver found one: message `02170d3e-daf5-41f3-a576-d749873d00d6`, `role: assistant`, conversation "Remote Hiring Benefits," **2024-09-11**, containing the exact headline text ("Helping Aspiring Entrepreneurs Build Financial Freedom 🤑 | Chief Fun Officer | Social Media Expert 📱...") that Derek then pasted into "LinkedIn Title Enhancement" **2024-09-13** (two days later) asking for further tweaks. **Verified directly against `01_INGEST/messages.jsonl` — this is real.** My original manual search for this record (during the very first pilot) never checked it against the full corpus; the resolver's exhaustive Stage 1 shingle index did.

### `gold_037` (Empire Blueprint Enhancement) — the case I deliberately left `UNRESOLVED` actually has a confirmed answer

I flagged this one explicitly as genuinely ambiguous — `role: user`, but reads in unmistakable assistant voice, no origin found despite a real search.

The resolver found one, and **I verified it directly**: message `4df2be21-cf21-474f-af92-6676e3e17fe6`, `role: assistant`, conversation "Flowla for DAC Funding," **2025-05-25T06:37:26** — word-for-word identical to the "ambiguous" message, which appears as `role: user` in "Empire Blueprint Enhancement" **17 hours later** the same day. This is a **third confirmed instance** of the exact reuse pattern first found in the Business Character Method case: Derek pasting the assistant's own earlier output into a fresh conversation. My manual search missed it because I was working from a truncated top-200 candidate list, not an exhaustive index.

**I have not edited `provenance_gold_set_v1.jsonl` to fix these** — per your freeze rule, and because the point of the freeze is to not let a specific resolver's output silently rewrite its own answer key. Both are genuine, verified corrections discovered *during resolver construction, before any scoring happened* — not post-hoc tuning. Recommend: a documented `v1.1` correction (or an explicit errata note against `v1`) capturing these two fixes, decided by you, not silently applied by me.

## The one real disagreement worth understanding: `gold_020`

"9 Things I've learned from a decade in online marketing..." — my gold label called this `P0`/`external` based on content inconsistent with Derek's own documented business path (infrastructure hardships suggesting a different narrator). The resolver called it `D0`, reasoning explicitly that "generic engagement-bait social-post structure raises mild stylistic suspicion, but [insufficient basis alone]" — i.e. it applied the "stylistic suspicion must not itself prove P0, only a located match does" rule (spec §6.0a) *more strictly than I did when building the gold set*. Neither call is clearly wrong; this is a legitimate difference about how much unconfirmed stylistic evidence should be enough to leave `D0`. Worth a ruling, since it's the only case driving both the False Derek Attribution Rate and the P0 Miss Rate above zero.

## The other three "disagreements" are not really disagreements

- **`gold_016`** (gold `P0`, pred `MIXED`): the resolver split "Should something like this be added?" (its own `D0` question) from the pasted framework (`P0`) — this is *more correctly following the spec's own mixed-message segmentation rule (§6.0c)* than my original gold label, which recorded the whole thing as one `P0` blob. Arguably the resolver is right and the gold label under-applied its own rule.
- **`gold_022`** (Meladerm pros/cons): resolver abstained (`UNRESOLVED`) rather than assert `external` origin without a located source — same "don't classify on stylistic suspicion alone" discipline as `gold_020`, applied in the more conservative direction this time.
- **`gold_010`** (a short "create an image for this title..." tactical command): resolver abstained based on a weak 7-shingle match against an unrelated message — this looks like a genuine resolver over-caution / false positive from Stage 1's shingle detector on a short, generic phrase. Worth tuning: Stage 1 should probably require a higher shingle-count floor (or a percentage-of-message-length floor) before flagging reuse suspicion on short messages, since short generic phrasing coincidentally overlaps more easily than long distinctive text does.

## What I'd want your ruling on

1. How to record the `gold_019`/`gold_037` corrections — errata against v1, or a v1.1 that supersedes just these two records?
2. `gold_020`: is the resolver's stricter "no stylistic-suspicion-only P0" reading correct, or was my original gold call right? This determines whether the resolver's 94.4% D0 precision is actually a real miss or an artifact of an overly strict gold label.
3. Given `D0` precision lands at 94.4% either way (even crediting the resolver on `gold_016`/`gold_037`/`gold_019`, none of those affect the D0 precision denominator), the resolver as built does not yet meet the ≥98% bar on this sample. Scale to a larger benchmark before trusting it further, or tune Stage 1's short-message threshold (the `gold_010` issue) and re-run against v1 first?
