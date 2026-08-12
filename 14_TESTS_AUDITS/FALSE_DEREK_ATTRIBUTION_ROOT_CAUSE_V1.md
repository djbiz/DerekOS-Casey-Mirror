# False Derek Attribution Root Cause V1

## Audit status

This is a read-only root-cause analysis of the 69 case IDs frozen in
`PROVENANCE_ADVERSARIAL_BENCHMARK_V1.json`. The adversarial cases, sealed
predictions, and blind adjudications were not modified.

The report classifies **why the resolver's D0 decision was unsafe**. It does
not establish final authorship for unresolved material and does not promote
any record into canonical knowledge.

## Finding

The dominant failure is not one bad phrase or regular expression. The
resolver treated a user-role submission as authorship evidence and therefore
converted imported agent reports, polished framework artifacts, external
material, and mixed messages into Derek attribution without positive origin
evidence.

`role=user` proves **submitted by Derek**, not **authored by Derek** and not
**adopted by Derek**.

## Primary-family counts

Each case receives exactly one primary family, so counts total 69. Secondary
signals can overlap but do not increase these counts.

| Primary failure family | Count | Share |
|---|---:|---:|
| Cross-platform AI reuse | 21 | 30.4% |
| AI-polished framework | 15 | 21.7% |
| External pasted material | 14 | 20.3% |
| Short carrier phrase + pasted body | 6 | 8.7% |
| Mixed Derek + pasted content | 4 | 5.8% |
| Unknown origin | 3 | 4.3% |
| Same-platform AI reuse | 2 | 2.9% |
| Long polished first-person material | 2 | 2.9% |
| Other | 2 | 2.9% |
| AI text substantially edited by Derek | 0 | 0.0% |
| Chronology/origin failure | 0 | 0.0% |
| **Total** | **69** | **100%** |

The zero counts are meaningful. C08 similarity does not prove that Derek
substantially edited AI text, and a later/weak similarity hit does not prove
an origin. Those remain secondary diagnostic signals unless trace evidence
supports the stronger claim.

## Overlap policy

- **Primary family** is the smallest decisive explanation for why D0 was
  unsafe.
- **Chronology/origin failure** is a secondary signal whenever the located
  match is later than the target, weak, or otherwise non-originating.
- **AI text substantially edited by Derek** requires a traceable earlier AI
  form plus evidence of Derek's material editing. Style or partial similarity
  alone is insufficient.
- Carrier phrases and mixed records overlap. A short wrapper around an
  artifact is classified as carrier phrase; a record with independently
  meaningful Derek and supplied segments is classified as mixed.
- “AI-polished” and “agent-shaped” describe the failure signature, not a
  final origin claim. When no source is traceable, the adjudicated class
  remains `UNRESOLVED`.

## Per-case classification and evidence

The evidence column paraphrases the frozen blind adjudication and bundle
signals. It is not a new adjudication.

