import json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
CHATGPT_DIR = ROOT / '00_RAW_ARCHIVE' / 'chatgpt'

# Key Gen 3 propositions with their exact phrases and conversation origins
propositions = [
    {"id": "GEN3-001", "phrase": "you do not manage companies; you manage HoldCos (Holding Companies)", "origin_conv": "6956279f-2074-8330-b7f7-8872615e4846", "origin_node": "32b9bf3e-6750-4c45-9ae7-83ea76f6d361"},
    {"id": "GEN3-002", "phrase": "Capital Allocation Manifesto", "origin_conv": "6956279f-2074-8330-b7f7-8872615e4846", "origin_node": "32b9bf3e-6750-4c45-9ae7-83ea76f6d361"},
    {"id": "GEN3-003", "phrase": "Banker-in-Chief", "origin_conv": "6956279f-2074-8330-b7f7-8872615e4846", "origin_node": "32b9bf3e-6750-4c45-9ae7-83ea76f6d361"},
    {"id": "GEN3-004", "phrase": "Hurdle Rate", "origin_conv": "695742ba-f824-8332-bad1-44e8ca02657b", "origin_node": "6971-line"},
    {"id": "GEN3-009", "phrase": "ESC is not a company", "origin_conv": "69569536-7908-832d-aea4-7834a2d130ee", "origin_node": "4158-line"},
    {"id": "GEN3-010", "phrase": "Capital allocation", "origin_conv": "69569536-7908-832d-aea4-7834a2d130ee", "origin_node": "4158-line"},
    {"id": "GEN3-011", "phrase": "Regional Stability Anchors", "origin_conv": "69569536-7908-832d-aea4-7834a2d130ee", "origin_node": "4158-line"},
    {"id": "GEN3-012", "phrase": "Africa remains Anchor #1", "origin_conv": "69569536-7908-832d-aea4-7834a2d130ee", "origin_node": "4158-line"},
    {"id": "GEN3-014", "phrase": "multi-layer institutional structure", "origin_conv": "695643ed-a2d8-832f-81ec-f2bb22ffb106", "origin_node": "2359-line"},
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
            chain.append({"role": author or "unknown", "text": text[:300], "node_id": parent_id})
        current = parent
    return chain

def find_child_context(mapping, node_id, depth=2):
    context = []
    for nid, node in mapping.items():
        if node.get('parent') == node_id:
            author, text = get_node_text(node)
            if text:
                context.append({"role": author or "unknown", "text": text[:300], "node_id": nid})
    return context[:depth]

for prop in propositions:
    print(f"\n{'='*80}")
    print(f"PROPOSITION: {prop['id']}")
    print(f"PHRASE: {prop['phrase']}")
    print(f"ORIGIN: {prop['origin_conv']} node {prop['origin_node']}")
    print('='*80)
    
    # Search all corpus files for this proposition
    all_occurrences = []
    for fname in sorted(os.listdir(CHATGPT_DIR)):
        if not fname.endswith('.json') or fname in ('ads.json', 'conversation_asset_file_names.json', 'export_manifest.json'):
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
            if prop['phrase'].lower() in text.lower():
                    all_occurrences.append({
                        'file': fname,
                        'conv_id': conv_id,
                        'title': title,
                        'timestamp': ct,
                        'author': author,
                        'node_id': nid,
                        'text': text,
                        'mapping': mapping,
                    })
    
    print(f"TOTAL OCCURRENCES: {len(all_occurrences)}")
    for i, occ in enumerate(all_occurrences):
        print(f"\n--- Occurrence {i+1} ---")
        print(f"File: {occ['file']}")
        print(f"Conversation: {occ['title']} ({occ['conv_id']})")
        print(f"Timestamp: {occ['timestamp']}")
        print(f"Author: {occ['author']}")
        print(f"Node ID: {occ['node_id']}")
        
        # Get parent chain (what Derek said before)
        parents = find_parent_chain(occ['mapping'], occ['node_id'], depth=2)
        if parents:
            print("PARENT CHAIN (what Derek said before):")
            for p in parents:
                print(f"  [{p['role']}] {p['text'][:200]}")
        
        # Get child context (what Derek said after)
        children = find_child_context(occ['mapping'], occ['node_id'], depth=2)
        if children:
            print("CHILD CONTEXT (what Derek said after):")
            for c in children:
                print(f"  [{c['role']}] {c['text'][:200]}")
        
        # Show snippet of the occurrence itself
        snippet = occ['text'].replace('\n', ' ')[:400]
        print(f"SNIPPET: {snippet}")
        print()
