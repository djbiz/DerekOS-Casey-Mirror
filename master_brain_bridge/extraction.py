"""Deterministic, provenance-preserving semantic extraction pipeline.

The extractor is deliberately conservative: it only promotes records backed by
an ingested message and by explicit source text. It has no model/provider
integration and does not infer unsupported semantics.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .candidate_intake import CANDIDATE_SUBTREE
from .config import RuntimeConfig
from .ingest import IngestError, validate_message_record
from .repository import ReadOnlyCanonicalRepository

EXTRACTION_OWNER = "master_brain_bridge.extraction"
EXTRACTION_SCHEMA_VERSION = 1

THOUGHT_TYPES = {
    "idea", "invention", "framework", "business", "goal", "principle",
    "correction", "decision", "observation", "question", "plan",
    "architecture", "strategy", "insight", "critique", "vision",
}
ENTITY_TYPES = {"person", "organization", "place", "product", "technology"}
RELATIONSHIP_TYPES = {"related_to", "builds_on", "supersedes", "contradicts", "depends_on", "part_of", "inspired_by", "evolved_into"}
TIMELINE_EVENTS = {"originated", "developed", "approved", "implemented", "superseded", "rejected", "revisited", "completed"}

ENTITY_LINE = re.compile(r"(?im)\b(?P<prefix>entity|person|organization|place|product|technology)\s*:\s*(?P<value>[^\n]+)")
ENTITY_TYPED = re.compile(r"^\s*(?P<name>[^()|]+?)\s*(?:\((?P<type>person|organization|place|product|technology)\)|\|\s*(?P<type2>person|organization|place|product|technology))?\s*$", re.I)
REL_LINE = re.compile(r"(?im)^\s*relationship\s*:\s*(.+?)\s*$")
TIMELINE_LINE = re.compile(r"(?im)^\s*timeline\s*:\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([a-z_]+)\s*\|\s*(.+?)\s*$")
FRONTMATTER_UNSAFE = re.compile(r"[:#{}\[\],&*?|><!%@`\"']")


class ExtractionError(RuntimeError):
    """Extraction could not complete safely."""


@dataclass(frozen=True)
class StageReport:
    operation: str
    status: str
    input_path: str | None
    output_path: str | None
    records_read: int = 0
    records_written: int = 0
    records_skipped: int = 0
    messages: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ExtractionReport:
    operation: str
    status: str
    stages: list[StageReport]

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "status": self.status,
            "stages": [stage.to_dict() for stage in self.stages],
        }


def _sha(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _thought_id(seed: str) -> str:
    return f"T{int(hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12], 16) % 10_000_000:07d}"


def _entity_id(seed: str) -> str:
    return f"E{int(hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12], 16) % 10_000_000:07d}"


def _relationship_id(seed: str) -> str:
    return f"R{_sha(seed, 12)}"


def _timeline_id(seed: str) -> str:
    return f"TL{_sha(seed, 12)}"


def _knowledge_id(seed: str) -> str:
    return f"MBK-EXTRACT-{_sha(seed, 12).upper()}"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ExtractionError(f"required artifact unavailable: {path}")
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ExtractionError(f"invalid JSON at {path} line {line_number}") from exc
            if not isinstance(record, dict):
                raise ExtractionError(f"{path} line {line_number} must be an object")
            records.append(record)
    if not records:
        raise ExtractionError(f"required artifact has no records: {path}")
    return records


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _atomic_write_jsonl(path: Path, records: list[dict[str, Any]], validator: Callable[[dict[str, Any], str], None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as output:
        temp = Path(output.name)
        try:
            for idx, record in enumerate(records, start=1):
                validator(record, f"{path.name} staged line {idx}")
                output.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            output.flush()
            os.fsync(output.fileno())
        except Exception:
            temp.unlink(missing_ok=True)
            raise
    try:
        # Re-read and validate the fully staged file before promotion. Empty
        # optional stages are valid and promote as deterministic empty files.
        staged: list[dict[str, Any]] = []
        for line_number, line in enumerate(temp.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ExtractionError(f"{path.name} staged reread line {line_number} must be an object")
            staged.append(record)
        if len(staged) != len(records):
            raise ExtractionError(f"staged record count mismatch for {path}")
        for idx, record in enumerate(staged, start=1):
            validator(record, f"{path.name} staged reread line {idx}")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _source_ref(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "file": message["source_file"],
        "conversation_id": message["conversation_id"],
        "conversation_title": message.get("conversation_title"),
        "message_id": message["message_id"],
        "source_record_id": message["source_record_id"],
        "timestamp": message.get("timestamp"),
        "author_role": message.get("role"),
        "original_text": message.get("text", ""),
    }


def _provenance(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_record_id": message["source_record_id"],
        "file": message["source_file"],
        "conversation_id": message["conversation_id"],
        "message_id": message["message_id"],
        "source_record_id": message["source_record_id"],
        "timestamp": message.get("timestamp"),
        "original_text": message.get("text", ""),
    }


def _summary(text: str) -> str:
    clean = " ".join(text.strip().split())
    if not clean:
        return ""
    sentence = re.split(r"(?<=[.!?])\s+", clean, maxsplit=1)[0]
    return sentence[:160].strip()


def _thought_type(text: str) -> str:
    lower = text.lower()
    cues = [
        ("decision", "decision"), ("decide", "decision"), ("plan", "plan"),
        ("goal", "goal"), ("principle", "principle"), ("architecture", "architecture"),
        ("strategy", "strategy"), ("framework", "framework"), ("question", "question"),
        ("?", "question"), ("critique", "critique"), ("vision", "vision"),
        ("invention", "invention"), ("business", "business"), ("correct", "correction"),
    ]
    for cue, value in cues:
        if cue in lower:
            return value
    return "observation"


def _originator(role: str | None) -> str:
    if role == "user":
        return "derek"
    if role == "assistant":
        return "assistant"
    return "unknown"


def _evidence(role: str | None) -> tuple[str, float]:
    if role == "user":
        return "D0", 1.0
    if role == "assistant":
        return "A0", 0.7
    return "X0", 0.2


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _safe_title(text: str) -> str:
    title = _summary(text).strip("# -") or "Untitled Extracted Knowledge"
    return title[:80]


def _yaml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if not text or FRONTMATTER_UNSAFE.search(text) or text[0] in {" ", "-"}:
        return json.dumps(text, ensure_ascii=False)
    return text


class ExtractionPipeline:
    """Staged deterministic extractor for ingested message artifacts."""

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self.config = config or RuntimeConfig.load()

    @classmethod
    def from_environment(cls) -> "ExtractionPipeline":
        return cls(RuntimeConfig.load())

    def extract_thoughts(self) -> StageReport:
        messages = self._load_messages()
        thoughts: list[dict[str, Any]] = []
        skipped = 0
        seen: set[str] = set()
        for message in messages:
            text = message.get("text", "")
            if not isinstance(text, str) or not text.strip():
                skipped += 1
                continue
            evidence_class, confidence = _evidence(message.get("role"))
            seed = f"thought\x1f{message['source_record_id']}\x1f{text.strip()}"
            thought_id = _thought_id(seed)
            while thought_id in seen:
                thought_id = _thought_id(seed + f"\x1f{len(seen)}")
            seen.add(thought_id)
            thought = {
                "id": thought_id,
                "name": _safe_title(text),
                "type": _thought_type(text),
                "originator": _originator(message.get("role")),
                "evidence_class": evidence_class,
                "status": "active_concept",
                "confidence": confidence,
                "created_at": message.get("timestamp") or datetime.fromtimestamp(0, timezone.utc).isoformat(),
                "source": _source_ref(message),
                "summary": _summary(text),
                "detail": text.strip(),
                "tags": [],
                "supersedes": [],
                "superseded_by": None,
                "relationships": [],
                "timeline": [],
                "entities_mentioned": [],
            }
            thoughts.append(thought)
        thoughts.sort(key=lambda item: (item["source"]["file"], item["source"]["conversation_id"], item["source"].get("timestamp") or "", item["id"]))
        _atomic_write_jsonl(self.config.thoughts_path, thoughts, self._validate_thought)
        return StageReport("extract_thoughts", "success", str(self.config.ingest_output_dir / "messages.jsonl"), str(self.config.thoughts_path), len(messages), len(thoughts), skipped)

    def extract_entities(self) -> StageReport:
        thoughts = self._load_stage(self.config.thoughts_path, self._validate_thought)
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        skipped = 0
        thought_by_src = {thought["source"]["message_id"]: thought for thought in thoughts}
        messages = self._load_messages()
        for message in messages:
            text = message.get("text", "")
            explicit = list(self._explicit_entities(text))
            if not explicit:
                skipped += 1
                continue
            thought = thought_by_src.get(message["message_id"])
            for name, entity_type in explicit:
                norm = _normalize(name)
                if not norm:
                    skipped += 1
                    continue
                key = (norm, entity_type)
                evidence_class, confidence = _evidence(message.get("role"))
                seen_ref = {"file": message["source_file"], "conversation_id": message["conversation_id"], "timestamp": message.get("timestamp") or datetime.fromtimestamp(0, timezone.utc).isoformat()}
                current = grouped.get(key)
                if current is None:
                    grouped[key] = {
                        "id": _entity_id(f"{entity_type}\x1f{norm}"),
                        "name": name.strip(),
                        "type": entity_type,
                        "role": "mentioned",
                        "evidence_class": evidence_class,
                        "confidence": confidence,
                        "aliases": [],
                        "first_seen": seen_ref,
                        "last_seen": seen_ref,
                        "mention_count": 1,
                        "description": f"Explicitly mentioned as {entity_type} in source text.",
                        "related_thoughts": [thought["id"]] if thought else [],
                        "related_entities": [],
                        "metadata": {"provenance_refs": [message["source_record_id"]], "extraction_owner": EXTRACTION_OWNER},
                    }
                else:
                    current["mention_count"] += 1
                    current["last_seen"] = seen_ref
                    if thought and thought["id"] not in current["related_thoughts"]:
                        current["related_thoughts"].append(thought["id"])
                    current["metadata"]["provenance_refs"].append(message["source_record_id"])
        entities = sorted(grouped.values(), key=lambda item: (item["name"].lower(), item["type"], item["id"]))
        for entity in entities:
            entity["related_thoughts"].sort()
            entity["metadata"]["provenance_refs"] = sorted(set(entity["metadata"]["provenance_refs"]))
        _atomic_write_jsonl(self.config.entities_path, entities, self._validate_entity)
        return StageReport("extract_entities", "success", str(self.config.thoughts_path), str(self.config.entities_path), len(thoughts), len(entities), skipped)

    def extract_relationships(self) -> StageReport:
        entities = self._load_stage(self.config.entities_path, self._validate_entity, allow_empty=True)
        thoughts = self._load_stage(self.config.thoughts_path, self._validate_thought)
        lookup = { _normalize(item["name"]): item["id"] for item in entities }
        lookup.update({_normalize(item["summary"]): item["id"] for item in thoughts if _normalize(item.get("summary", ""))})
        records: list[dict[str, Any]] = []
        skipped = 0
        for message in self._load_messages():
            for source_name, rel_type, target_name in self._explicit_relationships(message.get("text", "")):
                source_id = lookup.get(_normalize(source_name))
                target_id = lookup.get(_normalize(target_name))
                if not source_id or not target_id or rel_type not in RELATIONSHIP_TYPES:
                    skipped += 1
                    continue
                evidence_class, confidence = _evidence(message.get("role"))
                seed = f"{source_id}\x1f{rel_type}\x1f{target_id}\x1f{message['source_record_id']}"
                records.append({
                    "id": _relationship_id(seed),
                    "source_id": source_id,
                    "target_id": target_id,
                    "type": rel_type,
                    "evidence_class": evidence_class,
                    "confidence": confidence,
                    "provenance": _provenance(message),
                })
        dedup = {record["id"]: record for record in records}
        relationships = sorted(dedup.values(), key=lambda item: (item["source_id"], item["type"], item["target_id"], item["id"]))
        _atomic_write_jsonl(self.config.relationships_path, relationships, self._validate_relationship)
        return StageReport("extract_relationships", "success", str(self.config.entities_path), str(self.config.relationships_path), len(entities) + len(thoughts), len(relationships), skipped)

    def extract_timelines(self) -> StageReport:
        thoughts = self._load_stage(self.config.thoughts_path, self._validate_thought)
        records: list[dict[str, Any]] = []
        for thought in thoughts:
            timestamp = thought["source"].get("timestamp") or datetime.fromtimestamp(0, timezone.utc).isoformat()
            date = timestamp[:10]
            seed = f"originated\x1f{thought['id']}\x1f{date}"
            records.append({
                "id": _timeline_id(seed),
                "subject_id": thought["id"],
                "date": date,
                "event": "originated",
                "description": thought["summary"],
                "provenance": {
                    "source_record_id": thought["source"].get("source_record_id", thought["source"]["message_id"]),
                    "file": thought["source"]["file"],
                    "conversation_id": thought["source"]["conversation_id"],
                    "message_id": thought["source"]["message_id"],
                    "timestamp": thought["source"].get("timestamp"),
                    "original_text": thought["source"].get("original_text", ""),
                },
            })
        messages = self._load_messages()
        explicit_count = 0
        for message in messages:
            for date, event, description in TIMELINE_LINE.findall(message.get("text", "")):
                event = event.lower()
                if event not in TIMELINE_EVENTS:
                    continue
                explicit_count += 1
                subject_id = _thought_id(f"thought\x1f{message['source_record_id']}\x1f{message.get('text','').strip()}")
                records.append({
                    "id": _timeline_id(f"explicit\x1f{message['source_record_id']}\x1f{date}\x1f{event}\x1f{description}"),
                    "subject_id": subject_id,
                    "date": date,
                    "event": event,
                    "description": description.strip(),
                    "provenance": _provenance(message),
                })
        timelines = sorted({record["id"]: record for record in records}.values(), key=lambda item: (item["date"], item["subject_id"], item["id"]))
        _atomic_write_jsonl(self.config.timelines_path, timelines, self._validate_timeline)
        return StageReport("extract_timelines", "success", str(self.config.thoughts_path), str(self.config.timelines_path), len(thoughts), len(timelines), 0, [f"explicit_timeline_entries={explicit_count}"])

    def extract_canonical(self) -> StageReport:
        thoughts = self._load_stage(self.config.thoughts_path, self._validate_thought)
        self._load_stage(self.config.entities_path, self._validate_entity, allow_empty=True)
        self._load_stage(self.config.relationships_path, self._validate_relationship, allow_empty=True)
        self._load_stage(self.config.timelines_path, self._validate_timeline, allow_empty=True)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for thought in thoughts:
            key = _normalize(thought["summary"])
            if not key:
                continue
            grouped.setdefault(key, []).append(thought)
        records: list[dict[str, Any]] = []
        for key, items in grouped.items():
            items.sort(key=lambda item: (item["source"]["file"], item["source"]["conversation_id"], item["source"].get("timestamp") or "", item["id"]))
            first = items[0]
            evidence_ids = sorted({item["id"] for item in items} | {item["source"].get("message_id", "") for item in items if item["source"].get("message_id")})
            content_lines = [first["detail"].strip()]
            if len(items) > 1:
                content_lines.extend(["", "Additional provenance-backed occurrences:"])
                content_lines.extend(f"- {item['summary']} ({item['id']})" for item in items[1:])
            record = {
                "knowledge_id": _knowledge_id(key),
                "revision": 1,
                "canonical_status": "CURRENT",
                "title": _safe_title(first["summary"]),
                "summary": first["summary"],
                "content": "\n".join(content_lines).strip(),
                "evidence_ids": evidence_ids,
                "approval_status": "ACCEPTED",
                "projection_policy": "PUBLISH",
                "extraction_owner": EXTRACTION_OWNER,
                "extraction_stage_schema": EXTRACTION_SCHEMA_VERSION,
            }
            records.append(record)
        records.sort(key=lambda item: item["knowledge_id"])
        _atomic_write_jsonl(self.config.canonical_candidates_path, records, self._validate_canonical)
        self._promote_canonical_store(records)
        notes = self._write_candidate_notes(records)
        return StageReport("extract_canonical", "success", str(self.config.timelines_path), str(self.config.canonical_candidates_path), len(thoughts), len(records), 0, [f"candidate_notes_written={notes}", f"canonical_store={self.config.canonical_store_path}"])

    def run_all(self) -> ExtractionReport:
        stages: list[StageReport] = []
        for runner in (self.extract_thoughts, self.extract_entities, self.extract_relationships, self.extract_timelines, self.extract_canonical):
            stages.append(runner())
        report = ExtractionReport("extract_all", "success" if all(stage.ok for stage in stages) else "failed", stages)
        _write_json(self.config.extraction_report_path, report.to_dict())
        return report

    def _load_messages(self) -> list[dict[str, Any]]:
        path = self.config.ingest_output_dir / "messages.jsonl"
        records = _jsonl(path)
        for idx, record in enumerate(records, start=1):
            try:
                validate_message_record(record, context=f"messages.jsonl line {idx}")
            except IngestError as exc:
                raise ExtractionError(str(exc)) from exc
        return sorted(records, key=lambda item: (item["source_file"], item["conversation_id"], item.get("sequence_index") if item.get("sequence_index") is not None else 10**12, item["source_record_id"]))

    def _load_stage(self, path: Path, validator: Callable[[dict[str, Any], str], None], *, allow_empty: bool = False) -> list[dict[str, Any]]:
        if allow_empty and path.is_file() and not path.read_text(encoding="utf-8").strip():
            return []
        try:
            records = _jsonl(path)
        except ExtractionError:
            if allow_empty and path.is_file():
                return []
            raise
        for idx, record in enumerate(records, start=1):
            validator(record, f"{path.name} line {idx}")
        return records

    @staticmethod
    def _explicit_entities(text: str) -> Iterable[tuple[str, str]]:
        for match in ENTITY_LINE.finditer(text or ""):
            raw = match.group("value").strip()
            prefix = match.group("prefix").strip().lower()
            parsed = ENTITY_TYPED.match(raw)
            if not parsed:
                continue
            name = parsed.group("name").strip()
            entity_type = (parsed.group("type") or parsed.group("type2") or (prefix if prefix in ENTITY_TYPES else "")).lower()
            if name and entity_type in ENTITY_TYPES:
                yield name, entity_type

    @staticmethod
    def _explicit_relationships(text: str) -> Iterable[tuple[str, str, str]]:
        for match in REL_LINE.finditer(text or ""):
            raw = match.group(1).strip()
            if "|" in raw:
                parts = [part.strip() for part in raw.split("|")]
                if len(parts) == 3:
                    yield parts[0], parts[1].lower(), parts[2]
                    continue
            parts = raw.split()
            for rel_type in sorted(RELATIONSHIP_TYPES, key=len, reverse=True):
                token = rel_type.replace("_", " ")
                lowered = raw.lower()
                if f" {token} " in lowered:
                    left, right = re.split(re.escape(token), raw, maxsplit=1, flags=re.I)
                    yield left.strip(), rel_type, right.strip()
                    break

    @staticmethod
    def _validate_thought(record: dict[str, Any], context: str) -> None:
        required = {"id", "name", "type", "originator", "evidence_class", "status", "confidence", "source", "summary"}
        missing = required - set(record)
        if missing:
            raise ExtractionError(f"{context} missing fields: {sorted(missing)}")
        if not re.fullmatch(r"T[0-9]{7}", str(record["id"])):
            raise ExtractionError(f"{context} invalid thought id")
        if record["type"] not in THOUGHT_TYPES:
            raise ExtractionError(f"{context} invalid thought type")
        if record["originator"] not in {"derek", "assistant", "collaborative", "unknown"}:
            raise ExtractionError(f"{context} invalid originator")
        if record["evidence_class"] not in {"D0", "D1", "A0", "I0", "E0", "B0", "X0"}:
            raise ExtractionError(f"{context} invalid evidence_class")
        if not isinstance(record["confidence"], (int, float)) or not 0 <= record["confidence"] <= 1:
            raise ExtractionError(f"{context} invalid confidence")
        source = record.get("source")
        if not isinstance(source, dict) or not {"file", "conversation_id", "message_id"} <= set(source):
            raise ExtractionError(f"{context} invalid source")
        if not isinstance(record["summary"], str) or not record["summary"].strip():
            raise ExtractionError(f"{context} invalid summary")

    @staticmethod
    def _validate_entity(record: dict[str, Any], context: str) -> None:
        required = {"id", "name", "type", "evidence_class", "confidence", "first_seen", "last_seen"}
        if required - set(record):
            raise ExtractionError(f"{context} missing entity fields: {sorted(required - set(record))}")
        if not re.fullmatch(r"E[0-9]{7}", str(record["id"])) or record["type"] not in ENTITY_TYPES:
            raise ExtractionError(f"{context} invalid entity identity")
        if not isinstance(record.get("mention_count", 0), int) or record.get("mention_count", 0) < 0:
            raise ExtractionError(f"{context} invalid mention_count")

    @staticmethod
    def _validate_relationship(record: dict[str, Any], context: str) -> None:
        required = {"id", "source_id", "target_id", "type", "evidence_class", "confidence", "provenance"}
        if required - set(record):
            raise ExtractionError(f"{context} missing relationship fields: {sorted(required - set(record))}")
        if not re.fullmatch(r"R[a-f0-9]{12}", str(record["id"])) or record["type"] not in RELATIONSHIP_TYPES:
            raise ExtractionError(f"{context} invalid relationship")
        if not isinstance(record.get("provenance"), dict) or "source_record_id" not in record["provenance"]:
            raise ExtractionError(f"{context} invalid provenance")

    @staticmethod
    def _validate_timeline(record: dict[str, Any], context: str) -> None:
        required = {"id", "subject_id", "date", "event", "description", "provenance"}
        if required - set(record):
            raise ExtractionError(f"{context} missing timeline fields: {sorted(required - set(record))}")
        if not re.fullmatch(r"TL[a-f0-9]{12}", str(record["id"])) or record["event"] not in TIMELINE_EVENTS:
            raise ExtractionError(f"{context} invalid timeline")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record["date"])):
            raise ExtractionError(f"{context} invalid timeline date")

    @staticmethod
    def _validate_canonical(record: dict[str, Any], context: str) -> None:
        required = {"knowledge_id", "revision", "canonical_status", "title", "content", "evidence_ids", "approval_status", "projection_policy", "extraction_owner"}
        if required - set(record):
            raise ExtractionError(f"{context} missing canonical fields: {sorted(required - set(record))}")
        if not re.fullmatch(r"MBK-EXTRACT-[A-F0-9]{12}", str(record["knowledge_id"])):
            raise ExtractionError(f"{context} invalid knowledge_id")
        if record["revision"] != 1 or record["canonical_status"] != "CURRENT":
            raise ExtractionError(f"{context} invalid canonical revision/status")
        if record["approval_status"] != "ACCEPTED" or record["projection_policy"] != "PUBLISH":
            raise ExtractionError(f"{context} invalid publication fields")
        if record["extraction_owner"] != EXTRACTION_OWNER:
            raise ExtractionError(f"{context} invalid extraction owner")
        if not isinstance(record["evidence_ids"], list) or not all(isinstance(item, str) and item for item in record["evidence_ids"]):
            raise ExtractionError(f"{context} invalid evidence_ids")

    def _promote_canonical_store(self, records: list[dict[str, Any]]) -> None:
        destination = self.config.canonical_store_path
        if destination.exists():
            try:
                existing = _jsonl(destination)
            except ExtractionError as exc:
                raise ExtractionError(f"refusing to overwrite invalid existing canonical store: {destination}") from exc
            if any(record.get("extraction_owner") != EXTRACTION_OWNER for record in existing):
                raise ExtractionError(f"refusing to overwrite non-extraction-owned canonical store: {destination}")
        _atomic_write_jsonl(destination, records, self._validate_canonical)
        # Prove the promoted store satisfies the read-only repository contract.
        ReadOnlyCanonicalRepository(destination)

    def _write_candidate_notes(self, records: list[dict[str, Any]]) -> int:
        vault = self.config.obsidian_vault_path
        if vault is None:
            raise ExtractionError("OBSIDIAN_VAULT_PATH not configured; cannot write candidate notes")
        if not vault.is_dir():
            raise ExtractionError(f"Obsidian vault unavailable: {vault}")
        root = vault / CANDIDATE_SUBTREE
        root.mkdir(parents=True, exist_ok=True)
        written = 0
        for record in records:
            path = root / f"{record['knowledge_id']}.md"
            content = self._render_candidate_note(record)
            if path.exists():
                existing = path.read_text(encoding="utf-8")
                frontmatter = existing.split("---", 2)[1] if existing.startswith("---") and len(existing.split("---", 2)) >= 3 else ""
                if "master_brain_extraction_generated: true" not in frontmatter:
                    raise ExtractionError(f"refusing to overwrite non-extraction candidate note: {path}")
                if existing == content:
                    continue
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=root, prefix=f".{path.name}.", suffix=".tmp", delete=False) as output:
                temp = Path(output.name)
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            try:
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)
            written += 1
        return written

    @staticmethod
    def _render_candidate_note(record: dict[str, Any]) -> str:
        frontmatter = {
            "master_brain_extraction_generated": True,
            "candidate_type": "NEW",
            "proposed_operation": "CREATE",
            "proposed_knowledge_id": record["knowledge_id"],
            "base_canonical_revision": record["revision"],
            "submitter": "master_brain_bridge.extraction",
            "provenance_refs": ", ".join(record["evidence_ids"]),
        }
        lines = ["---", *(f"{key}: {_yaml_value(value)}" for key, value in frontmatter.items()), "---", "", f"# {record['title']}", "", record.get("summary", ""), "", "## Candidate Canonical Content", "", record["content"], "", "## Provenance", "", *(f"- {item}" for item in record["evidence_ids"]), ""]
        return "\n".join(lines)
