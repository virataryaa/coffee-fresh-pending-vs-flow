"""Brazil: Cecafe Arabica to the market's destination (timely, Arabica-only, history from 2007). Actual vs same-month normal, crop-year view, share."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c

CY_START = 7          # Brazil crop year Jul-Jun, as in the Cecafe apps
CY_MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]
D = " &nbsp;·&nbsp; "


def _same_month(s: pd.Series, m: pd.Timestamp, years: int) -> pd.Series:
    """The same calendar month in each of the previous `years` years."""
    return s.reindex([m - pd.DateOffset(years=k) for k in range(1, years + 1)]).dropna()


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
    yrs = st.radio("Normal = average of the same month over the last", [3, 5, 10], index=1, horizontal=True, key="br_norm",
                   format_func=lambda n: f"{n} years")

    # ── 1. history: each month vs its own same-month normal ──────────────────────────────────────────────
    with st.container(border=True):
        c.head("Actual vs normal", f"<b>Bars</b> exports to {dest}, green above / red below normal{D}<b>Navy</b> same-month {yrs}y normal"
                                   f"{D}<b>Orange</b> Brazil fresh pending a month later")
        lm = bel.index.max()
        win = bel[bel.index >= lm - pd.DateOffset(months=47)]
        nm = pd.Series({m: _same_month(bel, m, yrs).mean() for m in win.index})
        fps = fp.shift(-1, freq="MS")
        fig = go.Figure()
        fig.add_bar(x=win.index, y=win * u, name="Actual", marker_color=["rgba(46,139,87,.45)" if a >= n else "rgba(176,65,62,.40)" for a, n in zip(win, nm)],
                    marker_line_width=0)
        fig.add_scatter(x=nm.index, y=nm * u, name=f"{yrs}y normal", mode="lines", line=dict(color=c.NAVY, width=2, dash="dash"))
        fig.add_scatter(x=fps.index, y=fps * u, name="Fresh pending (next month)", mode="lines+markers",
                        line=dict(color="#e07b00", width=3), marker=dict(size=6, color="#e07b00"))
        c.style(fig, height=350, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M3", tickformat="%b-%y"))
        c.show(fig, "br_actual")

    # ── 2. this crop year by month vs the same-month normal and range ────────────────────────────────────
    cy = lambda m: m.year if m.month >= CY_START else m.year - 1          # noqa: E731
    cur_cy = cy(bel.index.max())
    l, r = st.columns([1.6, 1], gap="medium")
    with l, st.container(border=True):
        c.head(f"Crop year {cur_cy % 100:02d}/{(cur_cy + 1) % 100:02d} vs same-month normal",
               f"<b>Bars</b> this crop year{D}<b>Navy</b> {yrs}y normal{D}<b>Band</b> {yrs}y low-high{D}<b>Grey</b> last crop year")
        months = [pd.Timestamp(cur_cy + (1 if k >= 12 - CY_START + 1 else 0), (CY_START + k - 1) % 12 + 1, 1) for k in range(12)]
        this = [bel.get(m, float("nan")) for m in months]
        last = [bel.get(m - pd.DateOffset(years=1), float("nan")) for m in months]
        hist = [_same_month(bel, m, yrs) for m in months]
        avg, lo, hi = [h.mean() for h in hist], [h.min() for h in hist], [h.max() for h in hist]
        fig = go.Figure()
        fig.add_scatter(x=CY_MONTHS, y=[v * u for v in hi], mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=CY_MONTHS, y=[v * u for v in lo], mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(31,59,115,.10)",
                        name=f"{yrs}y range", hovertemplate="low %{y:,.0f}<extra></extra>")
        fig.add_bar(x=CY_MONTHS, y=[v * u for v in this], name="This crop year",
                    marker_color=[c.GREEN if pd.notna(t) and t >= a else c.RED for t, a in zip(this, avg)], marker_line_width=0, opacity=.85)
        fig.add_scatter(x=CY_MONTHS, y=[v * u for v in avg], name=f"{yrs}y normal", mode="lines+markers", line=dict(color=c.NAVY, width=2.4), marker=dict(size=5))
        fig.add_scatter(x=CY_MONTHS, y=[v * u for v in last], name="Last crop year", mode="lines", line=dict(color=c.GREY, width=1.6, dash="dot"))
        c.style(fig, height=330, xaxis=dict(color=c.AXIS, showgrid=False, categoryorder="array", categoryarray=CY_MONTHS))
        c.show(fig, "br_cy")
    with r, st.container(border=True):
        c.head("vs normal, last 6 months", f"Same-month {yrs}y average{D}Lot = 283.5 bags")
        rows = []
        for m in bel.index[-6:][::-1]:
            n = _same_month(bel, m, yrs).mean()
            ex = bel[m] - n
            cls = "up" if ex >= 0 else "dn"
            rows.append((c.mlabel(m), [c.kfmt(bel[m] * u), c.kfmt(n * u), (c.kfmt(ex * u), cls), (f"{ex / c.LOT_BAGS:+,.0f}", cls)], ""))
        c.table(["Actual", "Normal", "Diff", "Lots"], rows, corner="Month")

    with st.container(border=True):
        c.head(f"Share of Brazil Arabica going to {dest}", f"<b>Light</b> monthly{D}<b>Dark</b> 12-month average")
        s = share[share.index >= pd.Timestamp("2016-07-01")]
        fig = go.Figure()
        fig.add_scatter(x=s.index, y=s * 100, name="Monthly", mode="lines", line=dict(color="#b9c3de", width=1.4))
        fig.add_scatter(x=s.index, y=s.rolling(12).mean() * 100, name="12m avg", mode="lines", line=dict(color=c.NAVY, width=2.4))
        c.style(fig, height=290, fmt=".1f", yaxis=dict(ticksuffix="%", gridcolor=c.GRID, color=c.AXIS, tickfont=dict(size=10)))
        c.show(fig, "br_share")
