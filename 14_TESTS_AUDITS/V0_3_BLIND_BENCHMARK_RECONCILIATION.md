# V0.3 Blind Benchmark — Reconciliation Report

Status: `PRIMARY GATE PASSED — LABEL SET DIVERGENCE REQUIRES BOARD DECISION`

Date: 2026-08-12
Scope: `PROVENANCE_ADVERSARIAL_SET_V1` (230 records, frozen), resolver `v0.3`

---

## 1. Headline result — robust across BOTH label sets

Two independent frozen label files exist for the same 230 records (see §3).
v0.3 was scored against both. The primary gate conclusion is identical:

| Gate | vs committed labels (`blind_adjudication/`) | vs `FROZEN_ADJUDICATION_V1.jsonl` |
|---|---|---|
| **False Derek Attribution = 0** | **PASS (0)** | **PASS (0)** |
| D0 precision | 100% (38/38) | 100% (38/38) |
| D0 recall | 80.9% (38/47) | 52.1% (38/73, D0+D1) |
| P0 precision | 68.4% | 52.6% |
| MIXED precision / recall | 0% / 0% | — / 13.9% |
| AD3/AD4 accuracy | 91.7% (33/36) | 100% (38/38) |
| Evidence-class exact acc. | 55.2% | 14.3% |
| Abstentions (UNRESOLVED) | 149/230 (64.8%) | 149/230 (64.8%) |

**Both label sets agree: v0.3 eliminates false Derek attribution and reaches
100% D0 precision** — the directive's primary gate. It does so by failing
closed: user-role records are UNRESOLVED unless positive evidence (DAE-3/4)
establishes authorship. That is the intended safety posture.

## 2. The v0.1 blind benchmark remains the recorded FAIL baseline

- v0.1 (sealed predictions, revealed only after labels froze): **FDA = 69**
  (committed labels) / **51** (my label file) — FAIL on both.
- D0 precision 38.9%, recall 93.6% (committed labels).
- Recorded in `BLIND_BENCHMARK_SCORE_V1.json` and
  `PROVENANCE_ADVERSARIAL_BENCHMARK_V1.json`. Not mutated.

v0.3 was built from root-cause analysis of those failures and rerun against the
**same frozen benchmark**. The labels were never changed to improve scores.

## 3. CRITICAL: two divergent frozen label files exist

This is a governance issue that must be resolved before the secondary metrics
can be trusted. The two files disagree on **141 of 230 records**:

| File | Tracked | Evidence-class distribution |
|---|---|---|
| `blind_adjudication/PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl` | committed `c44dfc8` (10:22:49) | D0:47, MIXED:18, P0:101, UNRESOLVED:64 (no D1 class) |
| `FROZEN_ADJUDICATION_V1.jsonl` | **untracked** (10:24:54) | D0:35, D1:38, MIXED:36, P0:111, UNRESOLVED:10 |

Main disagreement families (my file → committed file):

- 38× D1 → D0 (committed set folds adoption into D0; no separate D1 class)
- 46× P0 → UNRESOLVED (committed set abstains where my set marked external)
- 18× MIXED → P0 and 5× MIXED → UNRESOLVED
- 14× D0 → P0, 8× D0 → UNRESOLVED, 5× D0 → MIXED
- 5× UNRESOLVED → P0, 1× MIXED → D0, 1× P0 → MIXED

The committed file is the git-authoritative freeze (`c44dfc8`, "freeze blind
adversarial labels") and matches the v1 benchmark report's SHA reference.
My file matches the spec's evidence-class taxonomy (D1 as a distinct
adoption class, per the provenance reset) and carries per-record segments,
notes, and adjudication provenance.

Per the Board rule, neither adjudication breaks the tie silently →
**ADJUDICATION_REQUIRED** on the diverging records before secondary metrics
are treated as authoritative.

## 4. Corpus baseline (reconciliation before PROVENANCE_CORPUS_V1)

- Adversarial set was built from the 72,241-record snapshot.
- **Current canonical corpus is stable at 72,241 messages / 3,969
  conversations** (`01_INGEST/messages.jsonl`, 305 MB, last modified 08:52).
- The 75,321 figure was a transient duplicate state during the Copilot delta
  import and is already deduped — not a separate baseline.
- The adversarial benchmark therefore covers the full in-scope corpus.
  The delta records (newest ~3,080) are a clean out-of-sample test for later.

## 5. Recommended disposition

1. **Accept the primary gate**: v0.3 passes FDA=0 with 100% D0 precision on
   both label sets. It is safe for automatic Derek-origin attribution.
2. **Resolve the label divergence** (Board decision): canonicalize one frozen
   set — either (a) accept the committed `c44dfc8` set as the single answer
   key, or (b) merge the two with human adjudication of the 141 diverging
   records. Do not silently pick.
3. **Known limitation to carry forward**: abstention is 64.8% and
   P0/MIXED/AD3-AD4 secondary metrics are weak. Improving recall must not
   weaken the D0 evidence bar (frozen Gate 1 stays at 0).
4. After (2), run `PROVENANCE_CORPUS_V1` on the reconciled 72,241-message
   corpus, then the Conglomerate reconstruction acceptance test.
