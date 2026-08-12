# RELAY_PATTERN_TEST_V0.1.md
# Created: 2026-08-12
# Status: FROZEN AS CANDIDATE EVIDENCE (founder directive 2026-08-12) —
#         review required; no authorship claims; nothing canonical.
#         NO permanent relay index or graph until the global message_id
#         collision remediation is complete and a corrected corpus release
#         with unique canonical record IDs exists. On resume, rerun the
#         detector and compare V0.1 -> corrected release (integrity test).
#         See MULTI_AGENT_RELAY_CHAIN_PATTERN_V0.1.md section 8.
# Pattern: MULTI_AGENT_RELAY_CHAIN (08_MASTER_PLAN/MULTI_AGENT_RELAY_CHAIN_PATTERN_V0.1.md)

## Corpus Coverage Header

- Corpus: CORPUS_RELEASE_001 (FROZEN), 72,241 messages scanned
- Sources included: ChatGPT exports (conversations*.json) plus Copilot CSV
  as ingested; latest timestamp 2026-08-09T22:57Z
- Known-unscanned areas: all material outside this release (other AI
  platforms, Notion, Obsidian, unexported sessions); unlabeled transports
  are NOT detectable by this heuristic
- Detection method: labeled relay headers (Actor [h:mm AM/PM]) inside
  user-role messages >= 200 chars; regex v0.1
- Reconstruction timestamp: 2026-08-12

## Result

**45 candidate relay events**, all in July 2026, all inside
conversations-032.json, across 7 conversations:

| Conversation | Events |
|---|---|
| Research Workflow Optimization | 19 |
| Market Intent Prediction Stack | 10 |
| Laptop Overheating Noise Issues | 7 |
| Team Update Strategy | 4 |
| Reality Check Execution Plan | 3 |
| Experiment Planning and Roles | 1 |
| Llama model download guide | 1 |

Relay actors observed (labeled headers): WorkClaw (37), Hermes Relay (17),
Town (12), Derek Jamieson (10), Genspark (8), Appy.ai (8), Stilla (7),
Julius (4), Hubi (3), Twin (3), Anrie (1), Demi (1).

## Reading

1. The pattern is REAL in the searched corpus: Derek pastes multi-agent
   room transcripts — including his own messages quoted back with actor
   headers ("Derek Jamieson [11:08 AM]") — into ChatGPT for refinement
   and integration. Several events carry multiple actor headers, i.e.
   whole-room transcripts, not single quotes.
2. In this corpus the pattern is concentrated in one July 2026 burst.
   Two coverage caveats prevent a stronger conclusion:
   - The heuristic detects LABELED relays only. The screened Growth
     Hacker Brief paste had no actor header and would be invisible here;
     unlabeled transports are OUT_OF_METHOD coverage, not absent.
   - The corpus pre-dates nothing after 2026-08-09 and contains no
     exports from the relay platforms themselves, so relay activity in
     earlier months or on other surfaces is OUT_OF_CORPUS_EVIDENCE_PENDING.
3. The founder hypothesis — "this may be one of the central
   knowledge-evolution patterns" — is supported within scope but NOT
   established globally. Testing against future releases (including the
   eventual CORPUS_RELEASE_002 and other-AI exports) is required.

## Integration-strength relevance (candidate only)

These 45 events are behavioral evidence of the "sent to another agent" /
"reused later" event classes in the pattern spec. They are CANDIDATE
integration events; no AD or D0 assignment follows from them.

## Disposition

- No authorship claims. H1/H2 for Zo AI remain OPEN.
- Five chains held; nothing canonicalized; conglomerate gate unchanged.
- Raw data: 14_TESTS_AUDITS/notion_audit/RELAY_PATTERN_TEST_V0.1.json

---
# END OF RELAY PATTERN TEST
