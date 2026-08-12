# PROVENANCE_INDEX_V0.3 — Design (not yet built)

**Status: design only.** Nothing in `03_PROVENANCE_INDEX/v0_2/` is modified by this
document. No code has been written against this design yet. Per the Architecture
Board's explicit instruction, this design is not being built to beat the frozen
30-case `PROVENANCE_INDEX_V0.2_FROZEN_BENCHMARK` — that benchmark is held out and
used only as an out-of-sample regression check once V0.3 exists, never as a
tuning target.

## 1. What layer this is, and what it is explicitly not

Restating the three-layer architecture (`MASTER_BRAIN_BUILD_SPEC.md` §12.12,
sharpened by the Architecture Board's latest message):

```
PROVENANCE INDEX        "Where could this come from?"
        |                candidate origins + transformation graph
        v
PROVENANCE RESOLVER      "Who authored/submitted/adopted it?"
        |                span-level provenance record
        v
ADOPTION/INTEGRATION     "How deeply did it become part of the real system?"
```

V0.3 is scoped to the **first layer only**. It must not:
- assign `evidence_class`, `submitted_by`, `adoption_status`, or any authorship
  judgment (that is Codex's Resolver lane — currently at FDA 0 / D0 100% /
  P0 96.55% / AD3-AD4 100%, mid-MIXED-semantics-audit, not to be touched here);
- compute `integration_strength` (that is a concept-graph-level rollup, §12.8,
  explicitly deferred until provenance is trustworthy — V0.3 can *emit the raw
  chain graph a later stage would compute it from*, but does not compute the
  IS0-IS5 value itself);
- touch `08_MASTER_PLAN/reconstruction_pilots/conglomerate/` (Kilo's Conglomerate
  lane) or run any Conglomerate V0.2 conclusions.

V0.3's job stays narrow and mechanical, same discipline as V0.2: given two
passages, is there textual evidence of derivation, and if so, in which
direction does chronology allow it to point. What's changing is *which
passages are eligible to be an origin* and *how many hops the output can
represent* — not the mechanism (shingle matching, passage segmentation,
diagonal contiguous-span detection, chronology-first filtering all carry
forward unchanged from V0.2; they were validated, not broken).

## 2. The concrete gap V0.2 has

V0.2's origin index (`origin_passage_index` in `provenance_index_v0_2.py`) is
built **only from `role == "assistant"` passages**. Every user-role passage is
only ever checked *against* that index, never added *to* it. This was a
reasonable first cut (it's the majority case: assistant proposes -> Derek
reuses), but the frozen benchmark itself now contains four confirmed real
cases V0.2 structurally cannot resolve correctly because of this:

- `fb_016`, `fb_017`, `fb_018` — Derek pastes raw external marketing copy,
  the assistant reformats it moments later in the same conversation. The
  *true* origin is Derek's own earlier message (which is itself carrying
  external content in) — V0.2 can only see the assistant's later reformat as
  a candidate, so it correctly refuses `DERIVATION_EDGE` (safe) but has no way
  to point at the real origin (incomplete).
- `fb_020` — the confirmed 3-hop chain: external copy -> Derek pastes it ->
  assistant reformats (same conversation) -> Derek reuses the *reformatted*
  version in a third, separate conversation. V0.2 finds the second edge
  (assistant reformat -> later reuse) correctly, but has no representation
  for the first hop (external -> Derek) at all, and no way to express that
  these are two hops of *one* chain rather than two unrelated hits.

This is exactly the shape the Architecture Board described: knowledge moves
`Derek -> AI -> Derek -> AI(different platform) -> Derek -> new system`, and a
one-directional, pairwise index can only ever see individual assistant-side
links in that chain, never the Derek-side links or the chain as a whole.

## 3. Core changes

### 3.1 Direction-neutral candidate discovery

Remove the `role == "assistant"` restriction on `origin_passage_index`. Every
passage (any role, any source) becomes eligible as **both** a candidate origin
and a candidate reuse. This roughly doubles the candidate-origin pool and the
matching cost, so passage segmentation (already required for >15,000-char
messages in V0.2) and the existing coarse-shingle pre-filter both matter more,
not less, at this scale — no algorithmic changes needed there, just confirming
the cost model still holds at ~2x candidate volume before running corpus-scale.

Direction is no longer assumed from role. It is decided the same way V0.2
already decides it for the assistant-only case: **chronology first** (only a
strictly earlier passage can be an origin), then **span strength** (longest
contiguous run, not raw shingle count) breaks ties among chronologically valid
candidates. The `reverse_match` / `SIMILARITY_EDGE` fallback stays exactly as
in V0.2 for the case where no chronologically valid candidate exists.

This change alone converts `fb_016`/`fb_017`/`fb_018` from "correctly silent"
to "correctly resolved": once Derek's earlier same-conversation message is
itself an eligible origin candidate, V0.2's own chronology-first logic already
knows how to prefer it over the later assistant passage.

