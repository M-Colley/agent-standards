# HCI Empirical Papers Style Specification (Colley et al.)

Reference specification measured on five papers:
1. Colley, Eder, Rixen, Rukzio, *Effects of Semantic Segmentation Visualization on Trust, Situation Awareness, and Cognitive Load in Highly Automated Vehicles*, CHI 2021.
2. Colley, Walch, Gugenheimer, Askari, Rukzio, *Towards Inclusive External Communication of Autonomous Vehicles for Pedestrians with Vision Impairments*, CHI 2020.
3. Colley, Krauss, Lanzer, Rukzio, *How Should Automated Vehicles Communicate Critical Situations?*, IMWUT 5(3), 2021.
4. Colley et al., *SwiVR-Car-Seat*, IMWUT 5(4), 2021.
5. Colley, Hartwig, Zeqiri, Ropinski, Rukzio, *AutoTherm*, IMWUT 8(3), 2024.

Full prose was analyzed across three papers (~20,700 words) and abstracts across all five.

## 1. Quantitative Targets

* **Sentence length**: Mean 18 words, median 16 words. Distribution: 25% of sentences are 10 words or shorter, 43% are 11 to 20 words, 21% are 21 to 30 words, and 11% exceed 30 words. Short declarative sentences carry claims; longer sentences carry qualified reasoning.
* **Paragraph length**: Median 45 words and 3 sentences, mean 76 words, 90th percentile 175 words. One-sentence and two-sentence paragraphs are normal and frequent, especially in Results. Reflow each paragraph onto one unbroken line without internal line breaks.
* **Abstract length**: Hard ceiling of 150 words (7 to 9 sentences, mean sentence length 17 to 19 words).
* **Conclusion length**: Hard ceiling of 150 words.
* **Full paper length**: Hard ceiling of 12,000 words.

## 2. Register and Voice

Write declarative scientific prose in first-person plural. `We` appears ~9 times per 1000 words and `our` ~3.4 times per 1000 words. Make `we` the grammatical agent of every methodological decision. Never refer to yourself as "the authors". Use passive voice (~14 markers per 1000 words) for measurements and procedures where the human actor is irrelevant (e.g., "Effects on trust were measured using a simulation.", "Position and head orientation were logged with 5 Hz.").

Place claims before evidence: state the finding, follow with the statistic, and close with the interpretation. Never narrate the analytical process prior to delivering its outcome.

## 3. Sentence and Paragraph Construction

Express one idea per sentence in subject-verb-object order. Break stacked noun phrases into separate clauses.

* **Commas**: Frequent (~80 per 1000 words) due to short adverbial openers and parenthetical measurement details.
* **Semicolons**: Rare (~3.7 per 1000 words) and reserved for tightly coupled result pairs.
* **Dashes**: Strictly prohibited (0 allowed). Never use em dashes, en dashes, or spaced hyphens.
* **Parentheses**: Heavy (~27 per 1000 words) carrying four categories of mechanical detail so the main clause stays readable: sample sizes `(N=32)`, descriptive statistics `(M=27.63, SD=8.07)`, cross-references `(see \autoref{fig:results})`, and clarifying examples `(e.g., parallax)`.
* **Openers and transitions**: Cluster sentence openers on `The`, `We`, `In`, `This`, `For`, `Additionally`, `However`, `While`, `Therefore`. Place explicit transitions at the front of sentences matching approximate corpus rates per 1000 words: `therefore` (1.8), `however` (1.7), `additionally` (1.5), `further` (1.1), `thus` (0.6), `overall` (0.6). Open every paragraph after the first with an explicit link to the preceding claim.
* **Paragraph structure**: Open with the claim, follow with evidence, and close with the consequence for design or the next study. Discussion subsections frequently open with a bare one-line or two-line assertion and then defend it. Keep Results signpost paragraphs to at most two sentences (e.g., "In the following, we report the results of the statistical analysis. Descriptive and inferential statistics are reported.").

## 4. Section Moves

### Abstract
Execute five moves in strict order: (1) domain claim, (2) problem, (3) gap in prior work, (4) what we did with sample sizes, and (5) what we found. Model rhythm from CHI 2021: "Autonomous vehicles could improve mobility, safety, and inclusion in traffic. While this technology seems within reach, its successful introduction depends on the intended user's acceptance. [...] We report the results of two comparative online studies [...] (N=32) and [...] (N=41). Results show that the visualization using Augmented Reality increases situation awareness while remaining low cognitive load." Always name the effect and its direction in the final sentence.

### Introduction
Present motivation, the specific interaction problem, what prior work leaves open, the proposed concept, the studies conducted with `N`, and an explicit contribution statement. Number and state research questions verbatim when confirmatory: `RQ1: What impact do the variables ... have on pedestrians in terms of (1) dominance, (2) cognitive load, ...`.

### Related Work
Organize subsections by theoretical construct rather than publication chronology. Attribute prior findings to named authors in running text via `\citet{}`. Close each subsection by stating what remains unresolved for the present study.

### Method
Use exact subsections in this order: `Apparatus`, `Procedure`, `Measurements`, `Participants`, `Analysis`. Provide every replication parameter another laboratory requires: hardware model, frame rate, resolution, gain factor, session duration, compensation, counterbalancing scheme, and recruitment channel. Name each instrument with its citation and scale anchors on first mention. State protocol deviations and their concrete reasons (e.g., "Due to space constraints, we added a gain factor.").

