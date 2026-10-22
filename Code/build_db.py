"""Build the study database from the three local source projects (no API calls, runs in a few seconds).

Sources (all refreshed by their own automators):
  1. Daily Miner   Database/Main/KC/kc_grading.parquet      ICE daily certified-stock report: Certs, Pending, Passed, Failed by origin and port
  2. TDM Pro       Database/Coffee/tdm_coffee.parquet        origin exports by partner (QTY1 tonnes)
                   Database/Coffee/tdm_coffee_imports.parquet Belgian imports by partner (QTY1 tonnes)
  4. Daily Miner   Database/Main/KC/price_link_kc.parquet    KC c1, c2, 1/2 spread (c/lb) and the Rollex active spread
  3. Cecafe Daily  Database/cecafe_destinations.csv          Brazil monthly exports by destination (K bags, Arabica / Robusta)

Outputs (Database/, committed so Streamlit Cloud can read them):
  grading_daily.parquet   Date, Port, Origin, Certs, Pending, Passed, Failed, FreshPending   (bags)
  flows_monthly.parquet   Market, Month, Origin, Source, Bags   Market Belgium / US (All for Cecafe totals);
                          Source in {Origin exports, Belgian imports / US imports, Cecafe Arabica, Cecafe Robusta, Cecafe ... (all destinations)}
  spread_daily.parquet    Date, c1, c2, spread_c12, spread_rollex, active_label   (c/lb, from 2015)
  manifest.json           build time and the latest date in each source

Fresh pending = change in Pending + Passed + Failed, per origin and port: coffee newly presented for grading that day.
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FUND = ROOT.parents[1] / "Fundamental"
SRC_GRADING = FUND / "Daily Miner" / "Database" / "Main" / "KC" / "kc_grading.parquet"
SRC_TDM = FUND / "TDM Pro" / "Comprehensive TDM" / "Database" / "Coffee"
SRC_CECAFE = FUND / "Cecafe Daily" / "Database" / "cecafe_destinations.csv"
SRC_PRICE = FUND / "Daily Miner" / "Database" / "Main" / "KC" / "price_link_kc.parquet"
OUT = ROOT / "Database"

BAGS_PER_TONNE = 1000 / 60
GREEN_HS = 90111          # green, not decaffeinated (90112 decaf is never graded)
TDM_START = 2019


def build_grading() -> pd.DataFrame:
    g = pd.read_parquet(SRC_GRADING)
    g = g[g["Tag"].isin(["Certs", "Pending", "Passed", "Failed"])]
    w = g.pivot_table(index=["Date", "Port", "Origin"], columns="Tag", values="Bags", aggfunc="sum").reset_index()
    w.columns.name = None
    for c in ["Certs", "Pending", "Passed", "Failed"]:
        if c not in w:
            w[c] = 0.0
    # every report day must carry every port x origin, else a missing row would look like a jump in Pending
    days = sorted(w["Date"].unique())
    keys = w[["Port", "Origin"]].drop_duplicates()
    full = keys.merge(pd.DataFrame({"Date": days}), how="cross")
    w = full.merge(w, on=["Date", "Port", "Origin"], how="left")
    w[["Pending", "Passed", "Failed"]] = w[["Pending", "Passed", "Failed"]].fillna(0.0)
    w = w.sort_values(["Port", "Origin", "Date"])
    w["Certs"] = w.groupby(["Port", "Origin"])["Certs"].ffill().fillna(0.0)
    w["FreshPending"] = w.groupby(["Port", "Origin"])["Pending"].diff() + w["Passed"] + w["Failed"]
    w["Date"] = pd.to_datetime(w["Date"])
    return w[["Date", "Port", "Origin", "Certs", "Pending", "Passed", "Failed", "FreshPending"]].reset_index(drop=True)


def _tdm(df: pd.DataFrame, origin_col: str, source: str) -> pd.DataFrame:
    df = df[(df["COMMODITY"] == GREEN_HS) & (df["YEAR"] >= TDM_START)]
    out = df.groupby([origin_col, "YEAR", "MONTH"], as_index=False)["QTY1"].sum()
    out["Month"] = pd.to_datetime(dict(year=out["YEAR"], month=out["MONTH"], day=1))
    out["Bags"] = out["QTY1"] * BAGS_PER_TONNE
    out["Source"] = source
    return out.rename(columns={origin_col: "Origin"})[["Month", "Origin", "Source", "Bags"]]


# market -> (TDM partner / importer name, Cecafe destination, imports source label)
MARKETS = {"Belgium": ("Belgium", "Belgium", "Belgian imports"), "US": ("United States", "USA", "US imports")}


def build_flows() -> pd.DataFrame:
    cols = ["REPORTER", "PARTNER", "COMMODITY", "YEAR", "MONTH", "QTY1"]
    ex_all = pd.read_parquet(SRC_TDM / "tdm_coffee.parquet", columns=cols)
    im_all = pd.read_parquet(SRC_TDM / "tdm_coffee_imports.parquet", columns=cols)
    cf = pd.read_csv(SRC_CECAFE).dropna(subset=["Bags (K)"])
    cf["Month"] = pd.to_datetime(dict(year=cf["Year"], month=cf["Month"], day=1))
    cf["Bags"] = cf["Bags (K)"] * 1000
    cf["Origin"] = "Brazil"
    out = []
    for mk, (tdm_name, cecafe_name, imp_label) in MARKETS.items():
        ex = _tdm(ex_all[ex_all["PARTNER"] == tdm_name], "REPORTER", "Origin exports")
        im = _tdm(im_all[im_all["REPORTER"] == tdm_name], "PARTNER", imp_label)
        c = cf[cf["Destination"] == cecafe_name].assign(Source="Cecafe " + cf["Type"])
        for part in (ex, im, c[["Month", "Origin", "Source", "Bags"]]):
            out.append(part.assign(Market=mk))
    tot = cf[cf["Destination"] == "Total"]
    out.append(tot.assign(Source="Cecafe " + tot["Type"] + " (all destinations)", Market="All")[["Month", "Origin", "Source", "Bags", "Market"]])
    return pd.concat(out, ignore_index=True)[["Market", "Month", "Origin", "Source", "Bags"]]


def build_spread() -> pd.DataFrame:
    p = pd.read_parquet(SRC_PRICE)
    p = p[p.index >= "2015-01-01"][["c1", "c2", "spread_c12", "spread_rollex", "active_label"]]
    return p.rename_axis("Date").reset_index()


def build_fits() -> pd.DataFrame:
    """Lead-lag tables for every origin x source, using the dashboard's own maths so the app only reads them."""
    import logging
    import sys
    logging.getLogger("streamlit").setLevel(logging.ERROR)
    for name in list(logging.root.manager.loggerDict):
        if name.startswith("streamlit"):
            logging.getLogger(name).setLevel(logging.ERROR)
    sys.path.insert(0, str(ROOT / "Dashboard"))
    import core
    rows = []
    for mk in core.MARKETS:
        for o in core.study_origins(mk):
            for s in core.sources_for(o, mk):
                t = core.calc_lag_corr(o, s, mk)
                t.insert(0, "Source", s)
                t.insert(0, "Origin", o)
                t.insert(0, "Market", mk)
                rows.append(t)
    return pd.concat(rows, ignore_index=True)