### 3.2 Actor tagging (new field, prerequisite, verified as a real gap)

Checked directly against `CORPUS_RELEASE_001/messages.jsonl`: `author_name` is
`null` on all 72,241 records, and `role` only ever takes the values `user` /
`assistant` / `None` (51 null-role records — a separate, minor data-quality
item worth flagging to the ingest lane, not fixed here). There is currently
**no field that distinguishes a ChatGPT-assistant message from a Copilot-
assistant message from an other-ai-export-assistant message** — they're all
just `role: assistant`.

This matters for V0.3 specifically because a cross-platform chain (ChatGPT
output pasted into Copilot, or vice versa) needs to be distinguishable from a
same-platform chain — not because the derivation logic changes, but because
`cross_source` (already a V0.2 field, currently computed from `source_file`
prefix) should be driven by a real actor identity, and because any future
consumer (Resolver, integration-strength rollup) will need to answer "did
this idea move between AI platforms" as a first-class question, per the
Architecture Board's own chain diagrams.

Proposed field, computed deterministically from existing data (no new ingest
work required, purely derived at index-build time):

```
actor = "derek"                  if role == "user"
      = "chatgpt_assistant"      if role == "assistant" and source_file startswith "conversations-"
      = "copilot_assistant"      if role == "assistant" and source_file startswith "copilot"
      = "other_ai_assistant"     if role == "assistant" and source_file == "conversations.json"  (the other-ai-export)
      = "unknown"                otherwise (the 51 null-role records)
```

This is a read-only derivation for index purposes — it does not modify
`01_INGEST/messages.jsonl` or propose changing the canonical schema. If the
Architecture Board wants `actor` promoted to a real ingest-time field later,
that's a separate, small ingest-lane change, not part of V0.3.

### 3.3 Chain graph, not just pairwise edges

V0.2's output is a flat list of pairwise hits (`reuse_hits.jsonl`). That's
sufficient for single-hop derivation but cannot express "these three edges are
one chain." V0.3 adds a **chain-linking pass** that runs after pairwise edge
discovery (3.1) and before any output is written:

1. Build pairwise `DERIVATION_EDGE`s exactly as in 3.1.
2. Group edges into chains where `edge[i].reuse_record_id == edge[i+1].candidate_origin_record_id`
   (a passage that is a reuse in one edge and an origin in the next) — a
   straightforward union-find over the edge list, no new matching logic.
