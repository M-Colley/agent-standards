---
name: hci-paper-writing
description: >-
  Drafts, revises, audits, and reviews HCI empirical papers, abstracts, proposals,
  theses, and rebuttals following the Colley et al. (CHI, IMWUT, AutomotiveUI)
  quantitative style specification and automated mechcheck verification. Activate
  whenever writing, editing, checking, or reviewing academic manuscripts, LaTeX
  sections, abstracts, grant proposals, or peer reviews.
---

# HCI Empirical Paper Writing and Verification

Apply this skill whenever drafting, revising, checking, or reviewing academic prose for CHI, IMWUT, AutomotiveUI, UIST, ASSETS, MobileHCI, or comparable scientific venues. Read [references/colley-hci-spec.md](references/colley-hci-spec.md) when writing or substantially editing full paper sections, checking statistical reporting formats, or calibrating lexicon and hedging rates.

## Hard Constraints

1. **Length ceilings**: Keep abstracts at 150 words or fewer (7 to 9 sentences, mean 17 to 19 words per sentence). Keep conclusions at 150 words or fewer. Keep full papers at 12,000 words or fewer.
2. **Paragraph reflow**: Output every paragraph as one single unbroken line with zero hard wraps inside the paragraph. Separate paragraphs with a blank line.
3. **Punctuation**: Never use em dashes, en dashes, or spaced hyphens in prose. Use commas (~80 per 1000 words) for short adverbial openers and parenthetical detail. Reserve semicolons (~3.7 per 1000 words) for tightly coupled result pairs. Use parentheses (~27 per 1000 words) for sample sizes `(N=32)`, descriptive statistics `(M=27.63, SD=8.07)`, cross-references `(see \autoref{fig:overview})`, and clarifying examples `(e.g., parallax)`.
4. **Forbidden framing**: Under ALL circumstances, never use contrastive clarification, metadiscursive qualification, scope delimitation, or corrective "not X but Y" framing.
5. **Forbidden vocabulary**: Never use metaphors, process meta-commentary ("We state this rather than obscure it", "a scan returns a result"), filler phrases ("in order to", "it is important to note", "we would like to", "moreover"), or marketing terms ("game-changing", "at scale", "headline result", "shippable", "seamless", "powerful", "free lunch", "anonymous knob", or self-praising "novel"). Use "novel" strictly as a neutral technical descriptor when required.
6. **LaTeX references**: Always use `\citet{key}` when authors form the grammatical subject and `\autoref{label}` for all figures, tables, sections, equations, and appendices.
7. **Open science**: State the persistent repository URL containing data, code, stimuli, and analysis scripts. Treat "available upon request" as unacceptable.
8. **Peer reviews**: Default the review verdict to **reject** unless rigorous empirical evidence, complete replication details, valid statistics, and open artifacts justify acceptance.

## Quantitative Rhythm (Colley et al. Corpus)

Write to the measured Colley et al. sentence-length distribution rather than uniform medium sentences:
* **Sentence length**: Mean 18 words, median 16 words. Target 25% at 10 words or fewer, 43% at 11 to 20 words, 21% at 21 to 30 words, and 11% above 30 words. Put core claims in short declarative sentences and qualified reasoning in longer sentences.
* **Paragraph length**: Median 45 words and 3 sentences, mean 76 words, 90th percentile 175 words. Use one-sentence and two-sentence paragraphs freely, especially in Results.
* **Voice**: Use first-person plural (`we` ~9/1000 words, `our` ~3.4/1000 words) for every methodological decision. Never write "the authors". Use passive voice (~14 markers/1000 words) for measurements and logging procedures where the actor is irrelevant.
* **Order and flow**: Open every paragraph with the claim, follow with statistical or empirical evidence, and close with the design or follow-up implication. Open every paragraph after the first with an explicit link to the preceding claim using front-loaded transitions (`therefore` 1.8/1000w, `however` 1.7, `additionally` 1.5, `further` 1.1, `thus` 0.6, `overall` 0.6).
* **Hedging**: State measurements flatly. Apply at most one calibrated hedge per interpretive claim (`could`, `seems`, `may`, `potentially`, `indicates`, `we assume`, `we argue`, `we believe`, `it seems appropriate`, `our findings suggest`). Express recommendations as design implications rather than "we recommend".

## Section Checklist

Read [references/colley-hci-spec.md](references/colley-hci-spec.md) for detailed section moves, statistical templates, and worked rewrites:
* **Abstract**: Execute five ordered moves: domain claim, problem, gap in prior work, study design with `(N=...)`, and main finding naming effect and direction in the final sentence.
* **Introduction**: State motivation, interaction problem, gap in prior work, proposed concept, studies with `N`, verbatim numbered research questions (`RQ1: ...`) when confirmatory, and explicit contributions.
* **Related Work**: Group subsections by theoretical construct. Attribute findings to named authors via `\citet{}` and end each subsection with the unresolved gap addressed by the present study.
* **Method**: Use exact subsections `Apparatus`, `Procedure`, `Measurements`, `Participants`, `Analysis` in that order. Give every replication parameter, cite every instrument with scale anchors on first use, and explain protocol deviations.
* **Results**: Report descriptive statistics before inferential statistics. Deliver test name, statistic, degrees of freedom, p-value, and effect size in one clause, justify test selection and post-hoc corrections, report null effects with equal precision, and include verbatim quotes with participant IDs (`"..." [P16]`).
* **Discussion & Limitations**: Use short concrete or question-form subsection titles, relate each interpretation to named prior work, end with a design consequence, enumerate and evaluate alternative explanations for unexpected results, and state concrete limitations plus any sensitivity re-analyses performed.
* **Conclusion**: Restate what was done with `N`, what was supported, what was unsupported, and the concrete next step in 150 words or fewer.

## Automated Verification with `mechcheck`

Always verify LaTeX papers and theses with [`mechcheck`](https://github.com/M-Colley/mechcheck) before finishing:

1. Check availability with `python -m mechcheck --help`. If missing or broken in the active Python environment, install from GitHub:
   ```bash
   pip install "git+https://github.com/M-Colley/mechcheck"
   ```
2. Run unambiguous auto-fixes first:
   ```bash
   python -m mechcheck fix .
   ```
3. Run the full mechanical check matching the target venue (`chi`, `imwut`, `autoui`, `uist`, `assets`, `mobilehci`, `chiplay`, `trf`, `neurips`, `iclr`, `cvpr`, `aaai`) and stage:
   ```bash
   python -m mechcheck check . --venue chi
   ```
   Pass `--profile thesis` for theses, `--profile paper-anonymous` for anonymized submissions, and `--build-dir build` when compiled PDF/logs exist.
4. Resolve every reported error and warning, confirm zero dashes and unbroken single-line paragraphs, and verify abstract and paper word counts. If `mechcheck` exhibits an actionable upstream bug or false positive, patch `mechcheck` and submit a pull request upstream.
