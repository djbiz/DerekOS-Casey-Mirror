"""
Builds PROVENANCE_INDEX_V0.3_BENCHMARK_TRANCHE_1 - a small, separate,
genuinely-verified case set targeting exactly what V0.2 structurally could
not represent (direction-neutral / multi-actor / cross-platform derivation),
per the Architecture Board's instruction to build additional benchmark cases
SEPARATELY from the frozen 30 and freeze them BEFORE evaluating V0.3 against
them.

Every case here was found by direct 8-gram shingle comparison and manual
text/timestamp reading against CORPUS_RELEASE_001 - NOT by reading V0.3's
conclusions (V0.3 had not finished its corpus run when this file was
written). Same blindness discipline as frozen_benchmark_cases.jsonl.

Honest scope: 6 cases, not a large tranche. Each one is real and precisely
verified (exact 8-gram overlap counts computed directly, shown in the notes)
rather than manufactured to hit a round number - same reasoning the 30-case
V0.2 benchmark and the original 40-case Gold Set already established.
"""

import json
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

cases = []


def add(case_id, category, reuse_id, reuse_conv, origin_id, origin_conv, similar, derived, earlier_in_corpus, true_origin, intellectual_origin, note):
    cases.append({
        "case_id": case_id,
        "category": category,
        "reuse_record_id": reuse_id,
        "reuse_conversation_id": reuse_conv,
        "candidate_origin_record_id": origin_id,
        "candidate_origin_conversation_id": origin_conv,
        "ground_truth": {
            "similar": similar,
            "derived_from_candidate": derived,
            "earlier_in_corpus": earlier_in_corpus,
            "true_corpus_origin": true_origin,
            "intellectual_origin": intellectual_origin,
        },
        "note": note,
    })


# ---- fbv3_001: THE key case. Origin is a role=="user" message (Derek's
# turn in the other-ai-export platform); reuse is a role=="assistant"
# message (Copilot). V0.2 cannot represent this direction at all - its
# origin index only ever contains role=="assistant" passages. Verified
# directly: 1099/1178 (93.3%) of the Copilot message's 8-gram shingles are
# covered by the earlier other-ai-export message, ~4h45m before it.
add("fbv3_001", "cross_platform_reverse_direction",
    "copilot_msg_b40e6910c34d07e4d87c14f820815983", "copilot_conv_df9ae3d4ab3cacbff35dc2ee637b939b",
    "1", "ed506c9c-9844-4e50-bf9e-4d2e1924b24a",
    True, "YES", "YES", "YES", "UNRESOLVED",
    "'Todd Brown AI Business-Building System' thread. The candidate origin (message_id '1', conversations.json/other-ai-export, role=user, 2026-01-19T23:02:48) opens 'Derek, this is exactly the kind of thing you and I do best together...' - clearly AI-authored voice despite being tagged role=user (this is Derek submitting AI-generated content as his own turn, a genuine P0 pattern, not a role-mislabeling bug - confirmed by reading the immediately-following role=assistant reply in the same conversation, which responds appropriately to it as Derek's submission). 93.3% of the later Copilot assistant message's shingles are covered by this earlier message - a near-exact copy, chronologically valid, cross-platform, and in the exact direction (user-role origin -> assistant-role reuse) V0.2's assistant-only origin index cannot see. intellectual_origin is marked UNRESOLVED, not 'derek' or 'assistant': I searched the full corpus for this exact opening phrase and found no earlier occurrence anywhere - genuine abstention per spec S6.0a ('no match found must NOT default to D0'), not a forced guess.")

# ---- fbv3_002: multiple near-duplicate origin candidates for the same
# reuse, both role=user, one minute apart, same conversation.
add("fbv3_002", "multiple_earlier_sources_same_conversation",
    "copilot_msg_b40e6910c34d07e4d87c14f820815983", "copilot_conv_df9ae3d4ab3cacbff35dc2ee637b939b",
    "3", "ed506c9c-9844-4e50-bf9e-4d2e1924b24a",
    True, "YES", "YES", "YES", "UNRESOLVED",
    "Same reuse message as fbv3_001. Message_id '3' in the same other-ai-export conversation is a near-duplicate of message_id '1' (same opening text), sent 1 minute later (23:03:48 vs 23:02:48). Both are chronologically valid, near-identical-strength candidates for the same later Copilot reuse - a genuine multiple-plausible-origin case, distinct from fbv3_001 only in which of the two duplicate submissions is picked as 'the' origin. A correct implementation should be able to pick either (they're near-identical) without being confused by having two valid candidates instead of one.")

