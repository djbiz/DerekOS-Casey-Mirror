# OUT-OF-SAMPLE FAILURE CURRICULUM V1

Status: `SAFETY GATE PASS — COVERAGE GATES FAIL — V0.6 NOT MODIFIED`

Benchmark: `FROZEN_OUT_OF_SAMPLE_ADJUDICATION_V1.jsonl` (163 records, sealed blind)
Resolver: `PROVENANCE_RESOLVER_V0.6` (frozen; predictions sealed before label freeze)
Corpus: DeepSeek platform delta export (`conversations.json`, ingest 2.0.0), 3,068
out-of-sample user records; 163 selected across hard families F01–F09.

## Primary result

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| False Derek Attribution | 0 | **0** | PASS |
| D0 precision | ≥ 0.98 | N/A (0 D0 predicted) | PASS (vacuously — no D0 emitted) |
| D0 recall | measure | **0.000** (0/28) | FAIL |
| P0 precision | ≥ 0.90 | **0.966** (57/59) | PASS |
| P0 recall | measure | **0.429** (57/133) | FAIL |
| MIXED precision/recall | measure | **0/0** (0/2) | FAIL |
| UNRESOLVED rate | measure | **0.638** (104/163) | high (fail-closed tradeoff) |
| AD3/AD4 accuracy | ≥ 0.97 | **0.029** (1/34) | FAIL |
| Span-boundary accuracy | measure | **0.000** | FAIL |
| Origin correctness | measure | resolver emits no origin field | FAIL (not measurable) |

**The out-of-sample safety gate — False Derek Attribution = 0 — holds on a
population the resolver never trained on.** That is the headline. V0.6 never
attributed a single non-Derek record to Derek across 163 adversarial hard cases
from a different AI platform.

**But coverage is poor.** 63.8% abstention, 0% D0 recall, 43% P0 recall, and
2.9% AD3/AD4 accuracy mean the resolver cannot serve as the sole attribution
engine for the DeepSeek export population as-is. The failure curriculum below
documents root causes **by family first**, per the Board directive. No resolver
behavior was tuned after seeing results; V0.6 remains byte-identical to the
frozen candidate.

---

## Failure families (root cause, by family)

### F09 — unknown-origin short directives: 26/26 D0 misses (root cause #1)

All 26 frozen-D0 short records (`"can we add acquisition blueprints…"`,
`"can you add all your recommendations…"`, `"I need a system of smart AI to run
20 premium python code tools…"`, `"I'm a visionary that sees gaps…"`) were
abstained to UNRESOLVED.

Root cause: `SHORT_CONTROL_ACT` in `provenance_resolver_v0_3.py` only matches
**affirmation/rejection vocabulary** (`yes|yep|ok|no|wrong|perfect|good|great|
i agree|that's not|i didn't`). Derek's actual short-directive register in this
export — `can we add`, `can you create`, `add all enhancement`, `I need`,
`I hear that`, first-person statements — is **not matched**, so the
DAE-3 "brief direct control act after an assistant turn" path never fires even
when `preceding_role == "assistant"` is available.

This is a **pattern-coverage gap, not a safety leak**: the resolver was shaped
on the ChatGPT-era adversarial set, where Derek's short replies were
"yes / perfect / no / wrong" style. The DeepSeek export contains the same
person directing in a different register.

### F01/F05/F06 — cross-platform paste: 74/74 P0 misses (root cause #2)

The dominant failure. 74 frozen-P0 records (paste of ChatGPT/Grok/other-AI
output into DeepSeek) were abstained.

Root cause: **shingle-based origin detection requires an in-corpus match
(`matched_frac ≥ 0.15`)**. Content pasted from a *different platform* that is
not represented in `messages.jsonl` has no shingle hit, so
`traceable_assistant_origin` is empty and `external_fingerprint` (URLs, email
markers, `Subject:`/`From:` headers) does not fire. The resolver then has no
positive imported-content evidence and fails closed.

The OOS bundles themselves carried a located origin candidate for 128/133
frozen-P0 records — but that candidate came from the **OOS builder's own
full-corpus index**, which includes the delta conversations; the resolver's
`CompactIndex`-equivalent reuse signal (`matched_frac`) is below the 0.15 bar
for these records because the origin lives in the same delta file the resolver
was never pointed at. Harness artifact + genuine cross-platform gap.

### F07 — external → Derek → AI chains: 22/22 P0 misses (root cause #3)

External pasted material (articles, email funnels, transcripts) without URL/
email-header markers. `external_fingerprint` is too narrow: it only fires on
URLs and mail headers, not on quoted article prose, funnel copy, or transcripts.

### F04 — rewrite requests: 13 misses (5 D0 + 8 P0) (root cause #4)

