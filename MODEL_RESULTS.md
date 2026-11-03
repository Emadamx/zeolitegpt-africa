# ZeoliteGPT Africa: phase model results

Recorded 3 November 2026. All numbers come from the scripts in this folder and can be reproduced by running them in order: `cv_models.py`, `evaluate_cv.py`, `fit_final.py`.

## 1. Training set

- **Source:** ZeoSyn (Pan et al., ACS Central Science 10(3), 729–743, 2024; doi:10.1021/acscentsci.3c01615).
- **Filter (kaolin-compatible chemistry only):**
  - no organic template;
  - gel contains only Si, Al, Na, K and water (no other heteroatoms or cations, no fluoride, solvent or acid);
  - gel Si/Al ≤ 5, computed from the molar Si and Al columns;
  - a single product: one framework, or amorphous.
- **Size:** 504 routes from 125 papers.

| Class | Routes |
|---|---|
| LTA | 124 |
| FAU | 108 |
| Other frameworks (MER, LTL, CHA, CAN, PHI, ANA, …) | 120 |
| Amorphous | 54 |
| GIS (zeolite P) | 53 |
| SOD (sodalite) | 45 |

**Recipe variables:** gel Si/Al, Na/Si, K/Si, H2O/Si, crystallisation temperature, crystallisation time, aging time. Ratios and times are log-transformed. Missing aging time is taken as 0.

## 2. Models

- **Random forest:** 500 trees, minimum 3 routes per leaf.
- **GP classifier:** one-vs-rest, with a Matern 5/2 kernel that has its own length scale for each variable. Its probabilities are sharpened with one fitted exponent (a = 1.23), which corrects the slight underconfidence of the one-vs-rest GP.
- **Headline model:** the equal-weight average of the two. The weighting was fixed in advance, not tuned.

## 3. Cross-validation on unseen papers

- **Method:** 5 folds grouped by DOI, repeated 3 times with different shuffles.
- **Scale:** 6 classes; always guessing the most common class scores 0.25 accuracy.

| Model | Accuracy | Log loss | Calibration error (top class) | Calibration error, P(FAU) | AUC FAU | AUC LTA | AUC SOD |
|---|---|---|---|---|---|---|---|
| No-skill (class frequencies) | 0.25 | 1.71 | – | – | – | – | – |
| Logistic regression | 0.53 | 1.39 | 0.108 | 0.058 | 0.77 | 0.90 | 0.92 |
| Random forest | 0.55 | 1.14 | 0.060 | 0.077 | 0.82 | 0.90 | 0.87 |
| GP (RBF kernel) | 0.56 | 1.39 | 0.074 | 0.084 | 0.84 | 0.87 | 0.77 |
| GP (Matern), uncalibrated | 0.60 | 1.23 | 0.120 | 0.076 | 0.86 | 0.92 | 0.81 |
| GP (Matern), calibrated | 0.60 | 1.22 | 0.063 | 0.079 | 0.85 | 0.91 | 0.81 |
| **Average of RF and calibrated GP** | **0.59** | **1.13** | **0.050** | 0.078 | **0.86** | – | 0.86 |

The GP's calibration exponent was cross-fitted: for each fold it was fitted only on the other folds' held-out predictions.

**Reliability of P(FAU):** see `fig_reliability_fau.png`. In the populated bins, observed frequencies stay within about ±0.15 of the predicted probability. The calibrated GP is underconfident in its top bin (mean prediction 0.84; every route there was FAU).

## 4. Out-of-range check

**Distance to the nearest training recipe and accuracy** (held-out routes, see `fig_error_vs_distance.png`):

| Distance band (quintiles of held-out routes) | RF accuracy | Calibrated GP accuracy |
|---|---|---|
| Closest 20% (distance ≤ 0.48) | 0.80 | 0.76 |
| Next 20% (0.48–0.84) | 0.60 | 0.60 |
| Remaining 60% (> 0.84) | 0.41–0.48 | 0.50–0.56 |

**Support levels used for recipes:**
- **Well supported:** distance ≤ 0.48.
- **Partly supported:** distance ≤ 0.84.
- **Outside:** beyond 0.84.

The model's own confidence flags its errors slightly better than distance does (AUROC 0.73 vs 0.63 for the random forest), so recipes are reported with both.

## 5. External test: published African kaolin syntheses

The test set has 19 runs from 9 verified papers; 16 of them gave a single product.

| | Accuracy |
|---|---|
| All 16 single-product runs (all three models) | 0.69 |
| Runs from calcined metakaolin (no NaOH fusion), n = 8 | 0.75 |
| Runs that used NaOH fusion, n = 8 | 0.62 |

**Probability quality on the 16 runs** (Brier score for P(FAU); no-skill baseline 0.234):

| Model | Log loss | Brier P(FAU) |
|---|---|---|
| Random forest | 1.01 | 0.184 |
| Calibrated GP | 1.18 | 0.191 |
| Average | 1.06 | 0.178 |

**What it gets right:**
- the three Nigerian zeolite A runs from Ahoko, Ajebo and Darazo, which the earlier two-model setup got confidently wrong;
- the Cameroon zeolite A run from calcined metakaolin;
- both Ethiopian runs at the stated gel ratio;
- the Egyptian zeolite X run (P(FAU) 0.84);
- the Cameroon 2021 zeolite X and Y runs;
- the South African zeolite X runs.

**What it gets wrong, and why:**
1. **Sodalite vs zeolite X (South African white clay, no added Al).** The real product was sodalite; the model gives P(FAU) 0.75 and P(SOD) 0.03. This was a NaOH-fusion route.
2. **Cameroon 2019, fusion route → zeolite X.** The model predicts LTA from the same gel that gave LTA without fusion. Pretreatment is not a model input.
3. **Ghana (Kibi) → zeolite A.** The model predicts FAU when all of the clay's silica is counted as reactive. If reactive Si/Al is about 1.0 (roughly half the silica present as unreactive quartz), both models switch to LTA (P ≈ 0.62). This points to the converter's quartz switch, not to the model.
4. **Ethiopian fusion run, mass-based ratios → predicted FAU.** At the paper's stated ratios the prediction is LTA (correct). The paper's two descriptions of the gel disagree.
5. **Elefun → predicted FAU.** This label is the weakest in the set: the paper shows no XRD of the product.

## 6. Consequences for the recipe search

- **Search only calcined-metakaolin recipes (no NaOH fusion).** That is the regime ZeoSyn covers, and where the external accuracy was higher. List fusion as a limitation.
- **The converter must have a reactive-silica (quartz) switch.** For quartz-rich clays the answer depends on it.
- **Report every recipe with:**
  - P(FAU), P(LTA) and P(SOD) from the averaged model, with the RF and GP values shown separately;
  - its support level;
  - the three nearest training recipes as evidence (their DOIs come from ZeoSyn and must be verified before being cited).
- **Treat sodalite as the main risk.** A high P(FAU) in a fusion-like, high-alkalinity region is not enough on its own.

## Files

| File | Contents |
|---|---|
| `zeomodel.py` | training-set filter and feature transform |
| `cv_models.py` | repeated paper-grouped CV (writes `cv_oof.npz`) |
| `evaluate_cv.py` | metrics (`cv_metrics.csv`, `cv_distance_bins.csv`) and figures |
| `temperature.py` | cross-fitted calibration check |
| `fit_final.py` | final models (`phase_model.joblib`) and African test (`african_test_predictions.csv`) |
| `phase_predict.py` | prediction helper used by the recipe search |
