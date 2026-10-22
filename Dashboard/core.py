"""Data loading, the study maths (fresh pending, lead-lag, conversion, nowcast) and shared chart helpers."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "Database"

NAVY, TEAL, GREEN, RED, AMBER, GREY = "#1f3b73", "#2a8c8c", "#2e8b57", "#b0413e", "#c9973f", "#8a94a6"
AXIS, GRID = "#5a6688", "rgba(15,23,42,0.07)"
PAL = [NAVY, TEAL, AMBER, GREEN, RED, "#6b7fb8", "#8fc7d0", "#e2c38a", "#9fd1bb", "#b9c3de", "#d9a3a3", "#4a5578"]
YEAR_PAL = ["#c9d2e6", "#9fb0d4", "#6b7fb8", "#3a5596", NAVY, "#0a2463"]

PORT = "Antwerp"                       # Belgium flows -> Antwerp grading
STUDY_START = pd.Timestamp("2023-08-01")   # report series starts 18-Jul-2023, so July has no first difference
LOT_BAGS = 37500 / 132.276             # ICE KC lot = 37,500 lb = 283.5 bags of 60 kg
MAX_LAG, AUTO_MAX_LAG, MIN_OBS = 6, 3, 18
LEAD_TOLERANCE, MIN_R = 0.05, 0.30          # prefer a lead when nearly as good; nowcast only fits with r >= MIN_R
SOURCES = ["Origin exports", "Belgian imports", "Cecafe Arabica"]
SOURCE_DESC = {"Origin exports": "TDM, origin customs: green coffee (HS 0901.11) exported to Belgium",
               "Belgian imports": "TDM, Belgian customs: green coffee (HS 0901.11) imported from the origin",
               "Cecafe Arabica": "Cecafe: Brazil Arabica exports to Belgium (Brazil only, Arabica only)"}


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
def port_daily(port: str = PORT) -> pd.DataFrame:
    g = grading()
    return g[(g["Port"] == port) & (g["Date"] >= STUDY_START)]


@st.cache_data(ttl=600)
def fp_monthly(port: str = PORT) -> pd.DataFrame:
    """Month x Origin fresh pending (bags), every month from STUDY_START, the current month included (month to date)."""
    d = port_daily(port)
    m = d.groupby([d["Date"].dt.to_period("M").dt.to_timestamp(), "Origin"])["FreshPending"].sum().unstack().fillna(0.0)
    return m.reindex(pd.date_range(STUDY_START, m.index.max(), freq="MS"), fill_value=0.0)


def last_full_month(port: str = PORT) -> pd.Timestamp:
    """Last month whose report days are complete: the latest report month counts only if the next month has started."""
    last = port_daily(port)["Date"].max()
    nxt = last + pd.offsets.BDay(1)
    cur = last.to_period("M").to_timestamp()
    return cur if nxt.month != last.month else cur - pd.DateOffset(months=1)


@st.cache_data(ttl=600)
def coverage(port: str = PORT) -> pd.Series:
    """Report days found per month / business days in the month (missing ICE files lose that day's Passed + Failed)."""
    d = port_daily(port)
    days = d.groupby(d["Date"].dt.to_period("M").dt.to_timestamp())["Date"].nunique()
    bdays = pd.Series({m: len(pd.bdate_range(m, m + pd.offsets.MonthEnd(0))) for m in days.index})
    return (days / bdays).clip(upper=1.0)


def study_origins(port: str = PORT, min_share: float = 0.005) -> list:
    """Origins graded at the port, by fresh pending since STUDY_START, dropping the ones below min_share."""
    t = fp_monthly(port).sum().sort_values(ascending=False)
    t = t[t > 0]
    return list(t[t / t.sum() >= min_share].index)


# ── flows ─────────────────────────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def flow(origin: str, source: str) -> pd.Series:
    """Monthly bags. A month the reporter delivered but the origin is absent from means zero; months after the reporter's
    latest delivery are missing (NaN), not zero."""
    f = flows()
    s = f[(f["Origin"] == origin) & (f["Source"] == source)].set_index("Month")["Bags"].sort_index()
    if s.empty:
        return s
    rep = f[f["Source"] == source]
    if source == "Belgian imports":
        last = rep["Month"].max()
    else:                                     # exports: each origin reports on its own schedule
        last = s.index.max()
    idx = pd.date_range(min(s.index.min(), pd.Timestamp("2019-01-01")), last, freq="MS")
    return s.reindex(idx, fill_value=0.0)


def sources_for(origin: str) -> list:
    f = flows()
    have = set(f.loc[f["Origin"] == origin, "Source"])
    return [s for s in SOURCES if s in have]


# ── lead-lag ──────────────────────────────────────────────────────────────────────────────────────────────
def lag_corr(origin: str, source: str, port: str = PORT, max_lag: int = MAX_LAG) -> pd.DataFrame:
    """Correlation of fresh pending(t) with flow(t - lag) over complete months both sides have. Lag in months."""
    fp = fp_monthly(port).get(origin)
    x = flow(origin, source)
    rows = []
    if fp is None or x.empty:
        return pd.DataFrame(columns=["lag", "r", "n", "conv"])
    fp = fp[fp.index <= last_full_month(port)]
    for k in range(0, max_lag + 1):
        xs = x.shift(k, freq="MS").reindex(fp.index)
        ok = xs.notna()
        n = int(ok.sum())
        r = fp[ok].corr(xs[ok]) if n >= 3 and xs[ok].std() > 0 and fp[ok].std() > 0 else np.nan
        conv = fp[ok].sum() / xs[ok].sum() if xs[ok].sum() > 0 else np.nan
        rows.append(dict(lag=k, r=r, n=n, conv=conv))
    return pd.DataFrame(rows)


@st.cache_data(ttl=600)
def best_fit(origin: str, port: str = PORT) -> dict:
    """The source and lag (0..AUTO_MAX_LAG months) with the highest correlation, needing MIN_OBS overlapping months.
    Lags are capped short on purpose: both series are seasonal, so long lags find spurious season-to-season matches.
    A fit with a lead of 1+ months wins if its r is within LEAD_TOLERANCE of the best: only a lead gives a view ahead."""
    cands = []
    for s in sources_for(origin):
        lc = lag_corr(origin, s, port)
        lc = lc[(lc["lag"] <= AUTO_MAX_LAG) & (lc["n"] >= MIN_OBS)].dropna(subset=["r"])
        cands += [dict(source=s, lag=int(r["lag"]), r=float(r["r"]), n=int(r["n"]), conv=float(r["conv"])) for _, r in lc.iterrows()]
    if not cands:
        return {}
    top = max(cands, key=lambda d: d["r"])
    lead = [d for d in cands if d["lag"] >= 1 and d["r"] >= top["r"] - LEAD_TOLERANCE]
    return max(lead, key=lambda d: d["r"]) if lead else top


def fitted(origin: str, source: str, lag: int, port: str = PORT) -> pd.Series:
    """Fresh pending implied by the flow: conversion x flow(t - lag), on every month the lagged flow exists (incl. ahead of today)."""
    lc = lag_corr(origin, source, port)
    conv = lc.loc[lc["lag"] == lag, "conv"]
    if conv.empty or pd.isna(conv.iloc[0]):
        return pd.Series(dtype=float)
    return flow(origin, source).shift(lag, freq="MS") * float(conv.iloc[0])


@st.cache_data(ttl=600)
def nowcast_table(port: str = PORT) -> pd.DataFrame:
    """Per origin: the auto fit and its fresh pending estimate for the current and next months, where the lagged flow is already out."""
    cur = port_daily(port)["Date"].max().to_period("M").to_timestamp()
    months = [cur + pd.DateOffset(months=i) for i in range(0, AUTO_MAX_LAG + 1)]
    fpm = fp_monthly(port)
    rows = []
    for o in study_origins(port):
        b = best_fit(o, port)
        if not b or b["r"] < MIN_R:
            continue
        fit = fitted(o, b["source"], b["lag"], port)
        row = dict(Origin=o, Source=b["source"], Lag=b["lag"], r=b["r"], Conv=b["conv"], n=b["n"],
                   MTD=float(fpm.loc[cur, o]) if o in fpm and cur in fpm.index else 0.0)
        for m in months:
            row[m] = float(fit.get(m, np.nan))
        rows.append(row)
    return pd.DataFrame(rows)


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


def page_title(title, sub=""):
    st.markdown(f"<div class='page-title'>{title}</div>" + (f"<div class='card-desc'>{sub}</div>" if sub else ""), unsafe_allow_html=True)


def kpis(items):
    """items: list of (label, value, sub). Custom HTML cards."""
    html = "".join(f"<div class='kpi'><div class='kl'>{l}</div><div class='kv'>{v}</div><div class='ks'>{s}</div></div>" for l, v, s in items)
    st.markdown(f"<div class='kpis'>{html}</div>", unsafe_allow_html=True)


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
