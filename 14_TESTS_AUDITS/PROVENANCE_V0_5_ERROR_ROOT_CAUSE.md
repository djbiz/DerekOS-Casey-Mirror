# PROVENANCE V0.5 Error Root-Cause Audit

**Audit basis:** frozen `FROZEN_ADJUDICATION_V1.jsonl` versus
`PROVENANCE_RESOLVER_V0_4_predictions.json`  
**Benchmark size:** 230  
**Scope:** remaining P0, MIXED, and AD3/AD4 errors only  
**Frozen inputs changed:** none

## Executive finding

V0.4 preserved the critical D0 safety boundary, but the remaining errors come
from two different problems that must not be solved with one broad heuristic:

1. **message-level origin and span-level composition are conflated**; and
2. **P0 certainty is conflated with P0 evidence class**.

The largest apparent error set is 94 P0 false negatives. Most are intentionally
conservative `UNRESOLVED` predictions for material that the blind labels call
P0 from human-readable structural evidence, but for which the resolver has no
traceable corpus origin. Promoting all of these automatically would weaken the
positive-evidence model. V0.5 should only promote a subset using independently
verifiable structural source evidence; otherwise it should preserve
`P0-PROBABLE` or `P0-UNRESOLVED` as review states.

## Counts

| Error surface | Count | Dominant cause |
|---|---:|---|
| P0 false positive | 16 | MIXED messages collapsed to the imported body |
| P0 false negative | 94 | imported-looking material lacks a traceable origin |
| MIXED false positive | 6 | own or wholly imported material over-segmented |
| MIXED false negative | 21 | short Derek carrier phrase not separated from a pasted body |
| AD3/AD4 error | 1 | modification strength / label inconsistency |

The P0 and MIXED sets overlap: nine true MIXED records are simultaneously P0
false positives and MIXED false negatives. Counts therefore must not be added
as if they were unique records.

## P0 false positives — 16

### PF-1 — True MIXED collapsed to imported body (9)

**Cases:** `adv_001443`, `adv_019337`, `adv_021989`, `adv_024223`,
`adv_026699`, `adv_028654`, `adv_030604`, `adv_033022`, `adv_034448`

**Evidence:** each record contains a short Derek-authored carrier or question
followed by a reused body. Located-source overlap ranges from 25.2% to 97.7%.
The resolver correctly recognizes imported content but incorrectly assigns its
class to the entire message.

**Boundary implication:** locate the first structural transition after carrier
phrases such as “Can we add this”, “Please update this”, “create a prompt”, or
“can we also add”. Preserve the carrier as a separate D0 span and classify the
body independently. A high reuse fraction is evidence about the body, never
permission to erase an original prefix.

**General rule:** when a compact imperative/interrogative prefix is followed by
a blank-line, heading, code fence, list, or high-overlap block, test a two-span
hypothesis before applying a whole-message P0 class.

### PF-2 — Low-overlap reuse mistaken for imported authorship (5)

**Cases:** `adv_001444`, `adv_017999`, `adv_024682`, `adv_025657`,
`adv_034886`

**Evidence:** the frozen labels identify respectively an original instruction,
an original systems request, continuation of the user's own document, a
correction quoting phrases under dispute, and the user's own terminal output.
Matched fractions of 15.6%–42.1% reflect templates, quoted material, or common
operational text—not authorship of the whole message.

**Boundary implication:** quotation, correction, continuation, and terminal-log
contexts require semantic role detection. A matching shingle is not an origin
span unless its extent and source role are established.

**General rule:** never promote to P0-CERTAIN from reuse alone when overlap is
partial and the message is a correction, continuation, instruction, or
first-party execution log. Require a dominant aligned span and an earlier
source with a compatible author role.

### PF-3 — Ambiguous artifact promoted instead of remaining unresolved (2)

**Cases:** `adv_005890`, `adv_010955`

**Evidence:** a structured empire plan and Kotlin source code have reuse/code
signals, but the blind labels explicitly say authorship is ambiguous. Neither
has enough evidence to establish an external or assistant author.

**General rule:** polished structure and code are not positive P0 evidence.
When source authorship cannot be traced, preserve `UNRESOLVED`.

## P0 false negatives — 94

These are grouped by observable source family. The grouping is exhaustive.

### PN-1 — AI-voice or assistant artifact without a sufficiently traceable origin (36)

