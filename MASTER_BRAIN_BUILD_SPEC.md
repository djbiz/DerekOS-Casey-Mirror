# MASTER_BRAIN_BUILD_SPEC.md

**Project:** DerekOS Master Brain — Conversation Archive Knowledge Extraction
**Status:** Draft v2 — Phase 1 (Ingest) complete and real. Phase 2 (Atomic Thoughts) not yet started at scale; a real pilot is in progress. Everything under §12 is forward-looking design, not executed work — do not treat any of it as having produced output until this status line says otherwise.
**Owner of this document:** Architecture Board (Derek). Changes to this spec require Board approval, the same way ADRs work in vox_v4.

**Provenance note (2026-08-12):** two messages in this build's history described detailed "Phase 2.5" and "Constitutional Core v0.1" results (specific record counts, file names, principles) that were never actually produced — verified directly against the filesystem, `02_EXTRACTED_THOUGHTS/`, `03_ENTITIES/`, and `08_MASTER_PLAN/` were empty when those messages arrived. The *design ideas* in those messages were sound and are captured in §6 (revised) and §12 below. The *results* were not real and must not be treated as prior art by any agent reading this spec. Every count/statistic in this document from this point forward is either labeled "not yet executed" or is backed by a file that actually exists in this directory — check before trusting.

---

## 0. Mission

Turn 35 raw ChatGPT conversation export files into a structured, provenance-tracked knowledge base that DerekOS can query — not a single summarized document, and not a RAG index over raw text. The deliverable is a layered pipeline:

```
Raw evidence → atomic thoughts → entities → relationships → timelines → canonical concepts → Master Plan
```

Every claim in every later layer must trace back to an exact message in the raw archive. The system must be able to distinguish **what Derek said** from **what an assistant suggested**, and must never let an AI-generated suggestion silently become a remembered "fact" about Derek's history.

This document is the contract. Six agents build one brain, not six interpretations of one.

---

## 1. Prime Directive

> **Nobody modifies `00_RAW_ARCHIVE`. Ever.**

`00_RAW_ARCHIVE/chatgpt/` is mounted read-only (POSIX `444` + Windows `readonly` attribute already applied). No agent — including Audit Bot — has a code path that writes there. If a script needs to "clean" or "normalize" the raw data, it writes the result to `01_INGEST/`, never back to `00_RAW_ARCHIVE/`.

Any agent whose task appears to require modifying `00_RAW_ARCHIVE` has misunderstood its task. Stop and escalate to the Board instead.

---

## 2. Source Corpus (what's actually in `00_RAW_ARCHIVE/chatgpt/`)

Extracted from the ChatGPT data export zip. Verified directly against the real files before writing this spec — this is not a guess at the schema.

| File | Contents |
|---|---|
| `conversations-000.json` … `conversations-034.json` | 35 files, the **primary corpus**. Each file is a JSON array of conversation objects (100 conversations in `conversations-000.json`, counts vary per file). |
| `ads.json` | Export metadata, secondary. |
| `conversation_asset_file_names.json` | Maps asset/attachment references used inside conversations to their export filenames. Secondary — useful for resolving `file-service://` references in message content if an agent's extraction hits one, not itself a source of thoughts. |

**Deliberately excluded from `00_RAW_ARCHIVE`:** `chat.html` (208MB, a redundant HTML rendering of the same JSON data) and ~hundreds of `file-*.dat` binary attachments (images/files referenced by conversations). The original zip in `Downloads/` is untouched and still contains everything, including these, if an agent's work later proves it needs a specific attachment. Do not re-extract them into `00_RAW_ARCHIVE` without Board approval — if genuinely needed, extract to `01_INGEST/attachments/` instead, keeping the read-only rule intact.

### 2.1 Real JSON shape (verified against `conversations-000.json`)

```
conversation := {
  "id": "<uuid>",                  # same value as conversation_id
  "conversation_id": "<uuid>",
  "title": "<string>",
  "create_time": <unix float>,
  "update_time": <unix float>,
  "current_node": "<node id>",     # tip of the currently-active branch
  "mapping": { "<node id>": node, ... },   # the full message graph, including edited/abandoned branches
  "is_archived": <bool>, "is_starred": <bool|null>, "default_model_slug": "<string>",
  ... (other export metadata fields not relevant to extraction)
}

node := {
  "id": "<node id>",
  "parent": "<parent node id>" | null,
  "message": message | null        # null for the synthetic root node
}

message := {
  "id": "<message id>",
  "author": { "role": "user" | "assistant" | "system" | "tool", "name": <string|null> },
  "create_time": <unix float | null>,
  "content": { "content_type": "text" | other, "parts": [<string>, ...] },
  "metadata": { ... }               # may contain model slug, citations, etc. - inspect per-message, don't assume a fixed shape
}
```

**Reconstructing conversation order:** `mapping` is a tree (edits/regenerations create siblings), not a flat list. To get the actual linear conversation as it was last seen, walk parent pointers backward from `current_node` to the root, then reverse. Do not assume `mapping`'s dict iteration order is conversation order — verified it is not guaranteed to be.

**Roles seen in sampling:** `user`, `assistant`. Do not hard-code only these two — `system`/`tool` roles are part of the standard export schema and may appear in other files; handle unknown roles by preserving them, not dropping them silently.

**Encoding:** content includes emoji and other non-ASCII Unicode. All tooling must read/write UTF-8 explicitly (Windows default encoding will crash on emoji — confirmed during corpus inspection for this spec).

---

## 3. Working Directory Structure

```
DerekOS_Master_Brain/
├── MASTER_BRAIN_BUILD_SPEC.md   # this file
│
├── 00_RAW_ARCHIVE/              # READ ONLY. Ever.
│   └── chatgpt/
│       ├── conversations-000.json ... conversations-034.json
│       ├── ads.json
│       └── conversation_asset_file_names.json
│
├── 01_INGEST/                   # Codex. Parsed, deduplicated, machine-readable message records.
├── 02_EXTRACTED_THOUGHTS/       # Claude. Atomic thought objects (see §5).
├── 03_ENTITIES/                 # Claude + Hermes. People, businesses, projects, inventions, places as named entities.
├── 04_PROJECTS/                 # Canonical per-project rollups (DerekOS, VOX, Mega Agent, Portal Farms, Cold Core, ...).
├── 05_BUSINESSES/               # Canonical per-business rollups.
├── 06_FRAMEWORKS/                # Canonical per-framework rollups (e.g. Business Character Method).
├── 07_DECISIONS/                # Explicit decisions Derek made, with the evidence class that supports each.
├── 08_MASTER_PLAN/              # The synthesized, canonical plan-of-record. Built LAST, from everything above.
├── 09_RELATIONSHIP_GRAPH/       # Hermes. Graph edges between entities/thoughts, each tagged fact vs inferred.
├── 10_CANONICAL_KNOWLEDGE/      # Deduplicated, merged, current-truth version of every concept (post-conflict-resolution).
├── 11_ARCHIVED_SUPERSEDED/      # Concepts that were explicitly replaced or abandoned - kept, not deleted, with supersedes/superseded_by links.
├── 12_CONFLICTS/                # Every detected contradiction, unresolved until the Board or explicit rule resolves it.
├── 13_SOURCE_INDEX/             # Reverse index: conversation_id/message_id -> every derived object that cites it.
└── 14_TESTS_AUDITS/             # Audit Bot's independent verification reports and the automated checks that gate promotion between phases.
```

Every directory from `01_` through `14_` holds JSON (or JSONL for large flat collections) plus a `README.md` describing the schema in effect at that stage. No agent invents a new top-level directory without Board approval — this list is the complete structure.

---

## 4. The Six Agents — Division of Labor

The rule that matters most: **each agent owns a stage, not a copy of the whole pipeline.** No agent re-implements another agent's stage "just to be safe." If an agent believes an earlier stage's output is wrong, it flags it (writes to `12_CONFLICTS/` or escalates to the Board) — it does not silently redo that stage's work with its own logic.

