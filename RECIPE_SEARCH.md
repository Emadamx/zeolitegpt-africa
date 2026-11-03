# ZeoliteGPT Africa: kaolin converter and recipe search

Recorded 3 November 2026. To reproduce, run `score_grid.py` and then `rank_recipes.py` (after the model scripts in `MODEL_RESULTS.md`).

## 1. Converter (`converter.py`)

All amounts are per **100 g of calcined clay (metakaolin)**. To get the raw clay to calcine, multiply by 100 / (100 − LOI); that is about 103–117 g of raw clay for these deposits.

**Reactive silica.** Calcination at 600–850 °C activates kaolinite but leaves quartz unreacted. Several African papers report quartz surviving the conventional route (Holmes et al. 2012; Ayele et al. 2016). Three modes are available:

| Mode | Rule | Use |
|---|---|---|
| stoichiometric (default) | silica beyond what kaolinite (Si/Al = 1) can hold, 1.1785 g SiO2 per g Al2O3, is inert quartz | calcined-metakaolin recipes |
| reported | the paper's measured quartz content is inert | only where a paper reports quartz (Cameroon 2021, Ethiopia) |
| all | every SiO2 counts as reactive | upper-bound sensitivity |

**Inert material.** Fe2O3, TiO2, CaO and MgO are inert diluents. The clay's own Na2O and K2O are also left out of the gel: in these clays they sit mainly in mica and feldspar, and they are small next to the added hydroxide.

**Reagents.** All have fixed stoichiometry, so no product-specific assay is assumed:
- NaOH
- KOH
- sodium metasilicate pentahydrate (Na2SiO3·5H2O), for extra silica
- aluminium hydroxide (Al(OH)3), for extra alumina
- water

**Checks:**
- The stoichiometric rule puts 35.76 wt% of the Cameroon 2021 clay's SiO2 in kaolinite. The paper's own mineralogy gives 35.71 wt%.
- The converter reproduces the Ethiopian fusion recipe's gel exactly (Si/Al 1.365, Na/Si 3.296, H2O/Si 62.6).
- Converting a recipe to grams and back recovers the gel ratios exactly. Re-checking all 305 listed recipes gives a worst relative error of 4 × 10⁻⁵, from rounding.

## 2. Search (`score_grid.py`, `rank_recipes.py`)

**Grid.** 113,400 gels on the calcined-metakaolin route (no NaOH fusion):

| Variable | Levels |
|---|---|
| Si/Al | 0.9–3.0 |
| Na/Si | 0.5–4 |
| K/Si | 0, 0.15, 0.35 |
| H2O/Si | 20–130 |
| Temperature | 60–100 °C |
| Crystallisation time | 6–96 h |
| Aging | 0–72 h |

28,771 of these are within the model's supported range (3,000 well supported, 25,771 partly supported).

**Filters.** A recipe is kept only if all of these hold:
- reachable with non-negative reagent amounts;
- the clay supplies at least half of the gel's Si + Al;
- (Na + K)/Al ≥ 1, so every framework Al has a balancing cation;
- training recipes from at least 2 different papers lie within the supported radius;
- the random forest and the GP agree on the target probability to within 0.25.

**Ranking.** Recipes are ranked by the averaged model's probability of the target, with lower P(sodalite) breaking ties. Each recipe carries the nearest training recipes from three different papers as evidence.

## 3. Results

Because the model sees only gel ratios and conditions, **the best gel is the same for every clay.** The clay decides how much reagent is needed and how much of the batch becomes zeolite. A quartz-rich clay is mostly inert filler: the South African clays are only about 37% reactive, so they yield much less zeolite per batch.

| List | Gel (per element) | Conditions | Averaged P(target) | RF / GP | P(SOD) | Support |
|---|---|---|---|---|---|---|
| Best FAU | Si/Al 2.0, Na/Si 2.0, H2O/Si 45 (oxide form: SiO2/Al2O3 4, Na2O/SiO2 1.0, H2O/Na2O 45) | 70 °C, 48 h, no aging | 0.88 | 0.82 / 0.95 | 0.02 | well, 5 papers |
| FAU from kaolin only (≤ 10 g extra silica or alumina) | Si/Al 1.0, Na/Si 4.0, K/Si 0.35, H2O/Si 60 | 80 °C, 24 h, no aging | 0.51 | 0.40 / 0.62 | 0.04 | well, 2 papers |
| Best LTA | Si/Al 0.9, Na/Si 2.0, H2O/Si 60 | 90 °C, 6 h, no aging | 0.93 | 0.93 / 0.93 | 0.01 | well, 11 papers |

