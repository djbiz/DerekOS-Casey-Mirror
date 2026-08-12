# MIXED_SEMANTICS_ADJUDICATION_V1

**Status:** Independent span-level adjudication of the MIXED evidence-class boundary.
**Scope:** Every disputed MIXED / P0 / UNRESOLVED record in `PROVENANCE_ADVERSARIAL_SET_V1` where the frozen message-level key and the resolver disagree, or where the frozen key itself is internally inconsistent.
**Inputs:** `blind_adjudication/PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl` (frozen, untouched), `PROVENANCE_RESOLVER_V0_5_predictions.json`, `adjudication_bundles/` (full target + prev/next context).
**Frozen-benchmark rule:** The frozen message-level key is *not* relabeled. This document is a new semantic contract that V0.6 implements and future scoring uses for the MIXED boundary. The primary regression gates (False Derek Attribution = 0, D0 precision ≥ 98%, frozen D0 set unchanged) remain scored against the frozen key.

---

## 1. The governing rule

> **A message is MIXED only when at least two independently attributable semantic spans exist and both contribute substantive meaning to the resulting message.**

A carrier phrase does not create MIXED. A CONTROL_ACT — "Add this:", "Summarize the transcript…", "Can you rewrite this in X style…" — is a task directive, not a semantic contribution. When the only Derek span is a CONTROL_ACT and the body is imported/reused material, the message class is **P0** (imported artifact) carrying Derek's **adoption** (AD3 for "use this", AD4 for material transformation, AD1 for engagement).

MIXED therefore requires the Derek span to be **substantive**: a modification, requirement, correction, opinion, or business data that changes the meaning of the imported material.

### Span function taxonomy

| Function | Meaning | Example | Not MIXED by itself |
|---|---|---|---|
| `CONTROL_ACT` | Task directive; zero semantic content contribution | "Add this:" / "Summarize in 10 bullets" / "Rewrite in Kevin James style" | Yes |
| `LABEL` | Attribution label, not content | "Her reply." / "BODY:" | Yes |
| `QUERY` | Question about imported material | "Is this inside the system." / "What can be done with these API keys" | Yes |
| `IMPORTED_CONTENT` | Reused/pasted material (transcript, code, email, framework, list) | YouTube transcript, `agency_economics_v2.py`, LinkedIn post URL | — |
| `REQUIREMENT` | Derek's own substantive requirement | "Can't we put a limit on how much or a plan that allows flexibility" | No — substantive |
| `MODIFICATION` | Derek changes the content/target of imported material | "…but don't make the businesses independent" / "…for me and DAC" | No — substantive |
| `DATA_SUBMISSION` | Derek's own identifying/business data | phone, email, LinkedIn URL, platform links | No — Derek-authored |

### Message / span / proposition classification

A record may carry all three levels independently:

```text
MESSAGE
  submitted_by = derek
  message_class = P0            (or MIXED / D0 / UNRESOLVED)

SPAN A  (0..300)  "Can you create a follow-up email from the email below in a Dan Ferrari style…"
  authored_by = derek
  class = D0
  function = CONTROL_ACT

SPAN B  (300..end)  the email body
  authored_by = assistant
  class = P0
  function = IMPORTED_CONTENT
  source_reference = origin message_id

PROPOSITION X
  origin = assistant
  adoption = AD4                (transformation request)
  integration_strength = LOW    (task directive on imported artifact)
```

`CONTROL_ACT` spans are Derek-authored (submitted + directed) but never make the message MIXED; they only carry adoption. Only substantive spans (REQUIREMENT / MODIFICATION / DATA_SUBMISSION) qualify as a MIXED ingredient.

---

## 2. Adjudication of the disputed records

26 records touch the MIXED boundary. The frozen key is **internally inconsistent** at the carrier margin: six structurally identical "Summarize the transcript…" records are split 3 MIXED / 3 P0, and five identical "rewrite in style" carriers are split 2 MIXED / 2 P0 / 1 UNRESOLVED. The adjudication below resolves each family to one principled class.

### Family A — Transcript-summarization template (6 records)

`adv_000346` · `adv_000735` · `adv_000941` · `adv_030261` · `adv_030897` · `adv_032963`

All six are the same template:

```
Summarize the transcript of a YouTube video in 10 bullet points. The video is by X and is titled Y. The entire transcript is given below. [40k-char transcript]
```

| Span | Author | Class | Function |
|---|---|---|---|
| "Summarize the transcript… given below." | derek | D0 | CONTROL_ACT |
| transcript body | external (video author) | P0 | IMPORTED_CONTENT |

