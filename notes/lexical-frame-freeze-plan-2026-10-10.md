# Assemble and freeze the word and pair lists

Revised after Brett's review, 2026-10-10. Source import and the 40-term pilot
are authorized. Full-vocabulary coding and commonness collection are later
stages; this document does not freeze a research frame. All coding
and new judgments use models. Brett reviews the scope and unresolved rules,
with no requirement to code individual words.

I recommend a scripted source import, two separate model coding passes,
and a source-based audit before we freeze anything. Start with a small pilot
to settle the rubric and estimate the work. This can proceed alongside the
current simulations; it does not require another outcome-model fit.

**Implementation update, 2026-10-10.** Source import and the authorized 40-term
pilot have now been completed; see the [pilot report](lexical-frame-pilot-report-2026-10-10.md).
The source-status paragraph below records what remained at planning, not the
current import state.

**Source status at planning.** The settled candidate sources are Anderson's 555
trait words and eligible person-descriptive adjectives from Warriner. Both
papers are in the local literature collection. The project has no assembled
vocabulary table or registered Warriner data file. The source-verification
note is partly stale: the papers have since been obtained. We still need
the actual source tables, their provenance and a fixed dictionary resource.

Anderson's selection procedure excluded extreme words, temporary states,
physical characteristics and strongly sex-linked words (1968, p. 272).
Warriner also selected vocabulary partly through familiarity and frequency
(2013, Method: Stimuli). The resulting frame will therefore describe these
source-defined vocabularies, not a random sample of every English adjective.
The expanded list helps address Anderson's exclusions without erasing source
selection. Keep Anderson-only and expanded-list results separate, as agreed.

1. **Import the candidate words without their ratings.** Extract Anderson's
   word column and obtain the original Warriner table from its authors or
   publisher. Record URL, access date, SHA-256, licence and source row/page.
   Work from a words-only export: withhold likableness, commonness, frequency,
   valence and arousal values from eligibility coding. Sort the export so
   Anderson's rating-based row order does not become a cue. Preserve original
   spellings and make normalization reversible. Account for every source
   entry, including duplicates and extraction uncertainties; check Anderson's
   advertised 555 entries rather than forcing the parser to return that count.