3. Tag each chain with its actor sequence (e.g. `["derek", "chatgpt_assistant", "derek"]`
   for `fb_020`'s pattern) — this is the field a future integration-strength
   rollup or the Resolver would consume to answer "did Derek's idea cross
   platforms."
4. A chain does not get a confidence score beyond its weakest edge — no new
   "chain confidence" metric is invented; a 3-hop chain is only as trustworthy
   as its least-supported single hop, reported plainly rather than averaged
   into a falsely-reassuring composite number.

Output schema addition to each hit record: `chain_id` (null if the edge is not
part of any multi-hop chain), plus a new sibling file `derivation_chains.jsonl`
listing each chain's ordered edge list and actor sequence, kept separate from
the per-edge `reuse_hits.jsonl` so existing single-edge consumers don't need
to change.

### 3.4 What does NOT change

- Passage segmentation (2,500-word / 250-word overlap for >15,000-char
  messages) — validated at 63/63 correct on the AXIOMOS-class case in the
  frozen benchmark, kept as-is.
- Diagonal-grouping contiguous-span detection — kept as-is.
- Chronology-first candidate filtering, never max-similarity-alone — kept
  as-is, now applied over a larger (direction-neutral) candidate pool.
- `SIMILARITY_EDGE` vs `DERIVATION_EDGE` split and the promotion rule — kept
  exactly as-is. This is the piece the frozen benchmark just confirmed at
  0/14 confirmed false promotions; there is no reason to touch it.
- Corpus release discipline — V0.3 reads `CORPUS_RELEASE_001` (or whichever
  release is current when it runs), never the live mutable `messages.jsonl`.

## 4. Open item, explicitly not decided here: reconciling integration-strength terminology

`08_MASTER_PLAN/reconstruction_pilots/conglomerate/build_gen3_adoption_chains_v4.py`
(Kilo's lane, read for context only, not modified) already has a working
`integration_strength()` function using a 5-bucket occurrence-count scheme:
`NONE / LOW / MEDIUM / HIGH / VERY_HIGH`, driven purely by how many times a
proposition's search string appears in the corpus. `MASTER_BRAIN_BUILD_SPEC.md`
§12.8 independently specs a semantic 6-level scale, `IS0`-`IS5`
(mentioned-once through operationalized-into-a-real-system) — not occurrence-
count-driven, but stage-of-adoption-driven.

These are two different measurements that happen to share a name. Kilo's
version is a cheap, already-working proxy; the spec's version is a richer
semantic target. V0.3's chain graph (3.3) is structured so it could feed
either — the `chain_id` grouping and actor sequence are the raw material both
schemes need. **Which scheme is canonical is an Architecture Board decision,
not something to resolve unilaterally inside this design.** Flagging it here
so it doesn't get silently decided by whichever lane builds the rollup first.

## 4a. Two real findings from grounding this design against the actual corpus (not hypothetical)

Before writing the benchmark tranche, I ran a direct (non-indexed, ad-hoc)
8-gram shingle scan of the 400 Copilot messages against the rest of
`CORPUS_RELEASE_001`, to check whether cross-platform, direction-neutral
candidates actually exist before designing around them.

1. **They do exist, beyond the already-known Legacy Forge case.** 181 Copilot
   messages (across 5 conversations) share at least one 8-gram with a
   non-Copilot message. One conversation
   (`copilot_conv_9ed50fbef4bfa0dbb96778a805d1a764`) is a genuine candidate
   worth a full case write-up: a Copilot user message dated 2026-01-20
   references "Todd Brown" and "Max Steingart" system recreations in a way
   that echoes phrasing patterns from earlier ChatGPT conversations.

2. **The scattered-weak-match risk is not unique to giant documents — it
   shows up here too, at normal message length.** One Copilot assistant
   message (`copilot_msg_389c140cc897c110d629874d032a59bd`, 9,804 chars)
   appeared to share content with "62 other-platform messages" under a naive
   count. Direct inspection showed the true picture: no single other-platform
   message shares more than 5 shingles with it — the 62 is 62 *different*
   messages each sharing exactly one generic phrase (assistant boilerplate:
   "would you like me to", "let me know if you", etc.), not one substantial
   match. This is the same failure mode the AXIOMOS bug exposed in V0.1,
   just at message-scale instead of 269,000-char-document scale. It confirms
   §3.4's decision to carry forward V0.2's contiguous-span / diagonal-grouping
   logic unchanged is correct — a raw "number of messages sharing any
   shingle" count would produce exactly this kind of misleading fan-out at
   corpus scale once the candidate pool roughly doubles under direction-
   neutral discovery (§3.1). Real motivating case for why 3.1's contiguous-
   span requirement is a de-scoped safeguard, not incidental.

3. **A related noise source specific to multi-actor matching, not present in
   V0.2's assistant-only design**: recurring assistant *voice* (e.g. "Derek,
   this is exactly the kind of thing you and I do best together") can echo
   across platforms/conversations purely because multiple AI assistants
   converge on similar flattering, similarly-trained phrasing — not because
   any text actually transmitted between them. One shingle of overlap on a
   stock phrase is not evidence of derivation. V0.3's minimum-contiguous-span
   threshold already filters this (a single 8-word stock phrase won't clear
   the span-length bar that promotes a hit to even `SIMILARITY_EDGE`), but
   it's worth naming explicitly as a new noise category direction-neutral
   discovery introduces: **cross-platform assistant-voice convergence**,
   distinct from **cross-conversation generic-boilerplate** (the AXIOMOS
   pattern) and genuine content derivation.

## 5. Benchmark strategy

- The frozen 30-case `PROVENANCE_INDEX_V0.2_FROZEN_BENCHMARK`
  (`03_PROVENANCE_INDEX/frozen_benchmark/`) stays exactly as frozen. Once V0.3
  exists, it gets run once as an **out-of-sample regression check** — it was
  never built with V0.3 in mind, so a clean pass on it is reassuring but not
  the target. In particular, `fb_016`/`fb_017`/`fb_018`/`fb_020` are the cases
  to watch: V0.2 correctly abstained on them (`SIMILARITY_EDGE`/`reverse_match`);
  V0.3 should be able to resolve them to real `DERIVATION_EDGE`s pointing at
  the true (Derek-side or external-side) origin. If V0.3 gets those *wrong*
  in a new way (e.g. a false attribution it didn't make before), that's a
  regression to report, not tune away silently.
- A **new, separate benchmark tranche** is being started (task tracked
  independently, see `03_PROVENANCE_INDEX/frozen_benchmark_v0_3/`, not yet
  frozen) targeting scenarios V0.2 structurally cannot represent at all:
  cross-platform multi-actor chains (Copilot <-> ChatGPT <-> other-ai-export),
  3+ hop chains, and same-conversation Derek-as-origin cases beyond the
  Matt-Diggs pattern already in the frozen 30. This tranche is being grounded
  in real corpus examples (verified by direct search, not invented), same
  discipline as the frozen 30.

## 6. Non-goals for this pass (explicit, per Architecture Board instruction)

- No changes to `PROVENANCE_RESOLVER_V0.2` or a `V0.3` resolver build.
- No MIXED-label semantics work — that is Codex's audit, on Codex's lane.
- No Conglomerate V0.2 execution or promotion of any `08_MASTER_PLAN` output.
- No `integration_strength` computation — raw material only (§4).
- No corpus-scale run yet — this document is design, not an execution report.