### OpenCode — Lead Builder
Owns the repository structure, the ingestion pipeline's scaffolding, the JSON schemas (in coordination with this spec), and integration between stages. Responsible for:
- The `01_INGEST/` pipeline's runnable entrypoint (script or module) that Codex's parsing logic plugs into.
- Enforcing that every stage's output validates against its schema before the next stage may consume it (schema validation gate, not just documentation).
- Wiring the final `10_CANONICAL_KNOWLEDGE/` + `08_MASTER_PLAN/` output into whatever DerekOS-facing retrieval interface comes next (out of scope for this spec's initial build, but the schema must not preclude it).
- Does **not** write extraction logic (that's Codex) or interpret meaning (that's Claude).

### Codex — Data / Extraction Engineer
Owns `01_INGEST/`. Responsible for:
- Correctly parsing the `mapping` tree per §2.1 (parent-chain walk from `current_node`, not naive dict iteration).
- Extracting one normalized message record per real message: conversation id/title, message id, role, author name, timestamp, full text (all `parts` joined), source file.
- Deduplication: the same conversation can legitimately appear only once per its `conversation_id` — flag (don't silently drop) any duplicate `conversation_id` found across different `conversations-NNN.json` files.
- Output: `01_INGEST/messages.jsonl` (one JSON object per message, see §5.1 for the record shape) plus `01_INGEST/conversations_index.json` (conversation-level metadata: id, title, create_time, update_time, source_file, message_count).
- Does **not** decide what a message *means* (that's Claude) or build relationships (that's Hermes).

### Claude — Knowledge Architect
Owns `02_EXTRACTED_THOUGHTS/`, `03_ENTITIES/` (content, not graph structure), `06_FRAMEWORKS/`, `07_DECISIONS/`. Responsible for:
- Reading Codex's normalized messages and identifying atomic thoughts: ideas, businesses, inventions, goals, principles, corrections, decisions, dependencies, and their evolution over time.
- For every extracted thought, determining **originator** — was this Derek's own statement, or an assistant suggestion Derek later adopted, or purely an assistant proposal never acted on? This is the single most important judgment call in the whole pipeline (see §6, Evidence Classes).
- Tracking evolution explicitly: when a later message develops, renames, or supersedes an earlier concept, record that as `supersedes`/`superseded_by`, not as a brand-new unrelated thought.
- Does **not** build the relationship graph (that's Hermes) or write production code (that's Kilo).

### Hermes — Relationship / Memory Engineer
Owns `09_RELATIONSHIP_GRAPH/`. Responsible for:
- Building graph edges between the entities and thoughts Claude and Codex produced: `Cold Core → Portal Farms`, `DerekOS → VOX → Mega Agent`, businesses → infrastructure → people → projects, and anything else the corpus actually supports.
- Every edge is tagged `fact` (explicitly stated in the source, e.g. "Portal Farms grew out of Cold Core") or `inferred` (Hermes connected two things because they're topically/temporally related, but the corpus never states the connection directly). **Inferred edges get `confidence < 1.0` and `evidence_class: "I0"` — never presented with the same weight as a stated fact.**
- Does **not** decide what a thought *means* (Claude's call) — Hermes connects what Claude and Codex have already extracted, it doesn't reinterpret it.

### Kilo — Implementation / Refactoring Agent
Turns Board-approved architecture (this spec, plus whatever `08_MASTER_PLAN/` schema OpenCode locks in) into production-quality code: the ingestion pipeline's runnable modules, indexes, search/retrieval, and eventually DerekOS integration. Responsible for:
- Implementing exactly what's specified — **not** independently reinterpreting the master plan while coding it. If the spec is ambiguous or looks wrong once Kilo is implementing it, that's a question back to the Board/OpenCode, not a unilateral design decision.
- Code quality, tests for the code itself (distinct from Audit Bot's content-correctness audits).

### Audit Bot — Independent Judge (read-only)
Owns `14_TESTS_AUDITS/`. Has read access to everything, write access only to `14_TESTS_AUDITS/`. Responsible for:
- Auditing every other agent's output against the original conversation corpus in `00_RAW_ARCHIVE/`, directly — not against another agent's derived summary of it.
- The canonical audit question: for a sample of extracted thoughts, re-read the actual source message and confirm the `originator`/evidence class is correct. Must be able to produce findings in the form: *"That claim is attributed to Derek, but the source shows the assistant proposed it and Derek never approved it."*
- Flagging every contradiction found into `12_CONFLICTS/` with both sides' evidence.
- **Never implements a fix.** Audit Bot reports; the owning agent (per §4) or the Board decides the resolution.

---

## 5. Schemas

### 5.1 Ingested Message Record (Codex → `01_INGEST/messages.jsonl`)

```json
{
  "message_id": "<id from message.id>",
  "conversation_id": "<id>",
  "conversation_title": "<string>",
  "source_file": "conversations-033.json",
  "role": "user | assistant | system | tool",
  "author_name": null,
  "timestamp": "<ISO 8601, converted from create_time>",
  "text": "<all parts of content.parts joined>",
  "sequence_index": 0
}
```
`sequence_index` = position in the parent-chain-walked linear order for that conversation, starting at 0. This is what lets later stages say "message 14 of conversation X" without re-walking the tree.

### 5.2 Atomic Thought (Claude → `02_EXTRACTED_THOUGHTS/`)

This is the object every later layer is built from. Matches the shape Derek specified exactly:

```json
{
  "id": "thought_0001842",
  "name": "Business Character Method",
  "type": "framework | idea | business | invention | goal | principle | correction | decision | dependency",
  "originator": "derek | assistant | collaborative",
  "evidence_class": "D0",
  "status": "active_concept | abandoned | superseded | proposed_only",
  "source_file": "conversations-033.json",
  "conversation_id": "...",
  "message_id": "...",
  "timestamp": "...",
  "original_text": "...",
  "summary": "...",
  "supersedes": [],
  "superseded_by": null,
  "relationships": [],
  "confidence": 1.0
}
```

Field notes:
- `originator: "collaborative"` is valid and expected — e.g. Derek states the seed idea (D0), the assistant develops it further in the same or a later message (A0), and Derek later uses/approves the developed version (D1). Don't force a single-message-only view of originator; track it as of the *specific text* being recorded, and let `supersedes`/evolution links show the collaborative arc across multiple thought records if the idea changes across messages.
- `relationships` here is a list of `{target_thought_id, relation_type}` — the same-layer, thought-to-thought links Claude can state directly from context. Cross-entity/cross-domain graph edges belong to Hermes in `09_RELATIONSHIP_GRAPH/`, not duplicated here.
- `confidence` reflects Claude's confidence in the *extraction/classification*, not a business judgment about whether the idea is good.

### 5.3 Entity (`03_ENTITIES/`)

```json
{
  "id": "entity_business_0004",
  "entity_type": "person | business | project | invention | place | infrastructure",
  "canonical_name": "Portal Farms",
  "aliases": ["Portal Farm", "PortalFarms"],
  "first_mentioned": { "source_file": "...", "conversation_id": "...", "message_id": "...", "timestamp": "..." },
  "status": "active | dormant | abandoned | unknown",
  "evidence_class": "D0",
  "thought_ids": ["thought_0001842", "..."]
}
```

### 5.4 Relationship Edge (Hermes → `09_RELATIONSHIP_GRAPH/`)

```json
{
  "id": "edge_000391",
  "from_entity": "entity_business_0002",
  "to_entity": "entity_business_0004",
  "relation_type": "evolved_into | depends_on | part_of | inspired | funds | competes_with | other",
  "kind": "fact | inferred",
  "evidence_class": "D0 | I0",
  "confidence": 1.0,
  "supporting_thought_ids": ["thought_0001842"],
  "note": "optional free text explaining the inference, required if kind=inferred"
}
```

### 5.5 Conflict Record (`12_CONFLICTS/`)

```json
{
  "id": "conflict_000012",
  "detected_by": "audit_bot | hermes | claude",
  "description": "...",
  "conflicting_objects": ["thought_0001842", "thought_0002210"],
  "status": "open | resolved_by_board | resolved_by_rule",
  "resolution": null
}
```

---

## 6. Evidence Classes (constitutional — applies to every object in every layer)

**Revised 2026-08-12: added `P0`.** Originally, pasted/external content had no distinct class and risked being conflated with `X0`. That conflation is a real error, not a stylistic choice — "Derek pasted this for discussion" and "Derek rejected this" are opposite epistemic states, and collapsing them would destroy exactly the adoption chains (external idea → Derek adopts → Derek modifies → canonical) this project exists to preserve.

| Code | Meaning |
|---|---|
| **D0** | Direct Derek statement — Derek said this himself, in his own words, in the source message. |
| **D1** | Derek explicitly approved/adopted something the assistant proposed, or adopted/modified `P0` external content ("yes, let's do that," "I like this," acted on it in a later message). |
| **A0** | Assistant suggestion only — proposed by the AI, never confirmed accepted or rejected by Derek in the corpus. |
| **P0** | Content submitted by Derek but demonstrably originating elsewhere — assistant output (including the assistant's own earlier response reused across conversations, not just outside sources), quoted material, pasted articles, transcripts, other people's frameworks. Non-Derek authorship, Derek-initiated inclusion. Distinct from `A0` (assistant-originated, still in the assistant's own turn) and from `X0` (rejected) — a `P0` record has not yet been evaluated as accepted or rejected merely by existing. |
| **I0** | Machine inference / relationship — a connection or claim derived by an extraction/graph agent, not stated directly by anyone in the source. |
| **E0** | Externally researched information — content the assistant pulled from outside knowledge (not from Derek), presented as background/context rather than as Derek's own idea. |
| **B0** | Claimed built/completed — someone (Derek or assistant) states something was built or finished; requires separate evidence before being trusted as actually done. Mirrors this session's own "no fabricated success" discipline from the vox_v4 sprint — a B0 claim is not itself proof. |
| **X0** | Rejected/superseded by Derek — Derek explicitly said no, changed his mind, or moved away from this. **Reserved strictly for explicit rejection/supersession.** Pasted external content that Derek never explicitly rejected must be `P0`, not `X0`, regardless of whether anyone later acts on it. |

**Adoption chain pattern (must be preserved, not collapsed):**
```
P0  — external framework/idea, pasted by Derek
 ↓  (Derek: "that's exactly what I want, add this")
D1  — Derek adopts it
 ↓  (Derek develops/changes it further)
D0  — Derek's own modification
 ↓
→ eligible for canonical status (§6 rule 4, §12)
```
An extraction agent that defaults unadopted `P0` content to `X0` "to be safe" is committing the exact error this revision fixes — the correct default for an un-actioned `P0` is to stay `P0`, not to become `X0`.

Rules:
1. Every atomic thought, entity, relationship edge, and canonical-knowledge object carries exactly one `evidence_class` (or, for objects synthesized from multiple sources, the class of its weakest supporting link — a canonical concept built from one D0 and one A0 source is not stronger than A0 unless a D1 approval exists).
2. **No object may claim `evidence_class: "D0"` unless the `original_text` field, when read by a human, is unambiguously Derek's own words** — not the assistant paraphrasing Derek, not the assistant's expansion of Derek's idea, not pasted external text (that's `P0`).
3. When an assistant response develops an idea Derek seeded (the Business Character Method example), record it as **two linked thoughts**: one D0 (Derek's original seed statement) and one A0 (the assistant's expansion), connected via `relationships`/`supersedes` so DerekOS can answer "who originated this" and "how did it evolve" as two different, both-true answers — never collapse them into a single D0 record that misattributes the expansion to Derek.
4. `08_MASTER_PLAN/` and `10_CANONICAL_KNOWLEDGE/` may only promote a concept to "canonical, active" status if it has at least one D0 or D1-backed component. A purely A0 concept (never adopted) stays visible and traceable but is marked `status: proposed_only`, not folded into the Master Plan as if it were a decision. A purely `P0` concept (pasted, never adopted) stays visible and traceable, marked `status: supplied_not_adopted` — never promoted, never silently reclassified as `X0`.
5. Audit Bot spot-checks evidence-class assignment as its primary job (§7), with specific attention to `P0`-vs-`X0` and `D0`-vs-`A0` misclassification (the two error modes already known to be easy to make).

### 6.0a `role` is not `evidence_class` — the single most important extraction rule

**Verified with a real example, not theoretical** (see `02_EXTRACTED_THOUGHTS/PILOT_REPORT.md`, `thought_pilot_0003`): the export's `message.author.role` field says who *submitted* a message, not who *originated* its content. A message tagged `role: "user"` can be Derek pasting the assistant's own prior output — verbatim, from a different conversation — back into a new thread. Trusting `role` alone would have misattributed a whole framework as `D0` (Derek's own origination) when it was demonstrably `P0` (submitted by Derek, authored by the assistant, twelve minutes earlier, in a different conversation).

Any `P0` classification driven by reused/pasted content must carry the origin, not just assert it:
```json
{
  "evidence_class": "P0",
  "submitted_by": "derek",
  "original_author": "assistant | derek | external | unknown",
  "origin_message_id": "<message_id of the earliest known occurrence>",
  "origin_conversation_id": "...",
  "reuse_message_id": "<message_id of this record>",
  "reuse_conversation_id": "..."
}
```
`original_author: "derek"` is valid — e.g. Derek pasting his *own* earlier writing from outside this archive (see `thought_pilot_0010`, a 2024 LinkedIn headline of unverifiable origin) is still `P0` per rule 2 below, because the text isn't unambiguously authored *in this message*, even if Derek wrote it somewhere else. `original_author: "unknown"` is used, not guessed, when authorship can't be determined from available evidence.

**Detecting likely reuse (a search trigger, never proof by itself):** unusually polished/structured prose for a `user`-role message, long markdown tables or headers, trademarked/named-framework language, repeated headings across conversations, phrases like "add this," "what do you think of this," "here's the text." **Stylistic suspicion may trigger a cross-corpus search. It must never itself produce a `P0` classification** — only a matching `origin_message_id` (an actual located source) does.

**Revised 2026-08-12 (`PROVENANCE_RESOLVER_V0.1` benchmark, `gold_020`): "no match found" does NOT mean "stays D0."** The original rule here said a stylistically-suspicious message with no located origin defaults to `D0` with lowered confidence. That default is wrong and was the direct, verified cause of the one real False Derek Attribution in the v0.1 benchmark — `gold_020` (a "9 things I've learned" listicle with hardship details inconsistent with Derek's documented business context) had no locatable cross-corpus match, and the old rule let "we searched and found nothing" stand in for "this is Derek's own writing." **Absence of a located match is not positive evidence of Derek origination — it just means the search didn't find anything.** The corrected rule: genuine stylistic suspicion with no located match goes to `UNRESOLVED` (§6.0f), not `D0`. `D0` is the default **only** when there is no meaningful suspicion signal in the first place — an ordinary, casual, in-voice message doesn't need a search to justify staying `D0`; a message that *does* trigger suspicion needs a located match to leave `UNRESOLVED`, not merely the absence of a hit.

**A second, separate refinement — quoted-span discounting**, for a distinct known failure mode (the `gold_010` abstention-tuning case, not the same bug as above): a short cross-corpus shingle match is *weak* evidence when the matched span appears inside quotation marks in the message being classified (e.g. `create an image for this title: "The Seven Myths About..."`) — this pattern is Derek referencing/reusing his own recurring title or label across multiple requests about the same content piece, which naturally produces a coincidental match against whatever other message also echoes that title back, and is not evidence that *this specific message* was authored elsewhere. An **unquoted** match of comparable size (e.g. the LinkedIn headline correction, §6.0h) is much stronger evidence, because free-standing prose matching another message word-for-word has no similarly innocent explanation. Both cases in this paragraph had nearly identical raw match statistics (~53% shingle coverage) — coverage percentage alone cannot separate them; the quoted/unquoted distinction can, cheaply and generalizably, without hand-coding either specific message.

```
role: user
   |
   v
Meaningful suspicion signal present? (polish/structure/length/paste-markers/
a cross-corpus shingle match that is NOT confined to a quoted title/label)
   |
   +--No--> D0 (no search needed to justify this - ordinary in-voice message)
   |
   +--Yes--> Cross-corpus search for a matching origin
              |
              +--> Earlier assistant-authored match found (unquoted) --> P0 (original_author: assistant)
              +--> External/other-person source identifiable --> P0 (original_author: external)
              +--> Match found but confined to a quoted title/label --> weak evidence,
              |     does not by itself move the record off D0 - treat as noise unless
              |     other suspicion signals are also present
              +--> No match found, suspicion signal still stands --> UNRESOLVED
              |     (NOT D0 - absence of a match is not evidence of Derek origination)
```

### 6.0b Adoption Strength (`AD0`–`AD4`) — a third, orthogonal axis

Resolves the open question from the pilot ("does continuing inside an assistant's frame count as adoption?"): **no, not by itself.** Continuing a conversation is engagement, not automatically adoption. Adoption strength is independent of both `evidence_class` (whose words) and `knowledge_value` (how significant) — a thought can be `A0` (assistant-originated) and `K5` (major idea) with `AD0` (Derek never acted on it), and that combination is itself meaningful: *"this may be a major idea, but there is no evidence Derek accepted it."*

| Code | Meaning |
|---|---|
| **AD0** | No evidence of adoption. |
| **AD1** | Engagement / continuation — Derek keeps the conversation going in the same frame, without endorsing or rejecting the specific prior proposition. |
| **AD2** | Implicit partial adoption — Derek builds on part of the proposal without an explicit statement of acceptance. |
| **AD3** | Explicit adoption — a clear "yes, add that" / "that's exactly it," resolved to the specific parent proposition it approves (not blanket-applied to everything preceding it in the conversation). |
| **AD4** | Explicit modification/ownership — Derek adopts *and* changes/extends it, making it demonstrably his own. |

Only `AD3` and `AD4` are normally eligible to promote assistant-originated (`A0`) or pasted (`P0`) content toward Derek-owned canonical status (interacting with the `D1` evidence class and the principle-maturity rules in §6.2) — `AD0`/`AD1`/`AD2` content stays visible and traceable but does not advance.

Worked example (mirrors the real pilot data):
```
Assistant: "Call it The Identity Switch."
Derek:     "Yes, add that to the method."          -> A0 + AD3 (on that specific naming choice)

Assistant: "Here are six pieces of the Business Character Method: Identity, Script, ..."
Derek:     "What if emotion becomes another trigger?"
  -> the original six pieces remain A0 / AD1 (Derek engaged with the frame, did not
     endorse or reject the six specifically)
  -> "emotion becomes another trigger" is itself a new D0 thought, linked via
     relationships to the A0 framework it extends
```

### 6.0c Mixed-message segmentation

A single message is not always one evidence class. If Derek pastes two pages of assistant output and adds *"This is good, but remove funding and make VOX the operator,"* that message must **not** be recorded as one `P0` blob. It segments:
```
P0            -> the pasted assistant material (with origin_message_id/reuse_message_id)
D0            -> "remove funding"
D0            -> "make VOX the operator"
D1 / AD4      -> the modification itself: partial adoption of the pasted material, with explicit changes
```
Extraction agents must not default a mixed message to a single evidence class for convenience — segmenting is required whenever a message contains both reused/pasted content and Derek's own original commentary on it.

### 6.0d AD3 vs AD4, tightened

Refined definition (supersedes the examples in §6.0b, same codes):

| Code | Meaning |
|---|---|
| **AD0** | No adoption evidence — content exists; Derek hasn't meaningfully engaged with it. |
| **AD1** | Engagement — Derek asks about it, explores it, or continues discussion in its frame, without endorsing or rejecting the specific proposition. |
| **AD2** | Implicit/partial adoption — Derek begins building on part of the concept, but doesn't clearly approve the whole thing. |
| **AD3** | Explicit adoption — clear language equivalent to "yes, use this / add this / we're doing this / keep this," resolved to the specific parent proposition it approves. |
| **AD4** | Adopted + transformed/owned — Derek explicitly adopts something **and** materially modifies, integrates, renames, operationalizes, or makes it part of another Derek system. Expected to be rare. |

**`D0` and `AD4` are not interchangeable and answer different questions.** `evidence_class: D0` answers *"who originated this specific statement."* `adoption_status: AD4` answers *"what did Derek subsequently do with someone else's (A0/P0) thought."* A thought can be `A0` + `AD4` (assistant originated it, Derek adopted and transformed it — the transformation itself may separately be recorded as its own `D0` thought, linked via `relationships`) — collapsing these into one field would lose exactly the distinction the evidence-class system exists to preserve.

### 6.0e Provenance Certainty (`PC0`–`PC4`) — a fourth, orthogonal axis

Answers "how sure are we about the origin claim," independent of `evidence_class` (whose words), `knowledge_value` (how significant), and `adoption_status` (what Derek did with it). Applies most directly to `P0`/`original_author` claims, but may be used for any origin claim including `D0`.

| Code | Meaning |
|---|---|
| **PC0** | Unknown — no basis for an origin claim beyond the message's own `role`. |
| **PC1** | Weak indication — stylistic suspicion only (see §6.0a's search-trigger list), no located source. |
| **PC2** | Probable — a plausible source exists but the match is partial/paraphrased, not exact. |
| **PC3** | Strong match — substantial verbatim overlap with a locatable source. |
| **PC4** | Exact provenance match — the origin message is identified with `origin_message_id`, and the reused text matches it exactly (modulo whitespace/markdown formatting, per the normalization already proven out in the 10-record pilot). |

**Unknown is an acceptable, permanent result — never a placeholder to be pressured into resolving.** `original_author: "unknown"` + `PC0`/`PC1` is a legitimate final classification (see `thought_pilot_0010`), not an unfinished one. The Business Character Method cross-reference (`thought_pilot_0002` -> `thought_pilot_0003`) is `PC4`: exact `origin_message_id`, verbatim (whitespace/markdown-normalized) match.

### 6.0f Abstention (`UNRESOLVED` / `originator: "unresolved"`) — a required, first-class outcome

**Ambiguity is not something to resolve by force.** When a message genuinely cannot be classified with the evidence available — verified real cases: `provenance_gold_set_v1.jsonl` `gold_037`/`gold_040`, both `role: user` with content that reads stylistically like it could originate elsewhere, no located source, no other resolving evidence — the correct output is an explicit abstention, not a forced best guess:

```json
{
  "evidence_class": "UNRESOLVED",
  "originator": "unresolved",
  "provenance_certainty": "PC1",
  "requires_review": true
}
```

`evidence_class` therefore has a sixth valid value beyond `D0/D1/A0/P0/I0/E0/B0/X0`: **`UNRESOLVED`**. An extractor (human or automated) that is rewarded for *always* picking `D0` or `A0` rather than abstaining when the evidence genuinely doesn't support either is optimizing for the wrong thing — see the Bad Abstention Rate metric in §6.0g. `requires_review: true` routes the record to Audit Bot / human review rather than silently asserting a classification nobody actually verified.

### 6.0g Safety metrics for any provenance classifier (human or automated)

Four failure measures, in order of how dangerous they are to DerekOS's long-term integrity:

1. **False Derek Attribution Rate** — content actually authored by the assistant (or pasted from elsewhere) incorrectly labeled `D0`/`D1`. **The single most dangerous error this project can make** — this is exactly what the Business Character Method discovery (§6.0a) prevented. This is why `D0` precision is held to a stricter bar than everything else (§12.6).
2. **False Assistant Attribution Rate** — content Derek actually authored incorrectly labeled `A0`/`P0`. Real, but the harm runs the other direction (erasing Derek's own authorship rather than fabricating it) — serious, not treated as equally dangerous as #1.
3. **P0 Miss Rate** — reused/pasted content that should have been flagged `P0` but was instead accepted as `D0` without a search ever being triggered. A subset of #1's causes, tracked separately because it's specifically about whether the reuse-detection step ran at all.
4. **Bad Abstention Rate** (the primary metric under the broader **Abstention Quality** concept) — cases correctly resolvable with available evidence that were marked `UNRESOLVED` anyway (under-confidence), *and*, separately, cases that were genuinely unresolvable but got forced into `D0`/`A0`/`P0` instead of abstaining (over-confidence). Good abstention behavior is rewarded, not penalized — see §6.0f.

Any resolver (§12.6) reports all four against the frozen Gold Set (§14) before its output is trusted for anything beyond the benchmark run itself.

### 6.0h Evidence Truth vs. Adjudication Truth — append-only provenance history

**Verified, not hypothetical**: `PROVENANCE_RESOLVER_V0.1`'s Stage 1 found genuine source evidence for two records (`provenance_gold_set_v1` `gold_019`, `gold_037`) that a careful, good-faith manual review had missed — see `14_TESTS_AUDITS/provenance_gold_set_v1_ERRATA.md`. A frozen benchmark can still be *wrong*, not because the adjudication was careless, but because the evidence available at adjudication time was incomplete. More source archives will be connected to this project later (see `00_RAW_ARCHIVE/` — currently one export; more are expected), which will only increase how often this happens: a message honestly marked `UNRESOLVED` today may have a locatable origin once an earlier-dated archive is ingested.

This requires distinguishing two different kinds of "truth," and never overwriting one with the other:

- **Evidence truth** — what the currently available source evidence actually supports. Changes over time as more of the corpus (or more corpora) become available. Not an opinion — it's what a search would find right now.
- **Adjudication truth** — what a human or agent concluded from the evidence *available at a specific point in time*. A historical record of a decision, not a live, self-updating fact.

**Rule: canonical knowledge may evolve when new evidence appears; provenance history is append-only.** A correction never silently replaces a prior adjudication — it supersedes it, with both preserved and linked:

```json
{
  "gold_id": "gold_037",
  "evidence_class": "P0",
  "origin_message_id": "4df2be21-cf21-474f-af92-6676e3e17fe6",
  "supersedes_v1_gold_id": "gold_037",
  "superseded_at": "2026-08-12",
  "correction_source": "provenance_gold_set_v1_ERRATA.md, Correction 2"
}
```
DerekOS should eventually be able to say: *"Originally classified as unresolved on 2026-08-12. Later provenance analysis (resolver v0.1, same day) found a verbatim assistant source from 2025-05-25. Classification superseded; original adjudication retained in `provenance_gold_set_v1.jsonl`, unmodified."* Never: silently different history with no trace the earlier adjudication ever existed.

**Applied here**: `provenance_gold_set_v1.jsonl` stays immutable forever (§14's freeze rule — this section is *why* that rule exists, not just a benchmark-hygiene convenience). `provenance_gold_set_v1_1.jsonl` is a new, derived artifact carrying the correction, explicitly linked back via `supersedes_v1_gold_id`. The same pattern applies to every future correction at every layer (`02_EXTRACTED_THOUGHTS/`, `10_CANONICAL_KNOWLEDGE/`, etc.), not just this benchmark.

### 6.1 Knowledge Value (`K0`–`K5`) — a second, orthogonal axis

Evidence class answers "whose idea/claim is this." Knowledge value answers "how durable/significant is it." A thought can be `D0` (definitely Derek's own words) and still be `K0` (a passing conversational remark with no durable content) — the two axes are independent and both required.

| Code | Meaning | Admission bar |
|---|---|---|
| **K0** | No durable knowledge value — conversational filler, a question, an acknowledgment. | — |
| **K1** | Contextual / supporting detail. | — |
| **K2** | Meaningful standalone idea. | — |
| **K3** | Important — a real decision, correction, requirement, or framework component. | Broad category; can be assigned relatively liberally. |
| **K4** | **Foundational** — changes a business, system, framework, architecture, strategy, operating philosophy, or long-term direction. | Must show **structural significance**, not just emphatic wording. Keyword presence alone ("must," "never," "always") is **not sufficient** — a K4 scorer that promotes on keywords alone is known to over-classify (this exact failure mode was described, unprompted, in feedback on this spec — treat it as a real risk to guard against even though no scorer has been built yet). Require at least one of: named system/business/framework, an architecture relationship, a persistent governance/ownership boundary, a long-term goal, an explicit correction of previous architecture, a cross-system dependency, or a concept that recurs across multiple, separated conversations. |
| **K5** | **Constitutional** — governs multiple systems, or establishes a master-plan/constitutional-level principle. Expected to be rare — a small fraction of a percent of the corpus, not one in four. | Same structural bar as K4, at master-plan scope. |

Any real K4/K5 scorer built for this pipeline must be audited on a stratified random sample (Audit Bot, §7/§8) before its output is trusted for the Constitutional Core or Domain Architecture phases (§12) — this is a gate, not a formality, precisely because keyword-driven over-classification is the known failure mode.

### 6.2 Principle Maturity (applies once Constitutional Core work begins, §12)

A `K5`/constitutional-candidate thought does not become governing DerekOS doctrine just by being extracted. Three maturity states, in order:

- **`candidate`** — one high-confidence `D0`+`K5` statement. Nothing more required to exist as a candidate; nothing less required to be recorded.
- **`established`** — multiple independent `D0` records support it, **or** one `D0` record explicitly frames it as a permanent/master governing rule (not just stated once in passing).
- **`canonical`** — established, **and** survives a contradiction/supersession audit (no unresolved `X0`/contradicting `D0` against it).

A principle promoted straight from `candidate` to governing-rule status on the strength of a single unreinforced statement is a spec violation — this is the guard against "one intense moment becoming DerekOS law forever."

Every principle object additionally carries:
```json
{
  "principle_id": "P1",
  "name": "...",
  "scope": ["data architecture", "business systems", "..."],
  "status": "candidate | established | canonical",
  "supporting_d0_ids": ["thought_...", "..."],
  "contradicting_d0_ids": [],
  "first_seen": "ISO 8601",
  "last_reaffirmed": "ISO 8601 or null"
}
```
`scope` matters because a correct principle in one domain (e.g. "Single Source of Truth" for data architecture) is not automatically correct applied to every domain (creative decisions, scientific ideas, business strategy) — an unscoped principle is a mechanism for DerekOS to misapply a good rule in the wrong context.

---

## 7. Phases, Owners, and Exit Criteria

| Phase | Directory | Owner | Input | Exit criteria (gate before next phase may consume it) |
|---|---|---|---|---|
| 1. Ingest | `01_INGEST/` | Codex | `00_RAW_ARCHIVE/` | Every conversation in all 35 files produces a `conversations_index.json` entry; every message produces one `messages.jsonl` record; zero silently-dropped conversations (duplicates are flagged, not dropped); OpenCode's schema validator passes on the full output. |
| 2. Atomic Thoughts | `02_EXTRACTED_THOUGHTS/` | Claude | `01_INGEST/` | Every thought has a valid `evidence_class` and non-null `source_file`/`conversation_id`/`message_id`; every D0 claim's `original_text` is independently verifiable by re-reading the cited message (Audit Bot checks this before the phase is considered exited, not after). |
| 3. Entities | `03_ENTITIES/` | Claude + Hermes | `02_EXTRACTED_THOUGHTS/` | Every entity has `first_mentioned` provenance and at least one linked `thought_id`. |
| 4. Relationship Graph | `09_RELATIONSHIP_GRAPH/` | Hermes | `03_ENTITIES/`, `02_EXTRACTED_THOUGHTS/` | Every edge tagged `fact` or `inferred`; every `inferred` edge has a `note` explaining the basis; no edge references a nonexistent entity/thought id. |
| 5. Domain Rollups | `04_PROJECTS/`, `05_BUSINESSES/`, `06_FRAMEWORKS/`, `07_DECISIONS/` | Claude (content) + OpenCode (structure) | Phases 2–4 | Each rollup file cites every thought/entity it aggregates; no rollup introduces a claim that doesn't already exist as a thought. |
| 6. Conflict Detection | `12_CONFLICTS/` | Audit Bot (primary), Hermes/Claude (contributing) | All prior phases | Every direct contradiction between two D0/D1 objects is logged; nothing with an open, unresolved conflict is promoted to `10_CANONICAL_KNOWLEDGE/`. |
| 7. Canonicalization | `10_CANONICAL_KNOWLEDGE/`, `11_ARCHIVED_SUPERSEDED/` | Claude + OpenCode | Phases 2–6 | Every canonical entry meets Evidence Class rule 4 (§6); every superseded concept is moved (not deleted) to `11_ARCHIVED_SUPERSEDED/` with `supersedes`/`superseded_by` intact. |
| 8. Master Plan | `08_MASTER_PLAN/` | OpenCode (structure) + Claude (content) | `10_CANONICAL_KNOWLEDGE/` | Built **last**, only from already-canonicalized objects — never directly from raw thoughts. |
| Continuous | `13_SOURCE_INDEX/` | OpenCode (tooling) | All phases | Reverse index kept in sync after every phase — for any `conversation_id`/`message_id`, must be able to list every derived object across all layers that cites it. |
| Continuous | `14_TESTS_AUDITS/` | Audit Bot | All phases | See §8. |

No phase's output may be treated as trustworthy input to the next phase until Audit Bot has run at least one spot-check pass against it (see §8) and logged the result.

---

## 8. Testing & Audits (`14_TESTS_AUDITS/`)

Audit Bot's required checks, minimum bar before any phase is considered "done":

1. **Provenance integrity** — for every object in every layer, the cited `conversation_id`/`message_id`/`source_file` combination must actually exist in `01_INGEST/` and, transitively, in `00_RAW_ARCHIVE/`. Any object citing a nonexistent message is an automatic REAL_GAP finding.
2. **Evidence-class spot-check** — random sample (minimum 5% of objects per phase, or 30 objects, whichever is larger) re-read directly against `00_RAW_ARCHIVE/`. Report format matches the example already given: *"That claim is attributed to Derek, but the source shows the assistant proposed it and Derek never approved it."*
3. **Originator misattribution scan** — specifically hunt for D0/D1 claims whose `original_text` reads like assistant phrasing (formal, expansive, "Here's how we could...") rather than Derek's own voice — this is the single most important audit given the Business Character Method precedent already known to exist in the corpus.
4. **No fabricated relationships** — every `inferred` edge in `09_RELATIONSHIP_GRAPH/` must have a `note` that a human could verify makes sense from the supporting thoughts; edges without one are a finding.
5. **No silent drops** — total message count reconstructable from `13_SOURCE_INDEX/` must reconcile against the raw archive's actual message count (computed once, directly from `00_RAW_ARCHIVE/`, as the ground truth to check every later stage against).

Classification vocabulary for every audit finding (matches the existing vox_v4 sprint's Audit Bot convention, reused deliberately for consistency):
`ALREADY_SOLVED | PARTIAL | REAL_GAP | STALE_BRANCH_FINDING | TEST_DEFECT | INFRASTRUCTURE_BLOCKED`
(Here, "STALE_BRANCH_FINDING" reads as "finding based on a since-superseded extraction pass — re-run against current output before trusting it.")

---

## 9. Definition of Done

**Per-phase DoD:** the exit criteria in the §7 table, plus a passing Audit Bot report in `14_TESTS_AUDITS/` for that phase with zero open REAL_GAP findings (PARTIAL/TEST_DEFECT findings may be carried forward with an explicit owner and are not blocking by themselves).

**Overall DoD for this build:**
- All 35 conversation files fully ingested (Phase 1 exit criteria met for every file, not a sample).
- Every atomic thought has a correct, audited evidence class.
- The relationship graph connects the domains Derek named as examples (Cold Core → Portal Farms, DerekOS → VOX → Mega Agent) *if and only if the corpus actually supports those specific edges* — do not force these example edges to exist if the evidence isn't there; report honestly if it isn't.
- `08_MASTER_PLAN/` exists, is built only from canonicalized (not raw) objects, and every entry in it traces to at least one D0/D1 source.
- The following example queries (from the Board directive) are answerable, with original evidence attached, using only the layered output — not by falling back to grepping raw JSON:
  - "Show me every idea I've ever had involving Africa."
  - "When did the concept that eventually became DerekOS first appear?"
  - "Find old inventions I abandoned that now connect to Portal Farms."
  - "What ideas did I have between 2024–2026 that I never followed through on but now fit the master plan?"
- Audit Bot's final report shows zero open REAL_GAP findings across all phases.

---

## 10. Guardrails (non-negotiable, mirrors the vox_v4 sprint's own governance)

- **No agent creates a competing pipeline, schema, or storage layer for a stage another agent owns.** If Hermes thinks Claude's thought extraction missed something, Hermes flags it — Hermes does not re-extract thoughts with its own logic.
- **No fabricated success.** A phase is not "done" because an agent says so; it's done when Audit Bot's independent check passes. This mirrors the exact discipline already proven out in the vox_v4 DerekOS Hardening sprint (Executive Ledger's `has_evidence`/honest-`None` pattern, never a fabricated 0% or a claimed delta without evidence).
- **Kilo implements, it does not redesign.** Once OpenCode/the Board lock a schema or architecture decision, Kilo builds exactly that. Ambiguity is a question upward, not a unilateral call.
- **Every AI-generated architecture in the corpus is preserved, not laundered into a Derek-originated fact.** The known example: an assistant once proposed an MCP-centered "Universal AI Operating System." That proposal stays in the corpus and is extractable (as A0, or D1 if Derek explicitly adopted it) — DerekOS must never later treat every sentence of that response as one of Derek's own original decisions.
- **`00_RAW_ARCHIVE/` is immutable.** Restated because it is the single most important rule in this document.
- **Absence-of-evidence rule:** No matching evidence found in the searched corpus does not establish that a concept does not exist. The reconstruction pipeline must always check whether corpus coverage was complete through the relevant period and sources before making any absence claim. If coverage is known to be incomplete, the only valid epistemic statuses are `NOT ESTABLISHED IN SEARCHED CORPUS` and `OUT_OF_CORPUS_EVIDENCE PENDING`. Stronger absence claims are reserved for cases where coverage is independently verified as sufficiently complete. This applies to all reconstruction output, not just provenance classification.

---

## 11. Open Questions for the Board (not yet decided — do not guess)

- Should `04_PROJECTS/05_BUSINESSES/06_FRAMEWORKS/07_DECISIONS` rollups be per-entity files (one JSON per project) or per-domain JSONL collections? (Recommendation: per-entity files — easier provenance tracing, easier for Audit Bot to spot-check one file at a time. Not yet Board-approved.)
- Should attachments referenced by `conversation_asset_file_names.json` be extracted at all for this build, or deferred entirely until a specific query needs one? (Currently deferred per §2.)
- Retrieval/query interface for DerekOS to actually consume `08_MASTER_PLAN/`/`10_CANONICAL_KNOWLEDGE/` is explicitly out of scope for this spec — OpenCode should raise it as a separate spec once the knowledge layers exist.

---

## 12. Forward-Looking Design: Constitutional Core & Domain Architecture

**Status: design only. Nothing in this section has been executed. No K5/K4 records, no principles, no clusters exist yet as of this revision.** This section exists so that when Phase 2 (§7) has actually produced real, audited `D0`+`K5`/`K4` records at scale, the next phases have an agreed design to build against rather than improvising — the same reason the rest of this spec exists.

### 12.1 Constitutional Core v0.1 — sequencing

Once real `D0`+`K5` records exist (expected to be a small set — see §6.1, K5 should be rare):

1. Claude generates **candidate** interpretations only (§6.2) — principle, vision, goal, constraint, architecture decision, operating rule, master-plan component, identity/philosophy, or whatever categories the evidence actually supports. **Categories are derived from evidence, not pre-imposed** — a fixed list like "01 Ultimate Vision, 02 Human Mission, ..." is an illustration of the kind of structure that might emerge, not a template to fill in.
2. Claude does **not** write `canonical_meaning` at this stage — that field stays `null` until Claude and Hermes agree and Audit Bot verifies (mirrors evidence-class rule 4).
3. Audit Bot source-verifies every candidate against `00_RAW_ARCHIVE/` directly — at K5 scale this should mean all of them, not a sample.
4. Only records that reach `established` or `canonical` maturity (§6.2) are eligible for the "Constitutional Core" deliverable name. A single unreinforced `candidate` principle is reported as exactly that, not smuggled in as core doctrine.

### 12.2 K4 / Domain Architecture — sequencing

Real K4 records must pass the structural-significance bar in §6.1 before this phase starts, and a stratified sample must be Audit Bot-verified first (recommended: 100 records, mixed random + stratified by source conversation era) with a reported precision number — if precision is low, the scorer is fixed and rerun before Claude sees the output, not after.

Once K4 output is trusted:
```
K4 records (post-audit)
  → semantic clustering by domain (DerekOS, VOX, Mega Agent, and whatever
    else the evidence reveals — not a preselected list)
  → chronological ordering within each cluster
  → Claude interpretation (sees evolution of an idea across time, not
    isolated fragments)
```
Per-domain output shape: `origin`, `major_evolutions`, `current_candidate_state`, `superseded_states`, `unresolved_conflicts`, `supporting_sources`, `related_domains`.

### 12.3 Contradiction Mapping

Before anything is promoted to canonical (§6, rule 4; §6.2), Audit Bot searches for: same concept + different dates + different requirements + corrections + reversals + abandoned versions. Output classification per concept: `CURRENT | SUPERSEDED | REJECTED | UNRESOLVED_CONFLICT`. Particularly relevant for DerekOS/VOX/Mega Agent, which are already known (from this build's own working history in `vox_v4`) to have gone through multiple generations of role/boundary definitions — the archive likely contains earlier drafts of boundaries that later commits superseded.

### 12.4 Hermes candidate relationship edges (revises §7 phase 4 exit criteria)

Hermes never writes directly to a "final" graph. Every edge Hermes produces is a **candidate**, explicitly pending audit:

```json
{
  "from": "Cold Core",
  "relationship": "supports",
  "to": "Portal Farms",
  "evidence": ["thought_...", "thought_..."],
  "relationship_origin": "explicit | inferred",
  "agent": "hermes",
  "confidence": 0.91,
  "audit_status": "pending"
}
```
`relationship_origin` is not optional decoration — it's the difference between "Derek directly said Cold Core powers Portal Farms" and "Hermes noticed both involve energy/water and connected them." Both are valuable; DerekOS must always be able to tell which one it's looking at. `09_RELATIONSHIP_GRAPH/` holds these candidate edges; nothing is treated as an established relationship until Audit Bot flips `audit_status` away from `pending`.

### 12.5 Target milestone naming (once real)

`DEREKOS_CONSTITUTIONAL_CORE_V0.1` and `DEREKOS_DOMAIN_ARCHITECTURE_V0.1` are the intended names for these two deliverables once they contain real, audited content. Neither name should be used for a document, directory, or status report before that's true — including in progress updates.

### 12.6 `proposition_origin` vs `submitted_by` vs `evidence_class` vs `adoption_status`

Verified real case (`provenance_gold_set_v1.jsonl` `gold_022`, "So my vision is now the trillion dollar ecosystem"): the assistant introduced "trillion-dollar ecosystem" framing one turn before Derek's message. Derek's sentence is still his own words, declaring it as his vision — that's `evidence_class: D0`. But the *idea itself* (the specific framing) originated with the assistant one turn earlier, and Derek's act of saying this sentence *is* an adoption event (`adoption_status: AD3`), not context-free origination. One record legitimately encodes both:
```json
{
  "evidence_class": "D0",
  "submitted_by": "derek",
  "proposition_origin": "assistant",
  "adoption_status": "AD3",
  "origin_reference": "previous_assistant_message"
}
```
`proposition_origin` (new field, distinct from `original_author` in the `P0` origin schema of §6.0a) answers "whose idea was this, tracing back through the conversation" even when `evidence_class` is `D0` because the *words in this specific message* are unambiguously Derek's own. This is not a contradiction — the words originated with Derek; the underlying proposition may have originated with someone else one or more turns earlier. Without this distinction, a resolver has to choose between misrepresenting Derek's adoption as origination (wrong) or misrepresenting his own words as not-`D0` (also wrong). Both `original_author` (§6.0a, for `P0` records where the message *is* someone else's words) and `proposition_origin` (this field, for `D0` records that adopt a prior proposition) are needed — they answer different questions and apply to different evidence classes.

### 12.7 PROVENANCE_RESOLVER_V0.1 — hybrid architecture (design; build tracked separately)

Not an LLM-classifies-everything pipeline. Four stages, each consuming only the previous stage's output — a classifier never "blindly reads a message and guesses":

1. **Deterministic evidence** (mechanical, cheap, provably correct or provably absent — no semantic judgment): exact/near-duplicate cross-corpus matches, earlier-message vs. later-message ordering, assistant-authored-then-reused-by-user detection (the shingle-index method proven out in `14_TESTS_AUDITS/find_reused_passages.py`), conversation topology (parent/child, `current_node` path membership), timestamps, known paste markers (forwarded-email footers, unsubscribe links, physical addresses, URLs, third-party signatures). Output: an **evidence package** per message — facts, not conclusions.
2. **Candidate segmentation**: given the evidence package, split a message into candidate spans (pasted-assistant-material / pasted-external-material / Derek-commentary / Derek-modification) at the boundaries the stage-1 evidence actually supports — real verified example needing this: `gold_030` (DAC Offer Strategy), which segments into a one-sentence `D0` question plus a full forwarded `P0` email.
3. **Semantic classification**: only for what stages 1–2 cannot resolve deterministically. Receives the evidence package and candidate segments as input — never the raw message in isolation. Outputs `evidence_class` (including `UNRESOLVED`, §6.0f), `submitted_by`, `originator`/`proposition_origin`, `origin_message_id`/`reuse_message_id` where known, `adoption_status` (`AD0`–`AD4`), `provenance_certainty` (`PC0`–`PC4`), `requires_review`, and the evidence actually used to reach the classification (traceable, not asserted).
4. **Benchmark**: run against the frozen `provenance_gold_set_v1` (§14) before any corpus-scale use. Report a full confusion matrix plus the four safety metrics (§6.0g). Do not tune the benchmark or edit frozen labels after seeing results (§14's freeze rule) — if the resolver performs badly, fix the resolver, not the answer key.

**Precision bar**: `D0` precision >= 98% before the resolver is trusted for any automatic Derek-origin attribution at scale, per the "False Derek Attribution Rate is the most dangerous error" principle (§6.0g). Recall is allowed to be low initially — under-attributing is a smaller harm than over-attributing, and coverage can improve in later versions without touching this precision bar.

**Independence requirement for a valid benchmark run**: a classifier (stage 3) must not have access to `provenance_gold_set_v1.jsonl`'s labels while classifying — scoring a classifier against a gold set it (or the same reasoning process that produced it) already memorized the answers to is not a valid measurement. If Claude is acting as stage 3, the classification pass must run in a context that cannot see the frozen labels.

### 12.8 `integration_strength` (`IS0`–`IS5`) — future concept, design only, do not implement yet

Message-level `adoption_status` (§6.0d) answers "did Derek adopt this specific proposition." It doesn't capture the pattern already visible in this corpus: an idea can evolve across many messages, with no single "I approve this" moment, and still clearly become part of the larger system (Derek Seed -> AI Expansion -> Derek Extension -> AI Architecture -> Derek Correction -> AI Revision -> Derek Integration). A future **concept-level** metric, distinct from any single message's `adoption_status`:

| Code | Meaning |
|---|---|
| **IS0** | Mentioned once, never returned to. |
| **IS1** | Explored — discussed across a couple of messages, then dropped. |
| **IS2** | Revisited — reappears in a later, separate conversation. |
| **IS3** | Incorporated into another concept — becomes a component of something larger. |
| **IS4** | Repeatedly developed — recurs and gets refined across multiple sessions/conversations. |
| **IS5** | Operationalized/built — the concept demonstrably became part of a real system (e.g. DerekOS, VOX, a named business). |

**Explicitly deferred.** Provenance (`evidence_class`/`adoption_status`/`provenance_certainty`) has to work correctly first — `integration_strength` is a concept-graph-level rollup that depends on relationships (§12.4) and canonicalization (§12.1–12.2) already being trustworthy. Recorded here so the design isn't lost, not because it's next.

### 12.9 Knowledge Status — a derived, object-level status (not a new per-message field)

**Verified, not hypothetical**: built while tracing the Copilot CSV import's "Legacy Forge Shared Business Context" — see `14_TESTS_AUDITS/COPILOT_INCREMENTAL_CORPUS_IMPORT_REPORT.md`. That document read as authoritative business documentation. Traced fully, its lineage is: no verified Derek business facts found anywhere in the source conversation → a ChatGPT assistant turn generated a "fully filled" version from a bare template request (confirmed by checking sibling/regenerated branches at that exact point: the other two attempts produced only *empty* templates, meaning nothing about the specific content came from Derek) → that content was pasted into Copilot minutes later → Copilot polished it further into "publication-ready" formatting. Each step made it look more authoritative without adding a single verified fact. This is **provenance laundering**: repeated reformatting and cross-platform reuse can make an unverified AI proposal look like established founder knowledge, purely through presentation, with nothing underneath it.

This is why composite knowledge objects (an SOP, a canonical concept, eventually anything in `10_CANONICAL_KNOWLEDGE/`) need a status **derived from their full traced lineage**, not asserted from how polished or recent their surface form is:

| Status | Meaning |
|---|---|
| **VERIFIED_DEREK** | Traced lineage shows genuine `D0` origin and/or explicit `D1`/`AD3`+ adoption — Derek's own facts or explicit decisions, confirmed. |
| **ADOPTED_AI** | Originated `A0`/`P0`, but Derek explicitly adopted and materially worked with it (`AD3`/`AD4`) — legitimate knowledge, honestly labeled by origin. |
| **AI_PROPOSED** | Originated `A0`/`P0`, no confirmed Derek adoption beyond engagement (`AD0`–`AD2`) — the Legacy Forge document's correct status. Still visible and traceable, never promoted to canonical, never phrased as "Derek's SOP says..." |
| **EXTERNAL_SOURCE** | Traced to a genuinely external, non-assistant origin (an article, another person's content) that Derek supplied but didn't author. |
| **UNVERIFIED** | Lineage incomplete or not yet traced — the honest default before analysis, not a permanent label to rest on. |
| **DISPUTED** | Conflicting evidence about origin/adoption exists and hasn't been resolved (relates to `12.3` Contradiction Mapping). |

**This status is computed from the underlying atomic thoughts' `evidence_class`/`adoption_status`/`provenance_certainty` (§6.0a–§6.0e) — it is never inferred directly from a source field like `Author` or `role`.** A `role: user` / `Author: Human` message is not evidence of `VERIFIED_DEREK` by itself, exactly per §6.0a's core rule, now applied at the composite-object level too. Not yet implemented as a computation — recorded here as the target shape once enough atomic-thought-level provenance exists to roll up from.

### 12.10 Operational Evidence (`OE0`–`OE5`) — future concept, design only, do not implement yet

A fourth question, distinct from the three already tracked (`evidence_class` = whose words; `adoption_status` = did Derek accept it; `knowledge_value` = how significant): **for something SOP-shaped, was it actually used?** An idea can be `A0` + `AD4` (assistant proposed it, Derek adopted and transformed it) and that is legitimate, valuable knowledge regardless of who originated it — but DerekOS still needs to know whether it ever became a real operating procedure or stayed a plan.

| Code | Meaning |
|---|---|
| **OE0** | Proposed only — exists as an idea/document, nothing more. |
| **OE1** | Discussed/planned — talked through, not yet prepared for use. |
| **OE2** | Prepared for implementation — a real plan/document/checklist exists, not yet used. |
| **OE3** | Used at least once — genuine operational evidence of a single use. |
| **OE4** | Repeated operational use — used more than once, becoming habitual. |
| **OE5** | Current standard operating procedure — the active, relied-upon process. |

Independent of `adoption_status` — `A0 + AD4 + OE5` ("AI proposed it, Derek adopted and transformed it, it became the real SOP") is a fully legitimate, common, and valuable combination; the point of this axis is not to privilege Derek-originated ideas over good AI ones, but to keep DerekOS honest about *what's actually true* versus *what was proposed and never used*. **Explicitly deferred — design only.** Does not block Copilot ingestion or any current work; recorded here so the eventual SOP schema (§12.11) has a place to put it once provenance-resolution work reaches that stage.

### 12.11 SOP schema sketch (future — illustrates how 12.9/12.10 compose, not yet built)

```yaml
sop_id: SOP-001
business: Legacy Forge
status: AI_PROPOSED   # per S12.9 - computed, not asserted
origin:
  platform: chatgpt
  originator: assistant
  evidence: ["af0c65b4-e6c2-4830-8318-c8db58c9469f"]
adoption:
  derek_explicitly_approved: false
later_reuse:
  - platform: copilot
    action: polished
operational_evidence: OE0   # proposed only - per S12.10
canonical_status: NOT_CANONICAL
```
Contrast with a real, trusted SOP's target shape: Derek supplies the operating rules (`D0`) → an assistant structures them (`A0`, linked) → Derek corrects/modifies them (`D0`/`AD4`) → genuinely used operationally (`OE3`+) → reaffirmed over time (`OE4`/`OE5`) → only then eligible for `VERIFIED_DEREK`/`CURRENT`. This is the shape `MASTER BRAIN/OPERATING SYSTEM/` (§13, target directory structure) will eventually hold — not built yet.

### 12.12 Three questions that must never collapse into one: `SIMILARITY_EDGE` / `DERIVATION_EDGE` / `INTELLECTUAL_ORIGIN`

Formalized after `03_PROVENANCE_INDEX_V0.2`'s redesign (built specifically because v0.1 conflated these). Three genuinely different questions, each answered by a different layer of the system, and none of them substitutes for another:

| Question | Answered by | Answer shape |
|---|---|---|
| **`SIMILARITY_EDGE`** — "We found related language." | `03_PROVENANCE_INDEX` mechanically | A text-overlap fact: these two passages share significant content, measured (coverage, contiguous span, dispersion). Says nothing about direction or causation. |
| **`DERIVATION_EDGE`** — "This passage was probably derived from that passage." | `03_PROVENANCE_INDEX`, promoted from a `SIMILARITY_EDGE` only when chronology is valid (candidate precedes reuse) and the contiguous span is substantial — never from similarity alone (§12.7's core fix). Still mechanical, still not an authorship claim. | A directional, chronology-gated claim about which text came from which. |
| **`INTELLECTUAL_ORIGIN`** — "Where did the underlying idea actually originate." | Semantic review only (Stage 3 / `PROVENANCE_RESOLVER`, never the index itself). May legitimately resolve to `UNKNOWN_EXTERNAL` (§12.9) even when a `DERIVATION_EDGE` exists — the earliest text-match in this corpus is not necessarily where the idea itself began. | `derek` / `assistant` / `external` / `unknown` / `UNKNOWN_EXTERNAL`. |

**Worked example, the general case (not yet real data — illustrates why all three layers matter together):**
```
AI writes framework           (SIMILARITY_EDGE candidate: none yet, this is A0's origin)
      ↓
Derek pastes framework        (DERIVATION_EDGE: text derives from the AI's message - mechanical, provable)
      ↓
Derek changes 40%             (a new D0/AD4 thought, linked to the DERIVATION_EDGE, not replacing it)
      ↓
Derek approves modified version   (adoption_status: AD3/AD4 - Codex's resolver layer, not this index)
      ↓
DerekOS implements it          (operational_evidence: OE3+ per S12.10 - a still-later, separate layer)
```
The *text's* derivation traces cleanly to the AI (`DERIVATION_EDGE`, high confidence, mechanical). The *intellectual proposition*, once Derek changes 40% of it, may be legitimately joint (`INTELLECTUAL_ORIGIN` could reasonably be recorded as `derek+assistant`, not forced to pick one). The *operational doctrine* (whether DerekOS actually runs on it) is a third, independent question again. Collapsing these into one field is exactly the provenance-laundering risk `12.9` documents — three honest, separately-evidenced answers are more valuable than one confident, wrong one.

**Division of labor this implies** (matches the current multi-agent split in practice, not just in theory): `03_PROVENANCE_INDEX` answers *where did this material come from* (derivation). The provenance resolver answers *who actually authored/submitted/adopted it* (attribution + adoption). Semantic extraction, once it exists, answers *what idea does it represent*. Canonicalization answers *what does Derek currently believe or want DerekOS to operate from*. These four layers must stay separate — a downstream layer may reference an upstream layer's output as evidence, but never silently inherit its confidence.
