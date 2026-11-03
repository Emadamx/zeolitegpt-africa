"""
Prediction and recipe-ranking engine used by the Streamlit app.

It reuses the same logic as the analysis scripts (fit_final.py,
score_grid.py, rank_recipes.py): averaged random forest + calibrated GP
probabilities, distance-based support levels, and the recipe filters
(reachable with non-negative reagents, kaolin share >= 0.5, (Na+K)/Al >= 1,
support from at least two papers, RF and GP within 0.25 of each other).
"""
import numpy as np
import pandas as pd
from zeomodel import transform, RAW_FEATURES
from converter import MW, reactive_moles

LISTS = {
    "FAU": dict(target="FAU", label="Best route to pure FAU (zeolite X)"),
    "FAU-kaolin-only": dict(target="FAU", label="FAU without extra silica (kaolin only)"),
    "LTA": dict(target="LTA", label="Best route to pure LTA (zeolite A)"),
}
MIN_KAOLIN_SHARE, MAX_DISAGREE, MIN_PAPERS, MAX_EXTRA_REAGENT_G = 0.5, 0.25, 2, 10.0
GEL = ["si_al", "na_si", "k_si", "h2o_si"]


def _probs(model, Z, classes):
    p = model.predict_proba(Z)
    P = np.zeros((len(Z), len(classes)))
    for j, c in enumerate(model[-1].classes_):
        P[:, classes.index(c)] = p[:, j]
    return P


def _scale(P, a):
    Q = np.clip(P, 1e-6, 1) ** a
    return Q / Q.sum(-1, keepdims=True)


def predict(bundle, X):
    """Probabilities (RF, calibrated GP, average), support level, number of
    nearby papers and the nearest training recipes from three different
    papers, for recipes given as raw variables."""
    classes = bundle["classes"]
    Z = transform(X[RAW_FEATURES].astype(float))
    rf = _probs(bundle["rf"], Z, classes)
    gp = _scale(_probs(bundle["gp"], Z, classes), bundle["gp_temperature"])
    Q = bundle["prep"].transform(Z)
    d = np.sqrt(((Q[:, None, :] - bundle["Z_train"][None, :, :]) ** 2).sum(-1))
    th = bundle["range_thresholds"]
    nn = d.min(1)
    support = np.where(nn <= th["well_supported"], "well", np.where(nn <= th["partly_supported"], "partly", "outside"))
    dois = np.array(bundle["doi_train"])
    papers = np.array([len(set(dois[row <= th["partly_supported"]])) for row in d])
    evidence = []
    for n, row in enumerate(np.argsort(d, 1)):
        picked, seen = [], set()
        for i in row:
            if dois[i] in seen:
                continue
            seen.add(dois[i])
            picked.append(dict(product=bundle["y_train"][i], doi=dois[i], distance=float(d[n, i]),
                               **{k: float(v) for k, v in zip(bundle["raw_features"], bundle["X_train"][i])}))
            if len(picked) == 3:
                break
        evidence.append(picked)
    return dict(rf=rf, gp=gp, avg=(rf + gp) / 2, nn_dist=nn, support=support, papers=papers, evidence=evidence)


def grams_for_grid(clay, G):
    """Reagent grams per 100 g calcined clay for every grid gel (see
    converter.ratios_to_grams; vectorised)."""
    n_si, n_al = clay["n_si"], clay["n_al"]
    up = G.si_al.values >= n_si / n_al
    s = np.where(up, G.si_al.values * n_al - n_si, 0.0)
    a = np.where(up, 0.0, n_si / G.si_al.values - n_al)
    si = n_si + s
    x = G.na_si.values * si - 2 * s
    k = G.k_si.values * si
    w = G.h2o_si.values * si - (5 * s + 1.5 * a + 0.5 * x + 0.5 * k)
    return pd.DataFrame({"NaOH": x * MW["NaOH"], "KOH": k * MW["KOH"], "Na2SiO3·5H2O": s * MW["Na2SiO3_5H2O"],
                         "Al(OH)3": a * MW["AlOH3"], "water": w * MW["H2O"],
                         "kaolin_share": (n_si + n_al) / (si + n_al + a),
                         "feasible": (x >= -1e-9) & (w >= -1e-9)}, index=G.index)


def rank(grid, clay, listname, top=5):
    """Ranked recipes for one clay (dict from reactive_moles) and one list."""
    target = LISTS[listname]["target"]
    g = grams_for_grid(clay, grid)
    keep = (g.feasible & (g.kaolin_share >= MIN_KAOLIN_SHARE)
            & ((grid.na_si + grid.k_si) * grid.si_al >= 1.0)
            & (grid.papers_nearby >= MIN_PAPERS)
            & ((grid[f"rf_{target}"] - grid[f"gp_{target}"]).abs() <= MAX_DISAGREE))
    if listname == "FAU-kaolin-only":
        keep &= (g["Na2SiO3·5H2O"] + g["Al(OH)3"]) <= MAX_EXTRA_REAGENT_G
    cand = pd.concat([grid, g], axis=1)[keep]
    cand = cand.sort_values([f"P_{target}", "P_SOD"], ascending=[False, True])
    return cand.drop_duplicates(GEL).head(top).reset_index(drop=True)


def clay_from_row(row, mode):
    return reactive_moles(row, mode)