**Adjudication: P0, adoption AD3.** The instruction is a CONTROL_ACT (task directive with fixed format); the substantive content is the imported transcript. **This resolves the frozen split 3 MIXED / 3 P0 → uniform P0.** V0.5's MIXED on `adv_030261/030897/032963` was correct relative to its (over-broad) carrier rule, but the rule itself over-fires.

### Family B — Rewrite-in-style / length-transform carriers (5 records)

`adv_001324` · `adv_001326` · `adv_029474` · `adv_031597` · `adv_033054`

| Span | Author | Class | Function |
|---|---|---|---|
| "Can you create a follow-up email from the email below in a Dan Ferrari writing style…" | derek | D0 | CONTROL_ACT |
| email / script / benefits body | assistant (traced) | P0 | IMPORTED_CONTENT |

**Adjudication: P0, adoption AD4.** A style directive is a transformation request — material transformation of imported content establishes AD4, but the Derek span carries no substantive meaning of its own. Resolves the split 2 MIXED / 2 P0 / 1 UNRESOLVED → uniform P0 + AD4.

### Family C — "Recreate this…" (2 records)

`adv_007563` (760-char constraint) and `adv_007820` ("…for me and DAC.")

| Span | Author | Class | Function |
|---|---|---|---|
| "Recreate this with 760 characters" / "Recreate this for me and DAC." | derek | D0 | CONTROL_ACT → MODIFICATION (borderline) |
| story transcript | assistant (traced 0.86–0.99) | P0 | IMPORTED_CONTENT |

**Adjudication: P0 + AD4.** Both are transformation requests over imported transcripts. "For me and DAC" names a target beneficiary but does not add a second independently attributable semantic span; it strengthens adoption (AD4) rather than creating MIXED. Flagged `requires_review` — this is the documented borderline between CONTROL_ACT and MODIFICATION.

### Family D — Query + imported code (2 records)

`adv_018155` · `adv_019425` ("Is this inside the system." + pasted Python)

| Span | Author | Class | Function |
|---|---|---|---|
| "Is this inside the system." | derek | D0 | QUERY |
| Python code (agency_economics_v2.py / HDE) | assistant (traced) | P0 | IMPORTED_CONTENT |

**Adjudication: P0 + AD1/AD2.** The Derek span is a query, not substantive content. `adv_013001` (n8n checklist) is a **pure paste with no carrier at all** — P0/UNRESOLVED by origin traceability, never MIXED.

### Family E — Label + third-party quote (1 record)

`adv_014438` ("Her reply." + her message)

**Adjudication: P0 + AD1.** "Her reply." is a LABEL; the message is imported third-party content.

### Family F — Intent carrier + external URL (1 record)

`adv_006905` ("This is a post I like to leave a thoughtful message" + LinkedIn URL)

**Adjudication: P0 + AD2.** Thin intent carrier; the post is external imported content.

### Family G — Query + imported list (1 record)

`adv_009750` ("What can be done with these API keys" + 3 API names)

**Adjudication: P0 + AD1.** Query + imported list.

### Family H — Carrier + Derek's own tooling message (1 record)

