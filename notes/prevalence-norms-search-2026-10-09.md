# Trait-prevalence norms: search report (2026-10-09)
<!-- SUMMARY: Subagent search for English trait-prevalence measures with item-level SEs; best candidates Ziano et al. 2021 (commonness + self + other ratings, 149 traits, OSF CC BY) and the ESCS self-ratings (~1,100 adjectives, Dataverse CC0); Hofstee 1995 flagged as an L1 precedent · status: report, parent-verified in part · updated: 2026-10-09 -->

Condensed by the parent session from a general-purpose subagent's final report (searched 2026-10-09); the full report, with its 19 verbatim web queries, is in the session transcript. Parent verification, 2026-10-09: Ziano et al.'s definition of commonness ("how widespread in the population the trait is perceived to be") and their Table 3 correlations with desirability (commonness .64, self-ratings .92, other-ratings .61) checked against the preprint the agent saved; the ESCS 360-PDA dataset confirmed CC0 with no restricted files via the Dataverse API. Everything else below is the agent's claim, unverified by the parent unless marked.

---

## Bottom line (agent)

- No published English norm set gives per-item perceived-prevalence means with SDs and Ns for a broad adjective list. The closest is Ziano, Mok & Feldman (2021), *SPPS* 12(6), 1005–1017, doi:10.1177/1948550620948973: direct "commonness" ratings for 149 traits (Alicke's 1985 list, drawn from Anderson 1968), with separate-group self-ratings, average-American ratings, desirability and controllability; MTurk, between-subjects (commonness n = 297; each rater saw 40 random traits, so about 80 ratings per trait); raw data on OSF (https://osf.io/2y6wj/, CC BY 4.0, not opened), so per-item SEs are computable.
- Rothbart & Park (1986), *JPSP* 50(1), 131–142, doi:10.1037/0022-3514.50.1.131: 150 adjectives rated on "frequency in the population" by 82 undergraduates; whether per-trait values are printed is unverified; no open data.
- Eugene-Springfield Community Sample (ESCS), Harvard Dataverse, CC0: self-ratings on roughly 1,100 distinct English adjectives across instruments (360-PDA, doi:10.7910/DVN/ZNGS1K, N = 1,128, 9-point; 525-PDA, doi:10.7910/DVN/GHYMEV, N = 700, 7-point; PAS, doi:10.7910/DVN/QYKXUE, N = 734; SDV, doi:10.7910/DVN/LHHONE, N = 701, also "desirable for others" ratings for 100 traits; EPS, doi:10.7910/DVN/GCV3ZZ, N = 726; Self/Peer, doi:10.7910/DVN/WDARN9, 40 Mini-Markers with 1,756 peer reports; BRI, doi:10.7910/DVN/LXKJIV, frequencies of 400 acts, N = 778, linked to the Big Five by Chapman & Goldberg 2017, *PAID* 116, 201–205). Self-ratings are relative to same-age, same-sex peers; the scale midpoint conflates "neutral" with "don't know the word"; scales differ across instruments. Sample: Eugene-Springfield homeowners recruited 1993, 56.9% female, 98.4% Caucasian.
- Purpose-built "base rate" norms exist only in German: Leising et al. (2014; on request, not open); Leistner, Hommel, Wendt & Leising (2025), *Personality Science* 6, doi:10.1177/27000710251391608 (876 descriptors, about 15 raters each, OSF https://osf.io/mpxse/, data CC BY-NC-ND 4.0); Wessels, Leising & Zimmermann (2025), *Collabra* 11(1), 127423 (OSF, no licence set).
- Ruled out as prevalence: Dumas, Johnson & Lynch (2002) (their "frequency" is word frequency); Anderson (1968) (likableness and meaningfulness); Hampson, Goldberg & John (1987) (category breadth); Goldberg (1990, 1992) (factor structure; markers' self-ratings public via ESCS and the psychTools R package); Skowronski & Carlston (1987, 1989); Condon, Coughlin & Weston (2022, word familiarity and Google Books frequency for 2,818 terms, CC0, doi:10.7910/DVN/5T80PF; usable as a word-knowledge covariate); Britz et al. (2023, ELoT); Chandler (2018); Lin, Dale & Stroessner (2026, breadth and desirability for 1,214 adjectives).

## Notes for the plan (agent)

- Valence bias differs by indicator: Ziano Table 3 (149 items) has desirability correlating .92 with self-ratings, .64 with commonness, .61 with average-American ratings (parent-verified). Wessels 2025: self- and other-rating means correlate .93 and .91 with desirability; judged base rate .61 and .48.
- Ziano's commonness wording mixes how often the average American displays a trait with how many people have it.
- Approximate raters per item: ESCS 700–1,128; Ziano about 80; Leistner about 15.
- Licences: Leistner data are no-derivatives; Wessels has no licence on OSF.

## Corpus-awareness flags (agent)

- Hofstee (1995), *EJP* 9(1), 71–73, doi:10.1002/per.2410090106: used Hampson et al.'s root/negation pairs where the negated word is the desirable one (*unenvious*/*envious*) to test "undesirable behaviours are less frequent"; frequency won in 10 of 12 cases. A direct precedent for L1, to read and adjudicate.
- Ashton, Lee & Goldberg (2004, fn. 3), citing Goldberg (1982, not opened): "desirable adjectives tend to be negated about twice as often as undesirable ones". Bears on H1's valence–negation collinearity.
- UWA cite Leising et al. (2014) for positivity prevalence; that evidence is German.

## Unverified (agent)

Rothbart & Park per-trait values; Dumas per-word tables; Ziano supplement; MIDUS/ICPSR access; the psychTools scale; ELoT and Lin OSF links; Chandler; whether the 2014 Leising ratings are among the Leistner files; Wessels rater-level ratings; McCauley & Stitt (1978) and Krueger et al. (2003) details.

## Searches run (agent)

Inward: `lit resolve` on dumas2002, anderson1968, leising2014, hampson1987, goldberg1990, goldberg1992, rothbart1986, skowronski1989 and author/topic strings; grep of the central bibliography; `ls literature`. Web (verbatim queries listed in the session transcript, 19 queries), Europe PMC full text (10 queries), SHARE/OSF (7 queries plus title filters), Harvard Dataverse search API (10 queries), openpsychometrics raw data. Documentation fetched (no data files): Leising 2014, Leistner 2025, the Ziano preprint, Ashton 2004, the ESCS technical report, Zimprich et al. 2012, seven ESCS questionnaires, and Dataverse DDI codebooks (which list per-item mean, SD and N).
