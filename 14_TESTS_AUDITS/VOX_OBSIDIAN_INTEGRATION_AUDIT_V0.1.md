# VOX Brain / Obsidian Integration Audit v0.1

**Date:** 2026-08-12

**Mode:** Read-only architecture audit

**Repositories inspected:** `D:\Projects\VOX\vox_v4`, `D:\Projects\VOX\DerekOS_Master_Brain`
**No runtime, vault, index, or corpus data was modified.**

## Executive finding

VOX already has a functioning Obsidian read path, a separate semantic indexing service, and several direct vault writers. The integration is not one system: it is multiple partially overlapping knowledge paths with different physical roots and different source-of-truth assumptions.

The Master Brain must connect through an explicit bridge contract. It must not be copied into Obsidian, indexed as if it were ordinary vault prose, or merged into VOX Brain.

## Physical vault and observed contents

- Default host vault: `C:\Users\starw\OneDrive\VOX\VOX\VOX`
- Exists: yes
- Approximate files: 1,056
- Markdown notes: 220
- Total bytes: 12,170,098
- Markdown bytes: 1,400,085

Observed top-level knowledge surfaces include:

- `01 Identity`
- `02 Projects`
- `03 Clients`
- `04 Business`
- `05 Knowledge`
- `07 Daily Notes`
- `09 SOPs`
- `10 AI Memory`
- `AI`, `AI-OS`, `AI-Workspace`
- `Business Frameworks`, `Business_OS`
- `DerekOS`
- `Industry Packs`
- `Playbooks`
- `memory`

The vault is also a Git/Obsidian working directory and includes application, cache, attachment, and archive content. It is not a narrowly curated canonical-knowledge store today.

## How VOX reads Obsidian

### In-process VOX Brain path

- `vox_brain/obsidian_reader.py::ObsidianReader`
- Default path: `OBSIDIAN_VAULT_PATH`, falling back to `C:\Users\starw\OneDrive\VOX\VOX\VOX`
- Reads Markdown recursively and skips `.obsidian`, `.git`, `.trash`, `venv`, and `node_modules`.
- Parses simple YAML frontmatter and Markdown heading sections.
- Is explicitly read-only.
- `vox_brain/retrieval.py::RetrievalService` builds an in-memory BM25 index from parsed sections.
- Consumers include Framework Engine, Strategic Council, Value Equation, Mega Agent execution, and briefing/content paths.

This index is process-local and rebuilt from files; it is not a persistent vector database.

### Knowledge Sync service path

- `knowledge_sync/indexer.py::KnowledgeIndexer`
- Container vault path: `/vault`
- Docker mount: `../brain/vault:/vault:ro`
- This mount does **not** point to the default host vault above unless external directory layout makes them the same; no evidence in the repository proves that equivalence.
- Splits Markdown by headings.
- Parses frontmatter, wikilinks, and tags.
- Generates embeddings through the configured embedding provider.
- Stores vectors in Chroma collection `vox_brain` at `chromadb:8000`.
- Stores delta-sync state in PostgreSQL table `knowledge_sync_state` using relative file path and an MD5 content hash.
- Polls and reindexes every 60 seconds.

## APIs, tools, and MCP surfaces

The Knowledge Sync FastAPI service exposes:

- `POST /knowledge/index`
- `POST /knowledge/search`
- `GET /knowledge/document/{doc_id}`
- `GET /knowledge/related/{doc_id}`
- `GET /knowledge/graph/{topic}`
- `GET /health`

No canonical Obsidian-specific MCP façade was found. Logseq exposes `knowledge.graph` MCP capabilities and AppFlowy exposes `workspace.knowledge`, but neither is the Obsidian source and neither should be repurposed as the Master Brain bridge.

## Does VOX write to Obsidian?

Yes, outside the read-only `ObsidianReader`:

- `backend/app/knowledge/mirofish.py::_store_to_obsidian` writes daily-learning Markdown.
- `backend/app/services/outcome_tracker.py::_write_vault_outcome` writes outcome JSON and appends daily-learning Markdown under `10 AI Memory`.
- Strategic intelligence and MiroFish clients reference the configured Obsidian vault.
- Temporal knowledge activities and some learning flows write to a second default path: `C:\Users\starw\OneDrive\VOX\VOX\KnowledgeGraph`.

These are operational observations/learning outputs, not evidence-reviewed Master Brain canon.

## Frontmatter and metadata conventions

The vault does not use one enforced schema. A sample of up to 500 Markdown notes found these keys:

- Common: `version`, `type`, `id`, `title`, `owner`, `tags`
- Synchronization/provenance-like: `source`, `synced`
- Less common: `name`, `description`, `space`, `space_id`, `framework`, `stages`, `doc_id`, `doc_name`, `parent_id`

No existing mandatory `master_brain_id`, canonical status, evidence revision, or candidate-state convention was found.

## Current source-of-truth assessment

The repository is internally inconsistent:

- `ObsidianReader` states that the vault is the source of truth.
- Operational writers treat the vault as a mutable memory/output surface.
- Knowledge Sync treats Markdown plus its Chroma derivative as searchable knowledge.
- The Master Brain specification establishes the Master Brain as provenance/evidence authority.

Therefore, the current source of truth is **ambiguous by knowledge type**, not globally defined:

- Live operational data belongs to VOX persistence/business systems.
- Existing human-authored notes currently originate in Obsidian.
- Historical conversation evidence and future canonical concepts belong to the Master Brain.
- Chroma, BM25, and PostgreSQL sync state are derived indexes, never source truth.

## Duplicate and drifting knowledge stores

1. Host vault at `...\VOX\VOX\VOX`.
2. Sibling `...\VOX\VOX\KnowledgeGraph` writer target.
3. Docker `../brain/vault` read-only mount.
4. In-memory BM25 section index.
5. Chroma `vox_brain` embedding collection.
6. PostgreSQL `knowledge_sync_state` index metadata.
7. Obsidian `10 AI Memory` JSON/Markdown runtime outputs.
8. Master Brain raw, extracted, and future canonical layers.

Indexes 4–6 are legitimate derivatives if their source identity is explicit. Locations 1–3 and 7–8 can drift because their ownership and synchronization contracts are not unified.

## DerekOS and Mega Agent references

- DerekOS is represented in the vault directory structure and participates in the broader VOX deployment.
- VOX Brain’s retrieval service feeds strategic reasoning components.
- `mega_agent/executor.py` lazily constructs `RetrievalService`, so Mega Agent can receive Obsidian evidence through VOX Brain.
- No current path lets DerekOS or Mega Agent query canonical Master Brain records by stable Master Brain ID.

## Audit disposition

- Existing VOX Brain/Obsidian integration: **PARTIAL / REAL**
- Single-source-of-truth definition: **REAL GAP**
- Master Brain connection: **NOT IMPLEMENTED**
- Data migration requirement: **NOT AUTHORIZED and not recommended**
- Runtime modification required for this audit: **NO**