def main():
    OUT.mkdir(exist_ok=True)
    g = build_grading()
    f = build_flows()
    g.to_parquet(OUT / "grading_daily.parquet", index=False)
    f.to_parquet(OUT / "flows_monthly.parquet", index=False)
    sp = build_spread()
    sp.to_parquet(OUT / "spread_daily.parquet", index=False)
    last = {f"{m} · {s}" if m != "All" else s: g_["Month"].max().strftime("%Y-%m") for (m, s), g_ in f.groupby(["Market", "Source"])}
    man = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "grading_last": g["Date"].max().strftime("%Y-%m-%d"),
           "grading_first": g["Date"].min().strftime("%Y-%m-%d"), "grading_days": int(g["Date"].nunique()), "flows_last": last,
           "spread_last": sp["Date"].max().strftime("%Y-%m-%d")}
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2))
    fits = build_fits()
    fits.to_parquet(OUT / "fits.parquet", index=False)
    print(f"fits           {len(fits):>7,} rows  ({fits['Origin'].nunique()} origins)")
    print(f"grading_daily  {len(g):>7,} rows  {man['grading_first']} .. {man['grading_last']}  ({man['grading_days']} report days)")
    print(f"spread_daily   {len(sp):>7,} rows  to {man['spread_last']}")
    print(f"flows_monthly  {len(f):>7,} rows  " + ", ".join(f"{k} {v}" for k, v in last.items()))


if __name__ == "__main__":
    main()
