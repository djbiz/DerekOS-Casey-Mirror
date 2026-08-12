import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = r'D:\Projects\VOX\DerekOS_Master_Brain\08_MASTER_PLAN\reconstruction_pilots\conglomerate\GEN3_ADOPTION_CHAINS_V0.1.json'
with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Update key finding to be properly scoped
data['meta']['key_finding'] = (
    "Within this 18-proposition Gen 3 candidate set, downstream evidence is dominated by "
    "reuse/echo/paste behavior rather than independently re-expressed formulations. "
    "Integration strength is generally LOW-MEDIUM. Requires release-delta analysis (CORPUS_RELEASE_002) "
    "to test whether Gen 4 transformed Gen 3 proposals into a substantially different corporate architecture."
)

# Add objective integration criteria
data['meta']['integration_criteria'] = {
  "LOW": "1-2 total occurrences; single conversation or single file; no Derek-submitted reuse; no independent expression; no implementation instruction.",
  "MEDIUM": "3-10 total occurrences; appears in multiple conversations/files; Derek-submitted at least once; some parent/child context showing operationalization or synthesis; at least one implementation instruction or reuse signal.",
  "HIGH": "11+ total occurrences; appears across multiple independent conversations/files; Derek-submitted multiple times; evidence of modification, independent expression, or dependency on other systems; implementation references present; survives later corrections or supersessions.",
  "VERY_HIGH": "HIGH-level integration plus proposition becomes a named dependency of another system, generates concrete implementation work, or is structurally referenced in later architectures."
}

with open(p, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated meta.key_finding and added integration_criteria")
print("New key_finding:", data['meta']['key_finding'])
print("Criteria:", json.dumps(data['meta']['integration_criteria'], indent=2))