| Case | Frozen class | Primary family | Evidence / rationale |
|---|---|---|---|
| `adv_000318` | UNRESOLVED | Short carrier phrase + pasted body | A request wraps a long historical script; submission does not establish authorship of the body. |
| `adv_001381` | UNRESOLVED | Short carrier phrase + pasted body | A formatting request wraps a polished example post; the bundle provides no decisive origin. |
| `adv_001825` | P0 | External pasted material | LinkedIn profile/outreach material identifies a third party. |
| `adv_006124` | UNRESOLVED | Unknown origin | Polished Blockverse whitepaper text has no traceable origin or direct Derek evidence. |
| `adv_006770` | UNRESOLVED | Short carrier phrase + pasted body | “more Hooks” precedes assistant-voice hook copy; the body cannot inherit carrier authorship. |
| `adv_007135` | P0 | External pasted material | A bare LinkedIn URL is submitted evidence, not an authored proposition. |
| `adv_007453` | UNRESOLVED | Long polished first-person material | First-person correspondence may be authored or supplied; style and user role cannot resolve it. |
| `adv_008147` | UNRESOLVED | External pasted material | Mid-article business prose is artifact-like and lacks positive Derek origin evidence. |
| `adv_009046` | UNRESOLVED | Unknown origin | REST API specification/code may be project work or imported AI output; the source is unproven. |
| `adv_009750` | MIXED | Same-platform AI reuse | Derek's question accompanies a strong partial same-conversation assistant-text match. |
| `adv_011993` | UNRESOLVED | AI-polished framework | A polished 30-day plan has assistant-style structure and no traceable authorship. |
| `adv_012035` | UNRESOLVED | AI-polished framework | Creator-Scout module documentation is a polished artifact without positive origin evidence. |
| `adv_012068` | UNRESOLVED | AI-polished framework | Supplier swap-list prose is a polished artifact without positive origin evidence. |
| `adv_012199` | UNRESOLVED | AI-polished framework | The 48-hour prototype document is polished plan text with no established author. |
| `adv_012236` | UNRESOLVED | AI-polished framework | Sprint pack documentation is artifact-shaped; user-role submission is insufficient. |
| `adv_012412` | UNRESOLVED | AI-polished framework | SEOForge add-on documentation has no traceable Derek origination. |
| `adv_013200` | UNRESOLVED | AI-polished framework | “100 M Business Factory” is an assistant-shaped framework with no direct origin proof. |
| `adv_013280` | UNRESOLVED | AI-polished framework | The named real-estate framework is polished but untraceable. |
| `adv_016829` | UNRESOLVED | AI-polished framework | Empire 19.0 fantasy documentation is artifact-shaped and untraceable. |
| `adv_017867` | UNRESOLVED | AI-polished framework | “everything … you created” is assistant-addressing language, not Derek authorship evidence. |
| `adv_017999` | MIXED | Unknown origin | A system request contains a partial reuse signal; segmentation and source review are required. |
| `adv_018391` | UNRESOLVED | Short carrier phrase + pasted body | A code request wraps a polished product description whose authorship is not established. |
| `adv_018536` | P0 | External pasted material | Scraped RealPage/accessibility webpage material is supplied content. |
| `adv_019103` | UNRESOLVED | External pasted material | A SaaS feature-comparison table appears supplied; exact source remains unresolved. |
| `adv_019128` | UNRESOLVED | Same-platform AI reuse | Architecture-review prose strongly resembles an assistant response in the same context. |
| `adv_019178` | P0 | External pasted material | Webinar landing-page copy and links identify supplied marketing material. |
| `adv_021093` | UNRESOLVED | Short carrier phrase + pasted body | “I can be a life coach with this” wraps a long assistant-voice framework. |
| `adv_021773` | UNRESOLVED | External pasted material | Google search-result markup is submitted source material, not original prose. |
| `adv_023273` | UNRESOLVED | Short carrier phrase + pasted body | A short business-model question wraps polished offer copy of unknown origin. |
| `adv_023806` | P0 | External pasted material | A long third-person Bitcoin mining guide is supplied technical material. |
| `adv_024945` | UNRESOLVED | AI-polished framework | The named Villain-Hero-Savior framework has no traceable earlier Derek origin. |
| `adv_025602` | P0 | External pasted material | Medical advisory prose addresses Derek and cites symptoms, indicating supplied advice. |
| `adv_025673` | P0 | Mixed Derek + pasted content | Derek's plan statement is combined with Hostinger pricing-page copy. |
| `adv_026055` | P0 | External pasted material | PicoClaw product/quick-start copy is supplied material. |
| `adv_026252` | P0 | External pasted material | Timestamped training-summary notes are source material with unknown note authorship. |
| `adv_027022` | UNRESOLVED | Cross-platform AI reuse | A complete autonomous-agent system handoff was submitted without traceable author identity. |
| `adv_027069` | UNRESOLVED | Cross-platform AI reuse | An agent campaign completion report claims actions but has no source trace. |
| `adv_027082` | UNRESOLVED | Cross-platform AI reuse | A Felix-stack handoff is agent-shaped and imported without definitive origin. |
| `adv_027470` | UNRESOLVED | Cross-platform AI reuse | A pipeline status handoff is operational agent prose without a traceable author. |
| `adv_027736` | UNRESOLVED | Cross-platform AI reuse | A credential-sweep report is an agent action artifact, not Derek-authored knowledge. |
| `adv_027756` | UNRESOLVED | Cross-platform AI reuse | A dashboard correction report is agent-shaped operational output. |
| `adv_027815` | P0 | Other | Terminal commands and Python syntax errors are machine-generated evidence. |
| `adv_027972` | UNRESOLVED | Long polished first-person material | A polished architecture correction may be Derek-supplied or agent-authored; no source resolves it. |
| `adv_027980` | P0 | Cross-platform AI reuse | First-person assistant boundary/refusal language explicitly describes AI limitations. |
| `adv_027990` | UNRESOLVED | Cross-platform AI reuse | Task execution and asset-generation reporting is agent-shaped and untraceable. |
| `adv_028025` | UNRESOLVED | Cross-platform AI reuse | An agent report says it changed files/memory; user-role submission cannot transfer authorship. |
| `adv_028040` | UNRESOLVED | Cross-platform AI reuse | Connector capability analysis is an imported agent-style report. |
| `adv_028118` | UNRESOLVED | Cross-platform AI reuse | Skill/tool execution and QA reporting lacks reliable origin evidence. |
| `adv_028257` | P0 | Other | A system-prompt template requesting hidden reasoning is supplied prompt content. |
| `adv_028263` | UNRESOLVED | AI-polished framework | A formal sprint architecture declaration is polished artifact text without traceable authorship. |
| `adv_028277` | UNRESOLVED | Cross-platform AI reuse | A sprint completion report is agent-shaped execution output. |
| `adv_028378` | UNRESOLVED | Cross-platform AI reuse | An enterprise sprint completion report lacks definitive author evidence. |
| `adv_028382` | P0 | Cross-platform AI reuse | Tool logs and an implementation summary are machine/agent-generated material. |
| `adv_028394` | UNRESOLVED | AI-polished framework | An implementation plan requests user review and reads as assistant output; exact source is unproven. |
| `adv_028399` | UNRESOLVED | AI-polished framework | A detailed plan says “you are absolutely right,” indicating response-shaped material. |
| `adv_028444` | UNRESOLVED | AI-polished framework | A formal Business Memory OS plan lacks reliable origin evidence. |
| `adv_028925` | P0 | Cross-platform AI reuse | The record explicitly labels the supplied report “CodeOne.” |
| `adv_028973` | P0 | Cross-platform AI reuse | The record explicitly labels the supplied response “From Hermes.” |
| `adv_029000` | P0 | Cross-platform AI reuse | The record explicitly labels the supplied acknowledgment “From OpenCode.” |
| `adv_029035` | P0 | Cross-platform AI reuse | A detailed Nextcloud test/build handoff is agent-generated operational reporting. |
| `adv_029198` | P0 | Cross-platform AI reuse | A formal post-merge hardening report is supplied agent analysis. |
| `adv_029212` | P0 | Cross-platform AI reuse | The record explicitly labels the supplied report “From Codex.” |
| `adv_030132` | P0 | External pasted material | A copied LinkedIn thread identifies Marcus and other correspondents. |
| `adv_030261` | P0 | Mixed Derek + pasted content | A summarization instruction wraps an external Kyrsti Snyder transcript. |
| `adv_030897` | P0 | Mixed Derek + pasted content | A transcript naming Derek as speaker is still supplied source material, not a direct chat statement. |
| `adv_032016` | P0 | External pasted material | A marketplace product title/specification is external product data. |
| `adv_032023` | P0 | External pasted material | A search-answer prompt wrapper and results are supplied template/content. |
| `adv_032963` | P0 | Mixed Derek + pasted content | A summarization instruction wraps an external Think Media transcript. |
| `adv_033504` | P0 | Cross-platform AI reuse | A safety critique addresses a submitted script and reads as assistant evaluation. |

