# Project brief (Brett, 2026-10-07, verbatim)
<!-- SUMMARY: Brett's founding brief for the marked-pole project, verbatim: three strands (UWA simulation, empirical markedness test on open data, optional lexical confound), ground rules, deliverables · status: founding brief · updated: 2026-10-07 -->

This is Brett's brief as pasted on 2026-10-07. It is the project's plan, not a source: its references and URLs are queued in `source-verification.md` until read. The "attached" PDF was found in `~/pdf-inbox` and filed in `literature/`; `uwa_replication.py` was not attached and isn't on disk (see `STATUS.md`).

---

# Project: marked-pole hypothesis and the UWA stereotype-negativity model

## Context
Unkelbach, Weitzel & Alves (2026, Psychological Review, doi:10.1037/rev0000647; PDF
attached) argue that stereotypes skew negative because perceivers characterize groups by
diagnostic attributes, high p(G|A), and rare attributes have higher PPV ceilings. My
hypothesis: stereotype content concentrates on the marked pole of evaluative oppositions,
because rarity drives both diagnosticity and overt morphological coding. This project
(a) extends their simulation and (b) tests the hypothesis on open data.

## Ground rules
- Never synthesize stand-in data. If a dataset can't be obtained, stop that strand and
  report it.
- Record provenance for every input: URL, access date, checksum, licence.
- Write `analysis_plan.md` (hypotheses, variables, exclusions, models, what would count
  against each hypothesis) and commit it BEFORE fitting any outcome model.
- Statistics in the Gelman style:
  - multilevel models with partial pooling (brms or PyMC; pick one and justify)
  - posterior predictive checks
  - effect sizes with uncertainty intervals
  - no significance-hunting
- Fix seeds. Log session and package versions.

## Strand A: simulation (start from the attached uwa_replication.py)
1. Reproduce UWA's design: K = 10 groups of 100; 50 positive and 50 negative binary
   attributes, independent of group; base-rate pairs .50/.50, .60/.40, .70/.30, .80/.20,
   .90/.10; 1,000 runs each. Outcomes: share negative among Group 1's top-5 PPV attributes;
   likelihood ratios with Jeffreys smoothing; mean p(A|G) of the top 5. Check against their
   Figure 6.
2. Fresh-sample check: recompute the same attributes' PPV and p(A|G) in an independent
   sample. Expected: chance (1/K) when there are no true differences.
3. Negativity diversity: 50 positive vs 100 negative attributes.
4. Consensus split: give each of N perceivers an independent finite sample. Measure
   agreement on top-5 attribute identity (Jaccard) and on top-5 negative share.
   Prediction: high valence agreement and low content agreement with no true group
   differences. Content agreement should rise as small true differences are added. Map how
   large the true differences must be for content agreement to approach observed
   stereotype consensus.

## Strand B: empirical test of the marked-pole hypothesis
Data (verify each; stop and report if unavailable):
- UWA Studies 1-2: https://researchbox.org/4585
- Ingendahl, Woitzel & Alves (2025): https://osf.io/b9f8h
- Nicolas, Bai & Fiske (2022), JPSP 123(6), 1243-1263, doi:10.1037/pspa0000312. Locate
  their data.
- Valence norms: Warriner, Kuperman & Brysbaert (2013), doi:10.3758/s13428-012-0314-x.
- Word frequency: an open norm such as SUBTLEX-US (verify availability).
- Antonym markedness probabilities: Ingram, Hand & Maciejewski (2016),
  doi:10.1371/journal.pone.0157141 (supplementary data).
- A morphological segmentation resource for detecting affixal negation (un-, in-/im-/il-/ir-,
  dis-, non-) and privative -less. Verify the resource and hand-check its output: *uniform*
  and *discuss* aren't negations.
- A reference set of person-descriptive adjectives to serve as the denominator: the
  candidate attributes that could have been produced (e.g., Anderson's trait-word list;
  verify availability).

Steps:
1. Normalize free-response stereotypes to adjective lemmas. Report coverage and what's
   lost (multiword responses, nouns, phrases).
2. H1: P(attribute is produced as a stereotype) rises with markedness (affixal negation;
   marked member of an antonym pair), controlling for valence and log frequency. Valence
   and markedness are collinear, so estimate and report that. The informative cases are
   where they come apart: marked positives (*flawless*, *blameless*) and unmarked
   negatives.
3. H2: within valence, rarer attributes are more often stereotypic.
4. Model structure: random effects for target group, participant and item, as the data
   allow.

## Strand C (optional): lexical confound
The stereotypes in Studies 1-2 were elicited with the word *stereotype*. In an openly
downloadable corpus (document which), compare the valence of collocates of *stereotype(s)*
with those of *characteristic(s)* and *trait(s)*, using Warriner norms. Report the size of
any prosody difference.

## Deliverables
- Repository with README (provenance, how to run), analysis_plan.md, scripts, data
  manifests.
- A results report in LaTeX (biblatex-APA) with figures. Linguistic objects in \textit{}
  or \mention{}, meanings in single quotes, \enquote{} for quotations. Oxford spelling
  (-ize). Contractions. No em dashes; use ~-- in LaTeX. Paragraphs around 60 words.
- A short section stating what results would falsify H1 and H2, and whether they occurred.
- At the end, a summary of what ran, what couldn't, and why.
