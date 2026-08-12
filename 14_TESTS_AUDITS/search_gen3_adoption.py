import json, os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
CHATGPT_DIR = ROOT / '00_RAW_ARCHIVE' / 'chatgpt'
search_terms = [
    'HoldCos',
    'Capital Allocation Manifesto',
    'Banker-in-Chief',
    'Monthly Capital Deployment Meetings',
    'One-Page Monthly Performance Review',
    'Ready-Now successors',
    'Leadership Rotational Program',
    'ESC is not a company',
    'ESC is a system operator',
    'Regional Stability Anchors',
    'Africa remains Anchor #1',
    'Standard RSA Stack',
    'multi-layer institutional structure',
    'Six Independent Capital Arms',
    'Manhattan Command Center',
    'Global Financial Operations Command',
    'DerekOS / VOX / Mega Agent',
    'Multi-Vertical Operations & Automation Division',
]
results = {}
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
            if not msg:
                continue
            author = msg.get('author', {}).get('role', '')
            if author != 'user':
                continue
            parts = msg.get('content', {}).get('parts', [])
            text = ' '.join(str(p) for p in parts)
            ct = node.get('create_time', 0)
            for term in search_terms:
                if term.lower() in text.lower():
                    if term not in results:
                        results[term] = []
                    results[term].append({
                        'file': fname,
                        'conv_id': conv_id,
                        'title': title,
                        'timestamp': ct,
                        'snippet': text[:500],
                        'node_id': nid,
                    })
for term, hits in sorted(results.items()):
    print(f'=== {term} ({len(hits)} hits) ===')
    for h in hits[:5]:
        print(f"  {h['file']} | {h['title']} | {h['timestamp']}")
        print(f"    {h['snippet'][:200]}")
    if len(hits) > 5:
        print(f"  ... and {len(hits)-5} more")
    print()
