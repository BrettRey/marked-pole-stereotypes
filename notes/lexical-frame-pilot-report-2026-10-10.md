# Lexical-frame pilot: findings and decisions

Source import and the two-family, 40-term pilot are complete. The workflow now distinguishes supported psychological readings, other readings, gaps in adjective evidence, and unresolved scope. It also checks for missed pairs. The frame is **not frozen**: interpretation, reading and judgment-target choices remain visible below. No commonness judgments or full-vocabulary coding have been launched.

**What was imported.** These are observed source counts, not constructed data.

| Source/accounting item | Count |
| --- | ---: |
| Anderson entries and normalized forms | 555 |
| Warriner source rows | 13,915 |
| Warriner normalized forms | 13,905 |
| Forms in both sources | 378 |
| Forms in their union | 14,082 |

Normalization preserves original spellings and source-row identities. Ten capitalization groups account for Warriner's row/form difference; they aren't assumed to represent identical senses. All ten Anderson word columns were checked against page images. Six OCR errors were corrected, and two apparent printed spelling variants were retained with separate lookup aliases.

The publisher's Warriner ZIP contains one CSV and no licence file. The complete vocabulary, source tables and source-bearing responses therefore remain private. Only words were exported into the coding packets. Anderson's person-likableness task and Warriner's affective word-rating task remain distinct. [Anderson (1968)](https://doi.org/10.1037/h0025907), [Warriner et al. (2013)](https://doi.org/10.3758/s13428-012-0314-x).

**Dictionary coverage and the revised rubric.** The fixed pilot comprised ten random Anderson terms, ten distinct random Warriner terms and twenty challenge terms, including complete pairs. WordNet 3.1 lacked adjective senses for eleven terms. Applying the same pinned English Wiktionary supplement to all eleven supplied adjective definitions for _onboard_ and _unattentive_. Nine terms still had only non-adjective definitions; none of the supplementary English entries was missing.

The source audit finds supported psychological/interpersonal adjective meanings under 25 source forms and excludes the supplied adjective readings of four. Two adjective words, _uniform_ and _valuable_, retain scope uncertainty. The remaining nine have no supported adjective reading in the checked resources. This distinction matters for _liar_: Anderson's trait-word list includes a person-denoting noun; membership in that source doesn't make it an adjective.

I recommend a **resource-attested adjective frame**: those nine terms aren't admitted without adjective evidence, while their coverage limitation remains recorded. The conservative alternative retains all nine as unresolved. A missing entry still goes to the unresolved route. Neither treatment claims that {==an adjective word with that spelling==}{>>to be clear, a given word is or isn't an adjective. That's not to say that there isn't a noun, verb, etc. with the same shape. But I take "use" to mean function, and the function would be attributive modifier, predicative complement, etc. Adjective is not a use/function.<<}{id="c1" by="user" at="2026-10-10T21:28:30.815Z"} cannot exist elsewhere, and neither uses a word's most frequent part of speech as the eligibility gate.

Here *form* means a spelling in the source table. An adjective word and a noun word can share that form; they don't become one word changing lexical category. *Adjective* names a category, while attributive modifier and predicative complement name functions. The pilot's legacy `word` and `word_status` fields aggregate by source form; lexical-item identity must be resolved before the research units are frozen.

At the sense level, retain personality, interpersonal behaviour, psychological states and capacities. Exclude physical, object, membership, institutional status and record-only readings. A psychological reading doesn't rescue every sense of its word. Nor does a mental interpretation automatically follow from an example about a performance or an object. _Cold_ meaning mastery of one's lines remains unresolved as a person-description target; _responsible_ must separate trustworthiness from merely being assigned accountability, even though WordNet combines them in one synset.

**What checking changed.** Codex `gpt-6.1-sol` and Claude `claude-sonnet-4-6` used the same packets and rubric in separate contexts, both at high effort. They agreed on 38/40 source-form labels and 84/93 adjective-sense labels. These are consistency counts, not accuracy estimates. The primary agent reviewed every pilot form and every supplied adjective sense against the source. Four sense decisions were explicitly amended from the record used to assemble the audit; original judgments and grouping alternatives remain intact. Nine terms with only non-adjective definitions received the same coverage treatment.

Two word-pass quotes and three original pair-pass quotes had lost Wiktionary link markup. Their displayed text was checked against the pinned definitions; the raw answers weren't overwritten. Substantive checking also caught unsourced etymology and a tendency to infer logical complementation from dictionary _not_/_lack_ glosses. A revised pair screen was published and submitted on the entire pilot pair class in both families. It asks separately whether someone could satisfy neither pole or both, at the same time and in the same respect. Unresolved readings remain unresolved; no further calls will chase agreement. Codex completed the revised screen; Claude hit the fixed 15-minute limit after an internal output-limit continuation and returned no final answer. That failed attempt is retained. Both original independent pair passes are complete, but there is **no completed two-family validation of the revised pair instrument**. The completed rerun leaves its proposed alignments unresolved rather than certifying contrary/complementary categories.