### Results
Report descriptive statistics prior to inferential statistics. Deliver test type, test statistic, degrees of freedom, p-value, and effect size in a single clause: `Cognitive load was significantly different for the concepts, F(2, 76) = 6.72, p < .001, r = .06.` Report non-significant outcomes with identical rigor. Provide verbatim participant quotations in quotation marks with participant identifiers: `"The visualization made me realize, how bad the recognition still works." [P16]`.

### Discussion
Split into short thematic subsections with concrete or question-form titles (e.g., `Does Duration or Information Content Matter?`, `Which Vehicles Should Communicate?`, `Visual Clutter and Practical Implications`). State one interpretation per subsection, relate it to a named prior finding via `\citet{}`, and end with a concrete design consequence. Enumerate and assess alternative explanations for unexpected results (`A potential explanation is that trust measurement in a simulation is not transferable [...] Another explanation is that the situations assessed were just too different [...] The third factor could be the position of the camera.`).

### Limitations
Keep limitations concrete and specific. Name sample skew, confounds, population-instrument mismatches, or constructs that simulation or VR cannot deliver. Report whether sensitivity re-analyses were executed to test threats and state their outcomes. Avoid generic boilerplate limitation paragraphs.

### Conclusion
Restate what was done with sample sizes, what was supported, what was unsupported, and the concrete next step in 150 words or fewer.

### Acknowledgments
Thank participants and named helpers first, then state the funding project and funding agency.

## 5. Reporting Conventions and Open Science

* **Samples**: `"N=41 participants (21 female, 20 male) took part in the study. These were, on average, M=27.63 (SD=8.07) years old."`
* **Scales**: `"On 5-point Likert scales (1 = Strongly Disagree, 5 = Strongly Agree)"`
* **Statistical tests**: Name the test, justify selection by distribution test or robustness under small/unequal samples, state the multiple-comparison correction used for post-hoc tests, always report effect sizes, and cite the effect-size formula source whenever non-obvious.
* **Open science**: State the repository URL hosting data, code, stimuli, and analysis scripts. Never write "available upon request".

## 6. Lexicon, Prohibitions, and Hedging Calibration

* **Preferred lexicon**: `however`, `therefore`, `additionally`, `further`, `thus`, `overall`, `while`, `still`, `especially`, `e.g.`, `i.e.`, `cf.`, `in line with`, `state of the art`.
* **Banned phrases and styles**: Never write `in order to`, `it is important to note`, `we would like to`, `moreover`, `"We state this rather than obscure it"`, metaphors, meta-commentary about the text, or marketing vocabulary (`game-changing`, `game changing`, `at scale`, `headline result`, `shippable`, `seamless`, `powerful`, `free lunch`, `anonymous knob`, self-praising `novel`). Never use contrastive clarification, metadiscursive qualification, scope delimitation, or corrective "not X but Y" framing.
* **Hedging calibration**: State measurements flatly without hedges. Apply single calibrated hedges only to interpretations (`could` 1.8/1000w, `seems` 0.6, `may` 0.5, `potentially` 0.5, `indicates` 0.4, `we assume` 0.3, `we argue`, `we believe`, `it seems appropriate`, `our findings suggest`). Never stack hedges. Frame recommendations as implications (`"The most important implication therefore is to include auditory cues."`) rather than `"we recommend"`. When current data cannot settle a question, state that directly and specify the follow-up study (`"This study cannot answer this question, however, this should be studied in the future to assess the external validity of simulator studies."`).
* **Citations and cross-references**: Integrate narrative citations with `\citet{}` (`"These results confirm the findings of \citet{colley2020} who report AR systems to increase trust and reduce cognitive load."`). Reference all figures, tables, sections, and equations with `\autoref{}`. Quote prior work with page numbers when exact phrasing carries the argument.

## 7. Worked Example

* **Flawed draft**: `"In this paper, we present a novel and powerful approach that leverages cutting-edge segmentation to seamlessly enhance the user experience of autonomous vehicles. Our results are highly promising and demonstrate significant improvements across a wide range of metrics, suggesting that this is a game changing direction for the field."`
* **Target style**: `"We visualize semantic segmentation output to the passenger of an automated vehicle. Two online studies evaluated the concept, one in simulation (N=32) and one with real world footage processed by Panoptic-DeepLab (N=41). Situation awareness increased in both studies. Cognitive load did not increase, and trust was unchanged in the second study. The visualization therefore seems suitable for calibrating expectations about vehicle perception during the introduction of automated vehicles."`

## 8. Pre-Delivery Verification Checklist

1. Sentence-length distribution approximates Colley et al. targets (mean ~18w, median ~16w; ~25% <=10w, ~43% 11-20w, ~21% 21-30w, ~11% >30w).
2. Zero dashes, zero metaphors, zero marketing vocabulary, zero meta-commentary, and zero banned rhetorical frames (`not X but Y`, contrastive clarification, metadiscursive qualification, scope delimitation).
3. Every claim precedes its evidence, and every paragraph after the first opens with an explicit transition linking to the prior claim.
4. Every paragraph is reflowed onto a single unbroken line.
5. Every inferential result carries test name, test statistic, degrees of freedom, p-value, and effect size.
6. Every instrument is cited with scale anchors, and participant demographics are complete.
7. Limitations are concrete and specific, and open-science repository links are stated.
8. Abstract and Conclusion are each 150 words or fewer; full paper is 12,000 words or fewer.
9. `\citet` and `\autoref` are used consistently throughout LaTeX source, and `mechcheck fix .` plus `mechcheck check .` pass cleanly.
