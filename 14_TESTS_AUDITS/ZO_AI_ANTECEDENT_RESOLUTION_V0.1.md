# ZO_AI_ANTECEDENT_RESOLUTION_V0.1.md
# Created: 2026-08-12
# Status: CANDIDATE EVIDENCE — founder review required; nothing canonical
# Target: the 2025-07-15 user-role antecedent of the Zo AI Business OS chain
#         (message bbb21af4-fd69-461f-9fff-12ec6ab8da00, conversation
#         "Custom AI Closer Bot", conversations-012.json)
# Evidence basis: CORPUS_RELEASE_001 (FROZEN) full scan; raw event data in
#         14_TESTS_AUDITS/notion_audit/ZO_AI_ANTECEDENT_RESOLUTION_V0.1.json

---

## Corpus coverage note

Searched corpus: CORPUS_RELEASE_001 (72,241 messages; latest timestamp
2026-08-09T22:57Z). Known gaps relevant here: the export drops some
messages inside "Custom AI Closer Bot" (sequence indices 4-8, 10, 12,
16-17 are absent), and other AI platforms plus non-exported sources are
outside the snapshot. Claims below are scoped to the searched corpus.

## Findings

### 1. The target message is a pasted artifact, not founder prose

The 6,481-character message is titled "DerekOS-Horsemen v1 – Full Private
Repo (plug-and-play, no fluff)" and consists of a complete code
deliverable: repo layout, FastAPI backend, multi-model router, frontend
notes. This matches the assistant-deliverable style seen throughout the
same conversation (emoji-titled blocks, "drop-in / locked and loaded"
framing), and it is immediately followed by an assistant acknowledgement
(2025-07-15T06:45:31Z): "DerekOS-Horsemen v1 is now fully structured
inside your private repo."

The genuine founder instructions around it are short and distinct in
voice, e.g. seq 11 (06:35:54Z): "I want to add the 6 horseman chatgpt,
Gemini, Claude, Kimi, and copilot and Grok."

Classification of the message itself: **USER_ROLE_PASTED_ARTIFACT**. It
cannot serve as D0 evidence for anything. User-role labeling in the export
does not establish founder authorship — exactly the failure mode the
provenance rules were built to catch.

### 2. No prior source for the pasted block is established in the corpus

44 earlier corpus messages match the target at >= 3 shingles, but every
shared shingle inspected is generic boilerplate: React/Tailwind fragments
("grid grid cols 1 md grid cols 2") and API endpoint strings. No earlier
message carries the substance of the DerekOS-Horsemen repo block.

The most likely producer — an assistant message around sequence 12 — is
one of the messages the export dropped. Therefore:

- Source of the pasted block: **NOT ESTABLISHED IN SEARCHED CORPUS**,
  with OUT_OF_CORPUS_EVIDENCE_PENDING (assistant origin is stylistically
  consistent but unproven; the paste could also come from another AI
  session not in the export).

### 3. Its link to the Zo AI Business OS page is boilerplate, not lineage

The target shares exactly 4 shingles with the Zo AI page, all variants of
the Anthropic API call pattern ("post https api anthropic com v1 messages
headers x"). This is shared code boilerplate. The chain report's earliest
occurrence for Zo AI (2025-07-15, x4) is therefore **downgraded**: it does
not establish substantive antecedence for the page. The Zo AI chain's
earliest-occurrence anchor must be re-evaluated against the first
substantive (non-boilerplate) match; that re-anchoring is left UNRESOLVED
pending founder direction.

### 4. Consequence for H1 vs H2

The July 15 antecedent provides no support for either lineage hypothesis:

- H1 (Derek original concept -> AI expansion -> Notion -> reuse): the
  antecedent is not demonstrably Derek-originated.
- H2 (AI proposal -> Derek saves/uses -> Notion): the pasted block's
  producer is not established in the searched corpus.

**H1 vs H2 remains OPEN.** The substantive Zo AI overlaps are the later,
post-creation ones (Growth Hacker Brief, user-role, x1566 on 2026-07-01;
Market Intent Prediction Stack, user-role x807 plus assistant cluster on
2026-07-02), and those user-role messages must themselves be checked for
the same pasted-artifact pattern before any authorship inference.

## Disposition

- Authorship: no D0 assigned anywhere in this resolution.
- Adoption: unchanged; Zo AI Business OS remains
  REUSE_FOUNDER_MATERIAL_CANDIDATE per founder disposition.
- Nothing canonicalized. Conglomerate V0.2 gate unchanged.

---
# END OF ANTECEDENT RESOLUTION
