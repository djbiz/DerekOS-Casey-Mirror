# PROVENANCE_INDEX_V0.3 benchmark expansion — status

**Not frozen. Not a case file yet. This is a scouting log**, kept deliberately
separate from `03_PROVENANCE_INDEX/frozen_benchmark/` so there is no risk of
confusing this in-progress work with the frozen, scored 30-case V0.2
benchmark. Nothing here should be treated as a verified case until it has the
same level of scrutiny the 30 frozen cases got (full message text read,
timestamps checked, sibling branches checked where relevant).

## What's confirmed so far

- **Cross-platform candidates genuinely exist in this corpus beyond the
  already-documented Legacy Forge case** (§12.9 of the spec). A direct 8-gram
  shingle scan of all 400 Copilot messages against the rest of
  `CORPUS_RELEASE_001` found 181 messages (5 distinct Copilot conversations)
  with at least one shared 8-gram against a non-Copilot message.
- **Most of that signal is noise, not derivation** — see
  `03_PROVENANCE_INDEX/v0_3/PROVENANCE_INDEX_V0.3_DESIGN.md` §4a for the two
  concrete failure modes found and ruled out: scattered-generic-phrase
  fan-out (AXIOMOS-pattern, at message scale) and cross-platform
  assistant-voice convergence (stock flattering phrases, not real content
  transmission).
- **One conversation is a real lead, not yet fully verified**:
  `copilot_conv_9ed50fbef4bfa0dbb96778a805d1a764` (Jan 2026, "Max Steingart" /
  "Todd Brown" system-recreation thread) references prior system-building
  work in a way that's consistent with — but not yet confirmed to be —
  genuine cross-platform derivation from an earlier ChatGPT conversation.
  Needs the same treatment fb_001-fb_030 got: full-text read of both sides,
  timestamp check, and a judgment call on whether the overlap is substantial
  content or just topical/stylistic echo, before it can be written up as a
  case with a ground-truth label.

## What's not done

- No verified V0.3-tranche cases exist yet — 0 written, 0 frozen.
- No coverage yet for: 3+ hop multi-actor chains, other-ai-export-sourced
  candidates (the 3,080-message `conversations.json` source is untouched by
  this scouting pass), or same-conversation Derek-as-origin cases beyond the
  Matt-Diggs pattern already in the frozen 30.
- No case file, no freeze marker, no scoring script for this tranche.

This is genuinely a separate, multi-session-scale undertaking, same as the
frozen 30 was. Reporting it as scouted-but-not-built rather than padding
with unverified cases, consistent with how the frozen 30 was reported against
the original 150-case target.
