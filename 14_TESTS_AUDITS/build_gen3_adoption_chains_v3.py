import json, os, sys, re
from pathlib import Path
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parent.parent
CHATGPT_DIR = ROOT / '00_RAW_ARCHIVE' / 'chatgpt'
OUT_PATH = ROOT / '08_MASTER_PLAN' / 'reconstruction_pilots' / 'conglomerate' / 'GEN3_ADOPTION_CHAINS_V0.1.json'

PROPOSITIONS = [
    {"id":"GEN3-001","claim":"At the trillion-dollar level, you do not manage companies; you manage HoldCos (Holding Companies).","keywords":["manage HoldCos","trillion-dollar level, you do not manage companies"],"origin_conv":"6956279f-2074-8330-b7f7-8872615e4846","origin_node":"32b9bf3e-6750-4c45-9ae7-83ea76f6d361","origin_title":"Scaling Daycare Centers","ts":1767253973.522136},
    {"id":"GEN3-002","claim":"Your primary SOP is the Capital Allocation Manifesto.","keywords":["Capital Allocation Manifesto"],"origin_conv":"6956279f-2074-8330-b7f7-8872615e4846","origin_node":"32b9bf3e-6750-4c45-9ae7-83ea76f6d361","origin_title":"Scaling Daycare Centers","ts":1767253973.522136},
    {"id":"GEN3-003","claim":"Founder Role: You are the 'Banker-in-Chief.' You don't fix their marketing; you decide if they deserve more capital or if that capital should move to a high-growth sector.","keywords":["Banker-in-Chief","deserve more capital"],"origin_conv":"6956279f-2074-8330-b7f7-8872615e4846","origin_node":"32b9bf3e-6750-4c45-9ae7-83ea76f6d361","origin_title":"Scaling Daycare Centers","ts":1767253973.522136},
    {"id":"GEN3-004","claim":"Establish a 'Hurdle Rate' (e.g., 15% ROIC). Any business unit failing to meet this for three consecutive quarters is flagged for restructuring or divestiture.","keywords":["Hurdle Rate","15% ROIC","three consecutive quarters"],"origin_conv":"695742ba-f824-8332-bad1-44e8ca02657b","origin_node":"6971-line","origin_title":"Conglomerate Governance Framework","ts":1767257174},
    {"id":"GEN3-005","claim":"Monthly Capital Deployment Meetings where CEOs of subsidiaries pitch for budget as if they were external startups.","keywords":["Monthly Capital Deployment Meetings","external startups"],"origin_conv":"695742ba-f824-8332-bad1-44e8ca02657b","origin_node":"6971-line","origin_title":"Conglomerate Governance Framework","ts":1767257174},
    {"id":"GEN3-006","claim":"Every subsidiary CEO must submit a single page containing: Revenue, EBITDA, Free Cash Flow, Critical Risk, Synergy Variable.","keywords":["single page containing","Synergy Variable"],"origin_conv":"695742ba-f824-8332-bad1-44e8ca02657b","origin_node":"6971-line","origin_title":"Conglomerate Governance Framework","ts":1767257174},
    {"id":"GEN3-007","claim":"No subsidiary CEO is allowed to operate without two 'Ready-Now' successors identified.","keywords":["Ready-Now successors"],"origin_conv":"695742ba-f824-8332-bad1-44e8ca02657b","origin_node":"6971-line","origin_title":"Conglomerate Governance Framework","ts":1767257174},
    {"id":"GEN3-008","claim":"Implement a Conglomerate Leadership Rotational Program. Move high-potential leaders from your tech arm to your manufacturing arm to build 'horizontal' thinkers.","keywords":["Leadership Rotational Program","horizontal thinkers"],"origin_conv":"695742ba-f824-8332-bad1-44e8ca02657b","origin_node":"6971-line","origin_title":"Conglomerate Governance Framework","ts":1767257174},
    {"id":"GEN3-009","claim":"ESC is not a company. ESC is a system operator. It stabilizes systems quietly, permanently, and at scale.","keywords":["ESC is not a company","system operator"],"origin_conv":"69569536-7908-832d-aea4-7834a2d130ee","origin_node":"4158-line","origin_title":"Global Stability Division HQ","ts":1767264068},
    {"id":"GEN3-010","claim":"ESC Global Core responsibilities: Capital allocation, Risk modeling, Global priority setting, Ops AI Core, Governance & incentives.","keywords":["Ops AI Core","Global priority setting"],"origin_conv":"69569536-7908-832d-aea4-7834a2d130ee","origin_node":"4158-line","origin_title":"Global Stability Division HQ","ts":1767264068},
    {"id":"GEN3-011","claim":"ESC Regional Stability Anchors (RSAs) are the execution arms. Each RSA is: Self-sufficient, Operational, Capitalized, Auditable, Replaceable.","keywords":["Regional Stability Anchors","Auditable, Replaceable"],"origin_conv":"69569536-7908-832d-aea4-7834a2d130ee","origin_node":"4158-line","origin_title":"Global Stability Division HQ","ts":1767264068},
    {"id":"GEN3-012","claim":"Africa remains Anchor #1. Other regions replicate when deployed.","keywords":["Africa remains Anchor #1","replicate when deployed"],"origin_conv":"69569536-7908-832d-aea4-7834a2d130ee","origin_node":"4158-line","origin_title":"Global Stability Division HQ","ts":1767264068},
    {"id":"GEN3-013","claim":"Standard RSA Stack: Command + Ops Floor, Infrastructure Labs, Asset & Conversion Cell, Talent & Ownership Engine, Logistics Spine.","keywords":["Standard RSA Stack","Logistics Spine"],"origin_conv":"69569536-7908-832d-aea4-7834a2d130ee","origin_node":"4158-line","origin_title":"Global Stability Division HQ","ts":1767264068},
    {"id":"GEN3-014","claim":"You do not deploy as a person. You create a multi-layer institutional structure: Parent Entity + 6 Independent Capital Arms.","keywords":["6 Independent Capital Arms","multi-layer institutional structure"],"origin_conv":"695643ed-a2d8-832f-81ec-f2bb22ffb106","origin_node":"2359-line","origin_title":"Business Scale & CPAs","ts":1767261189.906875},
    {"id":"GEN3-015","claim":"The 6 Independent Capital Arms: Infrastructure & Concessions, Real Assets & Land Control, Platforms & Mandatory Systems, Supply Chain & Logistics, Utilities/Energy/Environmental, Financial Plumbing & Payments.","keywords":["Financial Plumbing & Payments","Infrastructure & Concessions"],"origin_conv":"695643ed-a2d8-832f-81ec-f2bb22ffb106","origin_node":"2359-line","origin_title":"Business Scale & CPAs","ts":1767261189.906875},
    {"id":"GEN3-016","claim":"Africa is Anchor #1 for ESC Regional Stability Anchors because you already own logistics there.","keywords":["own logistics there"],"origin_conv":"69569536-7908-832d-aea4-7834a2d130ee","origin_node":"4158-line","origin_title":"Global Stability Division HQ","ts":1767264068},
    {"id":"GEN3-017","claim":"DerekOS / VOX / Mega Agent as shared intelligence + operating infrastructure layer.","keywords":["DerekOS / VOX / Mega Agent"],"origin_conv":"69564469-54a0-8325-9290-b7613f44a20d","origin_node":"26f15cb8-2cc2-40b2-8bc3-308fb9915b7b","origin_title":"Service Business Models Breakdown","ts":1767261520.710222},
    {"id":"GEN3-018","claim":"Multi-vertical operations should be organized under a single division with Central Command, Physical & Field Operations, Tech & Automation Layer, and shared Finance/HR/Data functions.","keywords":["Physical & Field Operations","Tech & Automation Layer"],"origin_conv":"695645d4-e0ac-832d-a375-fa237b463509","origin_node":"26f15cb8-2cc2-40b2-8bc3-308fb9915b7b","origin_title":"Multi-Vertical Division Blueprint","ts":1767261691.354036},
]