**Pair results.** Six prefix pairs provisionally pass source membership and word eligibility: _kind/unkind_, _friendly/unfriendly_, _patient/impatient_, _happy/unhappy_, _attentive/inattentive_ and _attentive/unattentive_. Their interpretations and readings still need to be fixed for collection. Five are available with both members in Anderson; _patient/impatient_ enters through the expanded frame. The six pairs involve eleven words in five connected sets. Both attention pairs share a base, so D2b needs the graph as well as the pair count.

| Analysis | Pilot disposition | Reason retained |
| --- | --- | --- |
| _kind/unkind_ | Provisional primary pair | Compatible person-descriptive meanings; a not-gloss doesn't fix the reading |
| _happy/unhappy_ | Provisional primary pair | Joy/distress alignment is available; willingness to help isn't the same target |
| _careless/care_ | Outside primary adjective pairs | The immediate base is nominal; _careful_ is a separately derived adjective |
| _invaluable/valuable_ | Rejected semantic opposition | Incalculable worth doesn't oppose having worth; no rating was used |
| {==_uniform_ (detector false positive)==}{>>this is clearly a mistake. The prefix is uni- not un-<<}{id="c2" by="user" at="2026-10-10T21:31:25.743Z"} | Rejected detector output | The prefix is _uni-_. The string detector wrongly strips _un-_ and returns _iform_; that output is an error, not a lexical counterpart |
| _uncouth/couth_ | Not admitted; morphology remains qualified | WordNet attests adjective _couth_, but neither candidate source contains it |

The _couth_ finding corrects an implementation risk in the older plan's “no extant root” example. We must record the actual source restriction, not infer lexical nonexistence. Its derivational history wasn't established here.

The original independent screens each inspected eleven apparent-negative words, without detector decisions. All eleven detector analyses were then audited, including rejections and absent/ineligible counterparts. This found no additional supported primary pair missed by the detector in this bounded pilot. That is not an estimate of detector recall over the full vocabulary.

**Proposed mapping to judgment targets.** A source row points to a normalized form; that form must be resolved into category-specific lexical items. Each adjective lexical item points to supported interpretations, dictionary evidence and a specified judgment target. A form hash is therefore a provisional identifier, not a decision that every same-spelling entry is one lexical item. Several synsets may support one interpretation, and one synset may require a split. The following are target specifications, not final collection prompts.

| Source word | Interpretation to preserve | Consequence for measurement |
| --- | --- | --- |
| _patient_ | Even-tempered endurance, excluding the medical noun | Use a description of responses to delay or difficulty; align _impatient_'s irritability sense, not its eagerness sense |
| _cold_ | Emotional distance, separately from absent enthusiasm, compunction and sexual responsiveness | An unglossed word question cannot stand in for any chosen interpretation |
| _responsible_ | Personal trustworthiness, excluding assigned accountability, causal agency and credit standing | Split the broad synset before generating descriptions |
| _angry_ | An experienced state, separately from a recurrent disposition | A moment, a tendency and ever having experienced anger require different questions |

Follow the settled L1 instrument: two descriptions per pole from two model families, avoiding the words and their roots, followed by equivalence and reading checks. Retain word-based judgments as a separate instrument. Alternative interpretations define separate analysis specifications. In word-level analyses, a lexical item receives one unit of weight within each specification. Pair analyses retain distinct eligible pairs while modelling their shared members. Extra synsets, wordings and shared-base pairs do not create independent lexical evidence.

{==The US was proposed as the population the models would be asked about==}{>>why and how?<<}{id="c3" by="user" at="2026-10-10T21:33:13.849Z"}. It would not be the judge panel: all new judges remain models. The practical reason was that the existing Ziano calibration source asks about the average American. That supports retaining its exact reference population and wording in the source-matched display-frequency arm. It doesn't establish that US adults are the right population for the separate description-based L1 comparison. See [the settled distinction](../analysis_plan.md#hypotheses) and the plan's Commonness judges section.

Operationally, each model would receive the same explicit reference population, interpretation and time specification. An illustrative person-prevalence question is: “Among people in [the specified population], which of these two descriptions applies to more people under [the specified time condition]?” The response options remain either description, about equal, or can't say. This defines what the model is judging; it neither samples people nor measures their actual prevalence. Changing the population wording is a model-protocol sensitivity comparison, not evidence that people in those populations differ.