# ---- fbv3_003 / fbv3_004: chain continuation, same-platform, cross-
# conversation - the reuse of fbv3_001's Copilot output into two later,
# separate Copilot conversations. V0.2-coverable in principle (assistant
# origin -> user reuse), included for chain completeness.
add("fbv3_003", "reuse_chain_multi_hop",
    "copilot_msg_daa986757d57a8aa8ea1ecd78f682ee9", "copilot_conv_29a1a2ab42302b97e278a37455ebd8b9",
    "copilot_msg_b40e6910c34d07e4d87c14f820815983", "copilot_conv_df9ae3d4ab3cacbff35dc2ee637b939b",
    True, "YES", "YES", "YES", "UNRESOLVED",
    "Chain continuation from fbv3_001. Derek carries the Copilot assistant's output (copilot_msg_b40e6910) into a NEW, separate Copilot conversation ~12 minutes later, asking for a 'Russell Bronson' variant. Verified: 884/899 (98.3%) shingle coverage - near-exact copy. Third hop of a real, verified multi-actor chain: other-ai-user -> copilot-assistant -> copilot-user (this hop) and copilot-user (fbv3_004, parallel branch, not sequential to this one).")
add("fbv3_004", "reuse_chain_multi_hop",
    "copilot_msg_2d0ea3addac1567ca4f374353246d86b", "copilot_conv_9ed50fbef4bfa0dbb96778a805d1a764",
    "copilot_msg_b40e6910c34d07e4d87c14f820815983", "copilot_conv_df9ae3d4ab3cacbff35dc2ee637b939b",
    True, "YES", "YES", "YES", "UNRESOLVED",
    "Parallel branch to fbv3_003 - same origin (copilot_msg_b40e6910), reused again ~8.5 hours later in a THIRD, separate Copilot conversation, asking for a 'Max Steingart' variant this time. Verified: 884/899 (98.3%) shingle coverage, identical strength to fbv3_003. Together, fbv3_001/003/004 form one real branching chain spanning 3 platforms (ChatGPT-adjacent 'other-ai-export' -> Copilot -> Copilot x2) and 3 actors (derek, other_ai-carried content, copilot_assistant), fully timestamp-verified across ~9.5 hours.")

# ---- fbv3_005: cross-platform assistant-voice convergence noise,
# identified during design-doc grounding (S4a). Weak (1-shingle) overlap
# only - should NOT be flagged as derivation.
add("fbv3_005", "cross_actor_voice_convergence_control",
    "746d390d-c845-44de-a6f1-45f1b7a8f204", "6929a5e9-4a28-832a-a0b3-bc4ea8fdbc54",
    None, None,
    False, "NO", "N/A", "N/A", "N/A",
    "ChatGPT assistant message (2025-11-28) opens 'Yeah, Derek — this is exactly the kind of thing Agent-style systems are built for.' This shares only ONE 8-gram shingle ('derek this is exactly the kind of thing') with the unrelated Copilot phrase family in fbv3_001-004 - a stock flattering-assistant-voice pattern both platforms converge on independently, not evidence of text transmission. Negative control: direction-neutral discovery must not treat single-shingle stock-phrase overlap as similarity.")

# ---- fbv3_006: message-scale scattered-generic-match noise, identified
# during design-doc grounding (S4a) - the AXIOMOS failure mode recurring
# at normal message length instead of giant-document length.
add("fbv3_006", "scattered_generic_overlap_control",
    "copilot_msg_389c140cc897c110d629874d032a59bd", "copilot_conv_9ed50fbef4bfa0dbb96778a805d1a764",
    None, None,
    False, "NO", "N/A", "N/A", "N/A",
    "Copilot assistant message (9,804 chars) superficially appeared to share content with '62 other-platform messages' under a naive shared-shingle-count. Direct verification: no single other-platform message shares more than 5 of its 8-gram shingles with it - the 62 is 62 different messages each sharing exactly one generic phrase (assistant boilerplate). Negative control for the contiguous-span requirement: a real implementation must not report this as 62 candidate matches or promote any of them to SIMILARITY_EDGE, let alone DERIVATION_EDGE.")

with (OUT_DIR / "frozen_benchmark_v0_3_cases.jsonl").open("w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

print(f"wrote {len(cases)} genuinely-verified V0.3 tranche cases")