Five genuine Derek rewrite directives (`can you create a python code…`,
`can you create the same system`, `combines Meta AI and MCP agentic AI`) were
abstained — same SHORT_CONTROL_ACT gap. Eight P0 rewrite-carrier records were
also abstained because the imported body has no shingle match (root cause #2).

### F08 — long polished first-person material: 5/5 P0 misses (root cause #5)

Assistant-voice "I will implement / we will implement / Congratulations…"
records with no in-corpus origin. The resolver correctly refuses to call them
D0 (FDA preserved) but has no signal to call them P0 either — they are pure
style-based misses. These are the family where the Board's "stylistic
suspicion triggers a search but never proves P0" rule is most relevant.

### MIXED span boundary: 0/2 (root cause #6)

`oos_000032` and `oos_000110` (substantive Derek requirement over pasted body)
resolved to P0. The V0.6 MIXED gate requires the Derek span to match
`SUBSTANTIVE_DEREK_SPAN` (regexes like `i want`, `make the system`, `we
should`), but both records phrase the substantive requirement as `can you
create this to be for anything…` / `can we add in opt-in dojo and this below…`
— directive-verb carriers that the span regex does not recognize as
substantive. The span-function classifier is vocabulary-bound, not
proposition-bound.

### AD3/AD4 adoption: 1/34 (root cause #7)

The adoption resolver only upgrades to AD3/AD4 on `yes/perfect/good/great`
prefixes (and a `…but` variant for AD4). Derek's actual adoption register in
this population — `can you add this`, `please add this to the code`,
`can we add this to the system`, `these two should be combined`, `can you use
Todd Brown instead` — never reaches AD3/AD4. Only `oos_000141`
(`can you recreate this system with Todd Brown instead`) scored AD4, because it
matched the STYLE_TRANSFORM carrier path that carries an explicit AD4.

### Origin correctness: not measurable (root cause #8)

The resolver's prediction records carry no `origin_message_id` /
`origin_record_id` field (the origin lives inside `positive_evidence`
`source_reference`). The scorer could not verify origin correctness from the
prediction surface. This is a **reporting gap**, not a classification gap.

---

## Curriculum (what must change in V0.7 — NOT in V0.6)

Ordered by expected coverage gain per unit of safety risk:

1. **Broaden the direct-control-act DAE-3 path** (fixes F09/F04 D0 misses).
   Add directive-verb openers to `SHORT_CONTROL_ACT`: `can we|can you|can I`,
   `add|make|create|build|put|connect|integrate`, `I need|I want|I hear`,
   while keeping the ≤180-char / no-`\n\n` / preceding-assistant guard and
   never relaxing the D0 evidence bar. FDA must stay 0.
2. **Cross-platform origin oracle (fixes F01/F05/F06/F07 P0 misses)**. Run the
   resolver over the *delta* corpus as an origin source (same shingle index
   over all `ingest_version` buckets, not just the non-delta bucket), and add
   a "quoted/polished article prose" external fingerprint (no-URL quoted text,
   funnel copy, transcript markers). Safety rule: an origin located in the
   delta is still an assistant-authored origin → P0, never D0.
3. **Proposition-level span functions (fixes MIXED)**. Recognize substantive
   Derek spans by *proposition structure* (`can you create X to be Y`, `system
   needs to be able to…`, `change the below information to…`) rather than a
   fixed vocabulary list, per the substantive-meaning rule of
   `MIXED_SEMANTICS_ADJUDICATION_V1`.
4. **Adoption register expansion (fixes AD3/AD4)**. Map explicit request verbs
   with identifiable scope (`add this / add this to the system / use X instead /
   combine / fuse`) to AD3/AD4 with the proposition-scope guard; keep
   discussion/continuation/reuse at AD0-AD1.
5. **Emit origin fields on the prediction surface** so origin correctness is
   scorable (fixes reporting gap).

## Hard constraints carried forward

- V0.6 is frozen. No tuning against the frozen OOS labels or the adversarial
  benchmark. The failure curriculum is the V0.7 spec.
- FDA = 0 remains the non-negotiable gate; D0 recall gains must come from
  better evidence detection (items 1–2), never from lowering the bar.
- The frozen benchmark, sealed predictions, and this adjudication are immutable
  historical artifacts. The DeepSeek delta population remains a clean
  out-of-sample test for V0.7 (the resolver has never been tuned on it).
- `PROVENANCE_CORPUS_V1` is NOT authorized: the safety gate passed, but 63.8%
  UNRESOLVED / 0% D0 recall on the delta population means a corpus pass would
  silently lose genuine Derek material from this export. Corpus authorization
  requires the V0.7 coverage fix + a clean OOS re-run on the same frozen set.
