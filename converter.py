"""
Kaolin -> gel converter for ZeoliteGPT Africa.

Works on 100 g of calcined clay (metakaolin). The clay's oxide analysis
is converted to an LOI-free basis, and only its reactive part enters the
gel:
  - Al2O3 is taken as fully reactive.
  - SiO2 is split into reactive and inert (quartz) silica according to a
    chosen silica mode:
      "all"          every SiO2 counts as reactive (upper bound);
      "reported"     the paper's quartz content is inert;
      "stoichiometric" silica beyond what kaolinite (Si/Al = 1) can hold
                     is treated as inert quartz, i.e. at most
                     1.1785 g SiO2 per g Al2O3 is reactive.
    Calcination at 600-850 C activates kaolinite but not quartz, and the
    African papers report quartz surviving the conventional route
    (Holmes et al. 2012; Ayele et al. 2016), so "stoichiometric" is the
    default for calcined-metakaolin recipes.
  - Fe2O3, TiO2, CaO, MgO are treated as inert diluents. The clay's own
    Na2O and K2O are also left out of the gel, because in these clays they
    sit mainly in mica and feldspar, which do not dissolve readily; they are
    small next to the added hydroxide.

Reagents (all of fixed stoichiometry, so no product-specific assay is
assumed): NaOH, KOH, sodium metasilicate pentahydrate Na2SiO3.5H2O (extra
silica), aluminium hydroxide Al(OH)3 (extra alumina), and water.

Gel ratios are per element (Si/Al, Na/Si, K/Si, H2O/Si), matching the
phase model. Water counts added water, the 5 H2O of the metasilicate,
1.5 H2O per Al(OH)3 and 0.5 H2O per NaOH or KOH (the usual oxide-formula
convention: 2 NaOH = Na2O + H2O).
"""
import numpy as np
import pandas as pd

MW = {"SiO2": 60.084, "Al2O3": 101.961, "Fe2O3": 159.687, "TiO2": 79.866, "Na2O": 61.979, "K2O": 94.196,
      "CaO": 56.077, "MgO": 40.304, "NaOH": 39.997, "KOH": 56.106, "Na2SiO3_5H2O": 212.14,
      "AlOH3": 78.004, "H2O": 18.015}
KAOLINITE_SIO2_PER_AL2O3 = 2 * MW["SiO2"] / MW["Al2O3"]  # 1.1785 g/g for Si/Al = 1
OXIDES = ["SiO2", "Al2O3", "Fe2O3", "TiO2", "Na2O", "K2O", "CaO", "MgO"]


def calcined_basis(row):
    """Oxide wt% of the calcined clay. When an LOI is reported the oxides
    are divided by (100 - LOI); otherwise they are normalised to their sum."""
    ox = {o: (float(row[o]) if pd.notna(row.get(o)) else 0.0) for o in OXIDES}
    loi = row.get("LOI")
    denom = (100.0 - float(loi)) if pd.notna(loi) else sum(ox.values())
    q = row.get("quartz_wt")
    quartz = float(q) * 100.0 / denom if pd.notna(q) else np.nan
    return {o: v * 100.0 / denom for o, v in ox.items()}, quartz


def reactive_moles(row, silica_mode="stoichiometric"):
    """Moles of reactive Si and Al in 100 g of calcined clay, plus the
    share of the clay that is reactive."""
    ox, quartz = calcined_basis(row)
    sio2, al2o3 = ox["SiO2"], ox["Al2O3"]
    if silica_mode == "all":
        sio2_r = sio2
    elif silica_mode == "reported":
        if np.isnan(quartz):
            raise ValueError("no quartz content reported for this clay")
        sio2_r = sio2 - quartz
    elif silica_mode == "stoichiometric":
        sio2_r = min(sio2, KAOLINITE_SIO2_PER_AL2O3 * al2o3)
    else:
        raise ValueError(silica_mode)
    return dict(n_si=sio2_r / MW["SiO2"], n_al=2 * al2o3 / MW["Al2O3"],
                sio2_reactive_g=sio2_r, sio2_inert_g=sio2 - sio2_r, al2o3_g=al2o3,
                inert_other_g=sum(ox[o] for o in ["Fe2O3", "TiO2", "CaO", "MgO", "Na2O", "K2O"]))


def grams_to_ratios(clay, naoh=0.0, koh=0.0, silicate=0.0, aloh3=0.0, water=0.0):
    """Forward conversion: grams of reagents added to 100 g calcined clay
    -> per-element gel ratios. `clay` is the dict from reactive_moles."""
    s, a = silicate / MW["Na2SiO3_5H2O"], aloh3 / MW["AlOH3"]
    x, k = naoh / MW["NaOH"], koh / MW["KOH"]
    si = clay["n_si"] + s
    al = clay["n_al"] + a
    na = 2 * s + x
    h2o = water / MW["H2O"] + 5 * s + 1.5 * a + 0.5 * x + 0.5 * k
    return dict(si_al=si / al, na_si=na / si, k_si=k / si, h2o_si=h2o / si)


def ratios_to_grams(clay, si_al, na_si, k_si, h2o_si):
    """Inverse conversion: target gel ratios -> grams of reagents per 100 g
    calcined clay. Si/Al above the clay's own value is reached with sodium
    metasilicate, below it with Al(OH)3. Returns None when the target
    cannot be reached with non-negative amounts (for example when the
    metasilicate alone already brings more sodium than the target)."""
    n_si, n_al = clay["n_si"], clay["n_al"]
    native = n_si / n_al
    if si_al >= native:
        s = si_al * n_al - n_si
        a = 0.0
    else:
        s = 0.0
        a = n_si / si_al - n_al
    si = n_si + s
    x = na_si * si - 2 * s
    k = k_si * si
    w = h2o_si * si - (5 * s + 1.5 * a + 0.5 * x + 0.5 * k)
    if x < -1e-9 or w < -1e-9:
        return None
    grams = dict(naoh=x * MW["NaOH"], koh=k * MW["KOH"], silicate=s * MW["Na2SiO3_5H2O"],
                 aloh3=a * MW["AlOH3"], water=max(w, 0.0) * MW["H2O"])
    grams["kaolin_share"] = (n_si + n_al) / (si + n_al + a)
    return grams
