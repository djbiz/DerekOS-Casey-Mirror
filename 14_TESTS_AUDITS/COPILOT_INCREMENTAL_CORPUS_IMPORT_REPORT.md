# Copilot Incremental Corpus Import Report

**Source file**: `copilot-2026-08-12T11_59_49.315Z.csv`
**Preserved at**: `00_RAW_ARCHIVE/copilot/copilot-2026-08-12T11_59_49.315Z.csv` (read-only, POSIX + Windows attrib, matching the ChatGPT archive's immutability treatment)
**SHA-256**: `4d08d154ea75037b884b1799f47ec8d561629f80b2c8b4311affffa858713b98`
**Status**: Pre-import analysis only. **Canonical knowledge has not been modified.** Ingestion into a unified message schema has not run — this report is the "before ingesting" gate requested.

## Basic composition

- 400 message rows, schema: `Conversation, Time, Author, Message`
- 28 distinct conversations (27 named + one group of 10 rows sharing an empty `Conversation` field — see Data Quality below)
- Author distribution: exactly 200 `Human` / 200 `AI`
- Timestamp range: **2025-05-31T20:11:57 to 2026-02-23T10:52:43** — sits within the ChatGPT archive's overall span, does not extend it
- Conversation sizes range from 2 rows to 88 rows (largest: "Metaphorical Exploration of Consciousness and Reality")

## Data quality findings

- **29 rows have an empty `Message` field.** 3 of these correlate with `Author=Human` rows immediately preceding an AI response about a file that "couldn't be opened" — almost certainly file/attachment shares the export doesn't capture text for, mirroring the ChatGPT export's `file-*.dat` attachment gap (§2 of the main spec). The remaining empty-message rows need individual review before ingestion assigns them any evidence class — an empty message is not itself a data error, but it also can't be classified as D0/A0/anything without content.
- **The CSV's row order is not reliably chronological within a conversation.** Verified directly: in "Creating a Shared Business Context Template," rows appear in the order `[10:52:43, 10:52:43, 10:46:00, 10:46:00]` — later timestamps before earlier ones. **The ingestion adapter must sort by `Time` per conversation, not trust file order** (this is a real, different failure mode from the ChatGPT export's `mapping` tree, which at least has explicit parent/child structure — this CSV has none, only a flat timestamp to reconstruct order from, and ties between a Human/AI pair share the same timestamp to the second).
- 43 within-Copilot near-duplicate row pairs detected (>=15 matching 12-word shingles) — expected for long single conversations where the AI recaps earlier context, not necessarily cross-conversation reuse. Not yet individually reviewed.

## Cross-corpus overlap with the ChatGPT archive: substantial, and important

**38 rows (out of 245 rows long enough to meaningfully check) show significant text overlap with the existing ChatGPT corpus** — 16 `Human`-authored, 22 `AI`-authored. This confirms your expectation directly: **Derek moves content between ChatGPT and Copilot in both directions**, not just within a single platform. The same "role/author does not equal originator" caution from `MASTER_BRAIN_BUILD_SPEC.md` §6.0a applies across sources, not just within one export — and needs a cross-*source* origin index eventually (matching your proposed `03_PROVENANCE_INDEX/`), not just cross-conversation within one file.

### The flagship case: "Legacy Forge Shared Business Context" — verified, and the finding changes its value

You flagged this conversation as an example of "highly relevant" SOP material. Tracing it fully across both sources changes that assessment:

