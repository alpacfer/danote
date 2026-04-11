# Typo detection strategy research (2026-02-26, revision 2)

## Context and constraints

Focuses on typo detection/correction improvement **without** manual labels, user feedback loops, or human validation.

Current Danote baseline: SymSpell + Levenshtein fallback for candidates; weighted distance/similarity/frequency/dictionary ranking; decision classes `typo_likely`, `uncertain`, `new`. Metrics: ~83% Top-1 correction, ~40% status classification.

Quality gap: candidate generation strong; main opportunity is **probabilistic scoring and calibration**.

---

## 1) Methods overview

### Method A — Noisy-channel decoding with unsupervised EM estimation

**Mechanism**

\[
\hat{w} = \arg\max_w P(w \mid x) = \arg\max_w P(x \mid w)P(w)
\]

- \(x\): observed token (possibly misspelled)
- \(w\): candidate correction
- \(P(w)\): language prior from clean corpora (token/lemma frequency + LM probability)
- \(P(x \mid w)\): error model (insert/delete/substitute/transpose, including Danish diacritics)

Estimate error model via EM from unlabeled text; treat latent clean word as hidden variable over candidate lattice from SymSpell.

**Why no manual feedback needed:** uses only unlabeled corpora + generated candidate sets. EM infers error probabilities from co-occurrence.

**Expected impact:** Candidate ranking **High** (principled prior + edit fusion). Classification accuracy **High** (posterior directly usable). FP rate **Medium/High reduction** via stronger \(P(w)\) prior.

---

### Method B — Synthetic typo generation for self-supervised training

**Mechanism**

Synthesize noisy tokens from clean Danish corpora via parameterized corruption: keyboard-neighbor substitution, diacritic perturbation (`a↔å`, `o↔ø`, `ae↔æ`), insertion/deletion/transposition, compounding boundary perturbation (`arbejdsmarked` ↔ `arbejds marked`), inflectional ending noise (`-en`, `-er`, `-ede`, etc.).

Train: (1) discriminative ranker on pairs \((x, w_i)\), or (2) char seq2seq/encoder scoring \(P(w\mid x)\). Curriculum: 70% realistic noise (keyboard/diacritics), 30% harder perturbations.

**Why no manual feedback needed:** labels auto-generated from clean text.

**Expected impact:** Candidate ranking **High** for in-distribution types. Classification **Medium/High**. FP rate **risk of increase** if synthetic distribution unrealistic (mitigate via calibration + held-out clean text checks).

---

### Method C — Masked language model (MLM) reranking for contextual plausibility

**Mechanism**

For each candidate \(w_i\) in context \(c\):

\[
s_i = \lambda_1 \log P_{\text{char}}(w_i\mid x) + \lambda_2 \log P_{\text{MLM}}(w_i \mid c)
\]

Run only for top-K SymSpell candidates. Gate to uncertain cases (small top1-top2 margin).

**Why no manual feedback needed:** MLM pretrained self-supervised; no task-specific labels.

**Expected impact:** Ranking **High** on context-sensitive ambiguities. Classification **Medium/High** via posterior sharpening. FP rate **Medium reduction** for named-entity vs typo (with entity priors).

---

### Method D — Unlabeled Bayesian threshold calibration (mixture modeling)

**Mechanism**

Treat score \(s\) as mixture of latent populations:

\[
p(s) = \pi\,p(s\mid z=\text{typo}) + (1-\pi)\,p(s\mid z=\text{new})
\]

Fit mixture (Beta or Gaussian on transformed logits) via EM. Posterior:

\[
P(z=\text{typo}\mid s) = \frac{\pi p(s\mid z=\text{typo})}{p(s)}
\]

Map posterior bands to `typo_likely` / `uncertain` / `new`.

**Why no manual feedback needed:** uses only unlabeled score distributions from production traffic/offline corpora.

**Expected impact:** Ranking **Low direct**. Classification **High** (primary target). FP rate **High reduction** via posterior-based thresholding + controlled prior \(\pi\).

---

### Method E — Unsupervised confusion-matrix estimation from corpora

**Mechanism**