def get_node_text(node):
    msg = node.get('message')
    if not msg or not isinstance(msg, dict):
        return None, ""
    author = msg.get('author', {}).get('role', '')
    parts = msg.get('content', {}).get('parts', [])
    text = ' '.join(str(p) for p in parts)
    return author, text

def find_parent_chain(mapping, node_id, depth=3):
    chain = []
    current = mapping.get(node_id)
    for _ in range(depth):
        if not current:
            break
        parent_id = current.get('parent')
        if not parent_id or parent_id not in mapping:
            break
        parent = mapping[parent_id]
        author, text = get_node_text(parent)
        if text:
            chain.append({"role": author or "unknown", "text": text[:400], "node_id": parent_id})
        current = parent
    return chain

def find_child_context(mapping, node_id, depth=2):
    context = []
    for nid, node in mapping.items():
        if node.get('parent') == node_id:
            author, text = get_node_text(node)
            if text:
                context.append({"role": author or "unknown", "text": text[:400], "node_id": nid})
    return context[:depth]

def is_modified(original, later):
    if not later or not original:
        return False
    o = re.sub(r'\s+', ' ', original.lower()).strip()
    l = re.sub(r'\s+', ' ', later.lower()).strip()
    return o != l

def integration_strength(occ_list):
    if len(occ_list) == 0:
        return "NONE"
    if len(occ_list) == 1:
        return "LOW"
    if len(occ_list) <= 3:
        return "MEDIUM"
    if len(occ_list) <= 10:
        return "HIGH"
    return "VERY_HIGH"

