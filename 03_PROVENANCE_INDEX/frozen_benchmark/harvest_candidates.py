"""
Harvests genuine candidates for the 13 frozen-benchmark categories from
CORPUS_RELEASE_001. This is a RECALL tool only - every candidate still
requires independent human/agent verification (reading raw text,
checking timestamps/sibling branches) before being accepted into the
benchmark. Using v0.1/v0.2 index output to FIND candidates is fine and
necessary at this corpus scale; what must stay blind is not looking at
what V0.2 CONCLUDED about a case before independently judging it.
"""

import json
import random
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_PATH = ROOT / "13_SOURCE_INDEX" / "corpus_releases" / "CORPUS_RELEASE_001" / "messages.jsonl"
V01_HITS = ROOT / "03_PROVENANCE_INDEX" / "v0_1" / "reuse_hits.jsonl"
V02_HITS = ROOT / "03_PROVENANCE_INDEX" / "v0_2" / "reuse_hits.jsonl"
OUT_DIR = Path(__file__).resolve().parent

random.seed(20260812)  # deterministic sampling, not Date.now()-style randomness


def load_messages():
    messages = {}
    with RELEASE_PATH.open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            messages[m["message_id"] + "|" + m["conversation_id"]] = m
    return messages


def main():
    messages = load_messages()
    by_id_list = defaultdict(list)
    for key, m in messages.items():
        by_id_list[m["message_id"]].append(m)

    v01 = [json.loads(l) for l in V01_HITS.open(encoding="utf-8")]
    v02 = [json.loads(l) for l in V02_HITS.open(encoding="utf-8")]

    candidates = {}

    # 1/2: exact cross-conversation / cross-platform reuse (from v0.2 DERIVATION_EDGE, high coverage)
    exact = [h for h in v02 if h.get("edge_type") == "DERIVATION_EDGE" and h["reuse_side_coverage"] >= 0.85]
    candidates["exact_cross_conversation"] = [h for h in exact if not h["cross_source"] and h["reuse_conversation_id"] != h["origin_conversation_id"]][:60]
    candidates["exact_cross_platform"] = [h for h in exact if h["cross_source"]][:60]

    # 3: partial reuse
    candidates["partial_reuse"] = [h for h in v02 if h.get("edge_type") == "DERIVATION_EDGE" and 0.2 <= h["reuse_side_coverage"] < 0.6][:60]

    # 4: heavily edited reuse (moderate coverage, real span, not exact)
    candidates["heavily_edited"] = [h for h in v02 if h.get("edge_type") == "DERIVATION_EDGE" and 0.15 <= h["reuse_side_coverage"] < 0.4 and h["longest_contiguous_span_words"] > 30][:60]

    # 6: long documents with scattered generic overlap (the AXIOMOS-class case)
    candidates["long_doc_scattered"] = [h for h in v01 if h.get("long_document_low_confidence")][:60]

    # 7: reverse-chronology matches
    candidates["reverse_chronology"] = [h for h in v02 if h.get("reverse_match")][:60]

    # 8: multiple possible earlier sources
    candidates["multiple_earlier_sources"] = [h for h in v02 if h.get("multiple_earlier_candidate_count", 0) >= 3][:60]

    # 10: chains (assistant -> Derek -> assistant, from v0.1 chains)
    chains_path = ROOT / "03_PROVENANCE_INDEX" / "v0_1" / "reuse_chains.jsonl"
    chains = [json.loads(l) for l in chains_path.open(encoding="utf-8")] if chains_path.exists() else []
    candidates["reuse_chains"] = chains[:40]

    for k, v in candidates.items():
        print(f"{k}: {len(v)} candidates available")

    (OUT_DIR / "harvested_candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote harvested_candidates.json")


if __name__ == "__main__":
    main()
