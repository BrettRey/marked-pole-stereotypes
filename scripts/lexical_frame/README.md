# Lexical curation: source import and 40-term pilot

Prospective specification, 2026-10-10. Brett authorized this stage after the
review of [the revised plan](../../notes/lexical-frame-freeze-plan-2026-10-10.md).
No full-vocabulary model coding, commonness collection or outcome fit is part
of this stage. All research inputs must come from their recorded sources.

The first import uses Anderson's existing portfolio PDF, the publisher's
Warriner supplementary archive and Princeton WordNet 3.1. Record complete
input hashes and access routes. Inspect the archive licence and headers;
export vocabulary only. Anderson's text layer is OCR: preserve its raw
extraction, source coordinates and every image-verified correction. A source
row is not a unique lexical item. Account for duplicates and normalize only
case, Unicode, spacing and dash variants, retaining the original spelling.

The source table and complete vocabulary remain under `data/raw/` and
`private/` until distribution rights are established. Public summaries may
report aggregate import and audit findings. Raw values and PDFs never enter
git. Dictionary-derived evidence retains the WordNet licence and attribution.

The random pilot half is ten Anderson terms and ten additional distinct
Warriner terms, sampled from normalized source lists with seed `20261010`.
Membership in both sources remains recorded; random allocation does not
erase overlap. Do not filter on a predominant part-of-speech label. The
challenge half contains twenty additional imported terms and complete pair
cases spanning supported affixation, false morphology, ambiguous sense
alignment, missing/ineligible counterparts and shared bases. Freeze the
actual selection with source IDs and reasons before model calls. If a
requested case is absent, record the gap rather than inventing an entry.

Code eligibility for each adjective sense or supported interpretation:
personality, interpersonal behaviour, psychological state or capacity.
Preserve physical-only, object-only, membership-only, record-only and
non-adjective readings as exclusions at the sense level. Keep stable and
temporary readings distinguishable. Dictionary gaps are unresolved, not
evidence that a word or base does not exist. WordNet sense order does not
determine selection. Group synonymous senses into task-relevant
interpretations only with an explicit justification.

Two separately invoked model families code the same supplied evidence.
Use fresh neutral work directories, no tools, no project instructions, no
rating columns and no supplied substantive prediction. Preserve exact model
IDs, prompts, parameters, elapsed time and reported usage. This withholds
specified current inputs; it does not demonstrate lack of training exposure.
The pilot is a workflow check, not an accuracy estimate. Agreement is
consistency, not validity. Stronger models are warranted for source-sensitive
sense distinctions; unavailable OpenRouter credit is not used. Local large
models would compete with the active sampler, so this pilot uses existing
Codex and Claude subscription routes, with returned model IDs verified.

Operational morphology uses the immediate pairing **base**, not a deeper
root. Generate candidates through the agreed prefix inventory and privative
`-less`, then verify evidence and sense compatibility. Keep `-less` nominal
bases separate from primary adjective pairs. Record these failure categories
separately, allowing multiple flags:

- `counterpart_absent_from_sources`
- `counterpart_absent_from_dictionary`
- `counterpart_present_but_ineligible`
- `no_compatible_sense_alignment`
- `not_supported_affixation`
- `unresolved_evidence`

Both members must occur in the independently eligible source vocabulary.
Anderson-only pairs require both members in Anderson; expanded pairs can
cross sources. Record shared word and base IDs and alternative alignments.
The detector cannot define the entire audit universe. Independently inspect
all pilot challenge words with apparent negative morphology against lexical
evidence without showing detector decisions. Compare these candidates only
after they are saved, and review rejected and absent-counterpart cases too.

Resolve identifiers programmatically and check their supporting glosses
against the written rule. Audit every pilot pair, source gap and disagreement;
also review all pilot word decisions (the pilot is smaller than the proposed
full-pass audit budget). A future full-pass audit divides each 50-case
inclusion/exclusion budget into 25 random and 25 targeted cases, reported
separately. Systematic mistakes require correction of the affected class.
All revisions and reruns retain their original outputs and reasons.

The pilot report must propose a source-entry → lexical-item → interpretation
→ judgment-target mapping. Description-based judgments identify a specified
interpretation; an unglossed word judgment remains a distinct lexical-cue
measurement. Multiple dictionary senses do not automatically create units.
Alternative interpretations define separate analysis specifications unless
an explicit mixture is justified. Within each specification each lexical
item retains one unit of weight. Shared-word/base graphs accompany counts.
Temporary-state targets need an explicit temporal reference; momentary
occurrence, repeated display and ever-occurrence remain separate. No lexical
package is fully frozen while its intended population, time reference or
presentation remains unspecified.

