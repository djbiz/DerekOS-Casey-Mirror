"""Frozen blind adjudication for PROVENANCE_OUT_OF_SAMPLE_SET_V1.

Adjudicated from the evidence bundles ONLY (full target text, prev/next context,
evidence flags, origin candidate). The sealed V0.6 predictions file was NOT
opened during adjudication.

One adjudicator reviewed all 163 records at span level and assigned per-record
labels. Every D0, MIXED, UNRESOLVED, AD3/AD4, and multi-origin record is flagged
requires_review=True for the independent Audit Bot pass. Disagreements must go
to ADJUDICATION_REQUIRED; no silent tie-breaking.

Primary gate: False Derek Attribution = 0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDITS = Path(__file__).resolve().parent
BUNDLES = AUDITS / "out_of_sample_bundles"
OUT = AUDITS / "FROZEN_OUT_OF_SAMPLE_ADJUDICATION_V1.jsonl"

# ---------------------------------------------------------------------------
# Per-record frozen labels.
#
# keys:
#   evidence_class : D0 | P0 | MIXED | UNRESOLVED
#   originator     : derek | assistant | external | mixed | unknown
#   origin_record_id : message_id or UNKNOWN
#   submitted_by   : derek (all records are user-role)
#   adoption_status: AD0-AD4 (only meaningful where adoption can be resolved)
#   pc             : PC0-PC4 provenance confidence
#   requires_review: bool
#   note           : adjudication rationale
# ---------------------------------------------------------------------------
L = {}

def lab(oid, cls, originator, adoption, pc, review, note, origin_id="UNKNOWN"):
    L[oid] = {
        "evidence_class": cls,
        "originator": originator,
        "origin_record_id": origin_id,
        "submitted_by": "derek",
        "adoption_status": adoption,
        "provenance_confidence": pc,
        "requires_review": review,
        "note": note,
    }

# --- Genuine Derek-authored records (short directives, corrections, personal
# --- statements, own operational artifacts). No located origin; conversational
# --- voice + control-act/report structure.
D0 = [
    ("oos_000000", "AD1", "PC2", False, "Derek proposes adding automated personas; builds on assistant frame, own idea"),
    ("oos_000003", "AD0", "PC3", False, "Opening requirement: system of smart AI to run 20 python tools; genuine Derek requirement"),
    ("oos_000005", "AD0", "PC3", False, "Opening observation: Roblox business opportunity; genuine Derek"),
    ("oos_000010", "AD0", "PC3", False, "Opening requirement: VA-replacement python code with AI + integrations; genuine Derek"),
    ("oos_000015", "AD0", "PC3", False, "Opening requirement: GHL funnel automation code; genuine Derek"),
    ("oos_000017", "AD1", "PC2", False, "Derek asks to add acquisition blueprints; own idea on assistant frame"),
    ("oos_000018", "AD1", "PC2", False, "Derek asks to integrate ClickFunnels; own idea"),
    ("oos_000029", "AD3", "PC2", True, "Derek directs: add all recommendations to system (explicit adoption of assistant's offered recommendations)"),
    ("oos_000033", "AD1", "PC3", True, "Derek correction + requirements: system is for Twitter, self-learning, add opt-in dojo"),
    ("oos_000040", "AD1", "PC2", False, "Derek directs: list improvements then add them"),
    ("oos_000041", "AD1", "PC2", False, "Derek proposes business-stacking AI / tax specialist additions; own idea"),
    ("oos_000045", "AD1", "PC3", True, "Derek reports his own Make.com Skool integration in first person; self-authored operational report"),
    ("oos_000050", "AD1", "PC2", False, "Derek requests UI that follows the system"),
    ("oos_000057", "AD1", "PC3", True, "Derek correction: system is for any business, not coffee shops"),
    ("oos_000067", "AD1", "PC2", False, "Derek asks to add Todd Brown E5 method; own idea"),
    ("oos_000111", "AD0", "PC3", False, "Derek personal statement: 'I'm a visionary that sees gaps'"),
    ("oos_000112", "AD0", "PC3", False, "Derek personal statement about AI and wealth"),
    ("oos_000115", "AD1", "PC3", True, "Derek correction: supposed to combine 2 python codes in this chat"),
    ("oos_000120", "AD3", "PC2", True, "Derek directive: add all enhancement and recommendations (adoption)"),
    ("oos_000125", "AD1", "PC2", False, "Derek continuation: create the same system"),
    ("oos_000126", "AD0", "PC3", False, "Opening requirement: combine Meta AI and MCP agentic AI"),
    ("oos_000128", "AD3", "PC2", True, "Derek directive: add all enhancements, full production build (adoption)"),
    ("oos_000135", "AD1", "PC2", False, "Derek directive: put everything together, add recommendation"),
    ("oos_000143", "AD3", "PC2", True, "Derek directive: add all enhancements in complete build (adoption)"),
    ("oos_000147", "AD1", "PC2", False, "Derek directive: put complete system together production-ready"),
    ("oos_000153", "AD1", "PC2", False, "Derek directive: put everything together, add enhancements"),
    ("oos_000155", "AD0", "PC4", False, "Derek's own terminal output (docker compose logs) pasted; self-authored operational artifact"),
    ("oos_000156", "AD0", "PC4", False, "Derek's own terminal output (docker compose logs) pasted; self-authored operational artifact"),
]
for oid, ad, pc, rev, note in D0:
    lab(oid, "D0", "derek", ad, pc, rev, note)

# Directive: every D0 candidate is independently reviewed by Audit Bot.
for oid, *_ in D0:
    L[oid]["requires_review"] = True

# --- MIXED: substantive Derek span + imported assistant body, both contributing
# --- substantive meaning to the resulting message.
MIXED = [
    ("oos_000032", "AD4", "PC2", True,
     "Derek adds substantive requirements (connectivity between python codes, "
     "adapt to Twitter) over pasted assistant body; two independently "
     "attributable substantive spans"),
    ("oos_000110", "AD4", "PC2", True,
     "Derek's substantive requirement (universal, self-evolving, not just "
     "business) over pasted assistant RECURSIVE WORLD MODEL implementation"),
]
for oid, ad, pc, rev, note in MIXED:
    lab(oid, "MIXED", "mixed", ad, pc, rev, note)

# --- P0: pasted/reused content (assistant-authored on another platform, or
# --- external). Carrier phrases do NOT create MIXED; they resolve to P0 +
# --- adoption per MIXED_SEMANTICS_ADJUDICATION_V1.
P0_AD3 = [  # explicit 'add this / use this / build this' with identifiable scope
    "oos_000001", "oos_000007", "oos_000013", "oos_000014", "oos_000019",
    "oos_000020", "oos_000028", "oos_000030", "oos_000031", "oos_000056",
    "oos_000060", "oos_000061", "oos_000070", "oos_000090", "oos_000103",
    "oos_000105", "oos_000113", "oos_000122", "oos_000123", "oos_000132",
    "oos_000133", "oos_000154",
]
for oid in P0_AD3:
    lab(oid, "P0", "assistant", "AD3", "PC3", True,
        "Carrier (add/create this) + pasted assistant body; explicit adoption of identifiable scope")

P0_AD4 = [  # transformation directive over reused material
    "oos_000075", "oos_000118", "oos_000134", "oos_000140", "oos_000141",
    "oos_000142",
]
for oid in P0_AD4:
    lab(oid, "P0", "assistant", "AD4", "PC3", True,
        "Transformation directive (combine/fuse/recreate with X instead) over imported body; AD4")

P0_AD1 = [  # query / weak engagement over pasted material
    "oos_000052", "oos_000106",
]
for oid in P0_AD1:
    lab(oid, "P0", "assistant", "AD1", "PC3", True,
        "Weak carrier (query/here-one) + pasted assistant body; engagement only")

# --- P0: pure pasted assistant/external content, no substantive Derek span.
P0_AD0 = [
    "oos_000002", "oos_000004", "oos_000006", "oos_000008", "oos_000009",
    "oos_000011", "oos_000012", "oos_000016", "oos_000021", "oos_000022",
    "oos_000023", "oos_000024", "oos_000025", "oos_000026", "oos_000027",
    "oos_000034", "oos_000035", "oos_000036", "oos_000037", "oos_000038",
    "oos_000039", "oos_000042", "oos_000043", "oos_000044", "oos_000046",
    "oos_000047", "oos_000048", "oos_000049", "oos_000051", "oos_000053",
    "oos_000054", "oos_000055", "oos_000058", "oos_000059", "oos_000062",
    "oos_000063", "oos_000064", "oos_000065", "oos_000066", "oos_000068",
    "oos_000069", "oos_000071", "oos_000072", "oos_000073", "oos_000074",
    "oos_000076", "oos_000077", "oos_000078", "oos_000079", "oos_000080",
    "oos_000081", "oos_000082", "oos_000083", "oos_000084", "oos_000085",
    "oos_000086", "oos_000087", "oos_000088", "oos_000089", "oos_000091",
    "oos_000092", "oos_000093", "oos_000094", "oos_000095", "oos_000096",
    "oos_000097", "oos_000098", "oos_000099", "oos_000100", "oos_000101",
    "oos_000102", "oos_000104", "oos_000107", "oos_000108", "oos_000109",
    "oos_000114", "oos_000116", "oos_000117", "oos_000119", "oos_000121",
    "oos_000124", "oos_000127", "oos_000129", "oos_000130", "oos_000131",
    "oos_000136", "oos_000137", "oos_000138", "oos_000139", "oos_000144",
    "oos_000145", "oos_000146", "oos_000148", "oos_000149", "oos_000150",
    "oos_000151", "oos_000152", "oos_000157", "oos_000158", "oos_000159",
    "oos_000160", "oos_000161", "oos_000162",
]
for oid in P0_AD0:
    lab(oid, "P0", "assistant", "AD0", "PC3", False,
        "Pure pasted assistant-authored content (cross-platform or same-platform reuse); no Derek span")

# Ambiguous P0 records with plausible multiple origins (product docs, code,
# project status tables) -> requires_review for the independent pass.
AMBIGUOUS_P0 = [
    ("oos_000084", "ResOS++ PRD could be Derek's own product doc OR AI-generated; polished investor-ready structure"),
    ("oos_000150", "motivation_api.py code block: could be Derek's own code OR AI-generated; no origin"),
    ("oos_000157", "VOX migration status table: assistant-style summary, but plausibly Derek's own project notes"),
]
for oid, note in AMBIGUOUS_P0:
    L[oid]["requires_review"] = True
    L[oid]["note"] = note

# --- Sanity: all 163 covered exactly once
with (BUNDLES / "batch_00.jsonl").open(encoding="utf-8-sig") as f:
    pass
all_ids = set()
for p in sorted(BUNDLES.glob("batch_*.jsonl")):
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            all_ids.add(json.loads(line)["oos_id"])
missing = all_ids - set(L)
extra = set(L) - all_ids
print(f"bundles: {len(all_ids)} | labeled: {len(L)} | missing: {sorted(missing)} | extra: {sorted(extra)}")
assert not missing and not extra, "label coverage mismatch"

# --- Write frozen adjudication
with OUT.open("w", encoding="utf-8") as f:
    for oid in sorted(L):
        rec = {"oos_id": oid, **L[oid]}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"wrote {OUT.name}: {len(L)} frozen labels")

# --- Distribution
from collections import Counter
dist = Counter(v["evidence_class"] for v in L.values())
print("class distribution:", dict(dist))