I withdraw the adult-only restriction and the twelve-month/thirty-day windows as default recommendations: those details were illustrative choices, not established by the anchor or the hypothesis. The calibrated arm should preserve the source wording. The unanchored description arm still needs an explicit scope decision about population and temporal target before freezing. Momentary state prevalence, recurrent disposition and frequency of display remain distinct quantities; that requirement survives without choosing arbitrary windows here.

**Imported ratings.** Preserve rating source and task, selected interpretation, and compatibility status separately. _Patient_ and _cold_ illustrate potential mismatch for isolated-word ratings. A person-likableness instruction narrows the domain but doesn't select a unique sense. No selected interpretation is declared empirically validated by a spelling join. Preserve uncertain orientation; don't delete inconvenient pairs. Source ratings have not been joined to this pilot. Additional exposure of the primary session to the paper's printed calibrator values is disclosed in `DECISIONS.md`; the coding packets withheld those values. Withholding inputs does not establish absence of prior model training exposure.

**Observed work and cost.** Twelve CLI calls were attempted: eight word batches, two original pair screens and two revised pair screens. Eleven completed; the last Claude recheck timed out. Across overlapping calls, elapsed service time totals 44.6 minutes, including the 15-minute failure. The word passes alone took 18.8 summed call-minutes. The completed Claude calls report $1.76 in API-equivalent accounting, of which $1.19 is word coding; the failed recheck has no final cost report. Codex reports 175,133 “tokens used” across its six calls; that CLI counter isn't assigned an invented dollar charge. All calls used existing CLI subscriptions; these figures aren't an invoice and no API credits were bought.

The import, implementation, source review and recorded audit occupied about 42 minutes of session wall time through the audit checkpoint, with work and inference overlapping. Active evidence-review time and this primary session's token cost weren't separately metered, so there is no defensible all-in per-word price. A naïve scaling of the word calls to all 14,082 raw forms is about 110 summed call-hours and $420 of Claude API-equivalent word-coding usage alone, excluding Codex pricing, dictionary retrieval, pair work, review and failures. This is an illustration of why inference-only extrapolation is inadequate, not a full-pass budget or authorization. The purposive challenge half also prevents treating this pilot as a representative workload sample.

All 17 import, evidence and audit tests pass. The completed audit checks 298 citations to dictionary evidence: 293 exact substrings and five verified Wiktionary display-text matches. Identifier checks and the revised screen's neither/both consistency checks pass; these don't certify semantic validity.

The first stage is complete as a pilot, with source-supported decisions and explicit alternatives. Full-pass readiness is not established: the revised pair instrument lacks a completed second-family recheck. Before full coding, settle the resource-boundary rule and the population/time targets, and require a bounded, workable pair-screen protocol and a workload budget. No row-by-row coding by Brett is required. Source coverage, meaning and interpretation remain limits on the claim; high agreement doesn't remove them.

Evidence: [aggregate results](../results/lexical-frame/pilot-20261010/SUMMARY.json), [complete word/sense audit](../private/lexical_frame/audit-20261010/word-audit.json), [complete pair and reading audit](../private/lexical_frame/audit-20261010/pair-audit.json), [quote checks](../private/lexical_frame/audit-20261010/quote-audit.json), [specification and run instructions](../scripts/lexical_frame/README.md), [source manifest](../data/manifests/sources.csv).


---
comments:
  c4:
    body: "Agreed. I replaced adjective use with adjective word and made category, function, source form and lexical-item identity explicit. The imported spelling can correspond to a noun and a distinct adjective; the legacy word fields in the pilot are source-form aggregates, not a claim that a word changes category with its function."
    by: "Codex"
    at: "2026-10-10T21:37:16.292166+00:00"
    re: "c1"
  c5:
    body: "Correct: uniform has uni-, not negative un-. The row was showing a deliberately retained false positive from raw string stripping, but its pair notation made it look like a proposed linguistic analysis. I have relabelled it as a detector error and stated the correct segmentation. It was rejected throughout and never counted among the six provisional pairs."
    by: "Codex"
    at: "2026-10-10T21:37:16.292166+00:00"
    re: "c2"
  c6:
    body: "The US suggestion referred to the population models would judge, not to recruiting human judges. Its practical motivation was the existing average-American calibration anchor. That reason applies directly to the source-matched display-frequency arm, not automatically to L1 descriptions. I have explained the prompt mechanism, distinguished model-protocol judgments from actual population prevalence, and withdrawn adult-only and fixed-window defaults that the source does not justify. The description-arm population and temporal target remain explicit unresolved scope decisions."
    by: "Codex"
    at: "2026-10-10T21:37:16.292166+00:00"
    re: "c3"
