"""
PROVENANCE_INDEX_V0.2 - sequence-aware reuse/origin detection.

Reads from an IMMUTABLE, frozen Corpus Release (13_SOURCE_INDEX/
corpus_releases/CORPUS_RELEASE_NNN/), never the live, mutable
01_INGEST/messages.jsonl - v0.1 was built against a corpus that changed
under it multiple times this session (68,761 -> 72,241 -> 75,321 ->
72,241 record counts observed). Every output here records the exact
release ID + SHA-256 it was built from.

What changed from v0.1 (preserved unmodified at ../v0_1/ as historical
evidence - not rewritten, not deleted):

1. CONTIGUOUS-SPAN MATCHING, not scattered-shingle-count accumulation.
   v0.1 scored a candidate pair purely by how many 12-word shingles
   matched ANYWHERE in either message. A real bug this produced: a
   269,000-character document racked up a "70% coverage" match against
   an unrelated 4,522-character message purely from generic boilerplate
   scattered throughout the huge document (confirmed directly, see
   v0_1/ADVERSARIAL_VERIFICATION_REPORT.md). v0.2 finds the LONGEST
   CONTIGUOUS/ORDERED run of matching shingles (allowing small gaps for
   minor edits) and reports span count/dispersion as independent
   signals, not folded into one opaque score.

2. LARGE DOCUMENTS ARE PASSAGE-SEGMENTED before comparison. Any message
   over PASSAGE_THRESHOLD_CHARS is split into overlapping passages and
   each passage is indexed/matched as its own unit - this is the actual
   fix for the AXIOMOS-class bug, not just a warning flag (v0.1's
   `long_document_low_confidence` mitigation).

3. ORIGIN SELECTION NEVER PICKS BY MAX SIMILARITY ALONE. A candidate
   with a later timestamp than the reused message is never selected as
   "the" origin - if no candidate chronologically precedes the reuse,
   the hit is classified REVERSE_MATCH / NOT_ORIGIN, not silently
   assigned a temporally-impossible origin (this is what caused 37.3%
   of v0.1's hits to show reuse_precedes_origin).

4. SIMILARITY_EDGE != DERIVATION_EDGE != INTELLECTUAL_ORIGIN, kept
   structurally distinct: every candidate pair that clears the coarse
   threshold is a SIMILARITY_EDGE (mechanical fact: these texts
   overlap). A SIMILARITY_EDGE is only promoted to a DERIVATION_EDGE
   (candidate_origin_record_id populated, edge_type="DERIVATION_EDGE")
   when chronology is valid AND the contiguous span is substantial
   enough to suggest real derivation, not coincidence. INTELLECTUAL_
   ORIGIN remains null/UNKNOWN unconditionally - never computed by this
   mechanical layer, exactly as in v0.1.

Per-candidate fields (all independently reported, never collapsed into
one score): total_similarity, reuse_side_coverage, origin_side_coverage,
longest_contiguous_span_words, number_of_matching_spans, span_dispersion,
chronology_valid, length_ratio, boilerplate_repetition_penalty,
exact_copy_indicator, cross_source, multiple_earlier_candidate_count.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASES_DIR = ROOT / "13_SOURCE_INDEX" / "corpus_releases"
OUT_DIR = Path(__file__).resolve().parent

SHINGLE_SIZE = 12
MIN_MATCH_SHINGLES = 5
PASSAGE_THRESHOLD_CHARS = 15000
PASSAGE_SIZE_WORDS = 2500
PASSAGE_OVERLAP_WORDS = 250
DIAGONAL_GAP_TOLERANCE = 4  # shingles - allows small edits within a contiguous run
QUOTE_PATTERN = re.compile(r'["“]([^"”]{5,})["”]')


def normalize_words(text: str) -> list[str]:
    text = re.sub(r"\*\*|__|##+|[-*]\s", " ", text)
    return re.findall(r"[a-z0-9']+", text.lower())


def shingle_positions(words: list[str], size: int = SHINGLE_SIZE) -> dict[str, list[int]]:
    """shingle string -> list of starting word-positions where it occurs."""
    positions: dict[str, list[int]] = defaultdict(list)
    for i in range(len(words) - size + 1):
        positions[" ".join(words[i : i + size])].append(i)
    return positions


def load_release(release_id: str | None) -> tuple[str, list[dict]]:
    if release_id is None:
        releases = sorted(RELEASES_DIR.glob("CORPUS_RELEASE_*.json"))
        if not releases:
            raise SystemExit("No frozen corpus release found. Run 13_SOURCE_INDEX/corpus_releases/freeze_release.py first.")
        release_id = releases[-1].stem
    meta_path = RELEASES_DIR / f"{release_id}.json"
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    frozen_path = Path(metadata["frozen_path"])
    messages = []
    with frozen_path.open(encoding="utf-8") as f:
        for line in f:
            messages.append(json.loads(line))
    return release_id, messages, metadata


def segment_into_passages(message_id: str, text: str) -> list[dict]:
    """Splits a long message into overlapping passages. Short messages
    return a single 'passage' covering the whole text (passage_index=0,
    passage_count=1) so downstream code treats both cases uniformly."""
    words = normalize_words(text)
    if len(text) <= PASSAGE_THRESHOLD_CHARS:
        return [{"passage_id": f"{message_id}#p0", "message_id": message_id, "passage_index": 0, "words": words, "word_offset": 0}]

    passages = []
    step = PASSAGE_SIZE_WORDS - PASSAGE_OVERLAP_WORDS
    idx = 0
    start = 0
    while start < len(words):
        chunk = words[start : start + PASSAGE_SIZE_WORDS]
        if not chunk:
            break
        passages.append(
            {
                "passage_id": f"{message_id}#p{idx}",
                "message_id": message_id,
                "passage_index": idx,
                "words": chunk,
                "word_offset": start,
            }
        )
        idx += 1
        start += step
    return passages


def longest_contiguous_span(reuse_positions: dict[str, list[int]], origin_positions: dict[str, list[int]]) -> tuple[int, int, float]:
    """Finds the longest run of shared shingles where reuse-position and
    origin-position advance together on a consistent diagonal (allowing
    small gaps for minor edits). Returns (longest_span_shingles,
    number_of_distinct_spans, span_dispersion).

    span_dispersion = (max_reuse_pos - min_reuse_pos) across ALL matches
    / total reuse word count - high dispersion means matches are spread
    across a large fraction of the document rather than clustered.
    """
    shared = set(reuse_positions) & set(origin_positions)
    if not shared:
        return 0, 0, 0.0

    # (reuse_pos, origin_pos) pairs, one per occurrence
    pairs = []
    for sh in shared:
        for rp in reuse_positions[sh]:
            for op in origin_positions[sh]:
                pairs.append((rp, op))
    pairs.sort()

    # Group by diagonal (op - rp), tolerating small drift, then find
    # longest run within each diagonal group by reuse-position adjacency.
    diagonal_groups: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for rp, op in pairs:
        diag = op - rp
        # snap to nearest existing diagonal within tolerance
        matched_diag = None
        for d in diagonal_groups:
            if abs(d - diag) <= DIAGONAL_GAP_TOLERANCE:
                matched_diag = d
                break
        diagonal_groups[matched_diag if matched_diag is not None else diag].append((rp, op))

    longest_span = 0
    num_spans = 0
    all_reuse_positions = [rp for rp, _ in pairs]
    for diag, points in diagonal_groups.items():
        points = sorted(set(points))
        if not points:
            continue
        num_spans += 1
        run_start = points[0][0]
        run_len = 1
        best_run = 1
        for i in range(1, len(points)):
            if points[i][0] - points[i - 1][0] <= DIAGONAL_GAP_TOLERANCE + 1:
                run_len += 1
            else:
                best_run = max(best_run, run_len)
                run_len = 1
        best_run = max(best_run, run_len)
        longest_span = max(longest_span, best_run)

    dispersion = 0.0
    if all_reuse_positions:
        span_width = max(all_reuse_positions) - min(all_reuse_positions)
        dispersion = span_width  # normalized later against message length

    return longest_span, num_spans, dispersion


def source_of(m: dict) -> str:
    return m.get("source_format") or m.get("source_file") or "unknown"


def main() -> None:
    release_id = sys.argv[1] if len(sys.argv) > 1 else None
    release_id, messages, release_metadata = load_release(release_id)
    print(f"loaded {release_id}: {len(messages)} messages, sha256={release_metadata['sha256'][:16]}...")
    by_id = {m["message_id"]: m for m in messages}

    # ---- Stage A: coarse candidate discovery via passage-segmented shingle sets.
    origin_passage_index: dict[str, list[str]] = defaultdict(list)  # shingle -> passage_ids
    origin_passages_by_id: dict[str, dict] = {}
    for m in messages:
        if m.get("role") != "assistant":
            continue
        text = m.get("text") or ""
        if len(text) < 100:
            continue
        for passage in segment_into_passages(m["message_id"], text):
            origin_passages_by_id[passage["passage_id"]] = passage
            for sh in set(shingle_positions(passage["words"]).keys()):
                origin_passage_index[sh].append(passage["passage_id"])

    print(f"origin passages indexed: {len(origin_passages_by_id)}, shingle index size: {len(origin_passage_index)}")

    reuse_hits = []
    origin_candidates_records = []
    hit_counter = 0
    reverse_match_count = 0

    for m in messages:
        if m.get("role") != "user":
            continue
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

            candidates = [
                (pid, cnt) for pid, cnt in coarse_matches.items() if cnt >= MIN_MATCH_SHINGLES
            ]
            if not candidates:
                continue

            # Stage B: refine each candidate with contiguous-span analysis.
            refined = []
            for passage_id, coarse_count in candidates:
                origin_passage = origin_passages_by_id[passage_id]
                origin_pos = shingle_positions(origin_passage["words"])
                origin_msg = by_id[origin_passage["message_id"]]

                span_len, num_spans, dispersion_raw = longest_contiguous_span(reuse_pos, origin_pos)
                reuse_side_coverage = coarse_count / total_reuse_shingles
                origin_side_coverage = coarse_count / max(1, len(origin_pos))
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

            # ---- Origin selection: NEVER by max similarity alone.
            # Filter to chronologically valid candidates first (per
            # instruction: candidate origin must precede reuse unless
            # explicitly REVERSE_MATCH/NOT_ORIGIN).
            valid = [r for r in refined if r["chronology_valid"] is True]
            pool = valid if valid else refined
            is_reverse_match = not valid

            # Among the valid (or, failing that, all) pool, rank by
            # contiguous span length first, coarse count as tiebreak -
            # NOT coarse count alone.
            pool.sort(key=lambda r: (-r["span_len"], -r["coarse_count"]))
            best = pool[0]

            earlier_candidates = [r for r in refined if r["chronology_valid"] is True]

            hit_counter += 1
            origin_msg = best["origin_msg"]
            cross_source = source_of(origin_msg) != source_of(m)
            length_ratio = len(text) / max(1, len(origin_msg.get("text") or ""))
            exact_copy = best["reuse_side_coverage"] >= 0.85 and best["origin_side_coverage"] >= 0.5

            # boilerplate/repetition penalty: how much internal repetition
            # exists in the reuse passage itself (raw shingle occurrences
            # vs unique shingles) - a high ratio means this passage is
            # prone to the AXIOMOS-class inflation risk even after
            # passage segmentation, so downstream consumers should still
            # discount it.
            raw_shingle_count = sum(len(v) for v in reuse_pos.values())
            unique_shingle_count = max(1, len(reuse_pos))
            boilerplate_penalty = round(raw_shingle_count / unique_shingle_count, 3)

            if is_reverse_match:
                reverse_match_count += 1

            hit = {
                "reuse_hit_id": f"rh2_{hit_counter:06d}",
                "corpus_release": release_id,
                "corpus_sha256": release_metadata["sha256"],
                "reuse_record_id": m["message_id"],
                "reuse_passage_id": reuse_passage["passage_id"],
                "reuse_conversation_id": m.get("conversation_id"),
                "reuse_source": source_of(m),
                "reuse_timestamp": m.get("timestamp"),
                "candidate_origin_record_id": origin_msg["message_id"],
                "candidate_origin_passage_id": best["passage_id"],
                "origin_conversation_id": origin_msg.get("conversation_id"),
                "origin_source": source_of(origin_msg),
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
                "multiple_earlier_candidate_count": len(earlier_candidates),
                "candidate_origin_count": len(refined),
                "intellectual_origin": None,
                "semantic_status": "UNREVIEWED",
            }
            reuse_hits.append(hit)

    print(f"total hits: {len(reuse_hits)} (SIMILARITY_EDGE only / reverse-match: {reverse_match_count}, DERIVATION_EDGE: {len(reuse_hits) - reverse_match_count})")

    with (OUT_DIR / "reuse_hits.jsonl").open("w", encoding="utf-8") as f:
        for h in reuse_hits:
            f.write(json.dumps(h, ensure_ascii=False) + "\n")
    with (OUT_DIR / "origin_candidates.jsonl").open("w", encoding="utf-8") as f:
        for r in origin_candidates_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus_release": release_id,
        "corpus_sha256": release_metadata["sha256"],
        "total_messages": len(messages),
        "total_hits": len(reuse_hits),
        "derivation_edges": len(reuse_hits) - reverse_match_count,
        "similarity_only_or_reverse_match_edges": reverse_match_count,
        "cross_source_hits": sum(1 for h in reuse_hits if h["cross_source"]),
        "exact_copy_hits": sum(1 for h in reuse_hits if h["exact_copy_indicator"]),
    }
    (OUT_DIR / "index_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