Keep source rating tasks distinct. Anderson measures person-likableness;
Warriner rates isolated words' affective valence. Attach source, instructions
and a compatibility flag (`supported`, `potentially_mismatched`, `unresolved`)
to any later sense-specific use. Do not use spelling joins or numerical
rescaling as validation. This pilot does not join numerical ratings into
coding inputs; compatibility assessment concerns the source task and sense
evidence. Problems qualify measurement, not lexical eligibility.

Every execution log records source commit, script/input hashes, fixed seeds,
commands, timestamps and tool/package versions. Commit and push each revised
specification and executable before the corresponding empirical execution.
Retain interrupted or failed records. Scientific source files for the active
D1c queues are not part of this implementation.

The report will show actual import counts and overlap, normalization and
source gaps, boundary decisions, complete accepted/rejected/unresolved pair
examples, proposed judgment targets, and observed coding/review/rerun costs.
Proceeding beyond the pilot requires defensible rules or explicit alternatives
for observed problems, not a high agreement score or a claim of full coverage.

After import 1 (2026-10-10): the Anderson OCR yielded 561 lines because six paragraph/footnote lines below the final table entered the last left column. The page image fixes the lower table boundary at y=210 PDF points on page 6. Import v2 retains v1 and applies that boundary. All ten word columns were inspected; six OCR corrections are recorded separately, and two apparent printed spelling variants remain explicit. Warriner contains 13,915 source rows and 13,905 case-folded forms; capitalization distinctions and source rows are retained, not assumed to be identical lexical senses. Its ZIP contains one CSV and no licence file, so public download is not treated as a redistribution licence.

Before coding the 40-term pilot (2026-10-10): the first packet identifies eleven terms with no WordNet adjective sense. Apply one supplementary policy to all eleven: retrieve and pin English Wiktionary revisions, then expose only English definition lines, omitting usage notes and quotations. Preserve unresolved absence; do not infer nonexistence. Rebuild the packet as v2 before any coding call. WordNet lookup is case-insensitive but retains original lemmas and every matching sense; this avoids accidentally dropping proper/capitalized entries. The earlier packet and its manifest remain. The model routes passed neutral connection probes: Codex gpt-6.1-sol with high reasoning and Claude claude-sonnet-4-6; probes contain no research items. Their prompts and coding schemas follow in a separate pre-call commit.

Coding v1 specification (2026-10-10): `word-prompt.txt` and `pair-prompt.txt`
are the exact frozen rubrics. `code_pilot.py words` makes four fresh calls of
ten alphabetized terms per model family; `pairs` makes one fresh independent
candidate-generation call per family over all forty terms. Codex CLI 0.161.0
uses `gpt-6.1-sol`, high reasoning; Claude CLI 2.1.296 uses
`claude-sonnet-4-6`, high effort. These are structured research judgments,
not the older no-reasoning OCR instrument. The neutral directories and
scrubbed environments prevent repository or peer-answer access. Prompts are
identical across families. Schemas differ only through provider transport.
Current source selection is fixed at seed 20261010; neither route exposes a
sampling seed here. Do not claim bitwise reproducibility of remote inference.

Use existing subscription routes, with no API keys in either child's
environment. Claude's $5 per-call limit is an API-equivalent accounting guard,
not permission to buy API credits. Record actual returned usage separately
from subscription cost. A transport failure stops that family's further
calls; an evidence-validation failure remains visible for review, not an
automatic silent retry. The strict schema and identifier/substring checks
test evidence integrity, while substantive evidence review checks support.

Every pilot word decision will receive source-based review by the primary
agent after both families finish, including agreements and all original
adjective senses. Independent pair lists are retained before joining to the
mechanical detector. Check all proposed, rejected, absent-counterpart and
missed candidates against source membership and dictionary evidence. Preserve
model outputs and a separate adjudication record; unresolved rules become
explicit alternatives rather than forced consensus. If a rubric changes,
publish the revision and rerun every affected pilot case before calling it
stable. Full-frame coding and commonness collection remain unauthorized here.

Source-bearing prompts and raw answers stay in `private/` because the source
word-table redistribution conditions remain unresolved; publish prompts as
templates, software, aggregate cost and audit summaries, and selected brief
examples with attribution. This source-specific restriction takes precedence
over the older generic instruction to publish complete scripted transcripts.
The simulation environment lacks `requests`; lexical imports use the logged
system Python 3.14.8 with requests 2.34.2. The first supplement invocation in
`.venv` failed at import before reading or writing any research data, then ran
successfully under the specified lexical-import interpreter.