`adv_002059` ("how can we make this better:" + Derek's own Chrome-extension message)

**Adjudication: NOT MIXED → D0-leaning / UNRESOLVED.** The pasted body is Derek's own content ("my chrome extension"); both spans are Derek-authored. The message-level class stays UNRESOLVED under the fail-closed D0 bar; marked `requires_review`, D0-leaning.

### Family I — Pure Derek requirement, no imported body (2 records)

`adv_017999` ("Can you make the system self learning and make sure this system can connect to other python codes…") and `adv_001444` ("create a video hook here… MUST BE NO LONGER THAN 95 CHARACTERS…")

**Adjudication: NOT MIXED → D0-leaning / UNRESOLVED.** No second span exists; V0.5's P0 on `adv_017999` and MIXED on `adv_001444` are both wrong. These are Derek-authored requirements (D0 candidates) that the fail-closed core leaves UNRESOLVED. **D0 set is not expanded** — this does not violate the frozen D0 invariant, it only prevents a false MIXED/P0.

### Family J — Derek's own business data (1 record)

`adv_004101` (phone, email, LinkedIn, funding-platform URLs — all Derek's own)

**Adjudication: NOT MIXED → UNRESOLVED (D0-leaning data).** Self-identifying data is Derek-authored, but the resolver's D0 bar is not expanded. Frozen MIXED is wrong; V0.5's UNRESOLVED is right for the wrong message-level reason.

### Family K — Genuine MIXED (2 records, kept)

`adv_003597` — "wait before we move on please help with this" + LinkedIn chat containing **Derek's own statements** ("Great I'm looking for closer and setters / Or I can train them to be") **and** Rob Walker's message.

| Span | Author | Class | Function |
|---|---|---|---|
| carrier | derek | D0 | CONTROL_ACT |
| Derek's own chat statements | derek | D0 | REQUIREMENT |
| Rob Walker's message | external | P0 | IMPORTED_CONTENT |

**Adjudication: MIXED.** Two independently attributable substantive spans (Derek's requirement + third-party message) both contribute meaning. **Kept.**

`adv_021989` — "Can't we put a limit on how much or a plan that allows the system flexibility." + imported capability list.

| Span | Author | Class | Function |
|---|---|---|---|
| "Can't we put a limit… allows flexibility" | derek | D0 | REQUIREMENT (substantive) |
| capability list (Writing files / Running new code / …) | assistant (traced) | P0 | IMPORTED_CONTENT |

**Adjudication: MIXED.** Derek's span is a substantive governance requirement; the list is imported. **Kept.**

---

## 3. Summary of the adjudicated boundary

| Disposition | Count | Records |
|---|---|---|
| P0 + AD3 (transcript template) | 6 | 000346, 000735, 000941, 030261, 030897, 032963 |
| P0 + AD4 (style/transform carrier) | 7 | 001324, 001326, 029474, 031597, 033054, 007563, 007820 |
| P0 + AD4 (create-prompt carrier) | 1 | 001443 |
| P0 / P0-UNRESOLVED (query + code / pure paste) | 3 | 018155, 019425, 013001 |
| P0 + AD1/AD2 (label / intent / query + list) | 3 | 014438, 006905, 009750 |
| NOT MIXED → UNRESOLVED, D0-leaning | 4 | 002059, 017999, 001444, 004101 |
| **MIXED (genuine)** | **2** | **003597, 021989** |

**Key finding:** the frozen key's MIXED class is systematically over-broad. 16 of its 18 MIXED records are CONTROL_ACT carriers (P0 under the substantive-meaning rule). Only 2 survive: the two records where Derek's span is a substantive requirement or his own statements.

**No relabeling was performed.** The frozen key remains the frozen key. This document is the span-level semantic contract.

---

## 4. Mandate for V0.6

1. **Safety frozen from V0.5:** FDA = 0, D0 precision ≥ 98%, frozen D0 set byte-identical, AD3/AD4 ≥ 97%. No change to any D0 decision.
2. **MIXED gate:** a record may be MIXED only when the resolver can produce **two substantive spans** — a Derek REQUIREMENT/MODIFICATION/DATA span and a traceable imported body. CONTROL_ACT / LABEL / QUERY spans never produce MIXED; they resolve to P0 + adoption.
3. **No D0 expansion:** D0-leaning records stay UNRESOLVED.
4. **Honest scoring:** regression gates scored against the frozen key; the MIXED boundary scored against this adjudication (the frozen key is inconsistent here by construction).

---

## 5. Implementation result — V0.6 (2026-08-12)

`provenance_resolver_v0_6.py` implements this contract over the frozen V0.5
safety core. Verified against the frozen 230:

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| FDA = 0 | 0 | 0 | PASS |
| D0 precision | ≥ 0.98 | 1.0 (38/38) | PASS |
| frozen D0 set vs V0.5 | identical | identical | PASS |
| AD3/AD4 accuracy | ≥ 0.97 | 1.0 (36/36) | PASS |
| MIXED precision (adjudication key) | 1.0 | 1.0 (2/2) | PASS |
| MIXED recall (adjudication key) | 1.0 | 1.0 (2/2) | PASS |
| P0 precision (adjudication key) | ≥ 0.9 | 1.0 (20/20) | PASS |

All 26 adjudicated records resolve exactly as this contract specifies. The
frozen message-level key is untouched; the MIXED boundary is now scored against
this adjudication, which supersedes the frozen key's over-broad MIXED labels.
See `PROVENANCE_RESOLVER_V0_6_REPORT.md`.

## 6. Open items

- `requires_review` on all P0+AD4 and borderline records — these carry real Derek adoption and matter for the Conglomerate reconstruction later.
- The two kept MIXED records (`003597`, `021989`) are the highest-value MIXED material: Derek's substantive contributions embedded in imported artifacts.
- `integration_strength` per proposition is recorded in `MIXED_SEMANTICS_ADJUDICATION_V1.jsonl` for downstream proposition extraction.
