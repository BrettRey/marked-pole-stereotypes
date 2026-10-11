# Six-pair review: completed bounded stage

2026-10-11. The twelve authorized attempts are complete: eleven returned
answers and one Claude attempt timed out at five minutes. Nothing was retried.
The source audit retains compatible interpretations for five pairs and holds
*attentive/unattentive* unresolved. No exact complementary reading is established.
This tests the six proposed pairs’ mapping and adjudication procedure; it
neither estimates missed-pair recall nor freezes the vocabulary.

Of the sixteen saved alignment proposals, twelve are retained with their
interpretation restrictions, three remain unresolved and one is rejected.
These are mappings within six pairs, not sixteen independent contrasts.
All original proposal IDs and both families’ answers remain unchanged.

| Pair | Saved proposals | Retained interpretation and temporal target | Application domain and outstanding question |
| --- | --- | --- | --- |
| kind/unkind | p01–p02 retained | Considerate/helpful nature versus deficient kindness or humane feeling; characteristic | Interpersonal regard in the same respect; nature, conduct and feelings cannot be equated. Degree and exhaustive division remain unresolved. |
| friendly/unfriendly | p01, p03–p04 retained; p02 unresolved | Friendlike character or supportive/non-hostile orientation versus cold/inimical orientation; characteristic | Same recipient or interests and interpersonal respect. Helpfulness is not automatically friendship inclination. No interaction does not establish hostility. |
| patient/impatient | p01 retained; p02 rejected | Even-tempered endurance versus irritability under delay/opposition; characteristic and state kept separate | The state comparison requires a relevant trying/delaying situation. WordNet’s broader impatient reading includes restlessness, which can coexist with even temper. Eagerness is not this opposite. |
| happy/unhappy | p01–p02 retained | Experienced joy/pleasure versus distress or sadness; state | Same waking moment and affective respect. Showing or causing emotion is distinct from experiencing it. Neutral affect permits neither; mixed feelings leave exclusion unsettled. |
| attentive/inattentive | p01–p04 retained | Cognitive attention or care versus deficient attention/care; characteristic and state kept separate | Same attention target, capacity and relevant occasion; any due-care standard stays explicit. Giving some care and satisfying due care cannot be silently equated. Only Codex completed this pair’s call. |
| attentive/unattentive | p01–p02 unresolved | Adjective attestation retained; particular negative interpretation unconfirmed | The single negative cross-reference does not select attention, care or courtesy, or establish their temporal and applicability conditions. |

Here p01 etc. abbreviate the preserved IDs prefixed by the displayed pair.
“Retained” means a source-supported candidate alignment with the recorded
restrictions. It does not mean a released description instrument, established
homonymy/polysemy analysis or fixed contrary/complementary classification.
The broad patient/impatient interpretation permits overlap; narrowing it to
short temper is an alternative interpretation, not a correction of the
original disjunctive gloss.

The broader supplement policy was applied once to these eleven distinct
forms because their previous alignment/reading evidence was unresolved.
Ten English Wiktionary entries were newly retrieved and revision-pinned;
*unattentive* already had pinned evidence. Both families received the same
WordNet and supplementary adjective evidence, with no earlier verdicts,
source ratings, commonness values or hypothesis supplied.

The models returned six additional proposal records representing five distinct
sense-ID alignments within the same pairs. These add a non-hostility branch
for friendly, a warmth/hostility branch, satisfaction with a specified object
for happy/unhappy, a supplementary kindness/harshness specification, and an
unresolved courtesy/unattentive possibility. Both families proposed the same
satisfaction alignment. Willingness or lack of objection is not substituted
for satisfaction. None creates another independent lexical pair.

**What the audit corrected.** Eight answers passed the initial structural and
evidence checks; three required review. Four Claude friendly quotations
omitted Wiktionary link markup but match its deterministic displayed text.
All 92 evidence references were checked: 88 exact source substrings and four
display matches. The original mismatches remain in the record.

Six target records used a conditional-complement label while exhaustiveness
was undetermined. Their application restrictions do not establish even a
conditional complement. Some domain fields restated a predicate’s truth
conditions; the primary audit instead records where either predicate can be
assessed. Episodic acts or manners alone do not establish psychological-state
targets for kind or friendly, and happy’s emotional episodes do not establish
an enduring-disposition target. Unsupported claims about frequency, how rare
inapplicable cases are, antonym ranking and conduct–feeling entailments were
not adopted. This audit is a primary-agent judgment, not an independent gold
standard. Agreement between families is not its validity criterion.

**The forty-form mapping.** The mapping preserves all forty forms, 59 source-row
links, 93 original adjective-sense decisions and both families’ old grouping
proposals. It explicitly separates 31 provisional adjective identity records
from 52 operational interpretation records, targets and presentations. These
record counts are not counts of independent words. For example, responsible’s
one broad source sense is split into personal trustworthiness and assigned
accountability; only the former has an eligible psychological target.

Nine forms have no adjective attested in the checked resources. The prior
form-level outcomes remain 25 eligible, four ineligible and two unresolved.
No word eligibility was silently recoded in this stage. Bare-word cues inherit
no selected interpretation; no descriptions or commonness observations were
generated. Identity and temporal assignments outside the six reviewed pairs
remain explicit release gates. Pair weighting remains a separate estimand
decision from word weighting and dependence modelling.

**Service use and the next budget.** Calls took 30.3 summed service minutes
and 15.6 minutes of wall time. Completed Claude calls report $1.1203
API-equivalent cost; the timed-out call has no final cost, so accounting is
incomplete. Codex reports 107,433 tokens used. These used existing subscriptions,
not purchased API credits or HF compute. Primary review time overlaps the
calls and is not separately metered; inference throughput is not total
curation cost.

This stage deliberately retained gpt-6.1-sol and claude-sonnet-4-6 at high
effort for continuity with the authorized pilot. That is not a justification
for freezing the eventual full-frame instrument on Sonnet 4.6. Brett’s new
model/version and allowance-budget concern must be resolved before full coding.
No further model calls follow automatically from this report.

The narrower category-gap trigger requires 10,296 supplementary lookups among
14,082 forms; 3,786 have WordNet adjective evidence. The broader in-scope and
unresolved-evidence trigger adds an unknown subset of those 3,786. Its
full-pass workload must therefore be budgeted explicitly, along with source
review, rejected analyses, plausible unmatched forms and independent candidate
generation. This challenge-enriched six-pair stage cannot estimate those
counts, full-pass accuracy or a representative per-word price. Full-vocabulary
coding and commonness collection remain unlaunched.

The target decisions and response wording are recorded in the
[adopted protocol](lexical-protocol-decisions-2026-10-11.md).
Detailed local artifacts: [forty-form mapping](../private/lexical_frame/six-pair-20261011/forty-form-mapping.json),
[every pair decision and source audit](../private/lexical_frame/six-pair-20261011/audited-pairs.json),
[public aggregate summary](../results/lexical-frame/six-pair-20261011/SUMMARY.json),
[call accounting](../logs/lexical-six-pair-calls-20261011.json),
and [32 passing checks](../logs/lexical-six-pair-final-tests-20261011.txt).
