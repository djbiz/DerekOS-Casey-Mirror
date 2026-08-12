# Slice 3 Candidate Intake — Build Intent

**Date:** 2026-08-12
**Baseline:** `f7af107`

## Inspected

The accepted Knowledge Contract, canonical publisher, concurrent candidate-intake draft, its tests, and its proposed documentation.

## Proposed change

Consolidate the existing draft into the canonical bridge while correcting self-approval, submitter trust, identity/revision, full-content custody, path, and idempotency behavior. No watcher, canonical mutation, or production intake is authorized.

## Files

- `master_brain_bridge/candidate_intake.py`
- `master_brain_bridge/__init__.py`
- `14_TESTS_AUDITS/test_master_brain_candidate_intake.py`
- `08_MASTER_PLAN/MASTER_BRAIN_CANDIDATE_INTAKE_V0.1.md`
- This report

## Risks and verification

Candidate notes are untrusted and cannot supply their own authority. Tests must prove path confinement, immutable revision intake, source non-mutation, self-approval denial, distinct-source preservation, and no canonical write.

## Final change question

**Does this move VOX closer to becoming the AI Workforce Operating System?** Yes. It admits proposed knowledge without confusing submission with truth or approval.
