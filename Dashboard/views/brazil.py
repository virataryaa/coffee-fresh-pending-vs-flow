"""Brazil: Cecafe Arabica to the market's destination (timely, Arabica-only, history from 2007). Excess vs normal, share, crop-year pace."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c



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

    with st.container(border=True):
        c.head(f"Share of Brazil Arabica going to {dest}", "Monthly and 12m average.")
        s = share[share.index >= pd.Timestamp("2016-07-01")]
        fig = go.Figure()
        fig.add_scatter(x=s.index, y=s * 100, name="Monthly", mode="lines", line=dict(color="#b9c3de", width=1.4))
        fig.add_scatter(x=s.index, y=s.rolling(12).mean() * 100, name="12m avg", mode="lines", line=dict(color=c.NAVY, width=2.4))
        c.style(fig, height=310, fmt=".1f", yaxis=dict(ticksuffix="%", gridcolor=c.GRID, color=c.AXIS, tickfont=dict(size=10)))
        c.show(fig, "br_share")
