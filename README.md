# The marked-pole hypothesis and the UWA model of stereotype negativity

Brett Reynolds (Humber Polytechnic and University of Toronto)

Unkelbach, Weitzel and Alves (2026) argue that most stereotypes are negative because perceivers characterize groups by diagnostic attributes, and rare attributes can reach higher diagnosticity. This project asks whether stereotype content also concentrates on the **marked pole** of evaluative oppositions, on the hypothesis that rarity drives both diagnosticity and overt morphological coding (affixal negation, the marked member of an antonym pair).

It has three strands:

- **A. Simulation.** Reproduce and extend the UWA simulation: a fresh-sample check, negativity diversity, and how far perceivers agree on stereotype valence vs content when groups don't truly differ.
- **B. Empirical test.** On open stereotype data, does the probability that an attribute is produced as a stereotype rise with its markedness, controlling for valence and frequency (H1), and within valence, with its rarity (H2)?
- **C. Optional.** Does *stereotype*, the word used to elicit the responses, carry a more negative prosody than *characteristic* or *trait*?

Status: set up 2026-10-07; nothing has run yet. See `STATUS.md`.

## Ground rules

No stand-in data: a strand whose data can't be obtained stops and says so. Every input is recorded with URL, access date, checksum and licence in `data/manifests/sources.csv`. `analysis_plan.md` is committed before any outcome model is fitted. Models are multilevel with partial pooling, checked with posterior predictive checks, and reported as effect sizes with intervals. Seeds are fixed and package versions logged.

## Layout

```
analysis_plan.md                 written and committed before any outcome model
data/manifests/sources.csv       provenance for every input
data/raw/                        downloads (not in git)
data/derived/                    shareable derived files
scripts/simulation/              strand A
scripts/empirical/               strand B
scripts/corpus/                  strand C
results/, figures/, logs/        outputs, figures, session and package logs
marked-pole-stereotypes.tex      results report (XeLaTeX, biblatex-APA)
sections/                        report sections
notes/project-brief.md           the founding brief
notes/source-verification.md     sources queued until read
```

## How to run

To be filled in as each strand is built: environment, seeds, and one command per strand. The report builds with `make` inside the portfolio (`.house-style` and `references.bib` are symlinks into it).

## Licence

Text and figures: CC BY 4.0 (`LICENSE`). Code: MIT (`LICENSE-code`). Third-party data keep their own licences, recorded in the manifest; raw data aren't redistributed here.
