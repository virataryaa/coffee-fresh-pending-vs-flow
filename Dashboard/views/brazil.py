"""Brazil: Cecafe Arabica to the market's destination (timely, Arabica-only, history from 2007). Excess vs normal, share, crop-year pace."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c

CY_START = 7          # Brazil crop year Jul-Jun, as in the Cecafe apps
MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]


def _normal(s: pd.Series, m: pd.Timestamp, years=5) -> float:
    v = s.reindex([m - pd.DateOffset(years=k) for k in range(1, years + 1)]).dropna()
    return float(v.mean()) if len(v) else float("nan")


def render():
    mk = c.market()
    M = c.MARKETS[mk]
    u = c.unit_factor()
    dest = M["dest"]
    c.page_title(f"Brazil · Cecafe Arabica to {dest}")
    bel = c.flow("Brazil", "Cecafe Arabica", mk)
    allb = c.flow("Brazil", "Cecafe Arabica (all destinations)", mk)
    if bel.empty:
        st.info("No Cecafe data.")
        return
    share = (bel / allb).dropna()
    cy = lambda m: m.year if m.month >= CY_START else m.year - 1          # noqa: E731
    pos = lambda m: (m.month - CY_START) % 12                             # noqa: E731
    cyid = pd.Series([cy(m) for m in bel.index], index=bel.index)
    cur_cy = cy(bel.index.max())
    fp = c.fp_monthly(mk).get("Brazil", pd.Series(dtype=float))

    with st.container(border=True):
        c.head("Actual vs normal", f"Green / red: above / below 5y normal. Dotted: Brazil fresh pending at {M['where']}, shifted back 1m.")
        lm = bel.index.max()
        win = bel[bel.index >= lm - pd.DateOffset(months=47)]
        nm = pd.Series({m: _normal(bel, m) for m in win.index})
        fps = fp.shift(-1, freq="MS")
        fig = go.Figure()
        fig.add_bar(x=win.index, y=win * u, name="Actual", marker_color=[c.GREEN if a >= n else c.RED for a, n in zip(win, nm)],
                    marker_opacity=.85, marker_line_width=0)
        fig.add_scatter(x=nm.index, y=nm * u, name="5y normal", mode="lines", line=dict(color=c.NAVY, width=2))
        fig.add_scatter(x=fps.index, y=fps * u, name="Fresh pending", mode="lines+markers", line=dict(color=c.AMBER, width=2, dash="dot"), marker=dict(size=4))
        c.style(fig, height=350, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M3", tickformat="%b-%y"))
        c.show(fig, "br_actual")

    l, r = st.columns(2, gap="medium")
    with l, st.container(border=True):
        c.head(f"Share of Brazil Arabica going to {dest}", "Monthly and 12m average.")
        s = share[share.index >= pd.Timestamp("2016-07-01")]
        fig = go.Figure()
        fig.add_scatter(x=s.index, y=s * 100, name="Monthly", mode="lines", line=dict(color="#b9c3de", width=1.4))
        fig.add_scatter(x=s.index, y=s.rolling(12).mean() * 100, name="12m avg", mode="lines", line=dict(color=c.NAVY, width=2.4))
        c.style(fig, height=310, fmt=".1f", yaxis=dict(ticksuffix="%", gridcolor=c.GRID, color=c.AXIS, tickfont=dict(size=10)))
        c.show(fig, "br_share")
    with r, st.container(border=True):
        c.head("Crop-year pace", "Cumulative from July.")
        fig = go.Figure()
        for i, y in enumerate(sorted(cyid.unique())[-6:]):
            sy = bel[cyid == y]
            fig.add_scatter(x=[MONTHS[pos(m)] for m in sy.index], y=sy.cumsum() * u, name=f"{y % 100:02d}/{(y + 1) % 100:02d}", mode="lines+markers",
                            line=dict(color=c.YEAR_PAL[i], width=2.8 if y == cur_cy else 1.6), marker=dict(size=4))
        c.style(fig, height=310, xaxis=dict(color=c.AXIS, showgrid=False, categoryorder="array", categoryarray=MONTHS))
        c.show(fig, "br_pace")

    with st.container(border=True):
        c.head("Excess vs normal, last 12 months", "Normal = 5y same-month average. Lot = 283.5 bags.")
        rows = []
        for m in bel.index[-12:][::-1]:
            n = _normal(bel, m)
            ex = bel[m] - n
            cls = "up" if ex >= 0 else "dn"
            nxt = m + pd.DateOffset(months=1)
            rows.append((c.mlabel(m), [c.kfmt(bel[m] * u), c.kfmt(n * u), (c.kfmt(ex * u), cls), (f"{ex / c.LOT_BAGS:+,.0f}", cls),
                                       (f"{bel[m] / n - 1:+.0%}" if n else "–", cls), f"{share.get(m, float('nan')):.1%}",
                                       c.kfmt(fp.get(nxt, float('nan')) * u) if nxt in fp.index else "–"], ""))
        c.table(["Actual", "Normal", "Excess", "Lots", "vs Normal", "Share", "FP next month"], rows, corner="Month")
