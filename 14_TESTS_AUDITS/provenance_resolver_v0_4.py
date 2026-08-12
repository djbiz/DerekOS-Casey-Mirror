"""PROVENANCE_RESOLVER_V0.4: span provenance, P0 tiers, adoption.

The v0.3 D0 result is an immutable safety boundary: this module may enrich it
but never changes which records v0.3 attributes to Derek.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from provenance_resolver_v0_3 import classify_adversarial_case


@dataclass(frozen=True)
class ProvenanceSpan:
    start: int
    end: int
    text: str
    authored_by: str
    evidence_class: str
    source_reference: str | None
    confidence_tier: str


MIXED_BOUNDARIES = [
    re.compile(r"(?i)(the entire transcript is given below\.[ \t]*\r?\n)"),
    re.compile(r"(?i)(here(?:'|’)s the word-for-word script transcription[^\n]*\r?\n)"),
    re.compile(r"(?i)(below is a single upgrade script[^\n]*\r?\n)"),
]

CARRIER_PREFIX = re.compile(
    r"(?is)^.{0,240}\b(?:summarize|rewrite|recreate|improve|review|make this better|"
    r"email below|script below|her reply|post i like|wait before we move on|"
    r"is this inside the system|what can be done with these)\b"
)

EXTERNAL_OR_AGENT_MARKERS = re.compile(
    r"(?im)(https?://|^subject:|^from:\s|^sent:\s|^her reply\b|"
    r"entire transcript is given below|word-for-word script transcription|"
    r"```(?:python|bash|json|yaml|sql)?|^architecture board|^board directive|"
    r"^implementation commit|^tests?\s*:\s*(?:pass|\d+ passed)|"
    r"^from (?:codex|claude|hermes|opencode|zcode)\b)"
)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _origin_is_prior(bundle: dict) -> bool:
    origin = bundle.get("origin_candidate") or {}
    return bool(
        _parse_time(origin.get("ts"))
        and _parse_time(bundle.get("target", {}).get("ts"))
        and _parse_time(origin["ts"]) < _parse_time(bundle["target"]["ts"])
    )


def _split_spans(text: str, source_reference: str | None) -> list[ProvenanceSpan]:
    for pattern in MIXED_BOUNDARIES:
        match = pattern.search(text)
        if match and 5 <= match.end() < len(text) - 20:
            return [
                ProvenanceSpan(0, match.end(), text[: match.end()], "derek", "D0", None, "DAE-3"),
                ProvenanceSpan(match.end(), len(text), text[match.end() :], "external", "P0", source_reference, "P0-PROBABLE"),
            ]

    if CARRIER_PREFIX.search(text):
        boundary = text.find("\n\n")
        if boundary < 0:
            boundary = text.find("\n")
        if 5 <= boundary <= 300 and len(text) - boundary > 40:
            return [
                ProvenanceSpan(0, boundary, text[:boundary], "derek", "D0", None, "DAE-3"),
                ProvenanceSpan(boundary, len(text), text[boundary:], "unknown", "P0", source_reference, "P0-PROBABLE"),
            ]
    return []


def _split_traceable_carrier(text: str, source_reference: str | None) -> list[ProvenanceSpan]:
    """Split a short instruction from a traceably reused body."""
    if not CARRIER_PREFIX.search(text):
        return []
    candidates = [position for position in (text.find("\n\n"), text.find("  "), text.find(":")) if position >= 5]
    if not candidates:
        return []
    boundary = min(candidates)
    if boundary > 300 or len(text) - boundary <= 30:
        return []
    return [
        ProvenanceSpan(0, boundary, text[:boundary], "derek", "D0", None, "DAE-3"),
        ProvenanceSpan(boundary, len(text), text[boundary:], "assistant", "P0", source_reference, "P0-CERTAIN"),
    ]


def _adoption(text: str, preceding_role: str | None) -> tuple[str | None, str]:
    if preceding_role != "assistant":
        return None, "AD0"
    stripped = text.strip()
    if re.match(r"(?is)^(?:yes|approved?|adopt).{0,180}\b(?:but|change|modify|add|connect|integrate)\b", stripped):
        return "derek", "AD4"
    if re.match(r"(?is)^(?:yes|approved?|perfect|use this|add this|keep this)\b", stripped):
        return "derek", "AD3"
    if re.match(r"(?is)^(?:can|could|what|how|review|summarize|rewrite|recreate)\b", stripped):
        return "derek", "AD1"
    return None, "AD0"


def resolve_case(case: dict, bundle: dict | None = None) -> dict:
    previous = ((bundle or {}).get("context", {}).get("prev") or {}).get("role")
    base = classify_adversarial_case(case, previous).to_dict()

    # Frozen invariant: v0.4 never expands or reduces the v0.3 D0 set.
    if base["evidence_class"] == "D0":
        return {**base, "resolver": "PROVENANCE_RESOLVER_V0.4", "p0_status": None, "spans": []}

    target = (bundle or {}).get("target") or {}
    text = target.get("text") or case.get("text_excerpt", "")
    origin = (bundle or {}).get("origin_candidate") or {}
    source_reference = origin.get("message_id")
    spans = _split_spans(text, source_reference)
    if spans:
        adopted_by, adoption_status = _adoption(spans[0].text, previous)
        return {
            **base,
            "resolver": "PROVENANCE_RESOLVER_V0.4",
            "evidence_class": "MIXED",
            "authored_by": "mixed",
            "adopted_by": adopted_by,
            "adoption_status": adoption_status,
            "p0_status": "P0-PROBABLE",
            "spans": [asdict(span) for span in spans],
            "requires_review": True,
            "reason": "Carrier and imported body are resolved as separate provenance spans.",
        }

    match_fraction = float(origin.get("matched_frac") or 0.0)
    exact_prior_origin = bool(source_reference and _origin_is_prior(bundle or {}) and match_fraction >= 0.15)
    imported_markers = bool(EXTERNAL_OR_AGENT_MARKERS.search(text))
    traceable_carrier_spans = _split_traceable_carrier(text, source_reference) if exact_prior_origin else []
    if traceable_carrier_spans:
        return {
            **base,
            "resolver": "PROVENANCE_RESOLVER_V0.4",
            "evidence_class": "MIXED",
            "authored_by": "mixed",
            "p0_status": "P0-CERTAIN",
            "spans": [asdict(span) for span in traceable_carrier_spans],
            "requires_review": True,
            "reason": "Traceable reused body is separated from its carrier instruction.",
        }
    if exact_prior_origin:
        tier = "P0-CERTAIN"
        author = "assistant" if exact_prior_origin else "external"
        adopted_by, adoption_status = _adoption(text, previous)
        return {
            **base,
            "resolver": "PROVENANCE_RESOLVER_V0.4",
            "evidence_class": "P0",
            "authored_by": author,
            "adopted_by": adopted_by,
            "adoption_status": adoption_status,
            "p0_status": tier,
            "spans": [asdict(ProvenanceSpan(0, len(text), text, author, "P0", source_reference, tier))],
            "requires_review": tier != "P0-CERTAIN",
            "reason": "Positive imported-content evidence; no Derek authorship inferred.",
        }

    if imported_markers:
        # Artifact markers justify a P0 hypothesis, not a claimed author. Until
        # a traceable source exists, the message-level class stays unresolved.
        return {
            **base,
            "resolver": "PROVENANCE_RESOLVER_V0.4",
            "evidence_class": "UNRESOLVED",
            "authored_by": "unknown",
            "p0_status": "P0-PROBABLE",
            "spans": [],
            "requires_review": True,
            "reason": "Imported-content markers found, but origin is not traceable enough for P0.",
        }

    return {
        **base,
        "resolver": "PROVENANCE_RESOLVER_V0.4",
        "p0_status": "P0-UNRESOLVED" if base["evidence_class"] == "UNRESOLVED" else base.get("p0_status"),
        "spans": [],
    }


def load_bundles(directory: Path) -> dict[str, dict]:
    rows = {}
    for path in sorted(directory.glob("batch_*.jsonl")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["adversarial_id"]] = row
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--bundles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    bundles = load_bundles(args.bundles)
    predictions = {case["adversarial_id"]: resolve_case(case, bundles.get(case["adversarial_id"])) for case in cases}
    args.output.write_text(json.dumps({"resolver": "PROVENANCE_RESOLVER_V0.4", "count": len(predictions), "predictions": predictions}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
