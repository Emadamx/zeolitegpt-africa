"""
ZeoliteGPT Africa - Streamlit app.

Shows, for a chosen African kaolin, the synthesis recipes most likely to
give phase-pure FAU (zeolite X) or LTA (zeolite A), with the model's
confidence, how well the recipe is supported by published data, and the
closest published recipes as evidence.
"""
import warnings
import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st

import engine
from converter import ratios_to_grams

warnings.filterwarnings("ignore")
st.set_page_config(page_title="ZeoliteGPT Africa", page_icon="⬡", layout="wide")

COBALT, OCHRE, GREY, INK, MUTED = "#2457A5", "#A8741A", "#A3ADB2", "#17222B", "#5B6870"
PRODUCT_LABELS = {"FAU": "FAU (zeolite X / Y)", "LTA": "LTA (zeolite A)", "SOD": "SOD (sodalite)",
                  "GIS": "GIS (zeolite P)", "amorphous": "Amorphous", "other": "Other frameworks"}
CLAY_LABELS = {
    "EG-ABUZENIMA": "Abu Zenima, South Sinai (Egypt)",
    "NG-AJEBO": "Ajebo, Ogun State (Nigeria)",
    "NG-DARAZO": "Darazo, Bauchi State (Nigeria)",
    "NG-ELEFUN-MK": "Elefun, Abeokuta (Nigeria), calcined analysis",
    "CM-YAOUNDE-2019": "Cameroon kaolinite clay, 2019 analysis",
    "CM-YAOUNDE-2021": "Cameroon kaolinite clay, 2021 analysis",
    "ET-HAWASSA": "Hawassa ceramic-factory kaolin (Ethiopia)",
    "GH-KIBI": "Kibi, Eastern Region (Ghana)",
    "ZA-WHITE": "White clay (South Africa)",
    "ZA-RED": "Red clay, Barrydale (South Africa)",
    "TZ-PUGU": "Pugu, Coast Region (Tanzania)",
    "TZ-MALANGALI": "Malangali, Iringa Region (Tanzania)",
    "UG-MUTAKA-RAW": "Mutaka (Uganda)",
}
CUSTOM = "Enter my own clay analysis"
SILICA_MODES = {
    "Quartz stays unreacted (recommended)": "stoichiometric",
    "Use the paper's measured quartz": "reported",
    "Count all silica as reactive": "all",
}
SILICA_HELP = ("Calcining kaolin at 600–850 °C activates the kaolinite but not quartz. The recommended setting "
               "treats any silica beyond what kaolinite can hold (Si/Al = 1) as unreactive quartz. "
               "'Count all silica as reactive' is an upper bound, useful to see how much the answer depends on quartz.")