## Resolver design implications

1. **Default to `UNRESOLVED`.** D0 requires positive, independent authorship
   evidence. No located prior origin is not evidence.
2. **Model three axes.** Persist `submitted_by`, `authored_by`, and
   `adopted_by/status` independently.
3. **Require DAE-3 or DAE-4 for D0.** User role, first person, recurrence,
   topical alignment, and style can never provide DAE-3/4 on their own.
4. **Detect transport wrappers before attribution.** URLs, transcripts,
   terminal output, search results, product pages, reports, and “From Agent”
   blocks are content carriers.
5. **Segment before classifying.** A short Derek instruction cannot transfer
   authorship to an attached body. Mixed records need segment-level origins.
6. **Treat agent artifacts as imported evidence.** Execution reports, sprint
   plans, handoffs, and assistant-addressing prose require source identity or
   abstention.
7. **Enforce chronology.** Only an earlier traceable record can support an
   origin claim; later or weak similarity is non-probative.
8. **Do not equate editing with authorship.** Substantial editing needs a
   traceable before/after chain and may still produce collaborative/mixed
   provenance rather than D0.
9. **Keep safety ahead of coverage.** The resolver may leave a large share
   unresolved. It must not lower its D0 threshold to improve coverage.

## Gate consequence

This analysis does not change the frozen benchmark result. Gate 1 remains
failed until a new resolver records **zero** false Derek attributions against
the unchanged cases and labels. `PROVENANCE_CORPUS_V1` and canonical commit
remain unauthorized.