After the first coding calls started (2026-10-10): Claude's strict JSON
transport advertises a `StructuredOutput` serialization tool even when its
research tool list is empty. The initial validator treats this as forbidden
and will retain the completed answer as a transport-validation failure. The
correction accepts only this schema serializer, checks the exact model and
continues to reject every file/network/shell tool. `resume_claude.py` preserves
the original failure manifest, reparses the saved response without a new
inference call, and then submits only unattempted batches. Prompts, models,
effort and research inputs do not change.

The independent calls need no ordering. After observing the first Claude call's
latency, `finish_words.py` submits only its three unattempted word batches,
with two concurrent calls, preserving the original prompt, model and effort.
The failed serializer check prevents the original word supervisor from
submitting those batches. No duplicate call or extra research item is added.

After pair pilot v1 (2026-10-10): identifier/quote checks passed, but substantive
review found unsupported etymology in one answer and complement readings
inferred just from dictionary glosses using *not* or *lack*. Those glosses do
not establish exhaustive categories. `pair-recheck-addendum.txt` adds an
explicit same-time/same-respect neither/both diagnostic, an unresolved route,
and a prohibition on unsupplied historical assertions. `recheck_pairs.py`
reruns the entire affected class (all pilot pair analyses) in both families,
with fresh contexts and unchanged source packets. It does not show either
original model answer or detector output. The original independent candidate
lists and decisions remain preserved. This is a post-pilot instrument revision,
not a claim that the original coding was prospectively adequate. No word
eligibility judgment or commonness judgment is silently replaced by this run.

Source-audit assembly (2026-10-10): `audit_pilot.py` combines all forty word
decisions and ninety-three adjective senses from each family, the original
independent pair lists, and their v2 rechecks. The primary agent's complete
post-pilot review is retained separately in private `pilot-audit-rules.json`,
with its hash logged. Original answers are immutable. The audit checks every
identifier and quote again. A quote rendered from Wiktionary links can match
their deterministic display text; the source wikitext and mismatch remain in
the record. This repairs representation, not meaning, with no new inference.

Nine pilot terms have entries but no supported adjective sense after both
resources were checked. Keep two explicit operational treatments: the
conservative coverage table leaves them unresolved; a resource-attested
adjective specification does not admit them, without claiming they have no
adjective use anywhere. Entry absence still requires the unresolved route.
The pilot report recommends the latter as a reproducible resource-boundary
rule, with the conservative table preserved. This is a proposed frame rule,
not a silently finalized exclusion list. No source list is expanded.

Record substantive audit disagreement and interpretation alternatives even
when whole-word eligibility agrees. The audit's labels are primary-agent
source judgments, not an independent gold standard. It also checks all
candidate/rejected pairs and source gaps, includes the shared-word/base graph,
and reports bounded missed-pair audit results without estimating recall.
Actual inference usage and API-equivalent accounting are logged. Primary-agent
evidence review occurred alongside model calls and is not separately metered;
the report must not advertise inference-only throughput as total curation cost.

Each model call retains its fixed 900-second limit. A failed final pair
recheck is reported as a failed attempt, with its elapsed time, rather than
causing another unplanned call or suppressing the completed original pilot.
The assembler requires both complete original word/pair passes; it can retain
a missing v2 recheck transparently, without manufacturing a replacement answer
or claiming complete inference-cost accounting for a timed-out transport.

After Brett’s report review (2026-10-10): *adjective* is a lexical category, not a function or a use. A noun and an adjective can share a spelling; attributive modifier and predicative complement are functions. Legacy `word`/`word_status` fields in the retained pilot mean source-form aggregates. The eventual frame needs a separate lexical-item layer between normalized forms and interpretations; current form hashes do not settle lexical identity. This clarifies terminology without altering any recorded model response or count. The uniform/iform row is explicitly a string-detector false positive: uniform has uni-, not negative un-, and iform was never accepted as a lexical counterpart. The report’s US population suggestion concerns what models judge, not human recruitment; only the calibrated arm inherits the existing average-American wording. Adult-only and fixed twelve-month and thirty-day windows are not settled defaults for the description arm. No additional inference call follows these report corrections.

## Existing-evidence inventory (2026-10-11)

The adopted next-stage decisions put an evidence inventory before the production budget. `evidence_inventory.py` reads the frozen vocabulary-only import, the pinned WordNet archive and already registered Wiktionary entries. It verifies their hashes and retains form/source IDs, spelling variants, alias lookups, dictionary evidence, evidence lengths and unresolved coverage. It makes no retrievals or model calls and reads no numerical ratings or commonness judgments.