def adoption_level(evidence_bits):
    if not evidence_bits:
        return "AD0"
    score = 0
    if evidence_bits.get('assistant_origin'): score += 1
    if evidence_bits.get('derek_submitted'): score += 1
    if evidence_bits.get('derek_modified'): score += 1
    if evidence_bits.get('derek_implemented'): score += 1
    if evidence_bits.get('independent_expression'): score += 1
    if evidence_bits.get('superseded'): score = max(0, score - 1)
    if score >= 4: return "AD4"
    if score == 3: return "AD3"
    if score == 2: return "AD2"
    if score == 1: return "AD1"
    return "AD0"

chains = []
for prop in PROPOSITIONS:
    all_occurrences = []
    for fname in sorted(os.listdir(CHATGPT_DIR)):
        if not fname.endswith('.json') or fname in ('ads.json','conversation_asset_file_names.json','export_manifest.json'):
            continue
        fpath = CHATGPT_DIR / fname
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for conv in data:
            title = conv.get('title', '')
            conv_id = conv.get('id', '')
            mapping = conv.get('mapping', {})
            for nid, node in mapping.items():
                msg = node.get('message')
                if not msg or not isinstance(msg, dict):
                    continue
                author = msg.get('author', {}).get('role', '')
                parts = msg.get('content', {}).get('parts', [])
                text = ' '.join(str(p) for p in parts)
                ct = node.get('create_time', 0)
                if any(kw.lower() in text.lower() for kw in prop['keywords']):
                    parents = find_parent_chain(mapping, nid, depth=2)
                    children = find_child_context(mapping, nid, depth=2)
                    all_occurrences.append({
                        'file': fname,
                        'conv_id': conv_id,
                        'title': title,
                        'timestamp': ct,
                        'author': author,
                        'node_id': nid,
                        'text': text,
                        'snippet': text[:700].replace('\n',' '),
                        'parent_chain': parents,
                        'child_context': children,
                    })

    all_occurrences.sort(key=lambda x: x['timestamp'] if x['timestamp'] else 0)

    earliest = None
    for occ in all_occurrences:
        if occ['author'] == 'assistant':
            earliest = occ
            break

    derek_occurrences = [o for o in all_occurrences if o['author'] == 'user']
    later_assistant = [o for o in all_occurrences if o['author'] == 'assistant' and earliest and o['node_id'] != earliest['node_id']]

    evidence = {'assistant_origin': earliest is not None, 'derek_submitted': len(derek_occurrences) > 0, 'derek_modified': False, 'derek_implemented': False, 'independent_expression': False, 'superseded': len(later_assistant) > 0}
    modifications = []
    implementations = []
    independent_expressions = []
    supersessions = []

    for d in derek_occurrences:
        if earliest and is_modified(earliest['text'], d['text']):
            evidence['derek_modified'] = True
            modifications.append({'node_id': d['node_id'], 'snippet': d['snippet'][:400]})
        before = ' '.join([p['text'] for p in d['parent_chain']]).lower()
        after = ' '.join([c['text'] for c in d['child_context']]).lower()
        impl_kws = ['implement','build','create','make','deploy','execute','do it','ship','launch','setup','set up']
        if any(k in before or k in after for k in impl_kws):
            evidence['derek_implemented'] = True
            implementations.append({'node_id': d['node_id'], 'snippet': d['snippet'][:400]})
        if any(kw.lower() in d['text'].lower() for kw in prop['keywords']):
            evidence['independent_expression'] = True
            independent_expressions.append({'node_id': d['node_id'], 'snippet': d['snippet'][:400]})

    for a in later_assistant:
        if any(kw.lower() in a['text'].lower() for kw in prop['keywords']):
            supersessions.append({'node_id': a['node_id'], 'snippet': a['snippet'][:400]})

    ad = adoption_level(evidence)
    integ = integration_strength(all_occurrences)

    chain = {
        "proposition_id": prop['id'],
        "claim": prop['claim'],
        "authored_by": "assistant",
        "submitted_by": "Derek Jamieson",
        "adoption": ad,
        "integration": integ,
        "evidence_class": "CANDIDATE_EVIDENCE",
        "status": "PENDING_RESOLVER_V0_4_OR_V0_5",
        "earliest_assistant_occurrence": {
            "file": earliest['file'],
            "conversation_id": earliest['conv_id'],
            "conversation_title": earliest['title'],
            "node_id": earliest['node_id'],
            "timestamp": earliest['timestamp'],
            "snippet": earliest['snippet'][:400],
        } if earliest else None,
        "total_occurrences": len(all_occurrences),
        "derek_submitted_occurrences": len(derek_occurrences),
        "later_assistant_occurrences": len(later_assistant),
        "occurrence_summary": [
            {
                "file": o['file'],
                "conversation_id": o['conv_id'],
                "title": o['title'],
                "timestamp": o['timestamp'],
                "author": o['author'],
                "node_id": o['node_id'],
                "snippet": o['snippet'][:300],
                "parent_chain": o['parent_chain'],
                "child_context": o['child_context'],
            }
            for o in all_occurrences[:20]
        ],
        "evidence_bits": evidence,
        "modifications": modifications,
        "implementations": implementations,
        "independent_expressions": independent_expressions,
        "supersessions": supersessions,
        "strongest_evidence": f"AD{min(4, sum([1 for k,v in evidence.items() if v and k != 'superseded']))}",
        "superseded_by_later_evidence": evidence['superseded'],
        "rationale": f"Traced {len(all_occurrences)} occurrences across corpus. Earliest assistant-authored occurrence in {earliest['title'] if earliest else 'unknown'}. Derek submitted {len(derek_occurrences)} times. Integration strength: {integ}.",
    }
    chains.append(chain)

