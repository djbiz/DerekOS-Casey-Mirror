import json, os, sys, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

root = os.path.join('D:', os.sep, 'Projects', 'VOX', 'DerekOS_Master_Brain', '00_RAW_ARCHIVE')

# Specific conglomerate-plan terms (narrow, low-noise)
terms = ['lagos', 'nairobi', 'johannesburg', 'africa logistics', 'logistics command',
         '300 business', '300 compan', '200+ business', '200 business',
         'warehouse', 'high-rise', 'high rise', 'corporate high', 'corporate tower',
         'corporate headquarter', 'corporate hq', 'reinvest profit', 'reinvesting profit',
         'profit reinvest', 'acquisition franchis', 'acquire franchis', 'buy franchis',
         'hub architecture', 'command center', 'centralized executive', 'executive control',
         'production r&d', 'manufacturing integration', 'logistics integration']

def safe_ts(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

max_ct = 0.0
max_ct_info = None
ct_count = 0
hits = []

for dirpath, dirs, files in os.walk(root):
    for fname in files:
        if not fname.endswith('.json'):
            continue
        path = os.path.join(dirpath, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        for conv in data:
            title = conv.get('title', '')
            conv_ct = safe_ts(conv.get('create_time'))
            if conv_ct and conv_ct > max_ct:
                max_ct = conv_ct
                max_ct_info = (fname, title)
            mapping = conv.get('mapping', {})
            for nid, node in mapping.items():
                ct = safe_ts(node.get('create_time'))
                if ct:
                    ct_count += 1
                msg = node.get('message')
                if not msg:
                    continue
                parts = msg.get('content', {}).get('parts', [])
                text = ' '.join(str(p) for p in parts).lower()
                matched = [t for t in terms if t in text]
                if matched:
                    author = msg.get('author', {}).get('role', '')
                    node_ct = safe_ts(node.get('create_time')) or safe_ts(msg.get('create_time'))
                    dt = datetime.datetime.fromtimestamp(node_ct).isoformat() if node_ct else 'no-ts'
                    hits.append((fname, title[:60], author, matched, dt, text[:200].replace(chr(10), ' ')))

print('LATEST CONV create_time:', datetime.datetime.fromtimestamp(max_ct).isoformat() if max_ct else 'none', '|', max_ct_info)
print('nodes with create_time:', ct_count)
print()
print(f'TERM HITS: {len(hits)}')
for h in hits[:80]:
    print(f'FILE={h[0]} CONV={h[1]} AUTHOR={h[2]} DATE={h[4]} TERMS={h[3]}')
    print(f'  {h[5]}')
    print()
