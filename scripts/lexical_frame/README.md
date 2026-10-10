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
