# Typo detection strategy research (2026-02-26, revision 2)

## Context and constraints

This revision focuses on approaches that improve typo detection/correction quality **without** manual labels, explicit user feedback loops, or human validation.

Current Danote baseline (from repo):

- Candidate generation: SymSpell + Levenshtein fallback.
- Ranking: weighted distance/similarity/frequency/dictionary signals.
- Decision classes: `typo_likely`, `uncertain`, `new`.
- Metrics: high Top-1 correction (~83%), lower status classification (~40%).

The quality gap suggests candidate generation is already strong; the main opportunity is **probabilistic scoring and calibration**.

---

## 1) Methods overview

### Method A — Noisy-channel decoding with unsupervised EM estimation

**Mechanism**

Use the classic objective:

\[
\hat{w} = \arg\max_w P(w \mid x) = \arg\max_w P(x \mid w)P(w)
\]

- \(x\): observed token (possibly misspelled)
- \(w\): candidate correction
- \(P(w)\): language prior from clean corpora (token/lemma frequency + LM probability)
- \(P(x \mid w)\): error model (insert/delete/substitute/transpose, including Danish diacritics)

Estimate error model parameters with EM from unlabeled text by treating latent clean word as hidden variable over candidate lattice from SymSpell.

**Why no manual feedback is needed**

- Uses only unlabeled corpora + generated candidate sets.
- EM infers error probabilities from co-occurrence likelihood.

**Expected impact**

- Candidate ranking: **High** (principled fusion of prior + edit process).
- Classification accuracy: **High** (posterior probability directly usable).
- False positive rate: **Medium/High reduction** via stronger \(P(w)\) prior.

---

### Method B — Synthetic typo generation for self-supervised training

**Mechanism**

From clean Danish corpora, synthesize noisy tokens using parameterized corruption operators:

- keyboard-neighbor substitution
- diacritic perturbation (`a↔å`, `o↔ø`, `ae↔æ`)
- insertion/deletion/transposition
- compounding boundary perturbation (`arbejdsmarked` ↔ `arbejds marked`)
- inflectional ending noise (`-en`, `-er`, `-ede`, etc.)

Train either:

1. A discriminative ranker on candidate pairs \((x, w_i)\), or
2. Character seq2seq/encoder model to score \(P(w\mid x)\).

Use curriculum mixing: 70% realistic noise (keyboard/diacritics), 30% harder perturbations.

**Why no manual feedback is needed**

- Training labels are generated automatically from clean text.

**Expected impact**

- Candidate ranking: **High** for in-distribution typo types.
- Classification accuracy: **Medium/High** via better separation of typo vs truly new.
- False positive rate: **Risk of increase** if synthetic distribution is unrealistic (mitigate via calibration and held-out clean text checks).

---

### Method C — Masked language model (MLM) reranking for contextual plausibility

**Mechanism**

For each candidate \(w_i\) in sentence context \(c\), compute pseudo-likelihood score:

\[
s_i = \lambda_1 \log P_{\text{char}}(w_i\mid x) + \lambda_2 \log P_{\text{MLM}}(w_i \mid c)
\]

Run only for top-K candidates from SymSpell to control latency.

Gate reranking to uncertain cases (e.g., small top1-top2 margin).

**Why no manual feedback is needed**

- MLM is pretrained self-supervised on raw text.
- No task-specific human labels required.

**Expected impact**

- Candidate ranking: **High** on context-sensitive ambiguities.
- Classification accuracy: **Medium/High** through posterior sharpening.
- False positive rate: **Medium reduction** for words plausible as named entities vs typos (if combined with entity priors).

---

### Method D — Unlabeled Bayesian threshold calibration (mixture modeling)

**Mechanism**

Treat model confidence score \(s\) as a mixture of latent populations:

\[
p(s) = \pi\,p(s\mid z=\text{typo}) + (1-\pi)\,p(s\mid z=\text{new})
\]

Fit mixture (e.g., Beta-mixture or Gaussian mixture on transformed logits) via EM. Convert score to posterior:

\[
P(z=\text{typo}\mid s) = \frac{\pi p(s\mid z=\text{typo})}{p(s)}
\]

Then map posterior bands to `typo_likely` / `uncertain` / `new`.

**Why no manual feedback is needed**

- Uses only unlabeled score distributions from production traffic/offline corpora.

**Expected impact**

- Candidate ranking: **Low direct**, but improves final decisioning.
- Classification accuracy: **High** (primary target).
- False positive rate: **High reduction** via posterior-based thresholding and controlled prior \(\pi\).

---

### Method E — Unsupervised confusion-matrix estimation from corpora

**Mechanism**