Estimate \(P(c'\mid c)\), insertion/deletion/transposition priors from noisy-clean alignment over candidate graphs:

1. Generate candidates per token.
2. Soft-align token to candidates with posterior weights.
3. Aggregate weighted edit operations into confusion matrix.
4. Iterate EM-like to convergence.

Use per-device keyboard layouts as separate priors if available.

**Why no manual feedback needed:** all alignments latent, inferred from unlabeled text.

**Expected impact:** Ranking **Medium/High**. Classification **Medium**. FP rate **Medium reduction** (lower implausible-edit probability).

---

### Method F — Character-level denoising model trained on synthetic noise

**Mechanism**

Train char Transformer/BiLSTM denoiser on synthetic \((x, w)\) pairs. Use output probability or edit posterior as candidate feature. In production: reranking scorer over dictionary-constrained candidates only (no free-generation to prevent hallucinations).

**Why no manual feedback needed:** synthetic supervision from clean corpora.

**Expected impact:** Ranking **Medium/High** for non-trivial patterns. Classification **Medium**. FP rate **Low/Medium risk** unless dictionary-constrained.

---

### Method G — Distributional anomaly detection for "new" vs typo separation

**Mechanism**

Token normality from char LM perplexity + subword frequency + morphology plausibility:

\[
a(x)=\alpha\,\text{PPL}_{\text{charLM}}(x)+\beta\,\text{OOD}_{\text{subword}}(x)+\gamma\,\text{morph\_penalty}(x)
\]

Combine with correction posterior to avoid over-correcting neologisms/loanwords.

**Why no manual feedback needed:** trained on unlabeled text statistics.

**Expected impact:** Ranking **Low direct**. Classification **Medium**. FP rate **High reduction** (main benefit).

---

### Method H — Morphology-aware candidate generation and scoring

**Mechanism**

For Danish morphology/compounding: segment candidates via weighted FST or Morfessor-like unsupervised segmentation; compute lemma/stem compatibility + inflection plausibility; penalize corrections violating Danish morphotactics.

**Why no manual feedback needed:** unsupervised segmentation + frequency-based morphology priors from raw corpora.

**Expected impact:** Ranking **Medium** (esp. long compounds). Classification **Medium**. FP rate **Medium reduction** for rare valid inflections.

---

## 2) Evidence

### Academic references

1. Brill & Moore (2000). *An Improved Error Model for Noisy Channel Spelling Correction*. ACL.
2. Kernighan, Church & Gale (1990). *A Spelling Correction Program Based on a Noisy Channel Model*. COLING.
3. Mays, Damerau & Mercer (1991). *Context based spelling correction*. IP&M.
4. Devlin et al. (2019). *BERT: Pre-training of Deep Bidirectional Transformers*. NAACL.
5. Pruthi et al. (2019). *Combating Adversarial Misspellings with Robust Word Recognition*. ACL.
6. Sun et al. (2020). *Chinese Spelling Correction as Noisy Channel*. COLING.
7. Neural spell correction surveys: https://arxiv.org/abs/2105.05977, https://aclanthology.org/2020.coling-main.82/

### Production evidence

- Google/Bing query spelling: large-language priors + error models + context (noisy-channel at scale).
- Microsoft spell checking: confusion sets, language priors, context signals (Office/Bing publications/patents).
- Grammarly: context-aware neural scoring/ranking (MLM/reranker architecture).

### Open-source implementations

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
| B. Synthetic typo self-supervision | Medium | Medium (training) / Low (inference if ranker) | Clean corpus | Medium (synthetic-real mismatch) |
| C. MLM reranker | Medium/High | Medium/High unless gated | Raw text + pretrained model | Medium (latency, infra) |
| D. Bayesian unlabeled calibration | Low/Medium | Low | Unlabeled score logs | Low (decision-layer only) |
| E. Unsupervised confusion estimation | Medium | Low at inference | Unlabeled tokens + candidate lattice | Medium (convergence quality) |
| F. Char denoiser (synthetic) | Medium/High | Medium | Clean corpus + synthetic noise | Medium/High (overcorrection risk) |
| G. Distributional anomaly detector | Medium | Low | Large unlabeled corpus | Medium (OOD threshold tuning) |
| H. Morphology-aware scoring | Medium/High | Medium | Danish corpus + segmentation artifacts | Medium (pipeline complexity) |

Implementation guidance: start with **D + A + E** in `ranking.py` / `decision.py` (minimal disruption). Add **C** as stage-2 reranker for `uncertain` bucket. Keep **F** dictionary-constrained behind feature flag.

---

## 4) Danish-specific applicability

### Diacritics (`æ`, `ø`, `å`)

Parameterize error model with asymmetric substitutions: `ae→æ`, `oe→ø`, `aa→å` + reverse. Include Danish keyboard-layout adjacency priors. Keep transliteration edits lower-cost than arbitrary substitutions.

### Compounding

Danish compounds frequent/productive. Add compound-aware candidate generation: split/merge hypotheses with corpus frequency priors. Allow rare-but-valid compounds when subparts are high-probability.

### Inflectional variation

Include stem+suffix plausibility score (noun definiteness, plural, verb tense endings). Penalize corrections improving edit distance but violating common inflectional patterns.

### Small-corpus constraints

Transfer from multilingual Scandinavian MLMs. Back off to n-gram LM + noisy-channel when neural confidence low. Regularize synthetic noise with conservative corruption rates.

---

## 5) Top 5 approaches

Criteria: quality gain, implementation cost, risk, maintainability.

1. **Noisy-channel + unlabeled EM estimation (A)** — High gain; Medium cost; Low/Medium risk; High maintainability.
2. **Bayesian unlabeled calibration (D)** — High gain (status accuracy); Low/Medium cost; Low risk; High maintainability.
3. **Unsupervised confusion-matrix estimation (E)** — Medium/High gain; Medium cost; Medium risk; Medium/High maintainability.
4. **MLM reranker with uncertainty gating (C)** — Medium/High gain; Medium/High cost; Medium risk; Medium maintainability.
5. **Synthetic typo self-supervised ranker (B)** — Medium/High gain; Medium cost; Medium risk; Medium maintainability.

These five address current gap (good candidates, weak status decisioning) and layer incrementally around existing SymSpell generation.

---

## Additional exploration directions

### Synthetic typo generation from clean corpora

Generator with operation priors \(\theta\): \(p(\tilde{x}\mid x;\theta)=\prod_t p(o_t\mid\theta)\). Fit \(\theta\) from unlabeled alignment statistics (Method E), not human labels.

### Noisy-channel spelling correction models

Weighted finite-state pipeline: Lexicon WFST \(L\), error WFST \(E\), LM WFST \(G\). Decode via shortest path in \(E \circ L \circ G\).

### EM-based error probability estimation

E-step: posterior over latent clean candidate per noisy token. M-step: re-estimate edit operation probabilities from expected counts.

### Confusion matrix estimation from unlabeled corpora

Aggregate expected edit counts by char pair + position. Separate matrices for mobile/desktop if telemetry exists.

### Masked language models as probabilistic rerankers

Pseudo-log-likelihood over sentence with candidate substitution. Blend with edit posterior + frequency prior.

### Bayesian threshold calibration without labels

Fit score mixture; set threshold by target posterior risk: choose \(\tau\) minimizing \(\mathbb{E}[C_{FP}\mathbf{1}_{s>\tau,z=new}+C_{FN}\mathbf{1}_{s\le\tau,z=typo}]\).

### Distributional anomaly detection for rare tokens

High anomaly + low correction posterior => `new`. Low anomaly + high posterior => `typo_likely`.

### Character-level neural models trained with synthetic noise

Denoising objective + constrained beam over lexicon candidates. Export scalar score feature to existing ranker (minimize integration churn).

---

## Concrete implementation pathway (no human labels)

1. Add noisy-channel score fields to `ranking.py` (prior, error likelihood, posterior).
2. Add offline EM job to estimate edit/confusion priors from unlabeled corpus snapshots.
3. Add Bayesian mixture calibrator in `decision.py` for posterior-to-class mapping.
4. Add optional MLM reranker path for `uncertain` cases only.
5. Extend benchmark with calibration plots (ECE proxy), class confusion, FP@new metrics.

Improves status calibration while preserving current fast candidate retrieval.
