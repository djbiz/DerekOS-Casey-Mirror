# DerekOS Master Brain

This is the canonical provenance-first conversation knowledge workspace.

Start with `MASTER_BRAIN_BUILD_SPEC.md`. The immutable raw corpus lives under `00_RAW_ARCHIVE/` but is deliberately excluded from Git because it is large and private. `13_SOURCE_INDEX/source_manifest.json` and the audit reports establish source custody. Reproducible normalized outputs are also excluded; regenerate them with:

```powershell
python 01_INGEST/ingest.py
python 14_TESTS_AUDITS/verify_phase1_reconciliation.py
```

Canonical location: `D:\Projects\VOX\DerekOS_Master_Brain`.

The similarly named Downloads workspace is noncanonical and must not receive new work.
