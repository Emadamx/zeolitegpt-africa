# ZeoliteGPT Africa

A web app that suggests synthesis recipes for turning African kaolin into FAU (zeolite X) or LTA (zeolite A), the zeolite families used in medical oxygen concentrators. Each suggestion comes with:
- the model's chance of getting the pure product;
- how well published data supports the recipe;
- the closest published recipes as evidence.

Built for the MaterialsGPT Africa hackathon by team ZeoliteGPT Africa.

## What the app does

| Page | What you can do |
|---|---|
| **Find a recipe** | Pick one of 13 published African clay analyses, or enter your own. Choose how to treat quartz and set a goal: best FAU, FAU without extra silica, or best LTA. The page shows a batch sheet in grams for your batch size, the chance of each product, the support level and three evidence papers. |
| **Try your own gel** | Set any gel composition and conditions, see what the model expects to crystallise, and convert the gel into grams for a chosen clay. |
| **How reliable is it?** | Cross-validated accuracy and calibration on unseen papers, the test on 16 published African kaolin syntheses, and the model's limits. |
| **Data and sources** | Clay analyses, the verified reference list, and the evidence papers. |

## How it works

- **Model:** the equal-weight average of a random forest and a calibrated Gaussian-process classifier. It is trained on 504 recipes from 125 papers in ZeoSyn, keeping only gels made of Si, Al, Na, K and water with gel Si/Al ≤ 5 and a single product.
- **Predictions:** six possible products (FAU, LTA, SOD, GIS, amorphous, other).
- **Converter:** turns a clay's oxide analysis plus reagent amounts (NaOH, KOH, sodium metasilicate pentahydrate, Al(OH)3, water) into gel ratios, with a switch for whether quartz counts as reactive.
- **Recipe search:** recipes come from a scored grid of 113,400 gels. A recipe is kept only if:
  - it can be made with non-negative reagent amounts;
  - the clay supplies at least half of the gel's Si + Al;
  - (Na + K)/Al ≥ 1;
  - at least two different papers support it;
  - the random forest and the GP agree to within 0.25.

The full results and their reproduction are documented in `MODEL_RESULTS.md` and `RECIPE_SEARCH.md` (included in this folder).

## Run it on your computer

```bash
pip install -r requirements.txt
streamlit run app.py
```

Python 3.13 is recommended. The saved model needs the exact library versions in `requirements.txt` (scikit-learn 1.9.1 in particular).

## Put it online (Streamlit Community Cloud, free)

1. **Create the repository.** Create a new public GitHub repository, for example `zeolitegpt-africa`. Upload the contents of this folder to the repository root: `app.py`, `engine.py`, `converter.py`, `zeomodel.py`, `requirements.txt`, the `.streamlit`, `data` and `assets` folders, and this README.
2. **Start a new app.** Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub and choose **Create app**.
3. **Point it at the code.** Pick the repository and branch, and set the main file to `app.py`.
4. **Set the Python version.** Open **Advanced settings** and choose **Python 3.13**.
5. **Deploy.** The first build takes a few minutes while the libraries install. The app then lives at an address like `zeolitegpt-africa.streamlit.app`, which you can choose.

**Before a demo:** apps on the free tier go to sleep after 12 hours without visitors, and the first visitor then waits for a restart. Open the app yourself a few minutes before you present.

## Files

| File | Purpose |
|---|---|
| `app.py` | the Streamlit interface |
| `engine.py` | predictions, support levels, evidence and recipe ranking |
| `converter.py` | clay analysis + reagents to gel ratios, and back |
| `zeomodel.py` | training-set definition and feature transform |
| `data/model.joblib` | the trained models and training points |
| `data/grid_scores.csv.gz` | the scored recipe grid |
| `data/clays.csv` | the 13 African clay analyses (plus the raw Elefun analysis), with sources |
| `data/references_verified.csv` | verified references for the clay data and the test set |
| `data/evidence_refs.csv` | verified records of the 22 papers cited as evidence |
| `data/cv_metrics.csv`, `data/cv_distance_bins.csv`, `data/african_test_predictions.csv` | validation results shown on the reliability page |
| `assets/*.png` | calibration and accuracy-versus-distance figures |
| `build_app_data.py` | regenerates `data/model.joblib` and `data/grid_scores.csv.gz` from the analysis pipeline |

## Data and licence

**Training data.** E. Pan, S. Kwon, Z. Jensen, M. Xie, R. Gómez-Bombarelli, M. Moliner, Y. Román-Leshkov, E. Olivetti. ZeoSyn: A Comprehensive Zeolite Synthesis Dataset Enabling Machine-Learning Rationalization of Hydrothermal Parameters. *ACS Central Science* 10(3), 729–743 (2024). doi:10.1021/acscentsci.3c01615. Released under the MIT licence; see `LICENSE-ZeoSyn.txt`.

**Clay data and test set.** These come from published papers, listed with full citations in `data/references_verified.csv`. Every reference was checked against at least three independent sources.

## Limits

- The recipes cover the calcined-metakaolin route only, not NaOH fusion.
- Iron, titanium, clay reactivity and calcination temperature are not model inputs.
- The model predicts which phase forms, not yield, crystallinity or N2/O2 selectivity.
- None of the recipes have been tested in a lab yet.
