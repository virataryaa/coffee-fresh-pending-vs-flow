"""Brazil: Cecafe Arabica to the market's destination (timely, Arabica-only, history from 2007). Actual vs same-month normal, crop-year view, share."""
import numpy as np
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
    c.group(f"Brazil flows to {dest}", "How much Brazil ships there vs normal")

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

    c.group("Excess flow → fresh pending", f"Does shipping more than normal show up at {M['where']} grading?")
    excess_study(bel, fp, yrs, M, u)


def _normal_series(s: pd.Series, years: int) -> pd.Series:
    return pd.Series({m: _same_month(s, m, years).mean() for m in s.index})


def excess_study(bel, fp, yrs, M, u):
    """Does Brazil shipping MORE than normal to the destination show up as fresh pending at its ports?"""
    full = c.last_full_month()
    fp = fp[fp.index <= full]
    ex = bel - _normal_series(bel, yrs)
    a1, a2, _ = st.columns([2.2, 2, 2])
    win = a1.radio("Excess measured over", [1, 3], horizontal=True, key="bx_win", format_func=lambda n: "1 month" if n == 1 else "3 months (running)")
    lag = a2.radio("Fresh pending, months later", [0, 1, 2, 3], index=1, horizontal=True, key="bx_lag")
    exw = ex.rolling(win).sum() if win > 1 else ex
    xs = exw.shift(lag, freq="MS").reindex(fp.index)
    ok = xs.notna()
    r_ex = np.corrcoef(xs[ok], fp[ok])[0, 1] if ok.sum() > 5 else np.nan
    raw = bel.rolling(win).sum().shift(lag, freq="MS").reindex(fp.index)
    r_raw = np.corrcoef(raw[ok], fp[ok])[0, 1] if ok.sum() > 5 else np.nan
    st.markdown(f"<div class='card-desc'>Excess = exports minus same-month {yrs}y normal{D}r excess <b>{r_ex:.2f}</b> (R² {r_ex ** 2:.2f})"
                f"{D}r raw flow <b>{r_raw:.2f}</b>{D}{int(ok.sum())} months</div>", unsafe_allow_html=True)

    l, r = st.columns([2, 1.2], gap="medium")
    with l, st.container(border=True):
        c.head("Excess flow vs fresh pending", f"<b>Bars</b> excess, green above / red below normal, moved {lag}m forward{D}<b>Orange</b> Brazil fresh pending at {M['where']}")
        e = exw.shift(lag, freq="MS")
        e = e[e.index >= c.STUDY_START - pd.DateOffset(months=3)]
        fig = go.Figure()
        fig.add_bar(x=e.index, y=e * u, name="Excess flow", marker_color=["rgba(46,139,87,.55)" if v >= 0 else "rgba(176,65,62,.5)" for v in e], marker_line_width=0)
        fig.add_scatter(x=fp.index, y=fp * u, name="Fresh pending", mode="lines+markers", line=dict(color="#e07b00", width=3), marker=dict(size=6))
        c.style(fig, height=360, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "bx_ts")
    with r, st.container(border=True):
        c.head(f"Correlation · r {r_ex:.2f} · R² {r_ex ** 2:.2f}", f"Each dot is a month{D}<b>Orange</b> latest")
        fig = go.Figure()
        fig.add_scatter(x=xs[ok] * u, y=fp[ok] * u, mode="markers", marker=dict(size=8, color=c.NAVY, opacity=.75),
                        text=[c.mlabel(i) for i in fp[ok].index], hovertemplate="%{text}<br>excess %{x:+,.0f}<br>fresh pending %{y:,.0f}<extra></extra>")
        if ok.sum() > 5:
            li = fp[ok].index.max()
            fig.add_scatter(x=[xs[li] * u], y=[fp[li] * u], mode="markers", marker=dict(size=12, color="#e07b00"), hoverinfo="skip")
            b_, a_ = np.polyfit(xs[ok], fp[ok], 1)
            xl = np.array([xs[ok].min(), xs[ok].max()])
            fig.add_scatter(x=xl * u, y=(a_ + b_ * xl) * u, mode="lines", line=dict(color=c.TEAL, dash="dot"), hoverinfo="skip")
        c.style(fig, height=360, legend=False, hovermode="closest", xaxis=dict(title="excess flow", color=c.AXIS, gridcolor=c.GRID, zeroline=True),
                yaxis=dict(title="fresh pending", color=c.AXIS, gridcolor=c.GRID))
        c.show(fig, "bx_sc")

    l, r = st.columns([1, 1.6], gap="medium")
    with l, st.container(border=True):
        c.head("After excess vs after shortfall", f"Average Brazil fresh pending {lag}m after each kind of month")
        groups = [("Shortfall", xs < 0, c.RED), ("Excess", xs >= 0, c.GREEN)]
        vals = [(n, fp[m_ & ok].mean(), int((m_ & ok).sum()), col) for n, m_, col in groups]
        fig = go.Figure(go.Bar(x=[v[0] for v in vals], y=[v[1] * u for v in vals], marker_color=[v[3] for v in vals],
                               text=[f"{c.kfmt(v[1] * u)}<br>n {v[2]}" for v in vals], textposition="outside", cliponaxis=False,
                               textfont=dict(size=11, color=c.AXIS), hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
        c.style(fig, height=320, legend=False, hovermode="closest", bargap=0.45)
        c.show(fig, "bx_bucket")
    with r, st.container(border=True):
        c.head("Lead-lag: excess vs raw flow", "Correlation with fresh pending at each lead. Taller = better guide")
        rows_ex, rows_raw = [], []
        for k in range(4):
            a = exw.shift(k, freq="MS").reindex(fp.index)
            b = bel.rolling(win).sum().shift(k, freq="MS").reindex(fp.index)
            m_ = a.notna() & b.notna()
            rows_ex.append(np.corrcoef(a[m_], fp[m_])[0, 1] if m_.sum() > 5 else np.nan)
            rows_raw.append(np.corrcoef(b[m_], fp[m_])[0, 1] if m_.sum() > 5 else np.nan)
        fig = go.Figure()
        fig.add_bar(x=list(range(4)), y=rows_ex, name="Excess", marker_color=c.NAVY, text=[f"{v:.2f}" for v in rows_ex], textposition="outside")
        fig.add_bar(x=list(range(4)), y=rows_raw, name="Raw flow", marker_color="#b9c3de", text=[f"{v:.2f}" for v in rows_raw], textposition="outside")
        c.style(fig, height=320, fmt=".2f", hovermode="closest", barmode="group",
                xaxis=dict(color=c.AXIS, showgrid=False, dtick=1, title="months later"), yaxis=dict(range=[-0.2, 1.05], gridcolor=c.GRID, color=c.AXIS))
        c.show(fig, "bx_lag_chart")
