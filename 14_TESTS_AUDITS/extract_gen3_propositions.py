import json, sys, os
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = Path(__file__).resolve().parent.parent
CHATGPT_DIR = ROOT / '00_RAW_ARCHIVE' / 'chatgpt'
target_convs = [
    'Path to Founder Role',
    'Conglomerate Governance Framework',
    'Global Stability Division HQ',
    'Global Continuity Insurer',
    'Offer Creation Division',
    'OEG Operational Framework',
    'In-house LLM Hub',
    'Anti-decay Design for Legacy',
    'Dev Team Structure for Deadlines',
    'Business Predictive System 2026',
    'AI-Optimized Legal Model',
    'Smart Parking Business Idea',
    'Business Strategy and AI',
    'CLI Shell Test',
    'Laptop Overheating Noise Issues',
    'Business Model Analysis Options',
    'Research Workflow Optimization',
]
for fname in sorted(os.listdir(CHATGPT_DIR)):
    if not fname.endswith('.json') or fname in ('ads.json', 'conversation_asset_file_names.json', 'export_manifest.json'):
        continue
    fpath = CHATGPT_DIR / fname
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        continue
    for conv in data:
        title = conv.get('title', '')
        if not any(t.lower() in title.lower() for t in target_convs):
            continue
        conv_id = conv.get('id', '')
        print(f'=== {title} ===')
        print(f'FILE={fname} ID={conv_id}')
        mapping = conv.get('mapping', {})
        nodes = []
        for nid, node in mapping.items():
            msg = node.get('message')
            if not msg: continue
            author = msg.get('author', {}).get('role', '')
            parts = msg.get('content', {}).get('parts', [])
            text = ' '.join(str(p) for p in parts)
            ct = node.get('create_time', 0)
            if text.strip():
                nodes.append((ct, author, text))
        nodes.sort(key=lambda x: x[0])
        for ct, author, text in nodes:
            if author == 'user':
                print(f'--- USER [{ct}] ---')
                print(text)
                print()
        print('=' * 80)
        print()
