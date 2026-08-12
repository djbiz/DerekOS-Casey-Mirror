"""
PROVENANCE_INDEX_V0.3 - direction-neutral candidate discovery + multi-actor
chain reconstruction, per PROVENANCE_INDEX_V0.3_DESIGN.md.

Builds on v0.2 (../v0_2/provenance_index_v0_2.py) by IMPORTING its matching
primitives (normalize_words, shingle_positions, segment_into_passages,
longest_contiguous_span, load_release, source_of) rather than copying or
editing them - v0.2's file is untouched, its own reuse_hits.jsonl/
index_report.json are not regenerated or overwritten by this script.

What's different from v0.2 (see design doc for full rationale):

1. DIRECTION-NEUTRAL CANDIDATE DISCOVERY. v0.2 only indexed role=="assistant"
   passages as origins and only checked role=="user" passages for reuse.
   v0.3 indexes EVERY passage (any role, any source) as a candidate origin,
   and checks EVERY passage for reuse. Direction is still decided the same
   way v0.2 already decided it - chronology first (only a strictly earlier
   passage can be an origin), span length breaks ties among chronologically
   valid candidates, never max-similarity-alone. This is additive to v0.2's
   logic, not a replacement of it.

2. DERIVED ACTOR METADATA. messages.jsonl has no field distinguishing a
   ChatGPT-assistant message from a Copilot-assistant message from an
   other-ai-export-assistant message (author_name is null on every record;
   role is only ever user/assistant). actor_of() derives one from
   (role, source_file), read-only, for index purposes only - it is not
   written back to the corpus or promoted to a canonical schema field here.

3. MULTI-HOP CHAIN RECONSTRUCTION. After all pairwise DERIVATION_EDGEs are
   found, edges are grouped into chains wherever one edge's reuse_record_id
   is the next edge's candidate_origin_record_id (a message that is a reuse
   in one edge and an origin in the next). Each chain gets an actor_sequence
   (e.g. ["derek","chatgpt_assistant","derek"]) - a chain's confidence is
   reported as its weakest edge, never averaged into one composite number.

Explicitly NOT computed here (kept as separate layers, per the design's
non-goals): evidence_class, submitted_by, adoption_status (Resolver's job),
integration_strength (a later concept-graph rollup), intellectual_origin
(stays null/UNREVIEWED, exactly as in v0.2 - semantic review only).
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

V03_DIR = Path(__file__).resolve().parent
V02_DIR = V03_DIR.parent / "v0_2"
ROOT = V03_DIR.parents[1]

sys.path.insert(0, str(V02_DIR))
from provenance_index_v0_2 import (  # noqa: E402
    MIN_MATCH_SHINGLES,
    SHINGLE_SIZE,
    load_release,
    longest_contiguous_span,
    segment_into_passages,
    shingle_positions,
    source_of,
)

OUT_DIR = V03_DIR


def actor_of(m: dict) -> str:
    """Derived, read-only actor identity - NOT written back to the corpus.
    See design doc S3.2: author_name is null on every record and role is
    only ever user/assistant, so this is the only way to currently tell
    a ChatGPT-assistant message apart from a Copilot-assistant message."""
    role = m.get("role")
    if role == "user":
        return "derek"
    if role == "assistant":
        sf = m.get("source_file") or ""
        if sf.startswith("copilot"):
            return "copilot_assistant"
        if sf == "conversations.json":
            return "other_ai_assistant"
        if sf.startswith("conversations-"):
            return "chatgpt_assistant"
        return "unknown_assistant"
    return "unknown"


def build_chains(derivation_edges: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Groups pairwise DERIVATION_EDGEs into multi-hop chains wherever one
    edge's reuse_record_id equals the next edge's candidate_origin_record_id.
    Message-level linkage (not passage-level) - matches the design doc's
    stated approach. Returns (chains, hit_id -> chain_id map)."""
    # union-find over message_ids that participate in a derivation edge
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.get(x, x) != x:
            parent[x] = parent.get(parent[x], parent[x])
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in derivation_edges:
        a, b = e["candidate_origin_record_id"], e["reuse_record_id"]
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        union(a, b)

    groups: dict[str, list[dict]] = defaultdict(list)
    for e in derivation_edges:
        root = find(e["reuse_record_id"])
        groups[root].append(e)

    chains = []
    hit_chain_map: dict[str, str] = {}
    chain_counter = 0
    for root, edges in groups.items():
        if len(edges) < 2:
            continue  # not a multi-hop chain, chain_id stays null
        chain_counter += 1
        chain_id = f"chain_{chain_counter:05d}"
        edges_sorted = sorted(edges, key=lambda e: e.get("origin_timestamp") or "")
        actor_sequence = []
        for e in edges_sorted:
            if not actor_sequence:
                actor_sequence.append(e["origin_actor"])
            actor_sequence.append(e["reuse_actor"])
        weakest_span = min(e["longest_contiguous_span_words"] for e in edges_sorted)
        for e in edges_sorted:
            hit_chain_map[e["reuse_hit_id"]] = chain_id
        chains.append(
            {
                "chain_id": chain_id,
                "hop_count": len(edges_sorted),
                "actor_sequence": actor_sequence,
                "weakest_edge_span_words": weakest_span,
                "edge_ids": [e["reuse_hit_id"] for e in edges_sorted],
                "message_sequence": [edges_sorted[0]["candidate_origin_record_id"]] + [e["reuse_record_id"] for e in edges_sorted],
            }
        )
    return chains, hit_chain_map


