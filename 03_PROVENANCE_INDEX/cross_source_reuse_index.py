"""
03_PROVENANCE_INDEX — cross-source reuse index builder.

Promoted from 14_TESTS_AUDITS/cross_source_reuse_index.py (preserved there
unmodified as historical evidence of the first pass, per instruction not
to move-and-erase prior audit artifacts). This version:
  - tracks ALL candidate origins per reused message, not just the
    strongest one (needed to detect multiple-plausible-origin cases)
  - computes the full extended schema (see README.md)
  - explicitly separates `earliest_corpus_occurrence` (a mechanical fact:
    which candidate has the earliest timestamp) from `intellectual_origin`
    (always null here, semantic_status always UNREVIEWED - this script
    makes zero authorship/origin claims, only mechanical observations)
  - builds reuse_chains.jsonl by graph-linking hits where a reused
    message is itself later reused elsewhere

CRITICAL: similarity is not authorship proof. Every record in
reuse_hits.jsonl carries semantic_status="UNREVIEWED" and
intellectual_origin=null unconditionally. Nothing in this script
concludes who originated anything - it only observes text overlap,
timestamps, and source metadata mechanically. A human/agent verification
pass (see index_report.json's adversarial sample) is required before any
hit here may inform a D0/A0/P0 classification.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST_DIR = ROOT / "01_INGEST"
OUT_DIR = Path(__file__).resolve().parent
SHINGLE_SIZE = 12
MIN_MATCH_SHINGLES = 5

QUOTE_PATTERN = re.compile(r'["“]([^"”]{5,})["”]')


def normalize_words(text: str) -> list[str]:
    text = re.sub(r"\*\*|__|##+|[-*]\s", " ", text)
    return re.findall(r"[a-z0-9']+", text.lower())


def shingles(words: list[str], size: int = SHINGLE_SIZE):
    for i in range(len(words) - size + 1):
        yield " ".join(words[i : i + size])


def source_of(m: dict) -> str:
    return m.get("source_format") or m.get("source_file") or "unknown"


def classify_overlap(coverage: float) -> str:
    if coverage >= 0.8:
        return "exact"
    if coverage >= 0.35:
        return "near"
    return "partial"


def transformation_distance(coverage: float) -> str:
    # Rough mechanical proxy only - NOT a semantic judgment. See README.md.
    if coverage >= 0.9:
        return "TD0"
    if coverage >= 0.7:
        return "TD1"
    if coverage >= 0.5:
        return "TD2"
    if coverage >= 0.3:
        return "TD3"
    if coverage >= 0.15:
        return "TD4"
    return "TD5"


def provenance_confidence(coverage: float, quoted_fraction: float, cross_source: bool) -> str:
    if quoted_fraction >= 0.7:
        return "PC1"  # confined to a quoted title/label - weak, see resolver v0.2 finding
    if coverage >= 0.8:
        return "PC4"
    if coverage >= 0.5:
        return "PC3"
    if coverage >= 0.25:
        return "PC2"
    return "PC1"


def main() -> None:
    messages = []
    with (INGEST_DIR / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            messages.append(json.loads(line))
    by_id = {m["message_id"]: m for m in messages}

    print(f"total messages: {len(messages)}")
    source_counts: dict[str, int] = defaultdict(int)
    for m in messages:
        source_counts[source_of(m)] += 1

    # Source registry
    source_registry = []
    for src, count in sorted(source_counts.items()):
        source_registry.append(
            {
                "source": src,
                "message_count": count,
                "role_counts": {
                    "user": sum(1 for m in messages if source_of(m) == src and m.get("role") == "user"),
                    "assistant": sum(1 for m in messages if source_of(m) == src and m.get("role") == "assistant"),
                },
            }
        )
    (OUT_DIR / "source_registry.json").write_text(
        json.dumps(
            {"generated_at": None, "sources": source_registry, "total_messages": len(messages)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote source_registry.json ({len(source_registry)} sources)")

    # Build shingle index over EVERY assistant-role message, across sources.
    #
    # BUG FIX (found during adversarial verification, before any manual
    # spot-check ran): shingles() yields a message's OWN internally-
    # repeated 12-word phrases multiple times (e.g. a 269,000-character
    # pasted document full of repeated code/template boilerplate). Using
    # a list here let one shared generic phrase between a huge message
    # and an unrelated short one multiply into thousands of spurious
    # "matches" purely from internal repetition - confirmed directly:
    # one hit (rh_003979) had normalized_overlap_length=1.1161, a
    # coverage ratio above 1.0, which is only possible if matches were
    # being double-counted. Deduplicating to a set per message (both
    # sides) means a given 12-word phrase counts at most once toward
    # match strength between any two messages, regardless of how many
    # times either one repeats it internally.
    origin_index: dict[str, set[str]] = defaultdict(set)
    for m in messages:
        if m.get("role") != "assistant":
            continue
        text = m.get("text") or ""
        if len(text) < 100:
            continue
        words = normalize_words(text)
        for sh in set(shingles(words)):
            origin_index[sh].add(m["message_id"])

    print(f"assistant shingle index size: {len(origin_index)}")

    reuse_hits = []
    origin_candidates_records = []
    hit_counter = 0

    for m in messages:
        if m.get("role") != "user":
            continue
        text = m.get("text") or ""
        if len(text) < 100:
            continue
        words = normalize_words(text)
        # Deduplicated - see bug-fix note above the origin_index build.
        # normalized_overlap_length is now guaranteed <= 1.0.
        reuse_shingles = set(shingles(words))
        total_reuse_shingles = max(1, len(reuse_shingles))

        match_counts: dict[str, int] = defaultdict(int)
        for sh in reuse_shingles:
            for origin_msg_id in origin_index.get(sh, ()):
                if origin_msg_id == m["message_id"]:
                    continue
                match_counts[origin_msg_id] += 1

        candidates = [
            (origin_id, count) for origin_id, count in match_counts.items() if count >= MIN_MATCH_SHINGLES
        ]
        if not candidates:
            continue
        candidates.sort(key=lambda kv: -kv[1])

        # quoted-span discount (resolver v0.2 finding, reused here)
        quoted_shingles = set()
        for quoted_span in QUOTE_PATTERN.findall(text):
            quoted_shingles.update(shingles(normalize_words(quoted_span)))

        # record every candidate for multi-origin detection
        for origin_id, count in candidates:
            origin_msg = by_id.get(origin_id)
            origin_candidates_records.append(
                {
                    "reuse_record_id": m["message_id"],
                    "candidate_origin_record_id": origin_id,
                    "matching_shingle_count": count,
                    "origin_source": source_of(origin_msg) if origin_msg else None,
                    "origin_timestamp": origin_msg.get("timestamp") if origin_msg else None,
                }
            )

        best_origin_id, best_count = candidates[0]
        origin_msg = by_id.get(best_origin_id)
        if origin_msg is None:
            continue

        coverage = best_count / total_reuse_shingles
        quoted_overlap = len(set(reuse_shingles) & quoted_shingles)
        quoted_fraction = quoted_overlap / max(1, best_count) if best_count else 0.0

        reuse_ts = m.get("timestamp") or ""
        origin_ts = origin_msg.get("timestamp") or ""
        origin_precedes_reuse = None
        temporal_direction = "unknown"
        if reuse_ts and origin_ts and not reuse_ts.startswith("UNPARSEABLE") and not origin_ts.startswith("UNPARSEABLE"):
            if origin_ts < reuse_ts:
                origin_precedes_reuse = True
                temporal_direction = "origin_precedes_reuse"
            elif origin_ts > reuse_ts:
                origin_precedes_reuse = False
                temporal_direction = "reuse_precedes_origin"
            else:
                origin_precedes_reuse = None
                temporal_direction = "same_timestamp"

        # earliest_corpus_occurrence: among ALL candidates for this reuse,
        # which has the earliest timestamp - a mechanical fact, not a claim
        # about who actually originated the idea.
        all_candidate_ts = [
            (cid, by_id[cid].get("timestamp"))
            for cid, _ in candidates
            if cid in by_id and by_id[cid].get("timestamp") and not by_id[cid]["timestamp"].startswith("UNPARSEABLE")
        ]
        earliest = min(all_candidate_ts, key=lambda kv: kv[1]) if all_candidate_ts else (None, None)

        hit_counter += 1
        cross_source = source_of(origin_msg) != source_of(m)
        hit = {
            "reuse_hit_id": f"rh_{hit_counter:06d}",
            "reuse_record_id": m["message_id"],
            "reuse_conversation_id": m.get("conversation_id"),
            "reuse_source": source_of(m),
            "reuse_author_role": m.get("role"),
            "reuse_timestamp": m.get("timestamp"),
            "candidate_origin_record_id": best_origin_id,
            "origin_conversation_id": origin_msg.get("conversation_id"),
            "origin_source": source_of(origin_msg),
            "origin_author_role": origin_msg.get("role"),
            "origin_timestamp": origin_msg.get("timestamp"),
            "similarity_method": f"shingle_overlap_{SHINGLE_SIZE}word",
            "similarity_score": best_count,
            "normalized_overlap_length": round(coverage, 4),
            "match_classification": classify_overlap(coverage),
            "temporal_direction": temporal_direction,
            "origin_precedes_reuse": origin_precedes_reuse,
            "cross_source": cross_source,
            "matched_span_mostly_quoted": quoted_fraction >= 0.7,
            "provenance_confidence": provenance_confidence(coverage, quoted_fraction, cross_source),
            "transformation_distance": transformation_distance(coverage),
            "multiple_origin_candidates": len(candidates) > 1,
            "candidate_origin_count": len(candidates),
            "earliest_corpus_occurrence": {
                "message_id": earliest[0],
                "timestamp": earliest[1],
            },
            # KNOWN LIMITATION, found during adversarial verification and
            # NOT fully fixed here (see README.md): coverage is computed
            # from scattered shingle overlap across the whole message, not
            # contiguous matching runs. A very long pasted document (e.g.
            # a 269,000-character system-config dump) can accumulate a
            # high coverage percentage against an unrelated short message
            # purely from generic boilerplate scattered throughout it -
            # confirmed directly on a real case (rh_003979 pre-fix).
            # Flagging rather than silently trusting scores on long
            # messages until a contiguous-run-based method replaces this.
            "long_document_low_confidence": len(text) > 15000 or len(origin_msg.get("text") or "") > 15000,
            # Deliberately unresolved at this mechanical stage - see module
            # docstring. Never inferred here.
            "intellectual_origin": None,
            "semantic_status": "UNREVIEWED",
        }
        reuse_hits.append(hit)

    print(f"total reuse hits: {len(reuse_hits)}")
    cross_source_hits = [h for h in reuse_hits if h["cross_source"]]
    multi_origin_hits = [h for h in reuse_hits if h["multiple_origin_candidates"]]
    print(f"cross-source hits: {len(cross_source_hits)}")
    print(f"multi-origin-candidate hits: {len(multi_origin_hits)}")

    with (OUT_DIR / "reuse_hits.jsonl").open("w", encoding="utf-8") as f:
        for h in reuse_hits:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")
    print(f"wrote reuse_hits.jsonl ({len(reuse_hits)} records)")

    with (OUT_DIR / "origin_candidates.jsonl").open("w", encoding="utf-8") as f:
        for r in origin_candidates_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote origin_candidates.jsonl ({len(origin_candidates_records)} records)")

    # ---- reuse chains: link hits where a reused message is ITSELF later
    # reused elsewhere, or where the origin was itself a reuse of
    # something earlier. Build a directed graph and extract chains.
    hit_by_reuse_id = {h["reuse_record_id"]: h for h in reuse_hits}
    # message_id -> hit where it is the ORIGIN of some other hit
    origin_to_hits: dict[str, list[dict]] = defaultdict(list)
    for h in reuse_hits:
        origin_to_hits[h["candidate_origin_record_id"]].append(h)

    chains = []
    chain_counter = 0
    visited_as_non_root = set()
    for h in reuse_hits:
        if h["reuse_record_id"] in visited_as_non_root:
            continue
        # walk forward: does this reuse message later become an origin for something else?
        chain_nodes = [h["candidate_origin_record_id"], h["reuse_record_id"]]
        current = h["reuse_record_id"]
        steps = 0
        while current in origin_to_hits and steps < 10:
            next_hits = origin_to_hits[current]
            next_hit = next_hits[0]  # take strongest/first if multiple
            if next_hit["reuse_record_id"] in chain_nodes:
                break  # cycle guard
            chain_nodes.append(next_hit["reuse_record_id"])
            visited_as_non_root.add(next_hit["reuse_record_id"])
            current = next_hit["reuse_record_id"]
            steps += 1
        if len(chain_nodes) >= 3:  # only record genuine multi-hop chains
            chain_counter += 1
            chains.append(
                {
                    "chain_id": f"chain_{chain_counter:05d}",
                    "length": len(chain_nodes),
                    "message_id_sequence": chain_nodes,
                    "source_sequence": [
                        source_of(by_id[mid]) for mid in chain_nodes if mid in by_id
                    ],
                }
            )

    with (OUT_DIR / "reuse_chains.jsonl").open("w", encoding="utf-8") as f:
        for c in chains:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"wrote reuse_chains.jsonl ({len(chains)} multi-hop chains, length>=3)")

    # ---- index report
    match_class_counts = defaultdict(int)
    td_counts = defaultdict(int)
    pc_counts = defaultdict(int)
    for h in reuse_hits:
        match_class_counts[h["match_classification"]] += 1
        td_counts[h["transformation_distance"]] += 1
        pc_counts[h["provenance_confidence"]] += 1

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_messages_indexed": len(messages),
        "sources": dict(source_counts),
        "total_reuse_hits": len(reuse_hits),
        "cross_source_hits": len(cross_source_hits),
        "multi_origin_candidate_hits": len(multi_origin_hits),
        "multi_hop_chains": len(chains),
        "longest_chain_length": max((c["length"] for c in chains), default=0),
        "match_classification_distribution": dict(match_class_counts),
        "transformation_distance_distribution": dict(td_counts),
        "provenance_confidence_distribution": dict(pc_counts),
        "semantic_status": "ALL records UNREVIEWED - see adversarial verification sample for spot-checked subset",
        "predecessor_artifacts_preserved": [
            "14_TESTS_AUDITS/find_reused_passages.py",
            "14_TESTS_AUDITS/reused_passages_candidates.json (provenance_resolver_v0_1)",
            "14_TESTS_AUDITS/check_copilot_overlap.py",
            "14_TESTS_AUDITS/copilot_chatgpt_overlap.json",
            "14_TESTS_AUDITS/cross_source_reuse_index.py (first pass, pair-only, no chains)",
            "14_TESTS_AUDITS/cross_source_reuse_index.json (first pass output)",
        ],
    }
    (OUT_DIR / "index_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote index_report.json")


if __name__ == "__main__":
    main()