output = {
    "meta": {
        "set_name": "GEN3_ADOPTION_CHAINS_V0.1",
        "status": "CANDIDATE_EVIDENCE",
        "created": datetime.now(timezone.utc).isoformat(),
        "resolver_required": "PROVENANCE_RESOLVER_V0.4_OR_V0.5",
        "safety_gate": "FROZEN_ADVERSARIAL_GATE",
        "note": "Adoption chains only. No propositions promoted to D0. Authorship preserved as assistant. Integration strength added as new dimension. Conglomerate V0.1/V0.2 unchanged.",
        "key_finding": "Initial trace indicates corpus behavior is primarily echo/paste rather than independent expression. Integration strength is generally LOW-MEDIUM. Requires release-delta analysis (CORPUS_RELEASE_002) to test whether Gen 4 transformed Gen 3 proposals into a substantially different corporate architecture."
    },
    "propositions": chains,
    "summary": {
        "total_propositions": len(chains),
        "ad0_count": sum(1 for c in chains if c['adoption'] == 'AD0'),
        "ad1_count": sum(1 for c in chains if c['adoption'] == 'AD1'),
        "ad2_count": sum(1 for c in chains if c['adoption'] == 'AD2'),
        "ad3_count": sum(1 for c in chains if c['adoption'] == 'AD3'),
        "ad4_count": sum(1 for c in chains if c['adoption'] == 'AD4'),
        "integration_none": sum(1 for c in chains if c['integration'] == 'NONE'),
        "integration_low": sum(1 for c in chains if c['integration'] == 'LOW'),
        "integration_medium": sum(1 for c in chains if c['integration'] == 'MEDIUM'),
        "integration_high": sum(1 for c in chains if c['integration'] == 'HIGH'),
        "integration_very_high": sum(1 for c in chains if c['integration'] == 'VERY_HIGH'),
        "status": "CANDIDATE_EVIDENCE_PENDING_RESOLVER_V0_4_OR_V0_5"
    }
}

OUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
print(f"Wrote {OUT_PATH}")
print(json.dumps(output['summary'], indent=2, ensure_ascii=False))