st.markdown(f"""
<style>
  .block-container {{ max-width: 1180px; padding-top: 2.2rem; }}
  .sheet {{ border: 1.5px solid {COBALT}; border-radius: 0.5rem; padding: 1.1rem 1.3rem 0.9rem; background: #FFFFFF; }}
  .sheet h4 {{ margin: 0 0 0.2rem 0; font-size: 1.15rem; }}
  .sheet .sub {{ color: {MUTED}; font-size: 0.9rem; margin-bottom: 0.8rem; }}
  .sheet table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; border: none !important; }}
  .sheet tr, .sheet td {{ border: none !important; background: transparent !important; }}
  .sheet td {{ padding: 0.32rem 0 !important; border-bottom: 1px solid #E3E9EA !important; vertical-align: baseline; }}
  .sheet td.amt {{ text-align: right; font-size: 1.35rem; font-weight: 700; white-space: nowrap; }}
  .sheet td.unit {{ width: 1.6rem; padding-left: 0.4rem !important; color: {MUTED}; }}
  .sheet .note {{ display: block; color: {MUTED}; font-size: 0.82rem; }}
  .sheet tr.step td {{ border-bottom: none !important; padding-top: 0.75rem !important; }}
  .gel {{ font-variant-numeric: tabular-nums; color: {INK}; }}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_model():
    return joblib.load("data/model.joblib")


@st.cache_data
def load_tables():
    grid = pd.read_csv("data/grid_scores.csv.gz")
    clays = pd.read_csv("data/clays.csv").set_index("kaolin_id")
    refs = pd.read_csv("data/references_verified.csv").set_index("ref_id")
    ev = pd.read_csv("data/evidence_refs.csv").set_index("doi")
    return grid, clays, refs, ev


bundle = load_model()
grid, clays, refs, evrefs = load_tables()


def fmt(x, nd=1):
    return f"{x:,.{nd}f}"


def dash(df):
    """Formats a table for display: missing values become a dash, and every
    column becomes text so mixed columns render cleanly."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = [("–" if pd.isna(v) else f"{v:g}") for v in out[c]]
        else:
            out[c] = out[c].where(out[c].notna(), "–").astype(str)
    return out


def prob_chart(p, highlight):
    df = pd.DataFrame({"product": [PRODUCT_LABELS[c] for c in bundle["classes"]], "p": p})
    hl = PRODUCT_LABELS[highlight]
    colour = alt.condition(alt.datum.product == hl, alt.value(OCHRE if highlight == "LTA" else COBALT), alt.value(GREY))
    base = alt.Chart(df).encode(
        y=alt.Y("product:N", sort=list(PRODUCT_LABELS.values()), title=None, axis=alt.Axis(labelLimit=200)),
        x=alt.X("p:Q", scale=alt.Scale(domain=[0, 1]), title="Chance of each product (averaged model)",
                axis=alt.Axis(format=".1f", values=[0, 0.2, 0.4, 0.6, 0.8, 1.0], grid=True, gridColor="#E3E9EA")),
        tooltip=[alt.Tooltip("product:N", title="Product"), alt.Tooltip("p:Q", title="Chance", format=".2f")])
    bars = base.mark_bar(height=16, cornerRadiusEnd=3).encode(color=colour)
    text = base.mark_text(align="left", dx=5, color=INK).encode(text=alt.Text("p:Q", format=".2f"))
    return (bars + text).properties(height=210).configure_view(strokeWidth=0)


def support_line(level, papers):
    if level == "well":
        return f":blue-badge[Well supported] close to published recipes from {papers} papers"
    if level == "partly":
        return f":orange-badge[Partly supported] published recipes from {papers} papers lie nearby"
    return ":red-badge[Outside the data] no published recipe is close; treat the prediction as a guess"


def evidence_block(ev_list):
    for e in ev_list:
        doi = e["doi"]
        if doi in evrefs.index:
            r = evrefs.loc[doi]
            cite = f"{r.first_author} (first author), {r.year}. *{r.title}*. {r.journal}."
        else:
            cite = "Source paper not yet checked against Crossref."
        st.markdown(
            f"**{PRODUCT_LABELS.get(e['product'], e['product'])}** from {cite} "
            f"[doi:{doi}](https://doi.org/{doi})  \n"
            f"<span class='gel'>Si/Al {e['si_al']:.2f}, Na/Si {e['na_si']:.2f}, K/Si {e['k_si']:.2f}, "
            f"H2O/Si {e['h2o_si']:.0f}, {e['T']:.0f} °C, {e['t']:.0f} h, aged {e['age']:.0f} h</span>",
            unsafe_allow_html=True)


st.title("ZeoliteGPT Africa")
st.markdown("Synthesis recipes for turning African kaolin into the zeolites used in medical oxygen concentrators, "
            "with the model's confidence and the published recipes behind each suggestion.")

tab_find, tab_try, tab_rel, tab_src = st.tabs(["Find a recipe", "Try your own gel", "How reliable is it?",
                                               "Data and sources"])

# ---------------------------------------------------------------------------
with tab_find:
    left, right = st.columns([1, 2.35], gap="large")
    with left:
        al2o3 = None
        options = list(CLAY_LABELS) + [CUSTOM]
        choice = st.selectbox("Kaolin", options, format_func=lambda k: CLAY_LABELS.get(k, k), index=0)
        if choice == CUSTOM:
            st.caption("Oxide analysis of the raw clay, in wt% (XRF or wet chemistry).")
            c1, c2 = st.columns(2)
            sio2 = c1.number_input("SiO2", 0.0, 100.0, 48.0, 0.1)
            al2o3 = c2.number_input("Al2O3", 0.0, 100.0, 36.0, 0.1)
            fe2o3 = c1.number_input("Fe2O3", 0.0, 50.0, 1.0, 0.1)
            tio2 = c2.number_input("TiO2", 0.0, 20.0, 1.0, 0.1)
            loi = c1.number_input("Loss on ignition", 0.0, 30.0, 12.0, 0.1)
            qz = c2.number_input("Quartz (0 = unknown)", 0.0, 90.0, 0.0, 0.5)
            row = pd.Series(dict(SiO2=sio2, Al2O3=al2o3, Fe2O3=fe2o3, TiO2=tio2, LOI=loi,
                                 quartz_wt=qz if qz > 0 else np.nan))
            clay_name, source = "your clay", None
        else:
            row = clays.loc[choice]
            clay_name = CLAY_LABELS[choice]
            source = refs.loc[row.ref_id]
        modes = [m for m, v in SILICA_MODES.items() if v != "reported" or pd.notna(row.get("quartz_wt"))]
        mode_label = st.radio("Silica assumption", modes, help=SILICA_HELP)
        listname = st.radio("Goal", list(engine.LISTS), format_func=lambda k: engine.LISTS[k]["label"])
        batch = st.number_input("Batch size (g of calcined clay)", 10.0, 10000.0, 100.0, 10.0)

        can_compute = choice != CUSTOM or al2o3 > 0
        if can_compute:
            clay = engine.clay_from_row(row, SILICA_MODES[mode_label])
            reactive = clay["sio2_reactive_g"] + clay["al2o3_g"]
            st.markdown(f"**Calcined clay:** {reactive:.0f}% reactive kaolinite, {clay['sio2_inert_g']:.0f}% "
                        f"unreacted quartz, {clay['inert_other_g']:.0f}% iron, titanium and other oxides.")
            if pd.notna(row.get("LOI")):
                st.caption(f"{batch * 100 / (100 - row['LOI']):,.0f} g of raw clay give {batch:,.0f} g calcined "
                           f"(loss on ignition {row['LOI']:.1f}%).")
            if source is not None:
                link = f"https://doi.org/{source.doi}" if isinstance(source.doi, str) and source.doi else \
                    source.doi_target.split("; ")[-1]
                st.caption(f"Clay analysis: {source.authors} ({source.year}). [{source.title}]({link}).")

    with right:
        if not can_compute:
            st.info("Enter an Al2O3 content above zero to see recipes.")
        else:
            res = engine.rank(grid, clay, listname, top=5 if listname == "FAU" else 3)
            target = engine.LISTS[listname]["target"]
            if res.empty:
                st.warning("No recipe passes all the checks for this clay with this goal and silica assumption. "
                           "Try another goal or the recommended silica assumption.")
            else:
                pick = st.radio("Option", list(range(len(res))), horizontal=True,
                                format_func=lambda i: f"Option {i + 1}: {res.loc[i, f'P_{target}']:.2f}",
                                help="Options are ranked by the averaged model's chance of the pure target product. "
                                     "Each option is a different gel, shown with its best conditions.")
                r = res.loc[pick]
                f = batch / 100.0
                lines = [("Calcined clay (metakaolin)", batch, "g", "calcined at 600–850 °C in the source papers")]
                for reag, name in [("NaOH", "Sodium hydroxide, NaOH"), ("KOH", "Potassium hydroxide, KOH"),
                                   ("Na2SiO3·5H2O", "Sodium metasilicate pentahydrate"),
                                   ("Al(OH)3", "Aluminium hydroxide, Al(OH)3"), ("water", "Water")]:
                    if r[reag] > 0.05:
                        lines.append((name, r[reag] * f, "g", ""))
                body = "".join(f"<tr><td>{n}" + (f"<span class='note'>{note}</span>" if note else "") +
                               f"</td><td class='amt'>{fmt(v)}</td><td class='unit'>{u}</td></tr>"
                               for n, v, u, note in lines)
                aging = f"Age at room temperature for {r.age:.0f} h, then crystallise" if r.age > 0 else "Crystallise without aging"
                body += (f"<tr class='step'><td colspan='3'>{aging} at <b>{r['T']:.0f} °C for {r.t:.0f} h</b> "
                         f"in a sealed vessel.</td></tr>")
                st.markdown(
                    f"<div class='sheet'><h4>Batch sheet for {clay_name}</h4>"
                    f"<div class='sub gel'>Gel: Si/Al {r.si_al:.2f}, Na/Si {r.na_si:.2f}, K/Si {r.k_si:.2f}, "
                    f"H2O/Si {r.h2o_si:.0f}. Kaolin supplies {100 * r.kaolin_share:.0f}% of the Si + Al.</div>"
                    f"<table>{body}</table></div>", unsafe_allow_html=True)

                X = pd.DataFrame([r[["si_al", "na_si", "k_si", "h2o_si", "T", "t", "age"]].astype(float)])
                pr = engine.predict(bundle, X)
                st.markdown(f"#### Chance of pure {target}: {r[f'P_{target}']:.2f}")
                st.markdown(f"Random forest {r[f'rf_{target}']:.2f}, Gaussian process {r[f'gp_{target}']:.2f}. "
                            f"Chance of sodalite instead: {r.P_SOD:.2f}.")
                st.markdown(support_line(pr["support"][0], int(pr["papers"][0])))
                st.altair_chart(prob_chart(pr["avg"][0], target), width="stretch")
                st.markdown("##### Closest published recipes")
                evidence_block(pr["evidence"][0])
                with st.expander("Compare all options"):
                    show = res[["si_al", "na_si", "k_si", "h2o_si", "T", "t", "age", f"P_{target}", f"rf_{target}",
                                f"gp_{target}", "P_SOD", "support", "papers_nearby", "NaOH", "KOH", "Na2SiO3·5H2O",
                                "Al(OH)3", "water"]].copy()
                    for c in ["NaOH", "KOH", "Na2SiO3·5H2O", "Al(OH)3", "water"]:
                        show[c] = show[c] * f
                    show.index = [f"Option {i + 1}" for i in range(len(show))]
                    st.dataframe(show.round(2), width="stretch", column_config={
                        "si_al": "Si/Al", "na_si": "Na/Si", "k_si": "K/Si", "h2o_si": "H2O/Si", "T": "°C",
                        "t": "Time (h)", "age": "Aging (h)", f"P_{target}": f"P({target})",
                        f"rf_{target}": "Forest", f"gp_{target}": "GP", "P_SOD": "P(sodalite)",
                        "support": "Support", "papers_nearby": "Papers nearby",
                        "NaOH": "NaOH (g)", "KOH": "KOH (g)", "Na2SiO3·5H2O": "Metasilicate (g)",
                        "Al(OH)3": "Al(OH)3 (g)", "water": "Water (g)"})
                st.caption("Predictions cover the calcined-metakaolin route only (no NaOH fusion). Iron, titanium, "
                           "clay reactivity and calcination temperature are not model inputs, and nothing here has "
                           "been tested in a lab yet.")

# ---------------------------------------------------------------------------
with tab_try:
    st.markdown("Set a gel composition and conditions to see what the model expects to crystallise.")
    a, b_ = st.columns([1, 1.35], gap="large")
    with a:
        si_al = st.slider("Gel Si/Al", 0.5, 5.0, 2.0, 0.05)
        na_si = st.slider("Na/Si", 0.0, 6.0, 2.0, 0.05)
        k_si = st.slider("K/Si", 0.0, 1.0, 0.0, 0.01)
        h2o_si = st.slider("H2O/Si", 10, 200, 45, 1)
        T = st.slider("Crystallisation temperature (°C)", 40, 200, 70, 5)
        t = st.select_slider("Crystallisation time (h)", [1, 2, 3, 4, 6, 8, 12, 18, 24, 36, 48, 72, 96, 144, 240], 48)
        age = st.select_slider("Aging time (h)", [0, 1, 3, 6, 12, 24, 48, 72, 144], 0)
    with b_:
        X = pd.DataFrame([dict(si_al=si_al, na_si=na_si, k_si=k_si, h2o_si=h2o_si, T=T, t=t, age=age)])
        pr = engine.predict(bundle, X)
        top = bundle["classes"][int(np.argmax(pr["avg"][0]))]
        st.markdown(f"#### Most likely: {PRODUCT_LABELS[top]}, {pr['avg'][0].max():.2f}")
        st.markdown(support_line(pr["support"][0], int(pr["papers"][0])))
        if (na_si + k_si) * si_al < 1:
            st.warning("(Na + K)/Al is below 1, so there are not enough cations to balance every framework "
                       "aluminium. The gel cannot convert fully.")
        st.altair_chart(prob_chart(pr["avg"][0], top), width="stretch")
        both = pd.DataFrame({"Random forest": pr["rf"][0], "Gaussian process": pr["gp"][0], "Average": pr["avg"][0]},
                            index=[PRODUCT_LABELS[c] for c in bundle["classes"]]).round(2)
        st.dataframe(both, width="stretch")
        st.markdown("##### Closest published recipes")
        evidence_block(pr["evidence"][0])
        with st.expander("Turn this gel into grams for a kaolin"):
            ck = st.selectbox("Kaolin", list(CLAY_LABELS), format_func=lambda k: CLAY_LABELS[k], key="try_clay")
            cm = st.radio("Silica assumption", [m for m in SILICA_MODES if SILICA_MODES[m] != "reported"],
                          key="try_mode", help=SILICA_HELP)
            g = ratios_to_grams(engine.clay_from_row(clays.loc[ck], SILICA_MODES[cm]), si_al, na_si, k_si, h2o_si)
            if g is None:
                st.warning("This gel cannot be made from this clay with these reagents: reaching the Si/Al needs more "
                           "sodium (from sodium metasilicate) or more water than the gel allows.")
            else:
                st.dataframe(pd.DataFrame({"Per 100 g calcined clay (g)": [g["naoh"], g["koh"], g["silicate"],
                                                                            g["aloh3"], g["water"]]},
                                          index=["NaOH", "KOH", "Sodium metasilicate pentahydrate",
                                                 "Aluminium hydroxide", "Water"]).round(1), width="stretch")
                st.caption(f"Kaolin supplies {100 * g['kaolin_share']:.0f}% of the gel's Si + Al.")

# ---------------------------------------------------------------------------
with tab_rel:
    st.markdown(
        "The model was trained on **504 published recipes from 125 papers** in the ZeoSyn dataset: gels made only "
        "of silicon, aluminium, sodium, potassium and water, with gel Si/Al up to 5 and a single product. "
        "It predicts which of six products forms. It was tested on papers it never saw, and on 16 published "
        "syntheses that used African kaolin.")
    m = pd.read_csv("data/cv_metrics.csv").set_index("model")
    rows = {"No-skill (class frequencies)": "Guessing from class frequencies", "LogReg": "Logistic regression",
            "RandomForest": "Random forest", "GP-RBF": "Gaussian process (RBF kernel)",
            "GP-Matern": "Gaussian process (Matern), uncalibrated",
            "GP-Matern-calibrated": "Gaussian process (Matern), calibrated"}
    tbl = pd.DataFrame({
        "Correct product": m["accuracy_mean"], "Log loss (lower is better)": m["log_loss_mean"],
        "Calibration error": m.get("top_label_ECE_mean"), "FAU ranking (AUC)": m.get("AUC_FAU_mean"),
        "Sodalite ranking (AUC)": m.get("AUC_SOD_mean")}).rename(index=rows)
    avg_row = pd.DataFrame({"Correct product": [0.586], "Log loss (lower is better)": [1.129], "Calibration error": [0.050],
                            "FAU ranking (AUC)": [0.857], "Sodalite ranking (AUC)": [0.859]},
                           index=["Average of forest and calibrated GP (used in this app)"])
    st.markdown("##### On papers the model never saw (5-fold, grouped by paper, 3 repeats)")
    st.dataframe(pd.concat([tbl, avg_row]).astype(float).map(lambda v: "–" if pd.isna(v) else f"{v:.3f}"),
                 width="stretch")
    c1, c2 = st.columns(2, gap="large")
    c1.image("assets/fig_reliability_fau.png",
             caption="Predicted chances of FAU track the observed rates to within about ±0.15 across the range.")
    c2.image("assets/fig_error_vs_distance.png",
             caption="Close to published recipes the model is right about 80% of the time; far away, about half.")
    st.markdown("##### On published syntheses from African kaolin")
    at = pd.read_csv("data/african_test_predictions.csv")
    show = at[["route_id", "label", "avg_pred", "avg_P_FAU", "avg_P_LTA", "avg_P_SOD", "support", "citation"]].rename(
        columns={"route_id": "Run", "label": "Reported product", "avg_pred": "Predicted", "avg_P_FAU": "P(FAU)",
                 "avg_P_LTA": "P(LTA)", "avg_P_SOD": "P(sodalite)", "support": "Support", "citation": "Paper"})
    st.dataframe(show, width="stretch", hide_index=True, height=35 * (len(show) + 1) + 3)
    st.markdown(
        "The model names the right product for **11 of 16** single-product runs: **6 of 8** made from calcined "
        "metakaolin and **5 of 8** made by fusing the clay with NaOH, a route the training data barely covers.")
    st.markdown("##### What it cannot tell you")
    st.markdown(
        "- **The NaOH fusion route.** Fused clay can give sodalite or zeolite X from the same gel, and the model "
        "cannot see the pretreatment.\n"
        "- **Effects of iron, titanium and clay reactivity.** These are not inputs.\n"
        "- **Yield, crystallinity and N2/O2 selectivity.** The model predicts which phase forms, nothing more. "
        "Exchanging the sodium of zeolite X for lithium is a separate, standard step.\n"
        "- **Lab-tested results.** None of these recipes have been made yet.")

# ---------------------------------------------------------------------------
with tab_src:
    st.markdown("##### Clay analyses")
    cl = clays.drop(index="NG-ELEFUN-RAW").copy()
    cl.insert(0, "Clay", [CLAY_LABELS[k] for k in cl.index])
    st.dataframe(cl[["Clay", "SiO2", "Al2O3", "Fe2O3", "TiO2", "Na2O", "K2O", "CaO", "MgO", "LOI", "quartz_wt",
                     "method", "citation", "doi"]].rename(columns={"quartz_wt": "Quartz", "method": "Method",
                                                                   "citation": "Source", "doi": "DOI"})
                 .pipe(dash),
                 width="stretch", hide_index=True, height=35 * (len(cl) + 1) + 3)
    st.caption("Oxide contents in wt% as reported in each paper.")
    st.markdown("##### Papers behind the clay data and the test set")
    st.caption("Every reference was checked against at least three independent sources (the paper or publisher page, "
               "Crossref or OpenAlex, and the DOI resolver); the 'Checks' column lists them.")
    rv = refs.reset_index()
    rv["Link"] = [f"https://doi.org/{d}" if isinstance(d, str) and d else t.split("; ")[-1]
                  for d, t in zip(rv.doi, rv.doi_target)]
    st.dataframe(rv[["authors", "year", "title", "journal", "volume", "pages", "Link", "checks"]].rename(
        columns={"authors": "Authors", "year": "Year", "title": "Title", "journal": "Journal", "volume": "Volume",
                 "pages": "Pages", "checks": "Checks"}).pipe(dash),
        width="stretch", hide_index=True, height=35 * (len(rv) + 1) + 3,
        column_config={"Link": st.column_config.LinkColumn("Link")})
    st.markdown("##### Papers cited as closest published recipes")
    er = evrefs.reset_index()
    er["Link"] = "https://doi.org/" + er.doi
    st.dataframe(er[["first_author", "year", "title", "journal", "Link", "verified_by"]].rename(
        columns={"first_author": "First author", "year": "Year", "title": "Title", "journal": "Journal",
                 "verified_by": "Checked with"}),
        width="stretch", hide_index=True, height=35 * (len(er) + 1) + 3,
        column_config={"Link": st.column_config.LinkColumn("Link")})
    st.markdown(
        "Training data: E. Pan, S. Kwon, Z. Jensen, M. Xie, R. Gómez-Bombarelli, M. Moliner, Y. Román-Leshkov, "
        "E. Olivetti. ZeoSyn: A Comprehensive Zeolite Synthesis Dataset Enabling Machine-Learning Rationalization of "
        "Hydrothermal Parameters. *ACS Central Science* 10(3), 729–743 (2024). "
        "[doi:10.1021/acscentsci.3c01615](https://doi.org/10.1021/acscentsci.3c01615). Dataset released under the "
        "MIT licence.")
