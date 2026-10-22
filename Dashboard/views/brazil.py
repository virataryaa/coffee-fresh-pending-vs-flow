"""Brazil: Cecafe Arabica to Belgium (timely, Arabica-only, history from 2007). Excess vs normal, Belgium's share, crop-year pace."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c

CY_START = 7          # Brazil crop year Jul-Jun, as in the Cecafe apps
MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]


def _normal(s: pd.Series, m: pd.Timestamp, years=5) -> float:
    prev = [m - pd.DateOffset(years=k) for k in range(1, years + 1)]
    v = s.reindex(prev).dropna()
    return float(v.mean()) if len(v) else float("nan")


def render():
    port = c.PORT
    u, un = c.unit_factor(), c.unit_name()
    c.page_title("Brazil · Cecafe Arabica to Belgium",
                 "Brazil is about half of Antwerp's fresh pending. Cecafe gives Arabica-only exports to Belgium a few days after month end, ahead of TDM.")
    bel = c.flow("Brazil", "Cecafe Arabica")
    allb = c.flow("Brazil", "Cecafe Arabica (all destinations)")
    if bel.empty:
        st.info("No Cecafe data.")
        return
    lm = bel.index.max()
    norm = _normal(bel, lm)
    share = (bel / allb).dropna()
    cy = lambda m: m.year if m.month >= CY_START else m.year - 1          # noqa: E731
    cyid = pd.Series([cy(m) for m in bel.index], index=bel.index)
    pos = lambda m: (m.month - CY_START) % 12                             # noqa: E731
    cur_cy, p = cy(lm), pos(lm)
    ytd = bel[(cyid == cur_cy)].sum()
    ly = bel[(cyid == cur_cy - 1) & (pd.Series([pos(m) for m in bel.index], index=bel.index) <= p)].sum()
    b = c.lag_corr("Brazil", "Cecafe Arabica", port)
    best = b[b["lag"] <= c.AUTO_MAX_LAG].dropna(subset=["r"])
    best = best.loc[best["r"].idxmax()] if not best.empty else None
    c.kpis([
        (f"To Belgium {lm:%b-%y}", c.kfmt(bel[lm] * u), f"{un}, normal {c.kfmt(norm * u)}"),
        ("Excess vs 5y", c.kfmt((bel[lm] - norm) * u), f"{(bel[lm] - norm) / c.LOT_BAGS:+,.0f} lots"),
        ("Belgium share", f"{share.iloc[-1]:.1%}", f"of Brazil Arabica, 5y avg {_normal(share, lm):.1%}"),
        (f"Crop {cur_cy % 100:02d}/{(cur_cy + 1) % 100:02d} to date", c.kfmt(ytd * u), f"{(ytd / ly - 1):+.0%} vs same point last year" if ly else ""),
        ("Fit to Antwerp FP", f"r {best['r']:.2f}" if best is not None else "–",
         f"lead {int(best['lag'])}m, conversion {best['conv']:.0%}" if best is not None else ""),
    ])

    with st.container(border=True):
        c.head("Arabica to Belgium: actual vs normal",
               "Bars: monthly Cecafe Arabica exports to Belgium, coloured by excess (green) or shortfall (red) against the same-month 5-year average (line). "
               "Dotted: Brazil fresh pending at Antwerp, plotted one month back so it lines up with the shipment that fed it.")
        win = bel[bel.index >= lm - pd.DateOffset(months=47)]
        nm = pd.Series({m: _normal(bel, m) for m in win.index})
        fp = c.fp_monthly(port).get("Brazil", pd.Series(dtype=float)).shift(-1, freq="MS")
        fig = go.Figure()
        fig.add_bar(x=win.index, y=win * u, name="Actual", marker_color=[c.GREEN if a >= n else c.RED for a, n in zip(win, nm)],
                    marker_opacity=.85, marker_line_width=0)
        fig.add_scatter(x=nm.index, y=nm * u, name="5y normal", mode="lines", line=dict(color=c.NAVY, width=2))
        fig.add_scatter(x=fp.index, y=fp * u, name="Brazil fresh pending (t+1)", mode="lines+markers", line=dict(color=c.AMBER, width=2, dash="dot"),
                        marker=dict(size=4))
        c.style(fig, height=350, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M3", tickformat="%b-%y"))
        c.show(fig, "br_actual")

    l, r = st.columns(2, gap="medium")
    with l, st.container(border=True):
        c.head("Belgium's share of Brazil Arabica exports", "Monthly share, with the 12-month average. A rising share means Brazil is routing more to the exchange's main grading port.")
        s = share[share.index >= pd.Timestamp("2016-07-01")]
        fig = go.Figure()
        fig.add_scatter(x=s.index, y=s * 100, name="Monthly", mode="lines", line=dict(color="#b9c3de", width=1.4))
        fig.add_scatter(x=s.index, y=s.rolling(12).mean() * 100, name="12m avg", mode="lines", line=dict(color=c.NAVY, width=2.4))
        c.style(fig, height=310, fmt=".1f", yaxis=dict(ticksuffix="%", gridcolor=c.GRID, color=c.AXIS, tickfont=dict(size=10)))
        c.show(fig, "br_share")
    with r, st.container(border=True):
        c.head("Crop-year pace to Belgium", "Cumulative Arabica exports to Belgium from July, one line per crop year (last 6).")
        fig = go.Figure()
        yrs = sorted(cyid.unique())[-6:]
        for i, y in enumerate(yrs):
            s = bel[cyid == y]
            cum = s.cumsum()
            fig.add_scatter(x=[MONTHS[pos(m)] for m in s.index], y=cum * u, name=f"{y % 100:02d}/{(y + 1) % 100:02d}", mode="lines+markers",
                            line=dict(color=c.YEAR_PAL[i], width=2.8 if y == cur_cy else 1.6), marker=dict(size=4))
        c.style(fig, height=310, xaxis=dict(color=c.AXIS, showgrid=False, categoryorder="array", categoryarray=MONTHS))
        c.show(fig, "br_pace")

    with st.container(border=True):
        c.head("Excess vs normal, last 12 months", "Normal = average of the same month over the previous 5 years. Lots of 283.5 bags. Next-month column: Brazil fresh pending at Antwerp the month after.")
        fpb = c.fp_monthly(port).get("Brazil", pd.Series(dtype=float))
        rows = []
        for m in bel.index[-12:][::-1]:
            n = _normal(bel, m)
            ex = bel[m] - n
            nxt = m + pd.DateOffset(months=1)
            rows.append((c.mlabel(m), [c.kfmt(bel[m] * u), c.kfmt(n * u), (c.kfmt(ex * u), "up" if ex >= 0 else "dn"),
                                       (f"{ex / c.LOT_BAGS:+,.0f}", "up" if ex >= 0 else "dn"), (f"{bel[m] / n - 1:+.0%}" if n else "–", "up" if ex >= 0 else "dn"),
                                       f"{share.get(m, float('nan')):.1%}", c.kfmt(fpb.get(nxt, float('nan')) * u) if nxt in fpb.index else "–"], ""))
        c.table(["Actual", "Normal", "Excess", "Lots", "vs Normal", "BE share", "FP next month"], rows, corner="Month")