**Agreement with an independent paper.** The best FAU gel nearly matches the gel that Soliman et al. (2025) used to make faujasite from Egyptian kaolin (SiO2/Al2O3 4, Na2O/SiO2 1, H2O/Na2O 40, at 80 °C for 80 h). That paper is not in the training data.

**Kaolin-only FAU.** Without extra silica, the model's best option is a mixed Na–K gel at Si/Al 1. That is the composition region of low-silica X (LSX), the parent of the Li-LSX oxygen-concentrator adsorbent. Its probability is only about 0.5, with P(LTA) about 0.25, so this route is a genuine gamble on this data.

**Reagents per 100 g calcined clay** (stoichiometric mode, top recipe of each list):

| Clay | Best FAU: NaOH / Na2SiO3·5H2O / water (g) | Kaolin-only FAU: NaOH / KOH / water (g) | Best LTA: NaOH / Al(OH)3 / water (g) |
|---|---|---|---|
| Nigeria, Ajebo | 68.8 / 192.3 / 1336 | 139.5 / 17.4 / 919 (+4.9 g silicate) | 68.8 / 5.7 / 913 |
| Nigeria, Darazo | 68.9 / 192.3 / 1336 | 139.6 / 17.4 / 919 (+4.7 g silicate) | 68.9 / 5.7 / 914 |
| Nigeria, Elefun (calcined) | 60.5 / 160.4 / 1144 | 121.0 / 14.8 / 788 | 60.5 / 6.6 / 802 |
| Cameroon (2019 analysis) | 67.4 / 178.6 / 1274 | 134.7 / 16.5 / 877 | 67.4 / 7.3 / 893 |
| Cameroon (2021 analysis) | 53.2 / 141.0 / 1006 | 106.4 / 13.1 / 693 | 53.2 / 5.8 / 705 |
| Ethiopia, Hawassa | 61.3 / 162.4 / 1159 | 122.5 / 15.0 / 798 | 61.3 / 6.6 / 812 |
| Egypt, Abu Zenima | 57.0 / 151.1 / 1078 | 114.0 / 14.0 / 742 | 57.0 / 6.2 / 755 |
| Ghana, Kibi | 37.6 / 99.8 / 712 | 79.1 / 10.2 / 816 (+10 g silicate; partly supported) | 37.6 / 4.1 / 499 |
| South Africa, white clay | 26.5 / 70.2 / 501 | 55.6 / 7.1 / 573 (+7 g silicate; partly supported) | 26.5 / 2.9 / 351 |
| South Africa, red clay | 27.3 / 72.3 / 516 | 57.2 / 7.4 / 591 (+7.2 g silicate; partly supported) | 27.3 / 3.0 / 361 |
| Tanzania, Pugu | 63.3 / 168.0 / 1198 | 126.7 / 15.5 / 825 | 63.3 / 6.9 / 839 |
| Tanzania, Malangali | 59.7 / 158.3 / 1129 | 119.4 / 14.7 / 777 | 59.7 / 6.5 / 791 |
| Uganda, Mutaka (raw) | 64.6 / 171.4 / 1223 | 129.3 / 15.9 / 842 | 64.6 / 7.0 / 856 |

The full list, with the top 5 FAU, top 3 kaolin-only FAU and top 3 LTA recipes for every clay and every silica mode, is in `recipes_ranked.csv` (305 rows).

**"All silica reactive" sensitivity.** If quartz did count as reactive, Kibi (Si/Al 2.03) would reach the best FAU gel with almost no added silica. Its kaolin-only FAU probability would jump from 0.61 to 0.88, and the South African clays would look similar. That is why the quartz assumption has to be stated: for quartz-rich clays it changes the answer.

## 4. Evidence references

All 22 ZeoSyn papers cited as nearest-recipe evidence were checked against Crossref or OpenAlex: each DOI resolves to a real paper with the recorded title, first author, journal and year. They are listed in `evidence_refs.csv`.

## 5. Limitations to state with the recipes

1. **Calcined-metakaolin route only.** NaOH fusion is outside the model's reach (external accuracy 0.62 on fusion runs vs 0.75 on calcined runs).
2. **What the model cannot see.** Iron and titanium oxides, clay reactivity and the calcination temperature are not inputs.
3. **The probabilities are for the phase that forms.** They say nothing about yield, crystallinity or N2/O2 selectivity. Li exchange of the Na-X product is a separate, standard step.
4. **The search grid is coarse.** Better optima may lie between grid points.
5. **No lab validation.** The recipes are ranked suggestions for experiments, each backed by named literature recipes.