Estimate character confusion probabilities \(P(c'\mid c)\), insertion/deletion priors, and transposition priors from noisy-clean alignment inferred over candidate graphs.

Practical route:

1. Generate candidate clean words for each token.
2. Soft-align token to candidates with posterior weights.
3. Aggregate weighted edit operations into confusion matrix.
4. Iterate (EM-like) to convergence.

Use per-device keyboard layouts (mobile vs desktop) as separate priors if available.

**Why no manual feedback is needed**

- All alignments are latent, inferred from unlabeled text.

**Expected impact**

- Candidate ranking: **Medium/High** (better realistic edit weighting).
- Classification accuracy: **Medium** via better confidence spread.
- False positive rate: **Medium reduction** by lowering probability of implausible edits.

---

### Method F — Character-level denoising model trained on synthetic noise

**Mechanism**

Train char-level Transformer/BiLSTM denoiser on synthetic pairs \((x, w)\). Use output sequence probability or edit posterior as additional candidate feature.

In production, do not free-generate by default; use it as reranking scorer over dictionary-constrained candidates to prevent hallucinations.

**Why no manual feedback is needed**

- Synthetic supervision from clean corpora.

**Expected impact**

- Candidate ranking: **Medium/High** for non-trivial typo patterns.
- Classification accuracy: **Medium**.
- False positive rate: **Low/Medium risk** unless dictionary-constrained.

---

### Method G — Distributional anomaly detection for “new” vs typo separation

**Mechanism**

Build token normality score from character LM perplexity + subword frequency + morphology plausibility.

Example anomaly score:

\[
a(x)=\alpha\,\text{PPL}_{\text{charLM}}(x)+\beta\,\text{OOD}_{\text{subword}}(x)+\gamma\,\text{morph\_penalty}(x)
\]

Combine with correction posterior to avoid over-correcting true neologisms/loanwords.

**Why no manual feedback is needed**

- Trained on unlabeled text statistics.

**Expected impact**

- Candidate ranking: **Low direct**.
- Classification accuracy: **Medium**.
- False positive rate: **High reduction** (main benefit).

---

### Method H — Morphology-aware candidate generation and scoring

**Mechanism**

For Danish morphology and compounding:

- Segment candidate compounds with weighted FST or Morfessor-like unsupervised segmentation.
- Compute lemma/stem compatibility score and inflection plausibility.
- Penalize corrections violating likely Danish morphotactics.

**Why no manual feedback is needed**

- Unsupervised segmentation and frequency-based morphology priors require only raw corpora.

**Expected impact**

- Candidate ranking: **Medium** (especially long compounds).
- Classification accuracy: **Medium**.
- False positive rate: **Medium reduction** for valid but rare inflections.

---

## 2) Evidence

### Academic references

1. Brill, E., & Moore, R. (2000). *An Improved Error Model for Noisy Channel Spelling Correction*. ACL.
   - Canonical noisy-channel spell correction with richer error model.
2. Kernighan, Church, & Gale (1990). *A Spelling Correction Program Based on a Noisy Channel Model*. COLING.
   - Early probabilistic framing still used in modern systems.
3. Mays, Damerau, Mercer (1991). *Context based spelling correction*. Information Processing & Management.
   - Demonstrates context-informed correction gains.
4. Devlin et al. (2019). *BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding*. NAACL.
   - Foundation for MLM-based contextual scoring.
5. Pruthi et al. (2019). *Combating Adversarial Misspellings with Robust Word Recognition*. ACL.
   - Char/subword robustness evidence relevant to typo noise.
6. Sun et al. (2020). *Chinese Spelling Correction as Noisy Channel* (COLING).
   - Modern noisy-channel + neural reranking hybrid template.
7. Survey examples for neural spell correction pipelines:
   - https://arxiv.org/abs/2105.05977
   - https://aclanthology.org/2020.coling-main.82/

### Production evidence (publicly documented patterns)

- Search engines (Google/Bing) have publicly discussed query spelling systems based on large-language priors + error models + context, i.e., noisy-channel style decomposition at web scale.
- Microsoft spell checking stack has long used confusion sets, language priors, and context signals in Office/Bing-era publications/patents.
- Grammarly engineering/public talks describe context-aware neural scoring and ranking, consistent with MLM/reranker architecture for ambiguity resolution.

(Exact internal implementations are proprietary; evidence is from public papers/blogs/talks and patents.)

### Open-source implementations to inspect

- SymSpell: fast candidate retrieval baseline.
- KenLM: efficient n-gram scoring for context prior.
- Hugging Face Transformers: Danish/Scandinavian MLM rerankers.
- Morfessor: unsupervised morphology segmentation.
- OpenFST / Pynini: weighted edit transducers for confusion-aware decoding.

---

## 3) Feasibility analysis

| Method | Eng. complexity | Runtime cost | Data requirements | Risk profile |
|---|---|---:|---|---|
| A. Noisy-channel + EM | Medium | Low/Medium | Unlabeled Danish corpus + lexicon | Low/Medium (well-understood) |
| B. Synthetic typo self-supervision | Medium | Medium (training) / Low (inference if used for ranker) | Clean corpus | Medium (synthetic-real mismatch) |
| C. MLM reranker | Medium/High | Medium/High unless gated | Raw text + pretrained model | Medium (latency, infra) |
| D. Bayesian unlabeled calibration | Low/Medium | Low | Unlabeled score logs | Low (decision-layer only) |
| E. Unsupervised confusion estimation | Medium | Low at inference | Unlabeled tokens + candidate lattice | Medium (convergence quality) |
| F. Char denoiser (synthetic) | Medium/High | Medium | Clean corpus + synthetic noise | Medium/High (overcorrection risk) |
| G. Distributional anomaly detector | Medium | Low | Large unlabeled corpus | Medium (OOD threshold tuning) |
| H. Morphology-aware scoring | Medium/High | Medium | Danish corpus + segmentation artifacts | Medium (pipeline complexity) |

Implementation guidance for current Danote stack:

- Start with **D + A + E** in current `ranking.py` / `decision.py` flow (minimal architecture disruption).
- Add **C** only as stage-2 reranker for `uncertain` bucket.
- Keep **F** dictionary-constrained and behind feature flag.

---

## 4) Specific applicability to Danish

### Diacritics (`æ`, `ø`, `å`)

- Explicitly parameterize error model with asymmetric substitutions:
  - `ae→æ`, `oe→ø`, `aa→å` and reverse mappings.
- Include keyboard-layout adjacency priors for Danish keyboards.
- Keep transliteration edits lower-cost than arbitrary substitutions.

### Compounding

- Danish compound words are frequent and productive.
- Add compound-aware candidate generation:
  - split/merge hypotheses with corpus frequency priors.
- Avoid false positives by allowing rare-but-valid compounds if subparts are high-probability.

### Inflectional variation

- Include stem+suffix plausibility score (noun definiteness, plural, verb tense endings).
- Penalize corrections that improve edit distance but violate common inflectional patterns.

### Small-corpus constraints

- Use transfer from multilingual Scandinavian models for MLM.
- Back off to n-gram LM + noisy-channel when neural model confidence is low.
- Regularize synthetic noise generator with conservative corruption rates to avoid overfitting artifacts.

---

## 5) Ranking of top 5 approaches

Ranking criteria: expected quality gain, implementation cost, risk, maintainability.

1. **Noisy-channel + unlabeled EM estimation (A)**
   - Gain: High; Cost: Medium; Risk: Low/Medium; Maintainability: High.
2. **Bayesian unlabeled calibration (D)**
   - Gain: High for status accuracy; Cost: Low/Medium; Risk: Low; Maintainability: High.
3. **Unsupervised confusion-matrix estimation (E)**
   - Gain: Medium/High; Cost: Medium; Risk: Medium; Maintainability: Medium/High.
4. **MLM reranker with uncertainty gating (C)**
   - Gain: Medium/High; Cost: Medium/High; Risk: Medium; Maintainability: Medium.
5. **Synthetic typo self-supervised ranker (B)**
   - Gain: Medium/High; Cost: Medium; Risk: Medium; Maintainability: Medium.

Why these five first:

- They directly address the current gap (good candidates, weak status decisioning).
- They can be layered incrementally around existing SymSpell candidate generation.

---

## Additional exploration directions (explicit requests)

### Synthetic typo generation from clean corpora

- Build generator with operation priors \(\theta\):
  \(p(\tilde{x}\mid x;\theta)=\prod_t p(o_t\mid\theta)\).
- Fit \(\theta\) from unlabeled alignment statistics (Method E), not human labels.

### Noisy-channel spelling correction models

- Implement weighted finite-state pipeline:
  - Lexicon WFST \(L\), error WFST \(E\), LM WFST \(G\).
  - Decode via shortest path in composed graph \(E \circ L \circ G\).

### EM-based error probability estimation

- E-step: posterior over latent clean candidate for each noisy token.
- M-step: re-estimate edit operation probabilities from expected counts.

### Confusion matrix estimation from unlabeled corpora

- Aggregate expected edit counts by character pair and position.
- Maintain separate matrices for mobile/desktop distributions if telemetry exists.

### Masked language models as probabilistic rerankers

- Use pseudo-log-likelihood over sentence with candidate substitution.
- Blend with edit posterior and frequency prior.

### Bayesian threshold calibration without labels

- Fit score mixture; set threshold by target posterior risk:
  - choose `typo_likely` threshold \(\tau\) minimizing
    \(\mathbb{E}[C_{FP}\mathbf{1}_{s>\tau,z=new}+C_{FN}\mathbf{1}_{s\le\tau,z=typo}]\).

### Distributional anomaly detection for rare tokens

- High anomaly + low correction posterior => classify as `new`.
- Low anomaly + high correction posterior => `typo_likely`.

### Character-level neural models trained with synthetic noise

- Use denoising objective with constrained beam over lexicon candidates.
- Export only scalar score feature to existing ranker to minimize integration churn.

---

## Concrete implementation pathway for Danote (no human labels)

1. Add noisy-channel score fields to `ranking.py` (prior, error likelihood, posterior).
2. Add offline EM job to estimate edit/confusion priors from unlabeled corpus snapshots.
3. Add Bayesian mixture calibrator in `decision.py` for posterior-to-class mapping.
4. Add optional MLM reranker path for `uncertain` cases only.
5. Extend benchmark script with calibration plots (ECE proxy), class confusion, and FP@new metrics.

This path improves status calibration while preserving current fast candidate retrieval architecture.
