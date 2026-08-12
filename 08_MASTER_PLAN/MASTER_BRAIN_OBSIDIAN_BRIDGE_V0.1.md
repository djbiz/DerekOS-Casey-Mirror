# Master Brain ↔ Obsidian Bridge v0.1

**Status:** Architecture proposal — no runtime implementation or migration authorized  
**Date:** 2026-08-12  
**Author:** Bob (DevOps Engineer) with Derek Jamieson

---

## Executive Summary

This document proposes a **bidirectional but asymmetric** knowledge bridge between the DerekOS Master Brain (provenance/evidence authority) and the Obsidian vault (curated human-readable knowledge surface). The bridge enables VOX to retrieve canonical knowledge without duplicating the entire corpus, while preserving the existing VOX Brain architecture.

**Core principle:** One source of truth per knowledge type; multiple brains can read it.

---

## 1. Current State Audit

### 1.1 Obsidian Vault

- **Path:** `C:\Users\starw\OneDrive\VOX\VOX\VOX`
- **Size:** ~220 markdown files, ~352 total files
- **Structure:** 38 top-level directories (00 Inbox through Templates, plus AI/Business folders)
- **Frontmatter usage:** Sparse — only 19/220 files (8.6%) have YAML frontmatter
- **Write access:** Read-only from all systems (VOX Brain, knowledge_sync, shared/knowledge_sync)

### 1.2 VOX Brain Read Paths (Three Independent Implementations)

| Path | Mechanism | Vector Store | Vault Path | Collection |
|------|-----------|--------------|------------|------------|
| `vox_brain/obsidian_reader.py` + `retrieval.py` | BM25, in-process | None | `C:\Users\starw\OneDrive\VOX\VOX\VOX` | N/A |
| `knowledge_sync/` microservice | ChromaDB HTTP | OpenAI `text-embedding-3-small` | `/vault` (Docker mount) | `vox_brain` |
| `shared/knowledge_sync/` library | ChromaDB PersistentClient | Not specified | `~/VOX/VOX` | `vox_knowledge` |

**Critical issues:**
- Three different vault paths for the same conceptual vault
- Two separate ChromaDB instances with potentially different data
- No coordination between BM25 and vector search
- Duplicate indexing pipelines

### 1.3 DerekOS Master Brain

- **Path:** `D:\Projects\VOX\DerekOS_Master_Brain`
- **Status:** Phase 1 (ingest) complete, Phase 2 (atomic thoughts) piloted with 10 records
- **Content:** 35 ChatGPT conversation exports (3,476 conversations, 68,761 messages)
- **Provenance system:** 8+ evidence classes (D0, D1, A0, P0, I0, E0, B0, X0, UNRESOLVED) with 4 orthogonal axes (knowledge value K0-K5, adoption strength AD0-AD4, provenance certainty PC0-PC4)
- **Integration status:** Completely isolated from live systems — no runtime bridge exists

### 1.4 Knowledge Duplication

1. **Strategy YAML files** exist in 3 locations:
   - `vox_v4/vox_brain/strategies/` (16 files)
   - `vox_v4/knowledge/business_strategy/hormozi/` (2 files)
   - `vox_v4/knowledge/frameworks/` (6 files)

2. **Hormozi Playbooks** exist in 3 forms:
   - PDFs in `knowledge/strategy/`
   - Markdown in vault `Playbooks/`
   - YAML in `vox_brain/strategies/`

3. **ChromaDB collections** duplicated across microservice and library

---

## 2. Architecture Principles

### 2.1 Three Knowledge Temperatures

| Temperature | System | Content | Characteristics |
|-------------|--------|---------|-----------------|
| **Hot** | VOX | Live operational state: customers, workflows, tasks, campaigns, agents | Real-time, ephemeral, high-write |
| **Warm** | Obsidian | SOPs, strategies, business plans, playbooks, current architecture | Curated, human-readable, medium-write |
| **Cold/Deep** | Master Brain | Years of conversations, provenance, abandoned ideas, evolution, evidence, historical reasoning | Immutable evidence, append-only, no-write |

### 2.2 Ownership Model

| Knowledge Type | Source of Truth | Rationale |
|----------------|-----------------|-----------|
| **Canonical knowledge** (verified SOPs, decisions, strategies) | Master Brain | Provenance-tracked, evidence-backed, auditable |
| **Working knowledge** (curated playbooks, frameworks, SOPs) | Obsidian | Human-editable, readable, operational |
| **Operational state** (tasks, customers, campaigns) | VOX | Real-time, high-write, ephemeral |
| **Raw evidence** (conversations, messages) | Master Brain | Immutable, provenance-tracked, append-only |