**Cases:** `adv_011018`, `adv_011310`, `adv_011599`, `adv_011640`,
`adv_011641`, `adv_011746`, `adv_011993`, `adv_012035`, `adv_012068`,
`adv_012199`, `adv_012210`, `adv_012236`, `adv_012410`, `adv_012412`,
`adv_012420`, `adv_012771`, `adv_013001`, `adv_013200`, `adv_013280`,
`adv_013750`, `adv_016498`, `adv_016642`, `adv_016829`, `adv_017867`,
`adv_018613`, `adv_019128`, `adv_021289`, `adv_022114`, `adv_022859`,
`adv_023806`, `adv_025602`, `adv_028404`, `adv_033504`, `adv_033685`,
`adv_034205`, `adv_034335`

**Evidence:** labels cite assistant voice, another-AI responses, copy-paste-ready
packages, generated technical plans, or assistant-built code. Many have very
low corpus reuse because the actual producing platform or earlier message is
outside the indexed corpus.

**General rule:** strong self-identifying AI discourse (“Below is…”, “I’ll help
you…”, second-person assessment addressed to Derek, turnkey response framing)
may support `P0-PROBABLE`, but must not become `P0-CERTAIN` without a traceable
origin or explicit source label. This family is a review-coverage opportunity,
not grounds to weaken D0 safety.

### PN-2 — Agent-generated operational artifacts (21)

**Cases:** `adv_027022`, `adv_027069`, `adv_027082`, `adv_027470`,
`adv_027736`, `adv_027756`, `adv_027980`, `adv_027990`, `adv_028025`,
`adv_028040`, `adv_028118`, `adv_028170`, `adv_028263`, `adv_028277`,
`adv_028378`, `adv_028382`, `adv_028394`, `adv_028399`, `adv_028411`,
`adv_028444`, `adv_029035`

**Evidence:** task reports, sprint plans, session reports, build/QA summaries,
connector reports, and autonomous-agent handoffs have machine-work-product
structure and often name an agent or operational action.

**General rule:** parse report headers and provenance fields as source evidence.
An internally named agent plus report-specific execution metadata can establish
P0-CERTAIN only when the named source is bound to the artifact; generic report
format alone remains P0-PROBABLE.

### PN-3 — Explicitly labeled agent output (5)

**Cases:** `adv_028920`, `adv_028925`, `adv_028973`, `adv_029000`,
`adv_029212`

**Evidence:** frozen notes identify explicit labels such as “From Gemini”,
“CodeOne”, “From Hermes”, “From OpenCode”, and “From Codex”.

**General rule:** a source label immediately governing a pasted block is direct
positive P0 evidence. Capture the label as a source-attribution span and the
governed body as P0-CERTAIN; do not rely on prose style.

### PN-4 — Third-party communications and profiles (14)

**Cases:** `adv_001825`, `adv_001964`, `adv_002015`, `adv_003182`,
`adv_007135`, `adv_014438`, `adv_014464`, `adv_014544`, `adv_030062`,
`adv_030092`, `adv_030107`, `adv_030132`, `adv_031092`, `adv_031229`

**Evidence:** LinkedIn threads/profiles, dating-chat messages, and named third-
party replies contain sender names, dialogue headers, URLs, or carrier labels.

**General rule:** parse platform transcript structure and explicit sender
headers. A named third-party message is P0-CERTAIN; an unlabeled dialogue block
is P0-PROBABLE. A carrier such as “Her reply” is submission context, not
necessarily a separate D0 proposition.

### PN-5 — External web pages, documents, listings, and transcripts (13)

**Cases:** `adv_000136`, `adv_006804`, `adv_008147`, `adv_018536`,
`adv_019103`, `adv_019178`, `adv_021773`, `adv_026722`, `adv_028546`,
`adv_028560`, `adv_032016`, `adv_032700`, `adv_033117`

**Evidence:** product instructions, marketing email, page fragments, scraped
webpages, comparison tables, landing/search pages, a YouTube transcript, forms,
Stripe onboarding, listings, and promos carry page/navigation/commerce or
transcript structure.

**General rule:** use bounded structural fingerprints—URL/navigation chrome,
speaker/timestamp markers, form labels, commerce metadata, or explicit product
page fields. Do not infer P0 merely because text is polished or promotional.

### PN-6 — Other external/unknown artifacts (5)

**Cases:** `adv_001102`, `adv_021528`, `adv_029198`, `adv_030954`,
`adv_032023`

**Evidence:** forwarded spam, a pasted technical article, a hardening-delta
report, an article draft, and a prompt/search-results bundle are externally
framed but lack one uniform source signature.

**General rule:** keep these P0-PROBABLE or unresolved unless a local carrier,
document header, origin URL, sender, or traceable source independently establishes
authorship. Do not introduce a catch-all “long polished text = P0” rule.

## MIXED false positives — 6

### MF-1 — User-owned content mistaken for imported body (3)

**Cases:** `adv_002059`, `adv_030897`, `adv_033054`

**Evidence:** Derek's own Facebook auto-message plus request, his own GDI video
transcript plus instruction, and his own email body plus instruction.

