# 01_INGEST — Phase 1 output (Codex role)

Produced by `ingest.py` from `00_RAW_ARCHIVE/chatgpt/` (read-only source, never modified).

## Files

- **`messages.jsonl`** — one JSON object per line, one line per message node found anywhere in every conversation's `mapping` tree (not just the linear "current" branch — see `branch` field below). Schema:

  ```json
  {
    "message_id": "...",
    "source_record_id": "srcmsg_<stable hash>",
    "node_id": "<mapping node id>",
    "conversation_id": "...",
    "conversation_title": "...",
    "source_file": "conversations-NNN.json",
    "role": "user | assistant",
    "author_name": null,
    "timestamp": "ISO 8601, or \"UNPARSEABLE_RAW:<value>\" for the 14 out-of-range timestamps found in this archive",
    "text": "extracted text - see extraction rules below",
    "content_type": "text | multimodal_text | reasoning_recap | thoughts",
    "branch": "main | alternate",
    "sequence_index": "int (position in the linear conversation) if branch=main, else null"
    "parent_message_id": "<parent mapping node id or null>",
    "child_message_ids": ["<child mapping node id>"],
    "source_sha256": "<SHA-256 of the immutable source file>",
    "ingest_version": "1.1.0"
  }
  ```

- **`conversations_index.json`** — one record per conversation: id, title, source file, timestamps, message counts (total / main-path / alternate-branch), and an `anomalous_current_node` flag.

- **`ingest_report.json`** — run summary Audit Bot's Phase 1 check should start from: total conversations/messages, any duplicate `conversation_id`s across files (none found), any anomalous conversations (none found), count of unparseable timestamps.
- **`checkpoint.json`** — restart/idempotency checkpoint containing the completed source-file list and normalized output hash.
- **`schemas/message-1.1.0.schema.json`** — immutable versioned contract for each line in `messages.jsonl`.
- **`../13_SOURCE_INDEX/source_manifest.json`** — canonical per-source hash, size, conversation, mapping-node, and message inventory.

Outputs are written through same-directory temporary files and atomically replaced. Re-running an unchanged corpus produces the same `messages.jsonl` SHA-256; run timestamps are deliberately excluded from normalized data and evidence reports.

## Extraction rules (what `text` actually contains)

Verified directly against this archive's real data, not assumed from the generic ChatGPT export spec:

| `content_type` | Source field | Notes |
|---|---|---|
| `text` | `content.parts` (string parts joined) | The normal case. |
| `multimodal_text` | `content.parts` (string parts joined, non-string parts skipped) | Non-string parts are image/attachment refs, not extracted here. |
| `reasoning_recap` | `content.content` | Short UI label from reasoning models (e.g. "Thought for a couple of seconds"). |
| `thoughts` | `content.thoughts[].content`, joined | Internal reasoning-model deliberation text. Genuinely empty (`thoughts: []`) for 503 of 68,761 messages — that's a fact about those messages, not an extraction failure. |
| anything else | — | Returns `""`. No other content_type was found in this archive as of this ingest run; if a future append to the corpus introduces one, it will silently return empty text here and should be added to `_joined_text()` in `ingest.py`. |

Empty `text` also occurs legitimately for `text`/`multimodal_text` messages that are attachment-only (e.g. a user submitting a PDF with no caption) — spot-checked directly against `00_RAW_ARCHIVE/` during Phase 1, confirmed genuine, not a bug.

## Known, deliberate gaps (not fixed in this phase — flagged for whoever needs them)

- **Attachments** (`message.metadata.attachments`, PDF/image/file refs) are not extracted. The binary files themselves were also deliberately excluded from `00_RAW_ARCHIVE/` (see spec §2). If a later phase needs "what was this attachment," it requires a separate pass against the original export zip in `Downloads/`.
- **`role` values seen:** only `user` and `assistant` in this archive. The spec (§2.1) warns not to assume only these two exist — none-the-less, that is what this specific corpus actually contains, confirmed by full-corpus role tally, not sampling.

## Numbers from the last run

- 35/35 source files processed
- 3,476 conversations
- 68,761 messages (67,878 on the main/current path, 883 on abandoned/edited-out branches — captured, not dropped)
- 0 duplicate `conversation_id`s
- 0 anomalous conversations (bad/missing `current_node`)
- 14 unparseable timestamps (out of range for `datetime.fromtimestamp` on this platform)
