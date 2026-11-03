"""
Regenerates the app's data files from the analysis pipeline.

Run from the pipeline folder (the one holding phase_model.joblib and
grid_scores.pkl, produced by fit_final.py and score_grid.py):

    python /path/to/app/build_app_data.py /path/to/app/data

It writes a lean model bundle (scikit-learn objects plus plain arrays and
lists, so loading does not depend on pandas' pickle format) and the scored
recipe grid as a compressed CSV.
"""
import sys
import joblib
import numpy as np
import pandas as pd

out = sys.argv[1] if len(sys.argv) > 1 else "data"
b = joblib.load("phase_model.joblib")
lean = dict(rf=b["rf"], gp=b["gp"], prep=b["prep"], Z_train=np.asarray(b["Z_train"], dtype=float),
            X_train=b["X_train"][b["raw_features"]].to_numpy(dtype=float), raw_features=list(b["raw_features"]),
            y_train=[str(v) for v in b["y_train"]], doi_train=[str(v) for v in b["doi_train"]],
            classes=list(b["classes"]), range_thresholds={k: float(v) for k, v in b["range_thresholds"].items()},
            gp_temperature=float(b["gp_temperature"]), gp_name=b["gp_name"])
joblib.dump(lean, f"{out}/model.joblib", compress=3)
S = pd.read_pickle("grid_scores.pkl")
keep = ["si_al", "na_si", "k_si", "h2o_si", "T", "t", "age", "nn_dist", "support", "papers_nearby"] + \
       [f"{p}_{c}" for p in ["rf", "gp", "P"] for c in b["classes"]]
S[keep].round(5).to_csv(f"{out}/grid_scores.csv.gz", index=False, compression="gzip")
print("wrote", f"{out}/model.joblib", "and", f"{out}/grid_scores.csv.gz")
