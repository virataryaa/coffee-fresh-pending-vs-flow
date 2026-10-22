"""Data loading, the study maths (fresh pending, lead-lag, conversion, nowcast) and shared chart helpers."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "Database"

NAVY, TEAL, GREEN, RED, AMBER, GREY = "#1f3b73", "#2a8c8c", "#2e8b57", "#b0413e", "#c9973f", "#8a94a6"
AXIS, GRID = "#5a6688", "rgba(15,23,42,0.07)"
PAL = [NAVY, TEAL, AMBER, GREEN, RED, "#6b7fb8", "#8fc7d0", "#e2c38a", "#9fd1bb", "#b9c3de", "#d9a3a3", "#4a5578"]
YEAR_PAL = ["#c9d2e6", "#9fb0d4", "#6b7fb8", "#3a5596", NAVY, "#0a2463"]

# market -> grading ports, flow labels. Belgium flows feed Antwerp; US flows feed the US ports.
MARKETS = {
    "Belgium": dict(ports=["Antwerp"], where="Antwerp", dest="Belgium", imports="Belgian imports"),
    "US": dict(ports=["Houston", "Miami", "New Orleans", "New York", "Virginia"], where="US ports", dest="the US", imports="US imports"),
}
STUDY_START = pd.Timestamp("2023-08-01")   # report series starts 18-Jul-2023, so July has no first difference
LOT_BAGS = 37500 / 132.276             # ICE KC lot = 37,500 lb = 283.5 bags of 60 kg
MAX_LAG, AUTO_MAX_LAG, MIN_OBS = 6, 3, 18
LEAD_TOLERANCE, MIN_R = 0.05, 0.30          # prefer a lead when nearly as good; nowcast only fits with r >= MIN_R


def market() -> str:
    return st.session_state.get("market", "Belgium")


def sources(mk: str) -> list:
    return ["Origin exports", MARKETS[mk]["imports"], "Cecafe Arabica"]


# ── load ──────────────────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def grading() -> pd.DataFrame:
    return pd.read_parquet(DB / "grading_daily.parquet")


@st.cache_data(ttl=600)
def flows() -> pd.DataFrame:
    return pd.read_parquet(DB / "flows_monthly.parquet")


@st.cache_data(ttl=600)
def manifest() -> dict:
    return json.loads((DB / "manifest.json").read_text())


def unit_factor() -> float:
    return 1 / LOT_BAGS if st.session_state.get("unit", "Bags") == "Lots" else 1.0


def unit_name() -> str:
    return st.session_state.get("unit", "Bags").lower()


# ── fresh pending ─────────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def port_daily(mk: str) -> pd.DataFrame:
    g = grading()
    return g[g["Port"].isin(MARKETS[mk]["ports"]) & (g["Date"] >= STUDY_START)]


@st.cache_data(ttl=600)
def fp_monthly(mk: str) -> pd.DataFrame:
    """Month x Origin fresh pending (bags), every month from STUDY_START, the current month included (month to date)."""
    d = port_daily(mk)
    m = d.groupby([d["Date"].dt.to_period("M").dt.to_timestamp(), "Origin"])["FreshPending"].sum().unstack().fillna(0.0)
    return m.reindex(pd.date_range(STUDY_START, m.index.max(), freq="MS"), fill_value=0.0)


def last_full_month(mk: str = "Belgium") -> pd.Timestamp:
    """Last month whose report days are complete: the latest report month counts only if the next month has started."""
    last = grading()["Date"].max()
    nxt = last + pd.offsets.BDay(1)
    cur = last.to_period("M").to_timestamp()
    return cur if nxt.month != last.month else cur - pd.DateOffset(months=1)


@st.cache_data(ttl=600)
def coverage() -> pd.Series:
    """Report days found per month / business days in the month (missing ICE files lose that day's Passed + Failed)."""
    d = port_daily("Belgium")
    days = d.groupby(d["Date"].dt.to_period("M").dt.to_timestamp())["Date"].nunique()
    bdays = pd.Series({m: len(pd.bdate_range(m, m + pd.offsets.MonthEnd(0))) for m in days.index})
    return (days / bdays).clip(upper=1.0)


def study_origins(mk: str, min_share: float = 0.01) -> list:
    """Origins graded in the market, by fresh pending since STUDY_START, dropping the ones below min_share."""
    t = fp_monthly(mk).sum().sort_values(ascending=False)
    t = t[t > 0]
    return list(t[t / t.sum() >= min_share].index)


# ── flows ─────────────────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def flow(origin: str, source: str, mk: str) -> pd.Series:
    """Monthly bags. A month the reporter delivered but the origin is absent from means zero; months after the reporter's
    latest delivery are missing (NaN), not zero."""
    f = flows()
    f = f[f["Market"].isin([mk, "All"])]
    s = f[(f["Origin"] == origin) & (f["Source"] == source)].set_index("Month")["Bags"].sort_index()
    if s.empty:
        return s
    rep = f[f["Source"] == source]
    if source.endswith("imports"):
        last = rep["Month"].max()
    else:                                     # exports: each origin reports on its own schedule
        last = s.index.max()
    idx = pd.date_range(min(s.index.min(), pd.Timestamp("2019-01-01")), last, freq="MS")
    return s.reindex(idx, fill_value=0.0)


def sources_for(origin: str, mk: str) -> list:
    f = flows()
    have = set(f.loc[(f["Origin"] == origin) & (f["Market"] == mk), "Source"])
    return [s for s in sources(mk) if s in have]


# ── lead-lag ──────────────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def fits() -> pd.DataFrame:
    """Lead-lag table for every origin x source at the study port, written by Code/build_db.py (empty if missing)."""
    p = DB / "fits.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame(columns=["Market", "Origin", "Source", "lag", "r", "n", "conv"])


def lag_corr(origin: str, source: str, mk: str) -> pd.DataFrame:
    """Lead-lag table: precomputed by the build when available, else calculated."""
    f = fits()
    if "Market" in f:
        sel = f[(f["Market"] == mk) & (f["Origin"] == origin) & (f["Source"] == source)]
        if not sel.empty:
            return sel[["lag", "r", "n", "conv"]].reset_index(drop=True)
    return calc_lag_corr(origin, source, mk)


def calc_lag_corr(origin: str, source: str, mk: str, max_lag: int = MAX_LAG) -> pd.DataFrame:
    """Correlation of fresh pending(t) with flow(t - lag) over complete months both sides have. Lag in months."""
    fp = fp_monthly(mk).get(origin)
    x = flow(origin, source, mk)
    rows = []
    if fp is None or x.empty:
        return pd.DataFrame(columns=["lag", "r", "n", "conv"])
    fp = fp[fp.index <= last_full_month()]
    for k in range(0, max_lag + 1):
        xs = x.shift(k, freq="MS").reindex(fp.index)
        ok = xs.notna()
        n = int(ok.sum())
        a, b = fp[ok].to_numpy(float), xs[ok].to_numpy(float)
        r = float(np.corrcoef(a, b)[0, 1]) if n >= 3 and a.std() > 0 and b.std() > 0 else np.nan
        conv = fp[ok].sum() / xs[ok].sum() if xs[ok].sum() > 0 else np.nan
        rows.append(dict(lag=k, r=r, n=n, conv=conv))
    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def best_fit(origin: str, mk: str) -> dict:
    """The source and lag (0..AUTO_MAX_LAG months) with the highest correlation, needing MIN_OBS overlapping months.
    Lags are capped short on purpose: both series are seasonal, so long lags find spurious season-to-season matches.
    A fit with a lead of 1+ months wins if its r is within LEAD_TOLERANCE of the best: only a lead gives a view ahead."""
    cands = []
    for s in sources_for(origin, mk):
        lc = lag_corr(origin, s, mk)
        lc = lc[(lc["lag"] <= AUTO_MAX_LAG) & (lc["n"] >= MIN_OBS)].dropna(subset=["r"])
        cands += [dict(source=s, lag=int(r["lag"]), r=float(r["r"]), n=int(r["n"]), conv=float(r["conv"])) for _, r in lc.iterrows()]
    if not cands:
        return {}
    top = max(cands, key=lambda d: d["r"])
    lead = [d for d in cands if d["lag"] >= 1 and d["r"] >= top["r"] - LEAD_TOLERANCE]
    return max(lead, key=lambda d: d["r"]) if lead else top


def fitted(origin: str, source: str, lag: int, mk: str) -> pd.Series:
    """Fresh pending implied by the flow: conversion x flow(t - lag), on every month the lagged flow exists (incl. ahead of today)."""
    lc = lag_corr(origin, source, mk)
    conv = lc.loc[lc["lag"] == lag, "conv"]
    if conv.empty or pd.isna(conv.iloc[0]):
        return pd.Series(dtype=float)
    return flow(origin, source, mk).shift(lag, freq="MS") * float(conv.iloc[0])


FILL_METHODS = ["Off", "Seasonal", "Last month", "3m average"]
FILL_DESC = {"Off": "leave blank", "Seasonal": "same month last year x this year's pace vs last year (last 3 months)",
             "Last month": "repeat the latest month", "3m average": "average of the latest 3 months"}


def fill_method() -> str:
    """Fill choice shared by every page (kept outside widget state so it survives page switches)."""
    return st.session_state.get("fill_m", "Seasonal")


def fill_picker(key: str) -> str:
    m = st.radio("Missing flow months", FILL_METHODS, index=FILL_METHODS.index(fill_method()), horizontal=True, key=key,
                 help="How to fill flow months that are not published yet, so every month gets an estimate")
    st.session_state["fill_m"] = m
    return m


def fill_flow(x: pd.Series, until: pd.Timestamp, method: str):
    """Extend a monthly flow past its last published month up to `until`. Returns (series, set of filled months)."""
    x = x.dropna()
    if method == "Off" or x.empty or x.index.max() >= until:
        return x, set()
    new = pd.date_range(x.index.max() + pd.DateOffset(months=1), until, freq="MS")
    last3 = x.iloc[-3:]
    if method == "Last month":
        vals = [float(x.iloc[-1])] * len(new)
    elif method == "3m average":
        vals = [float(last3.mean())] * len(new)
    else:                                    # Seasonal: last year's same month x this year's recent pace
        prev = x.reindex(last3.index - pd.DateOffset(years=1))
        pace = float(last3.sum() / prev.sum()) if prev.notna().all() and prev.sum() > 0 else 1.0
        pace = min(max(pace, 0.5), 2.0)
        vals = [float(x.get(m - pd.DateOffset(years=1), last3.mean())) * pace for m in new]
    return pd.concat([x, pd.Series(vals, index=new)]), set(new)


@st.cache_data(ttl=600)
def certs_share(mk: str) -> pd.Series:
    """Each origin's share of certified stock at the market's ports on the latest report day."""
    d = port_daily(mk)
    last = d[d["Date"] == d["Date"].max()].groupby("Origin")["Certs"].sum()
    return (last / last.sum()).sort_values(ascending=False) if last.sum() > 0 else last


@st.cache_data(ttl=600)
def nowcast_table(mk: str, method: str = "Off") -> pd.DataFrame:
    """Per origin: the auto fit and its fresh pending estimate for the current and next months. Months whose lagged flow is
    not published are filled with `method` (see fill_flow); `filled` lists those months."""
    cur = grading()["Date"].max().to_period("M").to_timestamp()
    months = [cur + pd.DateOffset(months=i) for i in range(0, AUTO_MAX_LAG + 1)]
    fpm = fp_monthly(mk)
    share = certs_share(mk)
    rows = []
    for o in study_origins(mk):
        b = best_fit(o, mk)
        if not b or b["r"] < MIN_R:
            continue
        x, filled = fill_flow(flow(o, b["source"], mk), months[-1] - pd.DateOffset(months=b["lag"]), method)
        fit = x.shift(b["lag"], freq="MS") * b["conv"]
        row = dict(Origin=o, Source=b["source"], Lag=b["lag"], r=b["r"], Conv=b["conv"], n=b["n"], Share=float(share.get(o, 0.0)),
                   LastFlow=flow(o, b["source"], mk).dropna().index.max(),
                   MTD=float(fpm.loc[cur, o]) if o in fpm and cur in fpm.index else 0.0,
                   filled={m + pd.DateOffset(months=b["lag"]) for m in filled})
        for m in months:
            row[m] = float(fit.get(m, np.nan))
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.sort_values("Share", ascending=False).reset_index(drop=True) if not out.empty else out


# ── format / charts ───────────────────────────────────────────────────────────────────────────────────────
def fnum(v, dec=0, sign=False):
    if v is None or pd.isna(v):
        return "–"
    return f"{v:+,.{dec}f}" if sign else f"{v:,.{dec}f}"


def kfmt(v):
    """Bags as 12.3k; lots as plain numbers."""
    if v is None or pd.isna(v):
        return "–"
    if unit_name() == "lots":
        return f"{v:,.0f}"
    return f"{v / 1000:,.1f}k" if abs(v) >= 1000 else f"{v:,.0f}"


def style(fig, height=320, legend=True, fmt=",.0f", y2=None, **kw):
    fig.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#1d1d1f", size=11, family="Inter, -apple-system, Segoe UI, sans-serif"),
                      margin=dict(t=8, b=28, l=8, r=8), hovermode="x unified", bargap=0.3, showlegend=legend,
                      legend=dict(orientation="h", x=0, y=1.02, yanchor="bottom", bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                      xaxis=dict(color=AXIS, showgrid=False, tickfont=dict(size=10)),
                      yaxis=dict(gridcolor=GRID, color=AXIS, hoverformat=fmt, zeroline=True, zerolinecolor="rgba(15,23,42,0.18)", tickfont=dict(size=10)))
    if y2:
        fig.update_layout(yaxis2={**dict(overlaying="y", side="right", showgrid=False, color=AXIS, tickfont=dict(size=10), hoverformat=fmt), **y2})
    if kw:
        fig.update_layout(**kw)
    return fig


def show(fig, key):
    st.plotly_chart(fig, use_container_width=True, key=key, config={"displayModeBar": False})


def head(title, desc=""):
    st.markdown(f"<div class='chart-head'>{title}</div>" + (f"<div class='card-desc'>{desc}</div>" if desc else ""), unsafe_allow_html=True)


def subtabs(options, key):
    """Sub-tab switch drawn as pills. Unlike st.tabs only the picked tab's code runs."""
    return st.radio("View", options, horizontal=True, key=key, label_visibility="collapsed")


def group(title, sub=""):
    """Section header that groups the cards below it."""
    st.markdown(f"<div class='grp'><span>{title}</span>" + (f"<em>{sub}</em>" if sub else "") + "</div>", unsafe_allow_html=True)


def page_title(title, sub=""):
    st.markdown(f"<div class='page-title'>{title}</div>" + (f"<div class='card-desc'>{sub}</div>" if sub else ""), unsafe_allow_html=True)


def table(header, rows, corner="", cls=""):
    """header: list of str; rows: list of (label, [cells], row_class); a cell is str or (str, class)."""
    th = f"<th class='l'>{corner}</th>" + "".join(f"<th>{h}</th>" for h in header)
    body = ""
    for lbl, cells, rc in rows:
        tds = "".join(f"<td class='{c[1]}'>{c[0]}</td>" if isinstance(c, tuple) else f"<td>{c}</td>" for c in cells)
        body += f"<tr class='{rc}'><td class='lbl'>{lbl}</td>{tds}</tr>"
    st.markdown(f"<div class='tw'><table class='st {cls}'><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>", unsafe_allow_html=True)


def mlabel(m) -> str:
    return pd.Timestamp(m).strftime("%b-%y")
