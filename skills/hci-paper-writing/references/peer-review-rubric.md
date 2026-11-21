# HCI Empirical Peer Review Rubric

Apply this rubric whenever reviewing manuscripts, conference submissions, journal articles, proposals, or rebuttals for CHI, IMWUT, AutomotiveUI, UIST, ASSETS, MobileHCI, or related venues.

## 1. Verdict Calibration

Default the overall recommendation to **reject**. Recommend acceptance or minor revision only when empirical validity, statistical modeling, replication completeness, and open-science artifacts all withstand audit without fatal threats. State every critique directly and candidly without sugar-coating or generic praise.

## 2. Four-Gate Methodological Audit

Evaluate every submission sequentially across four gates:

### Gate 1: Construct, Internal, and Ecological Validity
* Check whether experimental manipulations isolate the claimed theoretical constructs without confounding variables (such as unequal information density, uncalibrated modality salience, or asymmetric task duration).
* Verify counterbalancing or Latin-square ordering across within-subjects conditions and check whether learning, fatigue, or carryover effects were tested.
* Assess apparatus and ecological fidelity: flag simulator, crowd-sourced video, or wizard-of-oz designs that extrapolate safety, trust, or behavioral claims beyond what the apparatus can support.

### Gate 2: Statistical Rigor and Numerical Consistency
* Recompute p-values from reported test statistics and degrees of freedom (`statcheck` or `mechcheck`) and flag rounding or directional mismatches.
* Flag pseudoreplication whenever multi-trial repeated-measures observations are pooled into independent-samples tests or unaggregated ANOVAs without participant and stimulus random effects (`lme4`, `glmmTMB`, `ordinal::clmm`, or `ARTool`).
* Check that family-wise error or false-discovery corrections (such as Holm-Bonferroni) are applied across post-hoc contrasts and multi-metric families.
* Flag null-hypothesis fallacies whenever authors claim `"no effect"`, `"unchanged"`, or `"equivalent"` from $p \ge .05$ without an equivalence test (TOST) or Bayes factor ($BF_{01}$).
* Verify that standardized effect sizes and 95% confidence intervals accompany inferential tests, and check whether sample size `N` is justified by an *a priori* power or sensitivity analysis.

### Gate 3: Replication Completeness
* Audit `Method` (`Apparatus`, `Procedure`, `Measurements`, `Participants`, `Analysis`) for missing parameters required by an independent laboratory: hardware models, display field of view, frame rates, latencies, gain factors, exact questionnaire citations, Likert scale anchors, recruitment channels, compensation, exclusions, and session duration.
* Flag unvalidated single-item ad-hoc scales when established psychometric instruments exist.

### Gate 4: Open Science and Artifact Integrity
* Check for a persistent, working anonymized link (OSF, Zenodo, or anonymized GitHub) containing raw/de-identified data, statistical analysis scripts, experimental stimuli, and system code.
* Treat `"data available upon request"`, broken links, or missing analysis scripts as major Desk/Review defects.

## 3. Review Structure and Prose Rules

Obey all prose constraints from `AGENTS.md` (short declarative sentences, claims before evidence, explicit transitions, single-line unbroken paragraphs, zero prose dashes, and zero forbidden rhetorical styles):

1. **Summary (1 paragraph, 2 to 3 sentences)**: State what the submission built or tested, its sample size `N`, and its primary empirical claim.
2. **Recommendation and Core Rationale (1 short paragraph)**: State the verdict (**Reject**, **Major Revision**, or **Accept**) in the first sentence, followed by the decisive methodological or empirical reasons.
3. **Major Flaws (numbered list)**: Order defects by severity. Open each item with the concrete validity or statistical claim, cite the exact section, table, or statistic from the manuscript as evidence, and state what study or re-analysis would be required to resolve it.
4. **Minor Issues (numbered list)**: List localized reporting omissions, citation gaps, figure legibility issues, and `mechcheck`-level prose or cross-reference defects.
