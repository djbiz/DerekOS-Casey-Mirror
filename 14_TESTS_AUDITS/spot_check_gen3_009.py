import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'D:\Projects\VOX\DerekOS_Master_Brain\08_MASTER_PLAN\reconstruction_pilots\conglomerate\GEN3_ADOPTION_CHAINS_V0.1.json'
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)
c = next(x for x in data['propositions'] if x['proposition_id'] == 'GEN3-009')
print(f"Claim: {c['claim']}")
print(f"Total occurrences: {c['total_occurrences']}")
print(f"Derek submitted: {c['derek_submitted_occurrences']}")
print(f"Assistant origin: {c['evidence_bits']['assistant_origin']}")
print(f"Independent expression: {c['evidence_bits']['independent_expression']}")
print(f"Superseded: {c['evidence_bits']['superseded']}")
print(f"Earliest: {c['earliest_assistant_occurrence']}")
print()
print("First 5 occurrences:")
for o in c['occurrence_summary'][:5]:
    print(f"  - {o['title']} | {o['author']} | {o['timestamp']} | {o['snippet'][:120]}")