### 2.3 Bidirectional but Asymmetric Flow

**Master Brain → Obsidian (Publish):**
- Master Brain can publish verified/canonical knowledge to Obsidian automatically
- Published notes include frontmatter linking back to Master Brain ID
- Obsidian notes are "managed projections" — human-readable views of canonical knowledge
- Humans can edit published notes, but edits create **candidates** that flow back to Master Brain for evaluation

**Obsidian → Master Brain (Candidate):**
- Obsidian changes do NOT directly overwrite canonical knowledge
- Instead, they create **knowledge candidates** that Master Brain evaluates
- Master Brain decides: NEW / UPDATE / CONFLICT / SUPERSEDES
- This prevents accidental canonicalization of rough brainstorm notes

**VOX reads from both:**
- VOX queries Master Brain for canonical knowledge (verified SOPs, decisions)
- VOX queries Obsidian for working knowledge (playbooks, frameworks)
- VOX maintains its own hot operational state

---

## 3. Bridge Architecture

### 3.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DEREKOS MASTER BRAIN                      │
│  (Provenance Authority / Cold Knowledge)                     │
│  - 68K+ messages with evidence classification                │
│  - Canonical knowledge records                               │
│  - Append-only provenance history                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ Publish (canonical → curated)
                 │ Candidates (curated → canonical evaluation)
                 │
        ┌────────▼────────┐
        │  BRIDGE SERVICE  │
        │  (New component) │
        └────────┬────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌───────────────┐  ┌─────────────────┐
│   OBSIDIAN    │  │      VOX        │
│ (Warm Knowledge)│  │ (Hot Knowledge) │
│ - Curated SOPs │  │ - Live state    │
│ - Playbooks    │  │ - Tasks         │
│ - Frameworks   │  │ - Customers     │
└───────────────┘  └─────────────────┘
```

### 3.2 Bridge Service

**Purpose:** Mediate knowledge flow between Master Brain and Obsidian, enforce ownership rules, manage candidates.

**Responsibilities:**
1. **Publisher:** Export canonical Master Brain knowledge to Obsidian as readable notes
2. **Candidate Intake:** Receive Obsidian changes, create candidate records in Master Brain
3. **Conflict Detection:** Identify when Obsidian edits conflict with canonical knowledge
4. **Sync State:** Track which Obsidian notes are managed projections vs. human-authored
5. **Query Router:** Direct VOX queries to the appropriate knowledge source

**Implementation:**
- FastAPI service (new container in docker-compose)
- PostgreSQL database for candidate tracking and sync state
- Read access to Master Brain JSON/JSONL files
- Read/write access to Obsidian vault (via OneDrive sync path)
- Exposes REST API for VOX and DerekOS to query

### 3.3 Knowledge Record Schema

**Master Brain Canonical Record:**
```json
{
  "id": "SOP-SALES-0042",
  "business": "Legacy Forge",
  "type": "SOP",
  "status": "CURRENT",
  "evidence": [
    {
      "message_id": "msg_abc123",
      "conversation_id": "conv_xyz789",
      "evidence_class": "D0",
      "timestamp": "2025-03-15T10:30:00Z",
      "original_text": "..."
    }
  ],
  "supersedes": "SOP-SALES-0017",
  "content": {
    "title": "Sales Process",
    "steps": [...],
    "notes": "..."
  },
  "provenance": {
    "knowledge_value": "K3",
    "adoption_strength": "AD3",
    "provenance_certainty": "PC4"
  },
  "created_at": "2026-08-12T00:00:00Z",
  "updated_at": "2026-08-12T00:00:00Z"
}
```

**Obsidian Note (Managed Projection):**
```markdown
---
master_brain_id: SOP-SALES-0042
status: current
source: DerekOS_Master_Brain
last_synced: 2026-08-12T00:00:00Z
managed: true
business: Legacy Forge
type: SOP
---

# Sales Process

## Steps
1. ...
2. ...

## Notes
...

