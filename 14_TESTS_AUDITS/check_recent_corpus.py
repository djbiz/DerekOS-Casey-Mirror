import json, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = os.path.join('D:', os.sep, 'Projects', 'VOX', 'DerekOS_Master_Brain', '13_SOURCE_INDEX', 'by_date')

for m in ['2026-05.json', '2026-06.json', '2026-07.json', '2026-08.json']:
    path = os.path.join(base, m)
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'=== {m}: {len(data)} conversations ===')
    for c in data:
        print(f"  {c.get('title','')[:80]} | {c.get('source_file','')} | msgs={c.get('message_count','')}")
    print()
