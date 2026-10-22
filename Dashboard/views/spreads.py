"""Spreads: does the grading pipeline (certs + pending + fresh pending + flow-implied arrivals) explain the KC 1/2 spread?

Spread = Rollex active 1/2 spread (front active minus next, c/lb) from Daily Miner, C1-C2 where Rollex has no print yet.
Spread *changes* skip roll days (active contract switch), so a roll is not read as the market tightening or easing.
Stocks are exchange-wide (all ports): the spread prices the whole deliverable pool, not just Antwerp.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c


@st.cache_data(ttl=600)
def spread() -> pd.DataFrame:
    s = pd.read_parquet(c.DB / "spread_daily.parquet").set_index("Date").sort_index()
    s["spread"] = s["spread_rollex"].fillna(s["spread_c12"])
    lab = s["active_label"].ffill()
    roll = lab.ne(lab.shift()) & lab.shift().notna()
    s["d"] = s["spread"].diff().where(~roll, 0.0)            # roll-adjusted daily change
    s["roll"] = roll
    return s


@st.cache_data(ttl=600)
def pool() -> pd.DataFrame:
    """Daily exchange-wide Certs, Pending, Passed, Failed, FreshPending (bags)."""
    g = c.grading()
    return g[g["Date"] >= c.STUDY_START].groupby("Date")[["Certs", "Pending", "Passed", "Failed", "FreshPending"]].sum()


def _lnfit(x, y):
    ok = (x > 0) & np.isfinite(y)
    if ok.sum() < 5:
        return np.nan, np.nan, np.nan
    b, a = np.polyfit(np.log(x[ok]), y[ok], 1)
    res = y[ok] - (a + b * np.log(x[ok]))
    r2 = 1 - (res ** 2).sum() / ((y[ok] - y[ok].mean()) ** 2).sum()
    return a, b, r2


def render():
    u, un = c.unit_factor(), c.unit_name()
    s, p = spread(), pool()
    last = s.index.max()
    sp_now = s["spread"].iloc[-1]
    c.page_title("Spreads · KC 1/2 vs the grading pipeline",
                 f"Spread {sp_now:.2f} c/lb ({s['active_label'].ffill().iloc[-1]}, {last:%d-%b}). All ports. Changes skip roll days.")

    # ── 1. levels over time ──────────────────────────────────────────────────────────────────────────────
    with st.container(border=True):
        c.head("Spread vs certs + pending", "<b>Blue</b> certs &nbsp;·&nbsp; <b>Gold</b> pending &nbsp;·&nbsp; <b>Red</b> 1/2 spread &nbsp;·&nbsp; <b>Ticks</b> rolls")
        ss = s[s.index >= c.STUDY_START]
        fig = go.Figure()
        fig.add_scatter(x=p.index, y=p["Certs"] * u, name="Certs", stackgroup="a", mode="none", fillcolor="rgba(31,59,115,.55)")
        fig.add_scatter(x=p.index, y=p["Pending"] * u, name="Pending", stackgroup="a", mode="none", fillcolor="rgba(201,151,63,.55)")
        fig.add_scatter(x=ss.index, y=ss["spread"], name="1/2 spread", yaxis="y2", mode="lines", line=dict(color=c.RED, width=1.8))
        r = ss[ss["roll"]]
        fig.add_scatter(x=r.index, y=r["spread"], name="roll", yaxis="y2", mode="markers", marker=dict(symbol="line-ns-open", size=10, color=c.GREY))
        c.style(fig, height=360, y2=dict(title="c/lb", hoverformat=".2f"), xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "sp_levels")

    # ── 2. does pending add to certs? ────────────────────────────────────────────────────────────────────
    sm = s["spread"].groupby(s.index.to_period("M").to_timestamp()).mean()
    pe = p.groupby(p.index.to_period("M").to_timestamp()).last()
    m = pd.concat([sm.rename("spread"), pe["Certs"], pe["Pending"]], axis=1).dropna()
    m["Pool"] = m["Certs"] + m["Pending"]
    l, rr = st.columns(2, gap="medium")
    fits = {}
    with l, st.container(border=True):
        c.head("Spread vs stock: certs vs certs + pending", "Each dot is a month &nbsp;·&nbsp; higher R² = stock explains the spread better &nbsp;·&nbsp; <b>Ring</b> latest")
        fig = go.Figure()
        for col, name, colr in [("Certs", "Certs", c.NAVY), ("Pool", "Certs + pending", c.AMBER)]:
            a, b, r2 = _lnfit(m[col].values / 1000, m["spread"].values)
            fits[col] = (a, b, r2)
            fig.add_scatter(x=m[col] * u, y=m["spread"], mode="markers", name=f"{name} (R² {r2:.2f})", marker=dict(size=7, color=colr, opacity=.7),
                            text=[c.mlabel(i) for i in m.index], hovertemplate="%{text}: %{x:,.0f} | %{y:.2f} c/lb<extra></extra>")
            xs = np.linspace(m[col].min(), m[col].max(), 50)
            fig.add_scatter(x=xs * u, y=a + b * np.log(xs / 1000), mode="lines", line=dict(color=colr, dash="dot"), showlegend=False, hoverinfo="skip")
            fig.add_scatter(x=[m[col].iloc[-1] * u], y=[m["spread"].iloc[-1]], mode="markers", showlegend=False, hoverinfo="skip",
                            marker=dict(size=14, color="rgba(0,0,0,0)", line=dict(color=colr, width=2.2)))
        c.style(fig, height=340, hovermode="closest", fmt=".2f", xaxis=dict(title=f"stock ({un})", color=c.AXIS, gridcolor=c.GRID),
                yaxis=dict(title="c/lb", color=c.AXIS, gridcolor=c.GRID))
        c.show(fig, "sp_fit")

    # ── 3. does fresh pending move the spread? ───────────────────────────────────────────────────────────
    fpm = p["FreshPending"].groupby(p.index.to_period("M").to_timestamp()).sum()
    dm = s["d"].groupby(s.index.to_period("M").to_timestamp()).sum()
    full = c.last_full_month()
    fpm, dmf = fpm[fpm.index <= full], dm
    with rr, st.container(border=True):
        c.head("Fresh pending vs next spread move", "Negative r = more coffee into grading, then the spread eases")
        rows = []
        for k in range(0, 4):
            y = dmf.shift(-k, freq="MS").reindex(fpm.index)
            ok = y.notna()
            rows.append((k, fpm[ok].corr(y[ok]) if ok.sum() > 5 else np.nan, int(ok.sum())))
        lag = st.radio("Months ahead", [0, 1, 2, 3], index=1, horizontal=True, key="sp_k")
        y = dmf.shift(-lag, freq="MS").reindex(fpm.index)
        ok = y.notna()
        fig = go.Figure()
        fig.add_scatter(x=fpm[ok] * u, y=y[ok], mode="markers", marker=dict(size=8, color=c.NAVY, opacity=.75), name="month",
                        text=[c.mlabel(i) for i in fpm[ok].index], hovertemplate="%{text}: FP %{x:,.0f} | Δspread %{y:+.2f}<extra></extra>")
        if ok.sum() > 5:
            b, a = np.polyfit(fpm[ok], y[ok], 1)
            xs = np.array([fpm[ok].min(), fpm[ok].max()])
            fig.add_scatter(x=xs * u, y=a + b * xs, mode="lines", line=dict(color=c.TEAL, dash="dot"), hoverinfo="skip")
        c.style(fig, height=262, legend=False, hovermode="closest", fmt="+.2f", xaxis=dict(title=f"fresh pending ({un})", color=c.AXIS, gridcolor=c.GRID),
                yaxis=dict(title="Δ spread c/lb", color=c.AXIS, gridcolor=c.GRID, zeroline=True, zerolinecolor="rgba(15,23,42,.25)"))
        c.show(fig, "sp_fp")
        st.markdown("<div class='note'>r by months ahead: " + " · ".join(f"<b>{k}m</b> {r:+.2f} (n {n})" for k, r, n in rows) + "</div>",
                    unsafe_allow_html=True)
