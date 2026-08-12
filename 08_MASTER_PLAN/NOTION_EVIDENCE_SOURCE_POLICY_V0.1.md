# NOTION_EVIDENCE_SOURCE_POLICY_V0.1.md
# Created: 2026-08-12
# Governing rules: ABSENCE_OF_EVIDENCE_RULE_V0.1.md, MASTER_BRAIN_KNOWLEDGE_CONTRACT_V0.1.md
# Status: GOVERNANCE DECISION — source expansion approved; ingestion NOT yet approved

---

## 1. Decision

The Master Brain evidence layer expands from:

```
ChatGPT + other AI + Copilot  ->  Provenance Corpus
```

to:

```
ChatGPT + other AI + Copilot + Notion + Obsidian
    -> Evidence Layer
    -> Provenance Resolver
    -> Candidate Knowledge
    -> Human Review
    -> Canonical Master Brain
```

Notion becomes an independently versioned evidence source with its own
source identity: `notion-workspace`.

## 2. Separation from CORPUS_RELEASE_002 (founder directive)

- CORPUS_RELEASE_002 remains the clean ChatGPT-only delta of
  CORPUS_RELEASE_001 (parent=CORPUS_RELEASE_001). Notion material must
  NOT be mixed into it.
- Notion enters as a separate evidence source with its own release
  lineage (e.g. NOTION_EVIDENCE_RELEASE_001), versioned and hashed
  independently.
- Cross-source provenance indexing then connects Notion records to
  ChatGPT/other-AI/Copilot records; authorship and adoption are resolved
  by the provenance resolver, never assumed.

## 3. Notion record identity

Every Notion record entering the evidence layer must preserve:

```
page_id
page_title
created/edited timestamp
block/section
raw text
source hash
extraction timestamp
```

## 4. Epistemic rules (same as all other sources)

1. Notion presence proves that an idea existed in Derek's working
   environment. It does NOT prove founder authorship.
2. A Notion page written or drafted by AI is NOT automatically
   Derek-authored. Authorship classification (D0/A0/P0/MIXED/UNRESOLVED)
   and adoption strength (AD0-AD4) must be provenance-resolved.
3. Notion material is evidence, not canonical knowledge. Nothing reaches
   canonical_records.jsonl without founder review.
4. Template-like material (e.g. pre-filled "Company in-a-Box" structures)
   must not be treated as a founder decision just because it lives in the
   workspace. Templates carry maturity state CANDIDATE or UNRESOLVED, and
   authorship UNRESOLVED unless proven otherwise.
5. Corpus Coverage Headers that cite Notion must state the extraction
   timestamp, pages scanned, and known-unscanned areas.

## 5. Pre-import audit (REQUIRED before any Notion ingestion)

A reconnaissance pass (2026-08-12) surfaced these candidate areas:

| Area | Notes |
|---|---|
| DerekOS Master Dashboard | Explicit loop `THINK -> TEST -> DISTILL -> STORY -> TEACH -> ACT -> MEASURE`; RPM/7D cycle |
| DerekOS Rules & Principles | Potential founder-created principles/decisions absent from ChatGPT exports |
| Daily 7D Logs | Operating logs |
| Dragons & Obstacles | Friction/blocker tracking |
| Friction-Free Stories | Narrative/SOP material |
| VOX Command Center | Identifies Obsidian vault as local SSOT, Notion as cloud mirror; documents canonical local files, agent routing, operating rules, division of truth |
| Company in-a-Box | Projects, meetings, docs, team/org-chart, operating goals; PARTIALLY TEMPLATE-LIKE — handle per rule 4 |
| Ghost Protocol Ops | Not yet inspected |
| CRM | Not yet inspected |
| VOX AI Engine material | Not yet inspected |

Audit steps before ingestion:

1. Inventory all pages/databases in scope (page_id, title, timestamps,
   last editor where available).
2. Classify each area: founder-authored vs AI-drafted vs template vs
   UNRESOLVED (preliminary; final classification happens post-ingest in
   the provenance resolver).
3. Flag relevance to open reconstruction pilots (conglomerate V0.2,
   DerekOS/VOX evolution).
4. Produce NOTION_AUDIT_REPORT_V0.1.md.
5. Founder reviews audit. Only then: extraction, hashing, frozen
   NOTION_EVIDENCE_RELEASE_001.

## 6. Reconnaissance finding on the conglomerate pilot

The reconnaissance search of Notion (holding company, capital allocation,
Africa, acquisitions, conglomerate, corporate takeover) did NOT uncover a
clear Notion page containing the newer acquisition/conglomerate plan;
results were unrelated acquisition/marketing pages and older business
material. Notion therefore does NOT replace the missing August 10-12
ChatGPT evidence. The conglomerate V0.2 gate remains BLOCKED on the
fresh ChatGPT export (see CONGLOMERATE_PILOT_STATUS_V0.2.md).

## 7. What stays unchanged

- CORPUS_RELEASE_001: FROZEN, immutable.
- The locked 10-step conglomerate resume pipeline.
- FD-001/002/003: OPEN.
- No canonical writes without founder review.

## 8. Authorship vs adoption separation (founder directive, 2026-08-12)

> **Authorship and business adoption are different facts.**

A record may legitimately carry:

```
authored_by:      assistant
submitted_by:     Derek
adopted_by:       Derek
adoption_level:   AD2 / AD3 / AD4
operational_status: USED
```

and still be important Master Brain knowledge. AI-originated ideas that
Derek adopted and built into the business must NOT be discarded merely
because they are not D0. The Master Brain answers two separate questions:

1. "Did Derek originate this?" (authorship: D0/A0/P0/MIXED/UNRESOLVED)
2. "Did this become part of Derek's business system?" (adoption: AD0-AD4)

These must never be collapsed.

### Founder disposition of the five provenance candidates (2026-08-12)

| Record | Disposition |
|---|---|
| DAC Marketing Meeting Agenda | Accepted as A0 / adoption evidence; AD2 candidate |
| DAC Performance Dashboard | Accepted as A0 / adoption evidence; AD2 candidate |
| THE ULTIMATE PROMPT STACK FOR YOUR DAC EMPIRE | Accepted as strongest A0 candidate; AD2 candidate |
| DAC 30-Day Content Plan | Accepted as A0 / adoption evidence; AD2 candidate |
| Zo AI Business OS | Kept as REUSE_FOUNDER_MATERIAL_CANDIDATE; deeper chain trace required |

Approved for continued provenance/adoption review, NOT canonicalization.
No D0 status changes. AD2 stands only until stronger evidence shows
implementation, modification, repeated use, or explicit approval.

## 9. MULTI_AGENT_RELAY_CHAIN pattern (formalized 2026-08-12)

Provenance pattern (evidence topology), NOT an authorship class:
AI/agent artifact -> founder control/adoption act -> another AI/agent ->
refinement -> founder integration act -> operating system. Axes stay
separate (authorship / submission / adoption / integration / relay
actors). Full spec: 08_MASTER_PLAN/MULTI_AGENT_RELAY_CHAIN_PATTERN_V0.1.md.
Status: PATTERN_CANDIDATE pending broader-corpus testing.

---
# END OF POLICY