def main() -> None:
    release_id = sys.argv[1] if len(sys.argv) > 1 else None
    release_id, messages, release_metadata = load_release(release_id)
    print(f"loaded {release_id}: {len(messages)} messages, sha256={release_metadata['sha256'][:16]}...")
    by_id = {m["message_id"]: m for m in messages}

    # ---- Stage A: direction-neutral candidate discovery. EVERY passage
    # (any role, any source) is indexed as a candidate origin - the v0.2
    # role=="assistant" restriction is removed. Direction is decided later,
    # by chronology + span strength, exactly as v0.2 already does it.
    origin_passage_index: dict[str, list[str]] = defaultdict(list)
    origin_passages_by_id: dict[str, dict] = {}
    for m in messages:
        text = m.get("text") or ""
        if len(text) < 100:
            continue
        for passage in segment_into_passages(m["message_id"], text):
            origin_passages_by_id[passage["passage_id"]] = passage
            for sh in set(shingle_positions(passage["words"]).keys()):
                origin_passage_index[sh].append(passage["passage_id"])

    print(f"origin passages indexed (direction-neutral): {len(origin_passages_by_id)}, shingle index size: {len(origin_passage_index)}")

    reuse_hits = []
    origin_candidates_records = []
    hit_counter = 0
    reverse_match_count = 0

    for m in messages:
        text = m.get("text") or ""
        if len(text) < 100:
            continue

        reuse_passages = segment_into_passages(m["message_id"], text)
        for reuse_passage in reuse_passages:
            reuse_pos = shingle_positions(reuse_passage["words"])
            reuse_shingle_set = set(reuse_pos.keys())
            total_reuse_shingles = max(1, len(reuse_shingle_set))

            coarse_matches: dict[str, int] = defaultdict(int)
            for sh in reuse_shingle_set:
                for passage_id in origin_passage_index.get(sh, ()):
                    origin_passage = origin_passages_by_id[passage_id]
                    if origin_passage["message_id"] == m["message_id"]:
                        continue
                    coarse_matches[passage_id] += 1

            candidates = [(pid, cnt) for pid, cnt in coarse_matches.items() if cnt >= MIN_MATCH_SHINGLES]
            if not candidates:
                continue

            refined = []
            for passage_id, coarse_count in candidates:
                origin_passage = origin_passages_by_id[passage_id]
                origin_msg = by_id[origin_passage["message_id"]]

                span_len, num_spans, dispersion_raw = longest_contiguous_span(reuse_pos, shingle_positions(origin_passage["words"]))
                reuse_side_coverage = coarse_count / total_reuse_shingles
                origin_side_coverage = coarse_count / max(1, len(shingle_positions(origin_passage["words"])))
                dispersion = dispersion_raw / max(1, len(reuse_passage["words"]))

                origin_ts = origin_msg.get("timestamp") or ""
                reuse_ts = m.get("timestamp") or ""
                chronology_valid = None
                if origin_ts and reuse_ts and not origin_ts.startswith("UNPARSEABLE") and not reuse_ts.startswith("UNPARSEABLE"):
                    chronology_valid = origin_ts < reuse_ts

                origin_candidates_records.append(
                    {
                        "reuse_record_id": m["message_id"],
                        "reuse_passage_id": reuse_passage["passage_id"],
                        "candidate_origin_record_id": origin_passage["message_id"],
                        "candidate_origin_passage_id": passage_id,
                        "total_similarity": coarse_count,
                        "reuse_side_coverage": round(reuse_side_coverage, 4),
                        "origin_side_coverage": round(origin_side_coverage, 4),
                        "longest_contiguous_span_words": span_len + SHINGLE_SIZE - 1 if span_len else 0,
                        "number_of_matching_spans": num_spans,
                        "span_dispersion": round(dispersion, 4),
                        "chronology_valid": chronology_valid,
                        "origin_timestamp": origin_ts,
                    }
                )
                refined.append(
                    {
                        "passage_id": passage_id,
                        "origin_msg": origin_msg,
                        "origin_passage": origin_passage,
                        "coarse_count": coarse_count,
                        "reuse_side_coverage": reuse_side_coverage,
                        "origin_side_coverage": origin_side_coverage,
                        "span_len": span_len,
                        "num_spans": num_spans,
                        "dispersion": dispersion,
                        "chronology_valid": chronology_valid,
                    }
                )

            # Origin selection: never by max similarity alone. Chronology
            # first, span length breaks ties - identical rule to v0.2,
            # now applied over the larger, direction-neutral candidate pool.
            valid = [r for r in refined if r["chronology_valid"] is True]
            pool = valid if valid else refined
            is_reverse_match = not valid
            pool.sort(key=lambda r: (-r["span_len"], -r["coarse_count"]))
            best = pool[0]
            earlier_candidates = [r for r in refined if r["chronology_valid"] is True]

            hit_counter += 1
            origin_msg = best["origin_msg"]
            cross_source = source_of(origin_msg) != source_of(m)
            length_ratio = len(text) / max(1, len(origin_msg.get("text") or ""))
            exact_copy = best["reuse_side_coverage"] >= 0.85 and best["origin_side_coverage"] >= 0.5

            raw_shingle_count = sum(len(v) for v in reuse_pos.values())
            unique_shingle_count = max(1, len(reuse_pos))
            boilerplate_penalty = round(raw_shingle_count / unique_shingle_count, 3)

            if is_reverse_match:
                reverse_match_count += 1

            hit = {
                "reuse_hit_id": f"rh3_{hit_counter:06d}",
                "corpus_release": release_id,
                "corpus_sha256": release_metadata["sha256"],
                "reuse_record_id": m["message_id"],
                "reuse_passage_id": reuse_passage["passage_id"],
                "reuse_conversation_id": m.get("conversation_id"),
                "reuse_source": source_of(m),
                "reuse_actor": actor_of(m),
                "reuse_timestamp": m.get("timestamp"),
                "candidate_origin_record_id": origin_msg["message_id"],
                "candidate_origin_passage_id": best["passage_id"],
                "origin_conversation_id": origin_msg.get("conversation_id"),
                "origin_source": source_of(origin_msg),
                "origin_actor": actor_of(origin_msg),
                "origin_timestamp": origin_msg.get("timestamp"),
                "edge_type": "SIMILARITY_EDGE" if is_reverse_match else "DERIVATION_EDGE",
                "reverse_match": is_reverse_match,
                "total_similarity": best["coarse_count"],
                "reuse_side_coverage": round(best["reuse_side_coverage"], 4),
                "origin_side_coverage": round(best["origin_side_coverage"], 4),
                "longest_contiguous_span_words": best["span_len"] + SHINGLE_SIZE - 1 if best["span_len"] else 0,
                "number_of_matching_spans": best["num_spans"],
                "span_dispersion": round(best["dispersion"], 4),
                "chronology_valid": best["chronology_valid"],
                "length_ratio": round(length_ratio, 4),
                "boilerplate_repetition_penalty": boilerplate_penalty,
                "exact_copy_indicator": exact_copy,
                "cross_source": cross_source,
                "cross_actor": actor_of(origin_msg) != actor_of(m),
                "multiple_earlier_candidate_count": len(earlier_candidates),
                "candidate_origin_count": len(refined),
                "chain_id": None,  # filled in below, after all edges exist
                "intellectual_origin": None,
                "authorship": None,
                "adoption_status": None,
                "integration_strength": None,
                "semantic_status": "UNREVIEWED",
            }
            reuse_hits.append(hit)

    print(f"total hits: {len(reuse_hits)} (SIMILARITY_EDGE only / reverse-match: {reverse_match_count}, DERIVATION_EDGE: {len(reuse_hits) - reverse_match_count})")

    # ---- Stage C: multi-hop chain reconstruction over DERIVATION_EDGEs only.
    derivation_edges = [h for h in reuse_hits if h["edge_type"] == "DERIVATION_EDGE"]
    chains, hit_chain_map = build_chains(derivation_edges)
    for h in reuse_hits:
        h["chain_id"] = hit_chain_map.get(h["reuse_hit_id"])
    multi_hop_edge_count = sum(1 for cid in hit_chain_map.values() if cid)

    print(f"multi-hop chains reconstructed: {len(chains)} (covering {multi_hop_edge_count} edges)")

    with (OUT_DIR / "reuse_hits.jsonl").open("w", encoding="utf-8") as f:
        for h in reuse_hits:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")
    with (OUT_DIR / "origin_candidates.jsonl").open("w", encoding="utf-8") as f:
        for r in origin_candidates_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with (OUT_DIR / "derivation_chains.jsonl").open("w", encoding="utf-8") as f:
        for c in chains:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    actor_pair_counts: dict[str, int] = defaultdict(int)
    for h in derivation_edges:
        actor_pair_counts[f"{h['origin_actor']}->{h['reuse_actor']}"] += 1

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus_release": release_id,
        "corpus_sha256": release_metadata["sha256"],
        "total_messages": len(messages),
        "total_hits": len(reuse_hits),
        "derivation_edges": len(derivation_edges),
        "similarity_only_or_reverse_match_edges": reverse_match_count,
        "cross_source_hits": sum(1 for h in reuse_hits if h["cross_source"]),
        "cross_actor_hits": sum(1 for h in reuse_hits if h["cross_actor"]),
        "exact_copy_hits": sum(1 for h in reuse_hits if h["exact_copy_indicator"]),
        "multi_hop_chains": len(chains),
        "multi_hop_edges": multi_hop_edge_count,
        "derivation_edge_actor_pair_counts": dict(sorted(actor_pair_counts.items(), key=lambda x: -x[1])),
    }
    (OUT_DIR / "index_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