1. **ChatGPT**, conversation "Shared Business Context Form" (`699c3024-384c-832a-a189-85791d8ae107`), **2026-02-23T10:49:14**: a `role: user` message reading "Absolutely — I can fill in this entire Shared Business Context for you, but I need your business details first... the template is empty..." — itself assistant-voiced, not Derek's own words (same pattern as the ChatGPT Gold Set's `gold_037`). The paired `assistant` response is a **"fully filled" Legacy Forge™ document** — business identity, industry, founding year, business model — presented as complete.
2. **Checked the sibling branches at this exact point** (this message was regenerated three times in the ChatGPT export): the other two attempts, given the *identical* prompt, produced **empty fill-in templates** ("Business Name: ___, Industry: ___, Founded (Year): ___") — not filled content. **No message anywhere in this conversation contains Derek actually supplying business details.**
3. **Conclusion, with real confidence**: the "fully filled" Legacy Forge business context — the specific document you cited as valuable — is very likely **ChatGPT-generated/invented content**, not genuine facts Derek provided. The model produced a plausible-sounding business document from a template-request prompt, not from Derek's own input.
4. **Copilot**, conversation "Creating a Shared Business Context Template," **2026-02-23T10:52:43** (3.5 minutes later): this ChatGPT-invented document gets pasted into Copilot as a `Human` message (759 matching shingles, exact match), and Copilot's own `AI` response further polishes it into "fully completed, polished, publication-ready" formatting (418 matching shingles against the same ChatGPT origin).

**This is exactly the risk your own message named** ("we should reconstruct which pieces you supplied versus which pieces Copilot organized or added, rather than automatically treating the polished AI document as your original SOP") — turned out to be more severe than the original framing suggested: not just "Copilot organized it," but **the underlying content itself did not originate from you at all, in either conversation, on either platform.** If this had been ingested as SOP/operating knowledge without this trace, it would have become exactly the kind of fabricated-provenance error this whole project exists to prevent — a plausible, confident-sounding AI invention treated as documented business fact.

This doesn't mean the Legacy Forge business concept itself is fake — only that *this specific document's content* has no traced source in either archive. If you do have a real, independently-supplied Legacy Forge business context (verbally, in a different tool, on paper), that's the actual source of truth — not this file.

### Other notable cross-source matches (not yet individually traced to this depth)

- "Metaphorical Exploration of Consciousness and Reality" (the largest Copilot conversation, 88 rows) has multiple high-strength matches (692, 581 shingles) against ChatGPT content.
- Several `Human` rows opening with "Can you add this in the system," "Can we add this," "Can I add this" — the same lead-in pattern already characterized in the ChatGPT Gold Set (`gold_016`, `gold_030`, `gold_031`: Derek reusing an assistant's own prior output) — appearing here with matches against the *ChatGPT* corpus specifically, meaning this is the same behavior pattern operating across platforms, not just within one.
- Full list of all 38 matches, with row indices and candidate ChatGPT origin message/conversation IDs, is in `14_TESTS_AUDITS/copilot_chatgpt_overlap.json` for further tracing.

## What this means for the "SOP / Operating Knowledge" extraction class you proposed

Your instinct to add a dedicated `SOP / OPERATING KNOWLEDGE` extraction class is right, and this file does contain real candidate material for it (escalation rules, approval gates, KPIs, sales-stage language appear across multiple conversations, not just the one traced above). But the Legacy Forge case is a concrete, verified demonstration of why **`Author=Human` cannot be treated as `D0` by default for this purpose** — your own instruction already said this explicitly, and this finding is the evidence for why it matters this much. Any SOP extracted from this source needs the same segmentation (Derek's own operational rules vs. AI-organized/invented structure) as the ChatGPT provenance work, not a lighter-touch pass just because it's framed as "business documentation."

## Recommendation before ingestion

1. Build the `copilot_csv` adapter (normalizes into the canonical message schema, tagged with a `source: "copilot"` field so source-specific metadata like the flat `Conversation` title and `Author` values aren't lost — no `mapping`/`node_id` tree exists for this source, so provenance tooling needs a per-source-aware ordering strategy, not just reused ChatGPT logic).
2. Extend the cross-corpus shingle index to be source-aware from the start (Copilot AI messages should also be indexed as potential origins, not just ChatGPT assistant messages — Derek may paste Copilot's own output into ChatGPT too, and the current check only looked one direction).
3. Do not extract or promote any "Shared Business Context" / SOP-labeled document from either source to canonical status until its full origin chain is traced the way the Legacy Forge case was here.

Awaiting your go-ahead before building the adapter and running actual ingestion.