**General rule:** two structural spans do not imply two authors. MIXED requires
positive evidence that the spans have different originators. First-party names,
links, or a traceable first-party source prevent automatic imported-body status.

### MF-2 — Pointer/reference mistaken for an inline imported span (1)

**Case:** `adv_006905`

**Evidence:** the message references a LinkedIn post by URL; the external
content is not reproduced as a substantive span.

**General rule:** classify URLs and source pointers as references, not imported
content spans. MIXED requires substantive inline material.

### MF-3 — Entire imported artifact over-segmented (2)

**Cases:** `adv_013001`, `adv_014438`

**Evidence:** the first is one AI-voice n8n checklist document; the second is a
third party's reply introduced by a carrier label. The frozen labels treat both
messages as P0 rather than finding an original Derek proposition.

**General rule:** a source label or carrier that merely identifies the pasted
body is metadata about submission, not automatically a D0 semantic span.

## MIXED false negatives — 21

### MN-1 — Traceable imported body swallowed the original carrier (9)

**Cases:** `adv_001443`, `adv_019337`, `adv_021989`, `adv_024223`,
`adv_026699`, `adv_028654`, `adv_030604`, `adv_033022`, `adv_034448`

These are the same records as PF-1. Use source alignment to bound the reused
body, then classify unmatched leading/trailing text independently. The matched
span must not consume adjacent original text.

### MN-2 — Unknown-origin pasted body not detected after a carrier (12)

**Cases:** `adv_005835`, `adv_006770`, `adv_018391`, `adv_021093`,
`adv_023273`, `adv_025184`, `adv_025673`, `adv_026055`, `adv_031360`,
`adv_031661`, `adv_033881`, `adv_034117`

**Evidence:** each starts with a compact user instruction, question, title, or
adoption phrase, then transitions to a product description, framework, pricing
page, guide, response, or external copy. Corpus overlap is absent or weak.

**General rule:** carrier + structural transition + materially different body
is sufficient to propose MIXED for review, but not sufficient to call the body
P0-CERTAIN. Emit a D0 carrier span and a `P0-PROBABLE`/`P0-UNRESOLVED` body span
with explicit review status. Message-level MIXED can therefore coexist with
uncertain authorship of the imported-looking span.

## AD3/AD4 error — 1

### AF-1 — Modification strength overshoot and frozen-label tension

**Case:** `adv_024918`  
**Gold:** D1 / AD3  
**V0.4:** D0 / AD4  
**Text:** “Yes but they will also do the webinar, lives, and discovery call”

The resolver treats “Yes but … also” as adoption plus material extension. That
is consistent with the current build-spec definition of AD4 (“adopts and
changes/extends it”) and especially with the tightened definition (“materially
modifies, integrates … or makes it part of another Derek system”). The frozen
blind label records AD3 instead. This is a genuine benchmark/spec tension, not
safe evidence for a one-case lexical patch.

**General rule:** resolve adoption at proposition level. AD4 requires an
identified parent proposition plus a separately representable, material Derek
transformation. A minor scope clarification remains AD3. If materiality cannot
be established from context, choose AD3 and flag review rather than using “but”
or “also” as an automatic AD4 trigger.

**Label inconsistency flag:** do not relabel the frozen case. Before Gate 5 is
claimed, governance should decide whether adding three execution channels is a
material transformation under the tightened AD4 definition. Until then, report
both strict frozen-score accuracy and spec-conformance accuracy.

## V0.5 generalized rule set

1. Run exact/near-source alignment before message classification and preserve
   unmatched prefix/suffix spans.
2. Separate **span composition** (`MIXED`) from **origin certainty**
   (`P0-CERTAIN`, `P0-PROBABLE`, `P0-UNRESOLVED`).
3. Recognize short carrier phrases only when followed by a structural boundary
   and a substantive body; a URL pointer alone is not a body.
4. Treat explicit source labels, platform sender headers, and bound agent report
   provenance as positive source evidence.
5. Treat style, polish, length, code, and generic report structure only as weak
   contextual evidence.
6. Require positive evidence of distinct authors before classifying MIXED; two
   document sections alone are insufficient.
7. Do not let partial shingle overlap override correction, quotation,
   continuation, or first-party execution-log context.
8. Resolve AD3/AD4 against a specific parent proposition and require a material,
   separately expressible transformation for AD4.

## Safety constraints for implementation

- Preserve the frozen V0.3/V0.4 D0 set.
- Do not use P0 expansion as negative evidence that increases D0.
- Keep untraceable imported-looking bodies reviewable rather than certain.
- Never convert absence of a source into evidence of Derek authorship.
- Keep the benchmark, blind adjudications, and prior resolver outputs immutable.