---
*This note is a managed projection of canonical knowledge. Edits create candidates for evaluation.*
```

**Knowledge Candidate:**
```json
{
  "id": "CAND-2026-08-12-001",
  "source": "obsidian",
  "source_path": "Businesses/Legacy Forge/SOPs/Sales Process.md",
  "change_type": "UPDATE",
  "canonical_id": "SOP-SALES-0042",
  "diff": {
    "added": "...",
    "removed": "...",
    "modified": "..."
  },
  "status": "PENDING_EVALUATION",
  "evaluation": {
    "decision": null,
    "reason": null,
    "evaluated_at": null
  },
  "created_at": "2026-08-12T12:00:00Z"
}
```

### 3.4 Query API for VOX

**Endpoint:** `GET /api/v1/knowledge/query`

**Request:**
```json
{
  "query": "What is the current sales SOP for Legacy Forge?",
  "knowledge_type": "SOP",
  "business": "Legacy Forge",
  "depth": "canonical"
}
```

**Response:**
```json
{
  "answer": "The current sales SOP for Legacy Forge is...",
  "source": "master_brain",
  "canonical_id": "SOP-SALES-0042",
  "evidence": [
    {
      "message_id": "msg_abc123",
      "conversation_id": "conv_xyz789",
      "timestamp": "2025-03-15T10:30:00Z",
      "evidence_class": "D0"
    }
  ],
  "obsidian_note": "Businesses/Legacy Forge/SOPs/Sales Process.md",
  "confidence": 0.95
}
```

**Depth options:**
- `canonical` — Master Brain only (verified knowledge)
- `working` — Obsidian only (curated knowledge)
- `deep` — Master Brain with full provenance and lineage
- `auto` — Bridge decides based on query (default)

---

## 4. Migration Strategy

### 4.1 Phase 0: Consolidate VOX Brain Read Paths (Prerequisite)

**Goal:** Eliminate duplication and inconsistency in existing VOX Brain before adding Master Brain integration.

**Actions:**
1. **Standardize vault path:** Choose one canonical path (recommend `C:\Users\starw\OneDrive\VOX\VOX\VOX`)
2. **Deprecate duplicate ChromaDB:** Choose one ChromaDB instance (recommend `knowledge_sync/` microservice)
3. **Unify collection name:** Use `vox_knowledge` consistently
4. **Add frontmatter to existing notes:** Batch process to add minimal frontmatter (`type`, `owner`, `status`)
5. **Document read paths:** Create `VOX_BRAIN_ARCHITECTURE.md` explaining the unified path

**Deliverables:**
- Single `obsidian_reader.py` with standardized path
- Single ChromaDB instance
- Frontmatter on 100% of vault files (or explicit exception list)
- Architecture documentation

**Risk:** Low — internal refactoring, no external API changes

### 4.2 Phase 1: Bridge Service MVP (Read-Only)

**Goal:** Enable VOX to query Master Brain for canonical knowledge without modifying Obsidian.

**Actions:**
1. **Build Bridge Service:** FastAPI app with read access to Master Brain
2. **Implement Query API:** `/api/v1/knowledge/query` endpoint
3. **Add to docker-compose:** New `bridge` service container
4. **Update VOX routers:** `derekos_relay.py` queries Bridge for canonical knowledge
5. **Test with pilot data:** Use the 10-record atomic thoughts pilot

**Deliverables:**
- Bridge service running in Docker
- VOX can query Master Brain via Bridge
- Query API documented

**Risk:** Low — read-only, no Obsidian writes

### 4.3 Phase 2: Publisher (Master Brain → Obsidian)

**Goal:** Enable Master Brain to publish canonical knowledge to Obsidian as managed projections.

**Actions:**
1. **Implement Publisher:** Export canonical records to Obsidian markdown files
2. **Add frontmatter:** Include `master_brain_id`, `status`, `last_synced`, `managed: true`
3. **Track sync state:** PostgreSQL table mapping Master Brain IDs to Obsidian paths
4. **Handle conflicts:** Detect when managed notes are edited locally
5. **Pilot with SOPs:** Publish 5-10 verified SOPs to Obsidian

**Deliverables:**
- Publisher service
- Sync state tracking
- 5-10 managed Obsidian notes
- Conflict detection logic

**Risk:** Medium — writes to Obsidian, but only managed projections

### 4.4 Phase 3: Candidate Intake (Obsidian → Master Brain)

**Goal:** Enable Obsidian edits to create candidates in Master Brain for evaluation.

**Actions:**
1. **Implement file watcher:** Detect changes to managed Obsidian notes
2. **Create candidate records:** Store diffs in Bridge database
3. **Evaluation workflow:** DerekOS reviews candidates (NEW / UPDATE / CONFLICT / SUPERSEDES)
4. **Apply decisions:** Update Master Brain canonical records based on evaluation
5. **Pilot with manual evaluation:** Derek manually reviews candidates

**Deliverables:**
- File watcher for managed notes
- Candidate intake API
- Evaluation workflow
- Manual review process

**Risk:** Medium — creates candidates, but requires human evaluation

### 4.5 Phase 4: Full Integration

**Goal:** Complete bidirectional flow with automated evaluation.

**Actions:**
1. **Automate evaluation:** DerekOS uses provenance and evidence to auto-evaluate low-risk candidates
2. **Expand publisher:** Publish all canonical knowledge types (SOPs, decisions, frameworks, strategies)
3. **Expand intake:** Accept candidates from all Obsidian notes (not just managed)
4. **Add observability:** Metrics, logs, alerts for bridge health
5. **Document runbook:** Operational procedures for bridge service

**Deliverables:**
- Automated evaluation for low-risk candidates
- Full publisher coverage
- Observability stack
- Runbook

**Risk:** Higher — automated evaluation requires confidence thresholds and rollback

---

## 5. Obsidian Directory Structure (Target State)

After bridge implementation, Obsidian vault should organize knowledge as:

```
C:\Users\starw\OneDrive\VOX\VOX\VOX\
├── Businesses/
│   ├── Legacy Forge/
│   │   ├── SOPs/
│   │   │   └── Sales Process.md (managed: true, master_brain_id: SOP-SALES-0042)
│   │   ├── Decisions/
│   │   │   └── Pricing Strategy.md (managed: true, master_brain_id: DEC-OPS-0015)
│   │   └── Strategy/
│   │       └── Q3 2026 Goals.md (managed: false, human-authored)
│   └── ...
├── Frameworks/
│   ├── Hormozi/
│   │   └── Value Equation.md (managed: true, master_brain_id: FW-MKT-0003)
│   └── ...
├── SOPs/
│   ├── Global/
│   │   └── Customer Onboarding.md (managed: true, master_brain_id: SOP-GLOBAL-0001)
│   └── ...
└── ...
```

**Key:** `managed: true` indicates the note is a projection of Master Brain canonical knowledge. `managed: false` indicates human-authored or candidate knowledge.

---

## 6. Rollback Plan

### 6.1 Phase 0 Rollback
- Revert code changes via git
- No data migration occurred, so no data rollback needed

### 6.2 Phase 1 Rollback
- Stop Bridge service container
- Revert VOX router changes
- No Obsidian writes occurred, so no data rollback needed

### 6.3 Phase 2 Rollback
- Stop Publisher
- Delete managed Obsidian notes (they have `managed: true` frontmatter, so easy to identify)
- Revert sync state database
- Obsidian returns to pre-Phase 2 state

### 6.4 Phase 3 Rollback
- Stop file watcher
- Delete candidate records from Bridge database
- No Master Brain canonical records were modified (candidates are separate), so no data rollback needed

### 6.5 Phase 4 Rollback
- Disable automated evaluation
- Revert to Phase 3 manual evaluation
- No data loss — candidates and canonical records are separate

---

## 7. Approval Gates

| Phase | Approval Required | Approver | Criteria |
|-------|-------------------|----------|----------|
| Phase 0 | Code review | Derek | Consolidation plan reviewed, no data loss |
| Phase 1 | Deployment approval | Derek | Bridge service running, query API tested |
| Phase 2 | Write access approval | Derek | Publisher tested on 5-10 notes, conflict detection working |
| Phase 3 | Candidate workflow approval | Derek | Evaluation workflow tested, manual review process documented |
| Phase 4 | Automation approval | Derek | Auto-evaluation confidence thresholds validated, observability in place |

---

## 8. Residual Risks

1. **OneDrive sync conflicts:** If Bridge writes to Obsidian while OneDrive is syncing, could cause conflicts. Mitigation: Bridge writes to local path, lets OneDrive sync naturally.

2. **Frontmatter parsing:** Existing `obsidian_reader.py` has a simple frontmatter parser that doesn't handle nested YAML. Mitigation: Upgrade to `python-frontmatter` library (already used in `knowledge_sync/`).

3. **Candidate evaluation bottleneck:** If Derek doesn't review candidates regularly, they accumulate. Mitigation: Phase 4 adds automated evaluation for low-risk candidates.

4. **Master Brain Phase 2 incomplete:** Only 10 atomic thoughts extracted from pilot. Mitigation: Phase 1 of bridge uses pilot data; full integration waits for Master Brain Phase 2 completion.

5. **Knowledge temperature confusion:** VOX might query the wrong temperature (e.g., ask Master Brain for live operational state). Mitigation: Query API includes `depth` parameter; Bridge routes to appropriate source.

---

## 9. Success Criteria

### Phase 0
- [ ] Single vault path configured across all readers
- [ ] Single ChromaDB instance in use
- [ ] 100% of vault files have frontmatter (or exception list documented)
- [ ] Architecture documentation published

### Phase 1
- [ ] Bridge service running in Docker
- [ ] VOX can query Master Brain via Bridge API
- [ ] Query latency < 500ms for canonical knowledge
- [ ] Zero errors in 24-hour test period

### Phase 2
- [ ] Publisher exports 5-10 canonical records to Obsidian
- [ ] Managed notes have correct frontmatter
- [ ] Sync state tracked in PostgreSQL
- [ ] Conflict detection working (test with manual edit)

### Phase 3
- [ ] File watcher detects changes to managed notes
- [ ] Candidates created in Bridge database
- [ ] Manual evaluation workflow tested end-to-end
- [ ] Derek reviews 5+ candidates

### Phase 4
- [ ] Automated evaluation working for low-risk candidates
- [ ] All canonical knowledge types published
- [ ] Observability metrics collected
- [ ] Runbook documented and tested

---

## 10. Open Questions

1. **Master Brain Phase 2 timeline:** When will atomic thought extraction scale beyond the 10-record pilot? Bridge Phase 1 depends on this.

2. **Candidate evaluation authority:** Should DerekOS auto-evaluate candidates, or should Derek always review? What confidence threshold justifies auto-evaluation?

3. **Frontmatter standardization:** What minimal frontmatter fields should all vault files have? Recommend: `type`, `owner`, `status`, `managed`.

4. **ChromaDB consolidation:** Which ChromaDB instance should be canonical? Recommend: `knowledge_sync/` microservice (HTTP, already in Docker).

5. **Query depth routing:** How should the Bridge decide which knowledge temperature to query when `depth: auto`? Recommend: keyword matching + query classification.

---

## 11. Next Steps

1. **Derek reviews this proposal** and provides feedback
2. **Derek approves Phase 0** (consolidate VOX Brain read paths)
3. **Bob implements Phase 0** and validates
4. **Derek approves Phase 1** (Bridge service MVP)
5. **Bob implements Phase 1** and validates
6. **Continue through phases with approval gates**

---

## Appendix A: Existing VOX Brain Architecture

**Read paths:**
- `vox_brain/obsidian_reader.py` + `retrieval.py` (BM25)
- `knowledge_sync/` microservice (ChromaDB, embeddings)
- `shared/knowledge_sync/` library (ChromaDB, local)

**Vault paths:**
- `C:\Users\starw\OneDrive\VOX\VOX\VOX` (obsidian_reader.py)
- `/vault` (knowledge_sync Docker mount)
- `~/VOX/VOX` (shared/knowledge_sync)

**ChromaDB collections:**
- `vox_brain` (microservice, HTTP)
- `vox_knowledge` (library, local)

**APIs:**
- `knowledge_sync` on port 8002: `/knowledge/search`, `/knowledge/index`
- `vox-backend` on port 8003/8004: `/api/v1/knowledge/playbooks`

**MCP servers:**
- 9 MCP servers in `backend/app/mcp_servers/`
- `logseq` MCP for intelligence graph

## Appendix B: Master Brain Current State

**Phase 1 (Ingest):** Complete
- 35 ChatGPT conversation exports
- 3,476 conversations, 68,761 messages
- Normalized to JSONL with full provenance

**Phase 2 (Atomic Thoughts):** Piloted
- 10 records extracted from 3 conversations
- Full evidence classification (D0, D1, A0, etc.)
- Knowledge value, adoption strength, provenance certainty

**Phase 3+ (Entities, Projects, Businesses, etc.):** Not started

**Provenance system:**
- 8+ evidence classes
- 4 orthogonal axes
- Gold set benchmark: 39/40 (0.975) accuracy
- Append-only correction history
