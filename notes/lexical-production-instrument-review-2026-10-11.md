# Lexical production: first-packet hold and proposed correction

**Adopted 2026-10-11.** Brett approved this correction in chat after the Roughdraft checkpoint. The original instrument remains frozen; dispatch stays held until the successor is tested, published and frozen. The correction stays within the adopted 200-form stage and does not authorize a retry or a larger batch.

## What happened

The first-packet check caught a systematic ambiguity before the queue expanded. Both initial jobs returned the requested model identities. Codex passed the deterministic checks. Claude returned complete structured records, but nine of its ten forms failed the supplement and coverage rules, producing eighteen validation errors.

Every WordNet-adjective input had been labelled `supplement_required=false` and `review_complete=true`. Those flags described source availability before interpretation coding. Their names suggested that the eventual evidence requirement had already been decided. Claude explicitly relied on the false supplement flag in each of its nine refusals, despite the prompt requiring a supplement when no eligible interpretation was supported or a relevant question remained.

The prompt and validator agree on the intended rule. The correction should remove the misleading input, preserve the rule and retain the failed attempt. Making the validator accept the response would conceal the problem.

The parallel source audit found a related presentation issue. WordNet's inherited case-insensitive lookup supplies twelve case-only matches across ten selected forms, including three adjective records. Original lemma capitalization is preserved, but the production metadata does not explicitly identify those lookup relations. The frozen selection followed its specified operational strata; this is not a reason to redraw the sample. Case-only matches need explicit treatment before lexical identity is settled.

## Work preserved

- All **10,285 outstanding category-gap titles** were attempted. Including the eleven previously cached category gaps, the ledger contains 10,238 retrieved entries, 38 missing entries and twenty ambiguous cases. Missing and ambiguous results remain unresolved evidence states.
- All **200 selected forms and twenty initial packets** are frozen. Only the first ten forms have received initial assessments; the remaining 190 have not been dispatched.
- Exactly **two scientific judge jobs** ran. Codex took 448.53 seconds and reported 42,079 tokens. Claude took 215.70 seconds and reported $0.424458 in API-equivalent usage. That dollar amount is not an additional subscription charge or a measurement of remaining allowance.
- After both initial attempts ended, Codex's seven valid supplement requests were collected into one genuinely augmented packet. Both planned revised assessments remain **undispatched** because the hold is active.
- The original source packets, answers, validation failures, source hashes and instrument record remain intact. Separate analyst annotations preserve source-supported content and identify substantive qualifications. A mechanically valid record is not automatically a correct lexical decision.

One WordNet packet cannot estimate category-gap costs or support a full continuation quote. The initial assessments also used the defective presentation, so their costs must remain identified by instrument version.

## Successor instrument

Publish and freeze **v1.1** before any further judge job. Keep the original v1 record immutable and attach the active instrument version and actual model-input hash to every future job.

1. **Show factual coverage, without premature decisions.** Remove `supplement_required` and `review_complete` from the model-facing input. Retain source-attempt statuses, source text, parser limitations and the original private preparation records. The assessor computes required-review completeness after interpreting the evidence.
2. **State the decision order.** Assess the interpretations, determine whether the fixed supplement is required, then aggregate eligibility and coverage. With no eligible reading and an unattempted required supplement, request it and leave the form unresolved. With an eligible reading plus an additional relevant gap, retain eligibility while marking incomplete coverage. An already attempted supplement is not requested again.
3. **Make lookup relations explicit.** Mark exact-case and case-only WordNet matches, preserving original lemmas and all source evidence. A case-only match does not itself establish lexical identity with the input form. Do not automatically merge identities or delete the capitalized evidence. Keep the existing selected IDs, order and operational strata; describe the WordNet stratum as the original case-insensitive retrieval route when reporting workload.
4. **Preserve the substantive checks.** Keep the interpretation/sense/form aggregation rules, source accounting, exact quotation checks, two-family barrier and single revised-evidence round. Add targeted tests for the corrected input envelope, mixed exact/case-only matches, version attribution and the cumulative attempt ledger.

This changes the instrument's presentation, so future records must not be described as products of an unchanged v1 instrument. It does not change psychological scope or make agreement a validation criterion.

## Continuation within the existing allowance

Use the **two already planned revised-evidence jobs for the first packet** as v1.1's first real output check. They are justified by the seven newly supplied dictionary entries, not by the prompt correction. Both families receive the same augmented evidence in fresh contexts. The failed Claude initial attempt remains a failed v1 assessment; the Codex initial record remains a separate, earlier assessment.

After deterministic and substantive source review of that revised packet, release the remaining nineteen initial packets and their permitted evidence revisions. New questions that remain after the one revised round stay unresolved. Do not retrieve extra material merely to manufacture another job, replay an attempted slot, replace difficult forms or reset the allowance under a new version name.

The cumulative ceiling remains **eighty scientific judge jobs across v1 and v1.1**, with two already consumed, plus the two completed neutral route checks. No further neutral probes, paid API fallback or credit purchase is proposed. Each scientific job retains its fifteen-minute elapsed limit. Another systematic defect stops dispatch again; a corrected prompt is not permission to run repeated trials until outputs pass.

The final inventory must retain all 200 forms, distinguish v1 and v1.1 assessments, identify missing counterparts and uncompleted work, and preserve supported decisions alongside unresolved questions. Continuation estimates must still separate the two original evidence strata, initial coding, revised-evidence work and analyst review. Pair discovery, rejected/unmatched audits, alignment and weighting remain later stages.

## Implementation boundary

Brett's approval covers the bounded v1.1 correction and continuation described above, preserving the existing job slots and allowance. The Roughdraft checkpoint required by AGENTS.md has been satisfied through that explicit chat approval. Clear the hold only after the corrected successor has passed its checks and been published and frozen; source-review the two revised assessments before ramping.

The detailed diagnoses and source-review annotations remain in the private production record. Public status reports contain aggregate progress and provenance, not the complete candidate vocabulary or raw responses.
