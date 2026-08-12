import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'D:\Projects\VOX\DerekOS_Master_Brain\08_MASTER_PLAN\reconstruction_pilots\conglomerate\GEN3_ADOPTION_CHAINS_V0.1.json'
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)
for c in data['propositions'][:8]:
    earliest_title = c['earliest_assistant_occurrence']['conversation_title'] if c['earliest_assistant_occurrence'] else None
    print(f"{c['proposition_id']}: adoption={c['adoption']}, integration={c['integration']}, total={c['total_occurrences']}, derek={c['derek_submitted_occurrences']}, assistant_origin={c['evidence_bits']['assistant_origin']}, earliest={earliest_title}")
