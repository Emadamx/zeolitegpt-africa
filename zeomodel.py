"""
Shared data and feature definitions for the ZeoliteGPT Africa phase model.

The training set is the part of ZeoSyn that a kaolin-derived gel can
reproduce: no organic template, gel made only of Si, Al, Na, K and water
(no other heteroatoms, cations, fluoride, solvents or acids), gel Si/Al
computed from the molar columns and capped at 5, and a single product
(phase-pure framework, or amorphous).

Every route is described by seven recipe variables, the same ones the
kaolin converter and recipe search produce:
  si_al   gel Si/Al (molar, per element)
  na_si   Na/Si
  k_si    K/Si
  h2o_si  H2O/Si
  T       crystallisation temperature, C
  t       crystallisation time, h
  age     aging time, h (missing taken as 0 = no aging)
"""
import numpy as np
import pandas as pd

RAW_FEATURES = ["si_al", "na_si", "k_si", "h2o_si", "T", "t", "age"]
CLASSES = ["FAU", "LTA", "SOD", "GIS", "amorphous", "other"]
OTHER_ELEMENTS = ["P", "Li", "Sr", "Rb", "Cs", "Ba", "Ca", "F", "Ge", "Ti", "In", "B", "Mg", "Ga", "Ni",
                  "Mn", "Fe", "Co", "Cr", "Zn", "Nb", "Be", "W", "Ce", "Cu", "Sn", "Gd", "La", "Y", "Dy",
                  "Sm", "Ag", "Cd", "Zr", "V", "Ta", "Ru", "Hf", "Yb", "Tl", "As"]


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def load_training_set(df, si_al_cap=5.0):
    """Returns (raw feature frame, class labels, DOI groups, source rows)."""
    si, al = _num(df["Si"]), _num(df["Al"])
    no_osda = df[["osda1", "osda2", "osda3"]].isna().all(axis=1)
    amorphous = df["product1"].astype(str).str.strip().str.lower().eq("amorphous")
    labelled = df["Code1"].notna() | amorphous
    others = [e for e in OTHER_ELEMENTS if e in df.columns]
    has_other = (df[others].apply(_num).fillna(0) > 0).any(axis=1)
    extras = pd.Series(False, index=df.index)
    for col in ["sda1", "solvent", "acid"]:
        if col in df.columns:
            extras |= _num(df[col]).fillna(0) > 0
    mask = (no_osda & (si > 0) & (al > 0) & (si / al <= si_al_cap) & df["Code2"].isna()
            & labelled & ~has_other & ~extras)
    d = df[mask].copy()
    code = d["Code1"].fillna("amorphous").astype(str)
    y = np.where(code.isin(CLASSES), code, "other")

    s = _num(d["Si"])
    X = pd.DataFrame({
        "si_al": s / _num(d["Al"]),
        "na_si": _num(d["Na"]).fillna(0) / s,
        "k_si": _num(d["K"]).fillna(0) / s,
        "h2o_si": (_num(d["H2O"]) / s).replace(0, np.nan),
        "T": _num(d["cryst_temp"]).where(lambda v: v >= 20),
        "t": _num(d["cryst_time"]).replace(0, np.nan),
        "age": _num(d["aging_time"]).fillna(0),
    }, index=d.index)
    return X, pd.Series(y, index=d.index), d["doi"].astype(str), d


def transform(X):
    """Maps raw recipe variables to the modelling space. Ratios and times
    span orders of magnitude, so they are log-transformed; temperature is
    kept linear."""
    X = X[RAW_FEATURES]
    return pd.DataFrame({
        "log_si_al": np.log(X["si_al"]),
        "log1p_na_si": np.log1p(X["na_si"]),
        "log1p_k_si": np.log1p(X["k_si"]),
        "log_h2o_si": np.log(X["h2o_si"]),
        "T": X["T"],
        "log1p_t": np.log1p(X["t"]),
        "log1p_age": np.log1p(X["age"]),
    }, index=X.index)
