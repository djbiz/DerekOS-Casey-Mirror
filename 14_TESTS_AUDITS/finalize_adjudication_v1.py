#!/usr/bin/env python3
"""Freeze blind adjudication labels for PROVENANCE_ADVERSARIAL_SET_V1.

Each decision: (evidence_class, originator, origin_id, adoption, confidence,
requires_review, note). origin_id = located origin message_id or 'UNKNOWN';
for located-origin records the script pulls the origin id from the
adversarial evidence package to keep the pointer exact.

Output: 14_TESTS_AUDITS/FROZEN_ADJUDICATION_V1.jsonl (one JSON per record),
plus a coverage/validation report printed to stdout. The resolver
predictions file is NOT read here — it stays sealed until scoring.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "14_TESTS_AUDITS" / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl"
OUT = ROOT / "14_TESTS_AUDITS" / "FROZEN_ADJUDICATION_V1.jsonl"

# ---------------------------------------------------------------- decisions
# (evidence_class, originator, origin_id, adoption, confidence, requires_review, note)
# origin_id: "LOCATED" -> take from evidence.reuse.origin_message_id; "UNKNOWN" otherwise
D = {
# --- batch 0
"adv_000136": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LiveGood product usage copy pasted as content source; no corpus origin"),
"adv_000318": ("D0", "derek", "N/A", "N/A", 0.75, True, "Own instruction for hook/description on own script"),
"adv_000346": ("MIXED", "derek", "N/A", "N/A", 0.85, False, "Segments: [D0 lead instruction] + [P0 external YouTube transcript]"),
"adv_000443": ("P0", "external", "UNKNOWN", "AD1", 0.90, False, "Verbatim pasted ChatGPT session about Mike Dillard ('ChatGPT said:' markers)"),
"adv_000735": ("MIXED", "derek", "N/A", "N/A", 0.85, False, "Segments: [D0 lead instruction] + [P0 external YouTube transcript]"),
"adv_000941": ("MIXED", "derek", "N/A", "N/A", 0.85, False, "Segments: [D0 lead instruction] + [P0 external YouTube transcript]"),
"adv_001011": ("P0", "assistant", "LOCATED", "AD2", 0.75, False, "Reused assistant-generated ProductInsight style guide (origin located, earlier conv)"),
"adv_001102": ("P0", "external", "UNKNOWN", "AD0", 0.92, False, "Forwarded MLM spam message (Pavankumar) submitted for assistant processing"),
"adv_001306": ("D0", "derek", "N/A", "N/A", 0.80, False, "Own bio + rewrite instruction"),
"adv_001324": ("MIXED", "derek", "N/A", "N/A", 0.75, False, "Segments: [D0 instruction] + [P0 reused assistant email, origin located same conv]"),
"adv_001326": ("MIXED", "derek", "N/A", "N/A", 0.70, True, "Segments: [D0 instruction] + [P0 canned MLM live-answer script]"),
"adv_001381": ("D0", "derek", "N/A", "N/A", 0.60, True, "Own instruction + own 'Moving abroad' example post (same text recurs as own content)"),
"adv_001443": ("MIXED", "derek", "N/A", "N/A", 0.70, False, "Segments: [D0 'create a prompt for DALE'] + [P0 reused assistant thumbnail outline, origin located]"),
"adv_001444": ("D0", "derek", "N/A", "N/A", 0.65, True, "Own instruction echoing assistant template placeholder"),
"adv_001794": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn thread paste (Kumail Mehdi/Derek); Derek side partly assistant-crafted"),
"adv_001825": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn profile/outreach paste (Maximilian Gaedcke)"),
"adv_001964": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn thread paste (Sandi Cohen etc.)"),
"adv_002015": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn thread paste (Sandi Cohen)"),
"adv_002059": ("D0", "derek", "N/A", "N/A", 0.70, False, "Own Facebook auto-message + improvement request"),
"adv_002297": ("D1", "derek", "N/A", "AD3", 0.95, False, "Explicit adoption: 'Yes, give me the full Forbes DAC plan!'"),
"adv_002323": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to explicit assistant offer via context"),
"adv_002846": ("D1", "derek", "N/A", "AD3", 0.90, False, "Explicit adoption: 'Yes, let's go Day 21!'"),
"adv_003147": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_003182": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn thread paste (Marissa Cyrus)"),
"adv_003529": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_003589": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_003597": ("MIXED", "derek", "N/A", "N/A", 0.75, False, "Segments: [D0 'wait before we move on please help'] + [P0 pasted LinkedIn exchange]"),
"adv_003710": ("D0", "derek", "N/A", "N/A", 0.75, False, "Own 'Limitless Business Model' pitch"),
"adv_004101": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own contact info + DAC affiliate links"),
"adv_004806": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
# --- batch 2
"adv_005835": ("MIXED", "derek", "N/A", "N/A", 0.70, True, "Segments: [D0 'Create this for DAC'] + [P0 external Joe Syverson NLP script]"),
"adv_005852": ("D0", "derek", "N/A", "N/A", 0.95, False, "Own personal situation statement (DAC, depression, $5k)"),
"adv_005890": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "Structured empire vision plan; authorship ambiguous (own vs assistant-compiled)"),
"adv_006124": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "Blockverse whitepaper; polished AI-style doc, no origin, no personal markers"),
"adv_006285": ("P0", "assistant", "LOCATED", "AD1", 0.92, False, "Verbatim assistant response pasted into new conversation (frac 1.0, origin located)"),
"adv_006770": ("MIXED", "derek", "N/A", "N/A", 0.60, True, "Segments: [D0 'more Hooks'] + [P0 assistant-style hooks list, origin unknown]"),
"adv_006804": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "SMART Challenge marketing email paste"),
"adv_006905": ("D0", "derek", "N/A", "N/A", 0.80, False, "Own request referencing a LinkedIn post (URL pointer)"),
"adv_007135": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Bare external LinkedIn URL paste"),
"adv_007257": ("D0", "derek", "N/A", "N/A", 0.85, False, "Own question about marketing persona idea"),
"adv_007453": ("D0", "derek", "N/A", "N/A", 0.70, True, "Own drafted message; polished but no reuse evidence"),
"adv_007563": ("MIXED", "derek", "N/A", "N/A", 0.75, False, "Segments: [D0 'Recreate this with 760 characters'] + [P0 reused assistant content, origin located]"),
"adv_007820": ("MIXED", "derek", "N/A", "N/A", 0.80, False, "Segments: [D0 'Recreate this for me and DAC'] + [P0 assistant transcription, origin located]"),
"adv_008147": ("P0", "external", "UNKNOWN", "AD0", 0.85, False, "Mid-article external fragment paste"),
"adv_009046": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "REST-API spec/code; authorship ambiguous (own project work vs external AI)"),
# --- batch 3
"adv_009731": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_009750": ("MIXED", "derek", "N/A", "N/A", 0.60, True, "Segments: [D0 question] + [P0 API names quoted from assistant, origin located]"),
"adv_010654": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "TensorFlow quantization code; authorship ambiguous"),
"adv_010840": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "n8n guide; polished AI-style doc, no origin"),
"adv_010955": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "Kotlin mesh-simulation code; authorship ambiguous"),
"adv_011018": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "JSX from assistant-built Vibe Marketing System re-submitted; origin in-conversation not located by builder"),
"adv_011310": ("P0", "assistant", "UNKNOWN", "AD1", 0.65, True, "Assistant-voice status report re-submitted"),
"adv_011482": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "LyfWallet UX feedback list; authorship ambiguous (own review vs pasted)"),
"adv_011599": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice patents-filter doc ('Below are three copy-paste-ready filters')"),
"adv_011640": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice packaging guide ('Below is everything you need to ship...')"),
"adv_011641": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice intro + script ('Here is a drop-in upgrade that folds...')"),
"adv_011746": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice bonus-feature snippets ('Below are the copy-paste snippets...')"),
"adv_011993": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice 30-day plan ('Below is a step-by-step...')"),
"adv_012035": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice Creator-Scout module doc"),
"adv_012068": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice supplier swap-list doc"),
# --- batch 4
"adv_012199": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice 48-hour prototype doc"),
"adv_012210": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice TRAUMA-V2.1 upgrade doc"),
"adv_012236": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice Sprint 5 pack doc"),
"adv_012410": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice DUPE-PROOF automation recipe"),
"adv_012412": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice SEOForge add-ons doc"),
"adv_012420": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice 'Agency in a Box' doc"),
"adv_012485": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice reverse-funnel numbers doc"),
"adv_012699": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_012771": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice Confidence Gate spec"),
"adv_013001": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice n8n checklist doc"),
"adv_013200": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice 100M Business Factory doc"),
"adv_013280": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice Novation-to-Rent power-play doc"),
"adv_013330": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_013750": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice n8n workflow recipe doc"),
"adv_014438": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Third-party's chat reply pasted for coaching ('Her reply.')"),
# --- batch 5
"adv_014464": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Third-party dating-chat message pasted for coaching"),
"adv_014544": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Third-party dating-chat message pasted for coaching"),
"adv_014859": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_015875": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_016153": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_016489": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_016498": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-voice cost breakdown doc"),
"adv_016513": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_016630": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_016642": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice Empire 2025 code package"),
"adv_016684": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_016717": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_016829": ("P0", "assistant", "UNKNOWN", "AD1", 0.65, True, "AI-voice Empire 19.0 fantasy doc (assistant in-convo called it unreal)"),
"adv_016944": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_017675": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
# --- batch 6
"adv_017867": ("P0", "assistant", "UNKNOWN", "AD1", 0.60, True, "AI-voice Empire OS v-infinity package doc"),
"adv_017930": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_017999": ("D0", "derek", "N/A", "N/A", 0.85, False, "Own request to make system self-learning/interoperable"),
"adv_018019": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_018155": ("MIXED", "derek", "N/A", "N/A", 0.70, False, "Segments: [D0 'Is this inside the system.'] + [P0 AI-voice upgrade script, origin unknown]"),
"adv_018391": ("MIXED", "derek", "N/A", "N/A", 0.75, False, "Segments: [D0 'Can you create a python code with this inside'] + [P0 external product description]"),
"adv_018415": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_018484": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_018536": ("P0", "external", "UNKNOWN", "AD1", 0.90, False, "Scraped RealPage Lumina webpage paste"),
"adv_018613": ("P0", "assistant", "UNKNOWN", "AD1", 0.90, False, "Another AI's full response pasted ('I'll help you create...')"),
"adv_018887": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_019103": ("P0", "external", "UNKNOWN", "AD0", 0.85, False, "SaaS feature-comparison table paste"),
"adv_019128": ("P0", "assistant", "UNKNOWN", "AD1", 0.85, False, "Another AI's architecture review pasted ('The blueprint you outlined is solid...')"),
"adv_019150": ("D0", "derek", "N/A", "N/A", 0.85, False, "Own workflow/pipeline description"),
"adv_019178": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Webinar landing page paste"),
# --- batch 7
"adv_019222": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_019337": ("MIXED", "derek", "N/A", "N/A", 0.70, True, "Segments: [D0 'Can we add this.'] + [P0 tax-strategy content, origin located frac 0.718]"),
"adv_019425": ("MIXED", "derek", "N/A", "N/A", 0.70, False, "Segments: [D0 'Is this inside the system.'] + [P0 AI-voice script, origin unknown]"),
"adv_019452": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_019529": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_020243": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_020428": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_020646": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_021093": ("MIXED", "derek", "N/A", "N/A", 0.65, True, "Segments: [D0 'I can be a life coach with this'] + [P0 AI-voice framework doc, origin unknown]"),
"adv_021289": ("P0", "assistant", "UNKNOWN", "AD1", 0.70, True, "AI-voice Notion script doc ('Here is an updated and extended version...')"),
"adv_021528": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Pasted article on building multi-agent systems with Gemini API"),
"adv_021773": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Google search-results page paste"),
"adv_021920": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_021989": ("MIXED", "derek", "N/A", "N/A", 0.65, True, "Segments: [D0 question] + [P0 action list quoted from assistant, origin located]"),
"adv_021994": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
# --- batch 8
"adv_022114": ("P0", "assistant", "UNKNOWN", "AD1", 0.85, False, "Another AI's Mega-Agent technical response pasted"),
"adv_022216": ("P0", "assistant", "LOCATED", "AD1", 0.90, False, "Another AI's response pasted; origin located (frac 0.93)"),
"adv_022859": ("P0", "assistant", "UNKNOWN", "AD1", 0.85, False, "AI-voice street-smart cash engine code ('Author: AI Cash Flow Specialist')"),
"adv_023273": ("MIXED", "derek", "N/A", "N/A", 0.65, True, "Segments: [D0 'Can this work as a business model.'] + [P0 external offer copy]"),
"adv_023641": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_023806": ("P0", "assistant", "UNKNOWN", "AD1", 0.80, False, "Another AI's Bitcoin lottery build guide pasted"),
"adv_023994": ("D0", "derek", "N/A", "N/A", 0.80, False, "Own statement + hardware product reference"),
"adv_024223": ("MIXED", "derek", "N/A", "N/A", 0.80, False, "Segments: [D0 question] + [P0 assistant VSL content, origin located frac 0.969]"),
"adv_024593": ("D0", "derek", "N/A", "N/A", 0.80, False, "Own question + own tool list (re-sent edited version)"),
"adv_024682": ("D0", "derek", "N/A", "N/A", 0.60, True, "Own correction + continuation of own document ('No. Here's the rest:')"),
"adv_024794": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_024918": ("D1", "derek", "N/A", "AD3", 0.85, False, "Own substantive approval + requirement ('Yes but they will also do...')"),
"adv_024945": ("D0", "derek", "N/A", "N/A", 0.75, False, "Own 'Villain-Hero-Savior' framework ('what I call')"),
"adv_025184": ("MIXED", "derek", "N/A", "N/A", 0.50, True, "Segments: [D0 question] + [P0 AI-voice engagement factors body, origin unknown]"),
"adv_025602": ("P0", "assistant", "UNKNOWN", "AD1", 0.70, True, "Another AI's medical analysis pasted (addresses Derek's symptoms)"),
# --- batch 9
"adv_025657": ("D0", "derek", "N/A", "N/A", 0.75, True, "Own correction re disability hearing; quotes assistant-listed phrases"),
"adv_025673": ("MIXED", "derek", "N/A", "N/A", 0.70, False, "Segments: [D0 'This is the plan I'm going to have'] + [P0 Hostinger pricing page paste]"),
"adv_025720": ("D0", "derek", "N/A", "N/A", 0.85, False, "Own need statement for automated reporting dashboard"),
"adv_026055": ("MIXED", "derek", "N/A", "N/A", 0.60, True, "Segments: [D0 title] + [P0 PicoClaw guide paste]"),
"adv_026247": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_026252": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "Timestamped podcast summary notes; authorship of notes unknown"),
"adv_026480": ("D1", "derek", "N/A", "AD3", 0.80, True, "Bare 'Yes' resolving to assistant offer via context"),
"adv_026699": ("MIXED", "derek", "N/A", "N/A", 0.85, False, "Segments: [D0 question] + [P0 AI execution plan, origin located frac 0.977]"),
"adv_026722": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "YouTube video transcript paste (AI Business Blueprint)"),
"adv_027022": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.70, True, "Autonomous agent (Zo) system-handoff report pasted"),
"adv_027069": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.65, True, "Autonomous agent campaign report pasted"),
"adv_027082": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.65, True, "Autonomous agent (Felix stack) report pasted"),
"adv_027153": ("D0", "derek", "N/A", "N/A", 0.75, False, "Own operational priorities + market notes brief"),
"adv_027470": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Agent/system pipeline status report pasted"),
"adv_027517": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own terminal (ollama) output paste — operational log"),
# --- batch 10
"adv_027554": ("P0", "assistant", "UNKNOWN", "AD1", 0.70, True, "AI-voice Vox Day-2 questionnaire pasted (AI addressing Derek)"),
"adv_027661": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own PowerShell terminal output — operational log"),
"adv_027678": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own PowerShell terminal output — operational log"),
"adv_027736": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Agent credential-sweep report pasted"),
"adv_027756": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.55, True, "Agent/system dashboard-state correction report pasted"),
"adv_027762": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "Operational memo ('Memory updated...'); agent-vs-Derek authorship ambiguous"),
"adv_027814": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own Python error output — operational log"),
"adv_027815": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own Python error output — operational log"),
"adv_027927": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own docker ps output — operational log"),
"adv_027972": ("D0", "derek", "N/A", "N/A", 0.80, False, "Own analytical argument on VOX growth discipline"),
"adv_027980": ("P0", "assistant", "UNKNOWN", "AD1", 0.85, False, "Another AI data-agent's refusal message pasted"),
"adv_027990": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Agent task-execution report pasted"),
"adv_028025": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Agent memory/doc-update report pasted"),
"adv_028040": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Agent connector-analysis report pasted"),
"adv_028118": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Agent build/QA report pasted"),
# --- batch 11
"adv_028170": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Code-agent change-summary report pasted"),
"adv_028257": ("D0", "derek", "N/A", "N/A", 0.55, True, "Own tool/system-prompt configuration instructions"),
"adv_028263": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "VOX sprint plan doc (agent-generated project artifact)"),
"adv_028277": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "VOX sprint 11 completion report (agent-generated)"),
"adv_028378": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "VOX sprint 28 completion report (agent-generated)"),
"adv_028382": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "Code-agent session report (migration work) pasted"),
"adv_028394": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "VOX sprint 7 plan doc (agent-generated)"),
"adv_028399": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "VOX Ghost Protocol plan doc (agent-generated)"),
"adv_028404": ("P0", "assistant", "UNKNOWN", "AD1", 0.80, False, "Another AI's landing-page copy response pasted"),
"adv_028407": ("P0", "assistant", "LOCATED", "AD1", 0.90, False, "Another AI's pivot response pasted; origin located (frac 0.996)"),
"adv_028411": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "VOX sprint 2 plan doc (agent-generated)"),
"adv_028444": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.60, True, "VOX sprint 13 Business Memory OS plan doc (agent-generated)"),
"adv_028546": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Form (work-history) paste"),
"adv_028560": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Stripe onboarding page paste"),
"adv_028654": ("MIXED", "derek", "N/A", "N/A", 0.80, False, "Segments: [D0 'Can we add this in...'] + [P0 AI revenue-engine package, origin located frac 0.919]"),
# --- batch 12
"adv_028920": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.90, False, "Explicitly labeled 'From Gemini:' agent report"),
"adv_028925": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.90, False, "Explicitly labeled 'CodeOne:' agent report"),
"adv_028973": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.90, False, "Explicitly labeled 'From Hermes:' agent report"),
"adv_029000": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.90, False, "Explicitly labeled 'From OpenCode:' agent report"),
"adv_029035": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.80, False, "Agent session report (Nextcloud Artifact Storage v1)"),
"adv_029198": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.80, False, "Agent hardening-delta report pasted"),
"adv_029212": ("P0", "ai_agent", "UNKNOWN", "AD1", 0.90, False, "Explicitly labeled 'From Codex:' agent report"),
"adv_029474": ("MIXED", "derek", "N/A", "N/A", 0.70, False, "Segments: [D0 'Can you rewrite this...'] + [P0 external product benefits copy]"),
"adv_030062": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn messages paste (Wanda Perry)"),
"adv_030092": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn messages paste (Nathan Grimes)"),
"adv_030104": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn messages paste (Su Thinzar Han); Derek side assistant-crafted"),
"adv_030107": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn spam paste (Adrian Moore)"),
"adv_030132": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn messages paste (Marcus Rexwall)"),
"adv_030261": ("MIXED", "derek", "N/A", "N/A", 0.80, False, "Segments: [D0 lead instruction] + [P0 external YouTube transcript]"),
"adv_030342": ("P0", "assistant", "LOCATED", "AD2", 0.75, False, "Reused assistant-generated Savvy Shopper style guide (origin located frac 0.793)"),
# --- batch 13
"adv_030604": ("MIXED", "derek", "N/A", "N/A", 0.70, True, "Segments: [D0 'Please update this style guide...'] + [P0 reused style guide, origin located frac 0.627]"),
"adv_030670": ("D0", "derek", "N/A", "N/A", 0.80, False, "Own reflective writing on going one's own way"),
"adv_030780": ("D0", "derek", "N/A", "N/A", 0.60, True, "Own 'Moving abroad' post (recurs in corpus as own content)"),
"adv_030804": ("D0", "derek", "N/A", "N/A", 0.85, False, "Own reflective rant on 'broke people' mindset"),
"adv_030864": ("UNRESOLVED", "unknown", "UNKNOWN", "AD0", 0.0, True, "Motivational Labor Day greeting; forwarded-vs-own ambiguous"),
"adv_030897": ("D0", "derek", "N/A", "N/A", 0.70, True, "Transcript of Derek's OWN GDI video presentation + instruction"),
"adv_030954": ("P0", "assistant", "UNKNOWN", "AD1", 0.55, True, "AI-style article draft paste (How to Train Your Dragon)"),
"adv_031072": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn messages paste (JuJuan Buford)"),
"adv_031092": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn messages paste (Santa Whitewolf)"),
"adv_031229": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "LinkedIn/Messenger messages paste (Janice Firebrand)"),
"adv_031360": ("MIXED", "derek", "N/A", "N/A", 0.70, False, "Segments: [D0 'Can you rewrite this...'] + [P0 external product copy]"),
"adv_031597": ("MIXED", "derek", "N/A", "N/A", 0.70, True, "Segments: [D0 'Can you rewrite this only 1000 characters'] + [P0 store copy, origin located]"),
"adv_031661": ("MIXED", "derek", "N/A", "N/A", 0.70, False, "Segments: [D0 'create a reply from this?'] + [P0 external forum message]"),
"adv_031889": ("P0", "assistant", "LOCATED", "AD1", 0.65, False, "Reused assistant article-intro template (origin located frac 0.507)"),
"adv_032016": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "Product listing title paste"),
# --- batch 14
"adv_032023": ("P0", "external", "UNKNOWN", "AD1", 0.60, True, "Pasted QA prompt template + search results"),
"adv_032030": ("P0", "assistant", "LOCATED", "AD1", 0.65, False, "Reused assistant article-structure template (origin located frac 0.375)"),
"adv_032700": ("P0", "external", "UNKNOWN", "AD0", 0.85, False, "Network-marketing course promo paste"),
"adv_032963": ("MIXED", "derek", "N/A", "N/A", 0.80, False, "Segments: [D0 lead instruction] + [P0 external YouTube transcript]"),
"adv_033022": ("MIXED", "derek", "N/A", "N/A", 0.65, True, "Segments: [D0 'can you also add this formatte'] + [P0 article template, origin located frac 0.252]"),
"adv_033054": ("D0", "derek", "N/A", "N/A", 0.80, False, "Own instruction + own email body (his name/links)"),
"adv_033108": ("P0", "assistant", "LOCATED", "AD1", 0.65, False, "Reused assistant article-structure template (origin located frac 0.489)"),
"adv_033117": ("P0", "external", "UNKNOWN", "AD0", 0.90, False, "GotBackup MLM promo paste"),
"adv_033504": ("P0", "assistant", "UNKNOWN", "AD1", 0.80, False, "Another AI's critique response pasted"),
"adv_033685": ("P0", "assistant", "UNKNOWN", "AD1", 0.85, False, "Another AI's praise/verdict response pasted"),
"adv_033720": ("P0", "assistant", "LOCATED", "AD1", 0.85, False, "Another AI's response pasted; origin located (frac 0.776)"),
"adv_033805": ("P0", "assistant", "LOCATED", "AD1", 0.85, False, "Another AI's code package pasted; origin located (frac 0.593)"),
"adv_033881": ("MIXED", "derek", "N/A", "N/A", 0.70, True, "Segments: [D0 'should we do this for all games'] + [P0 another-AI response body]"),
"adv_033891": ("P0", "assistant", "UNKNOWN", "AD1", 0.85, False, "Another AI's Empire OS 2B implementation response pasted (addresses Derek as EMPEROR)"),
"adv_034117": ("MIXED", "derek", "N/A", "N/A", 0.70, True, "Segments: [D0 'Can we add this to the system.'] + [P0 another-AI ScoreApp architecture body]"),
# --- batch 15
"adv_034205": ("P0", "assistant", "UNKNOWN", "AD1", 0.80, False, "Another AI's integration response pasted"),
"adv_034335": ("P0", "assistant", "UNKNOWN", "AD1", 0.80, False, "Another AI's review response pasted"),
"adv_034448": ("MIXED", "derek", "N/A", "N/A", 0.75, False, "Segments: [D0 'can we add this to Jarvis.'] + [P0 timelessness content, origin located frac 0.675]"),
"adv_034886": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own psql terminal output — operational log"),
"adv_034912": ("D0", "derek", "N/A", "N/A", 0.90, False, "Own docker worker log output — operational log"),
}

SEGMENTS = {
"adv_000346": [("lead instruction", "D0"), ("YouTube transcript", "P0")],
"adv_000735": [("lead instruction", "D0"), ("YouTube transcript", "P0")],
"adv_000941": [("lead instruction", "D0"), ("YouTube transcript", "P0")],
"adv_001324": [("'Can you create a follow-up email...'", "D0"), ("pasted assistant email", "P0")],
"adv_001326": [("'Can you rewrite this...'", "D0"), ("canned live-answer script", "P0")],
"adv_001443": [("'create a prompt for DALE:'", "D0"), ("thumbnail outline from assistant", "P0")],
"adv_003597": [("'wait before we move on please help with this'", "D0"), ("LinkedIn exchange", "P0")],
"adv_005835": [("'Create this for DAC...'", "D0"), ("Joe Syverson NLP script", "P0")],
"adv_006770": [("'more Hooks'", "D0"), ("hooks list", "P0")],
"adv_007563": [("'Recreate this with 760 characters'", "D0"), ("marketing content (assistant origin)", "P0")],
"adv_007820": [("'Recreate this for me and DAC.'", "D0"), ("transcription (assistant origin)", "P0")],
"adv_009750": [("'What can be done with these API keys'", "D0"), ("API names quoted from assistant", "P0")],
"adv_018155": [("'Is this inside the system.'", "D0"), ("upgrade script", "P0")],
"adv_018391": [("'Can you create a python code with this inside..'", "D0"), ("product description", "P0")],
"adv_019337": [("'Can we add this.'", "D0"), ("tax-strategy content (assistant origin)", "P0")],
"adv_019425": [("'Is this inside the system.'", "D0"), ("Python script", "P0")],
"adv_021093": [("'I can be a life coach with this'", "D0"), ("framework doc", "P0")],
"adv_021989": [("'Can't we put a limit...'", "D0"), ("action list quoted from assistant", "P0")],
"adv_023273": [("'Can this work as a business model.'", "D0"), ("GMB offer copy", "P0")],
"adv_024223": [("'Can I create this for my clients instead...'", "D0"), ("VSL content (assistant origin)", "P0")],
"adv_025184": [("'What if my funnels...'", "D0"), ("engagement factors body", "P0")],
"adv_025673": [("'This is the plan I'm going to have...'", "D0"), ("Hostinger pricing page", "P0")],
"adv_026055": [("'Run on old Android Phones'", "D0"), ("PicoClaw guide", "P0")],
"adv_026699": [("'Should this be my first TikTok shop...'", "D0"), ("AI execution plan (assistant origin)", "P0")],
"adv_028654": [("'Can we add this in when you're finished...'", "D0"), ("revenue-engine package (assistant origin)", "P0")],
"adv_029474": [("'Can you rewrite this in the style of Kevin James'", "D0"), ("product benefits copy", "P0")],
"adv_030261": [("lead instruction", "D0"), ("YouTube transcript", "P0")],
"adv_030604": [("'Please update this style guide...'", "D0"), ("style guide (assistant origin)", "P0")],
"adv_031360": [("'Can you rewrite this...'", "D0"), ("selfie ring light copy", "P0")],
"adv_031597": [("'Can you rewrite this only 1000 characters please?'", "D0"), ("store copy (assistant origin)", "P0")],
"adv_031661": [("'create a reply from this?'", "D0"), ("Crush Store forum message", "P0")],
"adv_032963": [("lead instruction", "D0"), ("YouTube transcript", "P0")],
"adv_033022": [("'can you also add this formatte to the guide'", "D0"), ("article template (assistant origin)", "P0")],
"adv_033881": [("'should we do this for all games not just fortnight.'", "D0"), ("another-AI response body", "P0")],
"adv_034117": [("'Can we add this to the system.'", "D0"), ("another-AI ScoreApp architecture body", "P0")],
"adv_034448": [("'can we add this to Jarvis.'", "D0"), ("timelessness content (assistant origin)", "P0")],
}

# ------------------------------------------------------------------- build
def main():
    with SET.open(encoding="utf-8") as f:
        adv = [json.loads(l) for l in f if l.strip()]
    ids = {r["adversarial_id"] for r in adv}

    missing = ids - set(D)
    extra = set(D) - ids
    assert not missing, f"MISSING decisions: {sorted(missing)}"
    assert not extra, f"Unknown ids in table: {sorted(extra)}"
    assert len(D) == len(ids) == 230, f"count mismatch: decisions={len(D)} set={len(ids)}"

    rows = []
    stats = {}
    review_count = 0
    for r in adv:
        aid = r["adversarial_id"]
        cls, org, oid, adopt, conf, review, note = D[aid]
        if oid == "LOCATED":
            reuse = (r.get("evidence") or {}).get("reuse") or {}
            oid = reuse.get("origin_message_id") or "UNKNOWN"
        segs = [{"span": s, "evidence_class": c} for s, c in SEGMENTS.get(aid, [])]
        row = {
            "adversarial_id": aid,
            "message_id": r["message_id"],
            "conversation_id": r["conversation_id"],
            "conversation_title": r.get("conversation_title"),
            "timestamp": r.get("timestamp"),
            "source_file": r.get("source_file"),
            "categories": r.get("categories", []),
            "evidence_class": cls,
            "originator": org,
            "origin_record_id": oid,
            "submitted_by": "derek",
            "adoption_status": adopt,
            "provenance_confidence": conf,
            "requires_review": review,
            "segments": segs,
            "notes": note,
            "adjudication_agent": "claude+auditbot-blind-adjudication-v1",
            "resolver_prediction_seen": False,
        }
        rows.append(row)
        stats[cls] = stats.get(cls, 0) + 1
        if review:
            review_count += 1

    with OUT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"frozen records written: {len(rows)} -> {OUT.name}")
    print("class distribution:", json.dumps(stats, sort_keys=True))
    print(f"requires_review (human adjudication queue): {review_count}")
    print("coverage: 230/230 OK")

if __name__ == "__main__":
    main()
