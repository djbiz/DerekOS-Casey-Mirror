# D1→D0 Label Divergence — Schema Reconciliation V0.1

Status: `SCHEMA/VERSION RECONCILIATION — NO RELABELING PERFORMED`
Date: 2026-08-12
Scope: the 230-record `PROVENANCE_ADVERSARIAL_SET_V1` frozen adjudication

---

## 1. What D1 meant

In the provenance-reset taxonomy, `D1` is defined as:

> **D1 — Derek explicitly adopts/approves something.** The message is Derek's
> own wording (so it is still Derek-authored prose), and its content is an
> explicit adoption of a proposition originating elsewhere.

`D1` therefore occupies the intersection of two axes:

- **authorship axis:** the words are Derek's → `authored_by = derek`
- **adoption axis:** what Derek says is `AD3/AD4` adoption of a prior proposition

`D1` is distinct from `D0` (Derek-originated statement with no adoption
component) and from `P0 + AD3` (assistant-authored submission that Derek then
adopted — where the *words* are not Derek's).

## 2. Why the committed benchmark folded D1→D0

The committed answer key
(`blind_adjudication/PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl`, commit `c44dfc8`)
was produced by the **positive-evidence adjudication pass** and uses a
four-class schema: `D0 | P0 | MIXED | UNRESOLVED`.

In that pass, every record whose *words* were Derek's — including the brief
approval acts that the five-class schema would call `D1` — was recorded as
`D0`, with the adoption strength carried in the separate `adoption_status`
field (`AD3` for simple approvals, `AD4` for "yes, but …" modifications).

So the fold is:

```text
D1 (five-class schema)  →  D0 (four-class schema)  +  adoption_status = AD3/AD4
```

It is **not** a relabeling of authorship. Both representations agree that the
words are Derek-authored; they differ only in whether "Derek explicitly
adopting a prior proposition" deserves its own class or is modeled as an
adoption status on top of `D0`.

## 3. Which records are affected

141 of 230 records differ between the two frozen files by class string:

| Class transition (my file → committed file) | Count |
|---|---:|
| D1 → D0 | 38 |
| P0 → UNRESOLVED | 46 |
| MIXED → P0 | 18 |
| D0 → P0 | 14 |
| D0 → UNRESOLVED | 8 |
| MIXED → UNRESOLVED | 5 |
| D0 → MIXED | 5 |
| UNRESOLVED → P0 | 5 |
| MIXED → D0 | 1 |
| P0 → MIXED | 1 |

The 38 `D1 → D0` transitions are the **pure schema fold** described in §2 and
are fully explained by the five-class → four-class change.

The remaining 103 transitions are **judgment differences** between the two
independent adjudication passes, concentrated in three judgment boundaries:

- **P0 vs UNRESOLVED (46+5):** whether absence of a located origin makes
  "external-looking" material P0 or UNRESOLVED.
- **MIXED vs P0 (18+1):** whether a short Derek lead + pasted body is
  "mixed content" or "reused material with a carrier phrase".
- **D0 vs P0 / D0 vs UNRESOLVED (14+8+5):** whether Derek-supplied facts or
  brief control acts rise to D0.

These are genuine disagreements about borderline evidence, not mechanical
errors — the same near-identical cases (e.g. two "summarize this YouTube
transcript" records) were split differently across the two passes.

## 4. Which representation is authoritative for future scoring

**The committed file is authoritative for benchmark scoring:**

- `blind_adjudication/PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl` (commit
  `c44dfc8`) — four-class schema with `adoption_status`, `provenance_certainty`,
  `requires_review`, and per-record `rationale`.
- It is the frozen answer key used by the committed scorer
  (`benchmark_adversarial_v1.py`) and by `PROVENANCE_ADVERSARIAL_BENCHMARK_V1.json`.
- The Board directive requires the frozen benchmark to remain unchanged.

**The five-class file (`FROZEN_ADJUDICATION_V1.jsonl`) is retained as a
diagnostic artifact only.** It is untracked, is not used for scoring, and
preserves the richer `D1` class plus per-segment annotations for analysis.
It must not be substituted for the committed key.

## 5. Scoring implications

- **Primary gate (FDA=0)** is **unaffected**: both files agree on which
  records have zero Derek authorship. FDA = 0 for v0.3 under both keys.
- **D0 precision/recall** differs because the committed key counts `D1` as
  `D0`: v0.3 D0 precision 100% under both; D0 recall 80.9% (committed,
  D0-only denominator) vs 52.1% (five-class, D0+D1 denominator).
- **MIXED and P0 metrics** differ under the two keys (18 vs 36 MIXED, 101 vs
  111 P0). All v0.3/v0.4 gate reporting uses the **committed key**.

## 6. Governance

- No frozen artifact was modified to produce this document.
- A single canonical key is needed before `PROVENANCE_CORPUS_V1` metrics are
  treated as permanent history. Recommendation: ratify the committed key as
  canonical; treat `FROZEN_ADJUDICATION_V1.jsonl` as a superseded diagnostic.
- If the Board later wants the five-class schema restored, the 141 diverging
  records require **human adjudication** — not mechanical conversion — because
  103 of them are genuine judgment differences.