Run with the existing lexical interpreter (`python3`, Python 3.14.8 and requests 2.34.2) after publication. Full forms and evidence stay under `private/lexical_frame/evidence-inventory-20261011/`; only aggregate counts and provenance hashes go to `logs/lexical-evidence-inventory-20261011.json`. Existing pilot judgments remain separate. Alias evidence is recorded separately from direct-lookup coverage. The old string detector provides a separately stored workload inventory; it does not determine pair eligibility or replace independent discovery and rejection audits. Dictionary sense IDs do not count lexical units. Broader scope/alignment triggers still require source review. This inventory neither freezes the frame nor authorizes full-frame inference.

After inventory 1 (2026-10-11): all 14,082 forms and 14,470 source-row memberships are preserved. Direct WordNet adjective coverage remains 3,786 forms. There are 21 cached Wiktionary entries and 10,285 outstanding category-gap retrievals; nine already supplemented category gaps have no extracted adjective definition. Broader in-scope and alignment triggers remain unassessed by this inventory. The string detector gives 1,080 candidates, including 457 with both forms in the source vocabulary and 227 with direct WordNet adjective evidence on both sides. None of these figures is an eligibility count, validated pair count or recall estimate. All five private artifact hashes, six recorded input hashes, source-form identities and 1,080 candidate-edge identities pass the independent read check. No numerical ratings, commonness judgments, new retrievals or new model calls enter this run.


## First production stage (adopted 2026-10-11)

The [adopted production plan](../../notes/lexical-production-plan-2026-10-11.md) governs this stage and supersedes the pilot-specific call and eligibility conventions above. It authorizes the fixed category-gap retrieval queue and 200 new source forms, split equally between direct WordNet adjective evidence and category-gap evidence. Ten homogeneous packets per stratum support separate workload estimates. Frozen source-row identities remain distinct from lexical identities and interpretations.

The production implementation has separate evidence preparation, prompt/schema validation and dispatch modules. Publish the complete source before retrieval, preflight or judge dispatch. Run under the logged lexical interpreter (Python 3.14.8; requests 2.34.2; jsonschema 4.26.0). Raw sources, packet text and judge answers remain private; aggregate status, software, manifests and hashes can be published. No source rating values are inputs.

Eligibility, completeness and unresolved questions are separate fields. One supported eligible interpretation survives incomplete supplementary coverage. Form and source-sense status aggregate interpretations under the adopted rules; source-sense organization never manufactures lexical observations. Required complete exclusions distinguish psychological scope from absent adjective-category attestation. Exact quotation and reference checks precede substantive source review of every decision, including agreements, exclusions and unresolved cases.

Dispatch uses the fixed Codex and Claude subscription routes. A job is a bounded CLI invocation, potentially containing multiple underlying requests or structured-output repairs. Exposed internal activity and usage are recorded; lack of telemetry is unknown, not evidence of one request. The first production packet on each route must pass actual-output checks before concurrency rises. The packet-local initial-attempt barrier precedes a union of supplement requests; only new supplied evidence warrants the one allowed revised round. A failed initial attempt stays in the ledger even if the revised round later succeeds. Missing family assessments stay explicit.

At most 80 scientific jobs and two neutral preflight jobs are authorized. No automatic rerun of a failed scientific job, paid API fallback or additional credit purchase is allowed. Unattempted work stays queued at quota exhaustion. API-equivalent pricing does not measure subscription allowance. The continuation report separates evidence strata and initial coding, evidence revisions and source-review effort; it excludes completed work by instrument/stage and includes remaining uncertainties. Pair discovery independent of the detector, unmatched/rejected audits, alignment, adjudication and pair weighting remain later work.


Run the production stages after publication:

```bash
python3 scripts/lexical_frame/production_evidence.py selection
python3 scripts/lexical_frame/production_evidence.py collect
python3 scripts/lexical_frame/production_evidence.py packets
python3 scripts/lexical_frame/production_runner.py preflight
python3 scripts/lexical_frame/production_runner.py freeze
python3 scripts/lexical_frame/production_runner.py first --notify
```

Dictionary collection and the neutral route checks are independent and may run concurrently. Initial packets remain immutable after supplementary cache changes. After actual source-support review of both returned first-packet assessments, record the analyst's review and continue:

```bash
python3 scripts/lexical_frame/production_runner.py review --review-note /absolute/path/to/completed-first-packet-review.md
python3 scripts/lexical_frame/production_runner.py continue --notify
python3 scripts/lexical_frame/production_report.py --write
```

The review command records completed analyst work; it isn't a request for another approval from Brett. Unavailable routes remain explicit. A systematic-defect hold needs a documented analyst assessment before `clear-hold`; clearing a hold cannot rerun an attempted job. The inventory compiler never manufactures source review or adjudicates by agreement. Its per-packet `source-review/*.json` records require actual item-level review, interpretation dispositions with source evidence, separate corrections and unresolved questions. A partial inventory stays explicitly incomplete until all 200 selected forms have been reviewed, including their technical failures.