2. **Set a compact eligibility and sense rubric.** Proposed scope: adjectives
   that attribute personality, interpersonal behaviour, psychological states
   or capacities to a person. Include extreme meanings and temporary states,
   flagging the latter so a stable-characteristic subset can be reported
   separately. Exclude senses that describe only objects, physical appearance,
   group membership or competitive records. Brett accepted this broad scope provisionally for curation. Code these
   distinctions at the sense level: an eligible psychological sense is not
   excluded because the same spelling also has physical or membership senses.
   Preserve hyphens and participial status. A missing dictionary entry means
   unresolved coverage, not ineligibility or proof that a pairing base does not exist.

   Use a pinned WordNet release as the initial sense inventory, with exact
   sense identifiers and glosses. Evaluate its gaps in the pilot and fix a
   single supplementary dictionary policy before full coding. Do not select
   the first-listed sense automatically: WordNet explicitly warns against
   treating its sense ordering as reliable for research. Keep all supported
   eligible senses in the curation table; fix the rule for selecting or varying
   senses before commonness collection. Multiple senses of one lemma must not
   silently become extra independent words or extra production alternatives.
   [WordNet documentation](https://wordnet.princeton.edu/frequently-asked-questions)

3. **Pilot the rubric on 40 terms.** Draw ten random Anderson entries and
   ten distinct random Warriner entries, then choose twenty distinct challenge
   terms from the actual imports. Include complete candidate pairs covering a
   straightforward relation, misleading apparent morphology, multiple sense
   alignments, an absent or ineligible counterpart, and a shared base with
   multiple affixed counterparts. Record which cases the sources actually
   supply; synthetic software fixtures never enter the research frame. Do not
   gate adjective eligibility on a word's most frequent part of speech. Fix
   the selection rule and seed first. This is a
   workflow pilot, not an estimate of coding accuracy. Two model families
   receive the same source material in fresh contexts, without each other's
   answers, ratings or the marked-pole prediction. This describes the supplied
   inputs; it does not establish absence of training exposure to published data. Each returns eligibility,
   sense IDs, evidence and an uncertainty flag. Freeze the revised rubric,
   prompts and model versions, then recode pilot terms under the final rubric.
   Use the pilot to project full coding cost; existing HF authorization is
   for simulation compute, not an assumed budget for model API calls.

4. **Code the full vocabulary and derive candidate pairs.** Run both coding
   passes over the candidates, preserving exclusions and disagreements.
   Detect possible negation mechanically using the agreed affix inventory,
   then check the morphological relation and compatible senses against source
   evidence. Do not rely on either affix stripping or WordNet antonym links
   alone. Keep a pair only when both members are independently eligible in
   the agreed source vocabulary. Record missing counterparts rather than
   adding words ad hoc to improve pair counts.

   Keep the word-level negation categories broader than the primary pair
   frame: privative *-less*, for example, need not yield two eligible adjective
   poles. Words without a supported eligible pairing base stay in their agreed
   separate category; any exploratory opposite comparisons remain separate.
   For eligible pairs, code contrary versus complementary readings before
   writing commonness prompts. Preserve disputed readings as alternatives,
   following the settled plan (L1, Frame and Descriptions and judges). Use
   *base* for the immediate affixation base: *friendly* in *unfriendly*, not
   *friend*. A nominal base such as *care* in *careless* does not make an
   adjective pair with *careful*. Anderson-only pairs require both members in
   Anderson; the expanded union permits cross-source pairs with provenance.
   Record shared words and bases as a graph and retain alternative sense
   alignments; pair counts are not independent-contrast counts. No commonness
   question is asked in this stage.

5. **Audit decisions, including agreements and exclusions.** Resolve model
   disagreements by checking the cited lexical evidence, retaining unresolved
   cases visibly rather than taking a majority vote as truth. Review every
   proposed morphological pair, rejected candidate analysis and source gap.
   Also audit eligible apparent negatives with no accepted counterpart.
   Generate a separate bounded set of pair candidates by inspecting dictionary
   evidence without seeing the detector's decisions; this can expose pairs the
   detector never proposed. For the pilot, apply this check to every challenge
   word with apparent negative morphology. Before the full pass, fix a bounded
   audit sample from all eligible apparent negatives.

   Preserve distinct failure codes: counterpart absent from candidate sources;
   counterpart absent from the dictionary; counterpart present but ineligible;
   no compatible sense alignment; and not a supported affixation relation.
   Multiple codes may apply, with their evidence retained. For word decisions,
   divide each 50-case inclusion/exclusion audit budget between 25 random and
   25 targeted boundary cases (all cases if fewer), recording the components
   separately. Boundaries include adjective status, psychological/physical
   readings, states, participles, polysemy and apparent negation. Resolve every
   supplied identifier against the pinned source and inspect whether its gloss
   supports the written decision. A fresh context is not itself evidence.
   These audit counts check for systematic mistakes; they do not certify an
   error rate. If the
   audit exposes a faulty rule, correct and rerun every affected class.
   Agreement between model families measures consistency, not validity.

   Genuine scope ambiguity becomes an explicit alternative eligibility
   specification where feasible. A commonness-freeze must wait if unresolved
   source or extraction failures prevent a defensible frame. Do not invent
   missing entries or switch candidate sources silently.

6. **Produce the freeze package and inspect its composition.** Save versioned
   word, sense, pair and exclusion tables; the rubric; source and prompt/model
   manifests; audit records; and a dated report. Check that every pair points
   to eligible sense records and that every decision has provenance. Record
   totals by source, affix class, participial status, reading and uncertainty.
   After eligibility is locked, join permitted valence data to describe pair
   composition, including positive versus negative negated members. Preserve
   missing or uncertain orientation explicitly. Keep the imported rating,
   its source task, the selected sense and a sense-compatibility status
   (supported, potentially mismatched, unresolved) in separate fields.
   Spelling agreement is not evidence of sense compatibility. Anderson's
   person-likableness and Warriner's isolated-word affective ratings stay
   separate constructs. A compatibility problem qualifies the measurement or
   pole orientation; it does not remove the word or pair from the lexical frame. Sparse categories trigger
   limits on precision or scope, not selective additions to the list.

   Commit the rules, code, hashes and shareable derived files before new
   commonness judgments. Keep copyrighted source files and any unlicensed
   derived material out of the public repository. Later corrections require
   a new version and an explanation of their analytical consequences. Preserve
   the already recorded exposure to Rothbart–Park and Ingram values; freezing
   now does not make the entire design prospectively untouched.

The deliverable for review is a short report showing the actual counts,
source gaps, ambiguous rules and representative decisions, with the complete
tables available behind it. No row-by-row judgement from Brett is required.
Before a lexical package is called frozen, add an explicit mapping from
source entries to lexical items, task-relevant interpretations, supporting
dictionary senses and intended judgment targets. WordNet supplies evidence,
not the study's automatic units: synonymous senses can support one target.
Genuinely different readings must be conveyed in distinct descriptions or
retained as explicitly varied interpretations. An unglossed word question
measures responses to that lexical cue and cannot inherit a selected sense by
assumption. Glosses and descriptions are part of the measurement instrument.

The pilot report will propose this mapping with actual examples. Stable
characteristics, capacities and temporary states remain distinguishable.
State judgments must specify their temporal target: occurrence at a time,
frequency of display and occurrence at least once are different quantities.
No target may be released for collection with an unspecified population,
reference period or presentation. Within any analysis specification, a
lexical item retains one unit of weight; alternative interpretations define
separate specifications unless an explicit mixture is justified. Shared-word
and shared-base dependence, as well as counts, must pass to D1c/D2b. Detailed
prompt development can follow curation, but enough of the measurement target
must be fixed for the curated distinctions to be interpretable.

My recommended first implementation stage is source import plus the rubric
and 40-term pilot. Its output should establish a workable dictionary-gap policy, reveal
coverage and scope problems, and give an observed cost for coding, evidence
review and reruns. Forty terms cannot establish full-vocabulary coverage.
The first-stage report must show import counts and source overlap, a revised
rubric with boundary examples, accepted/rejected/unresolved pair analyses,
the proposed sense-to-target mapping, and observed costs. Moving on requires
defensible rules or explicit alternatives for the observed cases; high
inter-model agreement alone is insufficient.

Project anchors: [analysis plan](../analysis_plan.md), especially H2's word
list, L1's frame and descriptions, and Variables; [decision record](../DECISIONS.md);
[source manifest](../data/manifests/sources.csv). Source papers:
[Anderson (1968)](https://doi.org/10.1037/h0025907) and
[Warriner, Kuperman and Brysbaert (2013)](https://doi.org/10.3758/s13428-012-0314-x).

---
comments:
  c1:
    body: |-
      I’d proceed with source import and the 40-term pilot after a few targeted revisions. The overall workflow is sound: eligibility precedes commonness judgments; source restrictions remain visible; disagreements get checked against evidence; and uncertainty survives into the analysis rather than disappearing through adjudication. Your role can stay at the level of scope and rules. lexical-frame-freeze-plan-2026-…

      The most consequential changes concern missed pairs, the relationship between senses and judgment targets, and the interpretation of imported valence ratings. I’m assessing this document as a standalone plan; where the linked analysis plan or decision record already settles a point below, an explicit cross-reference should suffice.

      ### 1. The audit needs to find pairs the procedure misses

      Reviewing every proposed morphological pair checks whether the proposed pairs belong. It doesn’t check whether eligible pairs were never proposed. Both members could pass eligibility coding, yet an error in normalization, affix handling, or sense matching could prevent their relationship from entering the pair table.

      The proposed random audits of word inclusions and exclusions wouldn’t necessarily catch that failure either: the word-level decisions might both be correct.

      I’d extend the audit to cover:

      - Eligible words with apparent negative morphology for which the procedure finds no eligible counterpart.
      - Rejected candidate pair analyses, including the reason for rejection.
      - A small independently generated set of pair candidates, found by inspecting dictionary evidence without seeing the detector’s decisions.

      That last component matters because examining only the detector’s output, including its rejected candidates, still leaves its candidate-generation failures untested. This needn’t become an exhaustive search of every possible word combination. A bounded review of eligible affix-bearing words is enough to make the audit capable of discovering this class of error.

      The distinction between reasons for failure should also survive. *Counterpart absent from the candidate sources*, *counterpart absent from the chosen dictionary*, *counterpart present but ineligible*, and *no compatible sense pairing* have different implications. The draft largely recognizes these distinctions; I’d make them explicit output categories.

      ### 2. Make the pilot exercise complete pairs

      The 40-term pilot is a sensible size for testing the workflow. But its challenge half currently guarantees difficult words, not necessarily difficult pair decisions.

      Keep approximately the same size and select some challenge terms as complete candidate pairs. The pilot should exercise:

      - A straightforward eligible pair.
      - Apparent negative morphology that fails the morphological or semantic rule.
      - A pair with more than one plausible alignment of senses.
      - A source word whose apparent counterpart is absent or independently ineligible.
      - A case where one base has more than one possible negatively affixed counterpart.

      Use actual imported entries for these cases. A deliberately constructed example can test a script, but it shouldn’t silently become an addition to the research frame.

      I’d also specify that the random half is stratified by source. Otherwise, a draw from the pooled raw vocabulary could give Anderson very little representation and spend much of the Warriner portion on straightforward non-adjectives. Warriner’s stimulus list contains several parts of speech; the paper reports that only 22.5% of its entries are most often used as adjectives. [Paperity](https://paperity.org/p/18893928/norms-of-valence-arousal-and-dominance-for-13-915-english-lemmas?utm_source=chatgpt.com)

      A simple allocation such as ten random Anderson entries and ten distinct random Warriner entries would be adequate for this purpose. It’s a workflow sample, so proportional representation isn’t the objective.

      There’s a related implementation trap: a word’s *most frequent* part of speech mu
    by: user
    at: 2026-10-10T20:39:24.138Z
  c2:
    body: |-
      I’d proceed with source import and the 40-term pilot after a few targeted revisions. The overall workflow is sound: eligibility precedes commonness judgments; source restrictions remain visible; disagreements get checked against evidence; and uncertainty survives into the analysis rather than disappearing through adjudication. Your role can stay at the level of scope and rules. lexical-frame-freeze-plan-2026-…

      The most consequential changes concern missed pairs, the relationship between senses and judgment targets, and the interpretation of imported valence ratings. I’m assessing this document as a standalone plan; where the linked analysis plan or decision record already settles a point below, an explicit cross-reference should suffice.

      ### 1. The audit needs to find pairs the procedure misses

      Reviewing every proposed morphological pair checks whether the proposed pairs belong. It doesn’t check whether eligible pairs were never proposed. Both members could pass eligibility coding, yet an error in normalization, affix handling, or sense matching could prevent their relationship from entering the pair table.

      The proposed random audits of word inclusions and exclusions wouldn’t necessarily catch that failure either: the word-level decisions might both be correct.

      I’d extend the audit to cover:

      - Eligible words with apparent negative morphology for which the procedure finds no eligible counterpart.
      - Rejected candidate pair analyses, including the reason for rejection.
      - A small independently generated set of pair candidates, found by inspecting dictionary evidence without seeing the detector’s decisions.

      That last component matters because examining only the detector’s output, including its rejected candidates, still leaves its candidate-generation failures untested. This needn’t become an exhaustive search of every possible word combination. A bounded review of eligible affix-bearing words is enough to make the audit capable of discovering this class of error.

      The distinction between reasons for failure should also survive. *Counterpart absent from the candidate sources*, *counterpart absent from the chosen dictionary*, *counterpart present but ineligible*, and *no compatible sense pairing* have different implications. The draft largely recognizes these distinctions; I’d make them explicit output categories.

      ### 2. Make the pilot exercise complete pairs

      The 40-term pilot is a sensible size for testing the workflow. But its challenge half currently guarantees difficult words, not necessarily difficult pair decisions.

      Keep approximately the same size and select some challenge terms as complete candidate pairs. The pilot should exercise:

      - A straightforward eligible pair.
      - Apparent negative morphology that fails the morphological or semantic rule.
      - A pair with more than one plausible alignment of senses.
      - A source word whose apparent counterpart is absent or independently ineligible.
      - A case where one base has more than one possible negatively affixed counterpart.

      Use actual imported entries for these cases. A deliberately constructed example can test a script, but it shouldn’t silently become an addition to the research frame.

      I’d also specify that the random half is stratified by source. Otherwise, a draw from the pooled raw vocabulary could give Anderson very little representation and spend much of the Warriner portion on straightforward non-adjectives. Warriner’s stimulus list contains several parts of speech; the paper reports that only 22.5% of its entries are most often used as adjectives. [Paperity](https://paperity.org/p/18893928/norms-of-valence-arousal-and-dominance-for-13-915-english-lemmas?utm_source=chatgpt.com)

      A simple allocation such as ten random Anderson entries and ten distinct random Warriner entries would be adequate for this purpose. It’s a workflow sample, so proportional representation isn’t the objective.

      There’s a related implementation trap: a word’s *most frequent* part of speech mu
    by: user
    at: 2026-10-10T20:39:34.689Z
  c3:
    body: "Accepted the six revisions from the complete review supplied in chat: missed-pair audits and failure codes; source-stratified random terms and complete pair challenges; sense-to-target mapping and temporal targets; rating-sense compatibility; immediate bases, source membership and shared-member graphs; mixed random/targeted source audits and bounded blinding claims. Source import and the pilot are authorized; the research frame is not yet frozen."
    by: Codex
    at: "2026-10-10T20:42:24.251144+00:00"
    re: c2
