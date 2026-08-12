import json
import time
from pathlib import Path

messages_path = Path(r'D:\Projects\VOX\DerekOS_Master_Brain\01_INGEST\messages.jsonl')
index_path = Path(r'D:\Projects\VOX\DerekOS_Master_Brain\01_INGEST\conversations_index.json')

# Deduplicate messages by source_record_id, keeping first occurrence
seen = set()
deduped = []
with messages_path.open(encoding='utf-8') as f:
    for line in f:
        m = json.loads(line)
        sid = m.get('source_record_id')
        if sid in seen:
            continue
        seen.add(sid)
        deduped.append(m)

print(f'Messages before: {sum(1 for _ in messages_path.open(encoding="utf-8"))}, after dedup: {len(deduped)}')

# Write back
tmp = messages_path.with_suffix('.jsonl.tmp')
with tmp.open('w', encoding='utf-8', newline='\n') as f:
    for m in deduped:
        f.write(json.dumps(m, ensure_ascii=False, sort_keys=True))
        f.write('\n')
    f.flush()
    import os
    os.fsync(f.fileno())

for attempt in range(6):
    try:
        tmp.replace(messages_path)
        break
    except PermissionError:
        if messages_path.exists() and tmp.read_bytes() == messages_path.read_bytes():
            tmp.unlink()
            break
        if attempt == 5:
            raise
        time.sleep(0.1 * (attempt + 1))

# Deduplicate conversations_index by conversation_id + source_file, keeping first
seen_conv = set()
deduped_conv = []
with index_path.open(encoding='utf-8') as f:
    index = json.load(f)
for c in index:
    key = (c.get('conversation_id'), c.get('source_file'))
    if key in seen_conv:
        continue
    seen_conv.add(key)
    deduped_conv.append(c)

print(f'Conversations before: {len(index)}, after dedup: {len(deduped_conv)}')

tmp2 = index_path.with_suffix('.json.tmp')
tmp2.write_text(json.dumps(deduped_conv, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

for attempt in range(6):
    try:
        tmp2.replace(index_path)
        break
    except PermissionError:
        if index_path.exists() and tmp2.read_bytes() == index_path.read_bytes():
            tmp2.unlink()
            break
        if attempt == 5:
            raise
        time.sleep(0.1 * (attempt + 1))

print('Done.')
