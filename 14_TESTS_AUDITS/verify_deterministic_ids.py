import json
import hashlib
from pathlib import Path

source_file = 'conversations.json'
source_path = Path(r'D:\Projects\VOX\DerekOS_Master_Brain\00_RAW_ARCHIVE\other-ai-export\conversations.json')
messages_path = Path(r'D:\Projects\VOX\DerekOS_Master_Brain\01_INGEST\messages.jsonl')

# Compute source hash
h = hashlib.sha256()
with source_path.open('rb') as f:
    for chunk in iter(lambda: f.read(512 * 1024), b''):
        h.update(chunk)
source_hash = h.hexdigest()

# Load all delta messages into memory
delta_messages = []
with messages_path.open(encoding='utf-8') as f:
    for line in f:
        m = json.loads(line)
        if m.get('source_file') == source_file:
            delta_messages.append(m)

print(f'Total delta messages to verify: {len(delta_messages)}')

mismatches = 0
for m in delta_messages:
    raw = source_hash + '\x1f' + m['conversation_id'] + '\x1f' + m['node_id'] + '\x1f' + str(m['fragment_index'])
    expected = 'srcmsg_' + hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]
    if m['source_record_id'] != expected:
        mismatches += 1
        print(f'MISMATCH: {m["source_record_id"]} != {expected}')

print(f'Deterministic ID mismatches: {mismatches}')
if mismatches == 0:
    print('PASS: All source_record_ids are deterministic and reproducible.')

# Verify no duplicate source_record_ids in delta
ids = [m['source_record_id'] for m in delta_messages]
print(f'Unique source_record_ids: {len(set(ids))}')
print(f'Total source_record_ids: {len(ids)}')
print(f'Duplicate IDs: {len(ids) - len(set(ids))}')
