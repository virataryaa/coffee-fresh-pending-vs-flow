"""Origin study: one origin, one flow source, one lead. Overlay, lead-lag profile, scatter, seasonality and grading outcome."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c


def controls(port, default_origin=None, key="os"):
    origins = c.study_origins(port)
    if default_origin and f"{key}_origin" not in st.session_state and default_origin in origins:
        st.session_state[f"{key}_origin"] = default_origin
    o = st.radio("Origin", origins, horizontal=True, key=f"{key}_origin", label_visibility="collapsed")
    b = c.best_fit(o, port)
    srcs = c.sources_for(o)
    if not srcs:
        st.info(f"No flow data to Belgium for {o}.")
        return o, None, None, b
    a1, a2, _ = st.columns([2.6, 2.2, 2])
    opts = ["Auto"] + srcs
    src = a1.radio("Flow source", opts, horizontal=True, key=f"{key}_src_{o}")
    src = b.get("source", srcs[0]) if src == "Auto" else src
    lc = c.lag_corr(o, src, port)
    ok = lc[(lc["lag"] <= c.AUTO_MAX_LAG) & (lc["n"] >= 3)].dropna(subset=["r"])
    dflt = int(ok.loc[ok["r"].idxmax(), "lag"]) if not ok.empty else 1
    lag = a2.radio("Lead (months)", list(range(0, c.MAX_LAG + 1)), index=dflt, horizontal=True, key=f"{key}_lag_{o}_{src}")
    return o, src, lag, b


def render():
    port = c.PORT
    u, un = c.unit_factor(), c.unit_name()
    c.page_title("Origin Study", "Fresh pending for one origin at Antwerp against its flow to Belgium, moved forward by the lead.")
    o, src, lag, b = controls(port)
    if src is None:
        return
    fpm = c.fp_monthly(port)[o]
    full = c.last_full_month(port)
    x = c.flow(o, src)
    lc = c.lag_corr(o, src, port)
    row = lc[lc["lag"] == lag].iloc[0]
    fit = c.fitted(o, src, lag, port)
    st.markdown(f"<div class='card-desc'>{c.SOURCE_DESC[src]}. "
                f"Auto pick for {o}: <b>{b.get('source', '–')}</b>, lead {b.get('lag', '–')}m, r {b.get('r', float('nan')):.2f}.</div>",
                unsafe_allow_html=True)

    cur = fpm.index.max()
    c.kpis([
        ("Correlation", f"{row['r']:.2f}" if pd.notna(row["r"]) else "–", f"{int(row['n'])} complete months, lead {lag}m"),
        ("Conversion", f"{row['conv']:.0%}" if pd.notna(row["conv"]) else "–", "fresh pending / lagged flow"),
        ("Latest flow", c.kfmt(x.dropna().iloc[-1] * u) if len(x.dropna()) else "–", f"{c.mlabel(x.dropna().index.max())}, {un}" if len(x.dropna()) else ""),
        (f"Implied {cur:%b}", c.kfmt(fit.get(cur, np.nan) * u), f"MTD actual {c.kfmt(fpm.get(cur, np.nan) * u)}"),
        ("Next month implied", c.kfmt(fit.get(cur + pd.DateOffset(months=1), np.nan) * u), "needs lead ≥ 1 and flow out"),
    ])

    l, r = st.columns([2.3, 1], gap="medium")
    with l, st.container(border=True):
        c.head(f"{o}: fresh pending vs {src.lower()} moved {lag} month{'s' if lag != 1 else ''} forward",
               "Bars: fresh pending (left axis). Line: flow (right axis). Dotted: conversion x flow, the flow-implied fresh pending, carried past today where the flow is already out.")
        start = c.STUDY_START - pd.DateOffset(months=6)
        xs = x.shift(lag, freq="MS")
        xs = xs[xs.index >= start]
        fig = go.Figure()
        fig.add_bar(x=fpm.index, y=fpm * u, name="Fresh pending", marker_color=[c.NAVY if m <= full else "#9fb0d4" for m in fpm.index], marker_line_width=0)
        fig.add_scatter(x=xs.index, y=xs * u, name=f"{src} (t-{lag})", yaxis="y2", mode="lines+markers", line=dict(color=c.AMBER, width=2), marker=dict(size=4))
        ff = fit[fit.index >= c.STUDY_START]
        fig.add_scatter(x=ff.index, y=ff * u, name="Flow-implied", mode="lines", line=dict(color=c.TEAL, width=2, dash="dot"))
        c.style(fig, height=360, y2=dict(rangemode="tozero"), xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "os_overlay")
    with r, st.container(border=True):
        c.head("Lead-lag profile", "Correlation of fresh pending with the flow N months earlier. A clear peak at 1-2 months is the transit + queue time.")
        fig = go.Figure(go.Bar(x=lc["lag"], y=lc["r"], marker_color=[c.NAVY if k == lag else "#b9c3de" for k in lc["lag"]],
                               text=[f"{v:.2f}" if pd.notna(v) else "" for v in lc["r"]], textposition="outside", textfont=dict(size=10, color=c.AXIS),
                               cliponaxis=False, hovertemplate="lead %{x}m: r %{y:.2f}<extra></extra>"))
        c.style(fig, height=360, legend=False, fmt=".2f", hovermode="closest",
                xaxis=dict(color=c.AXIS, showgrid=False, dtick=1, title="lead (months)"), yaxis=dict(range=[-1, 1.1], gridcolor=c.GRID, color=c.AXIS, tickfont=dict(size=10)))
        c.show(fig, "os_lag")

    l, r = st.columns(2, gap="medium")
    with l, st.container(border=True):
        c.head("Flow vs fresh pending, month by month", f"Each dot a complete month. Line: conversion through zero ({row['conv']:.0%}). Latest month in amber.")
        xx = x.shift(lag, freq="MS").reindex(fpm.index)
        m = xx.notna() & (fpm.index <= full)
        fig = go.Figure()
        fig.add_scatter(x=xx[m] * u, y=fpm[m] * u, mode="markers", name="month", marker=dict(size=8, color=c.NAVY, opacity=.75),
                        text=[c.mlabel(i) for i in fpm[m].index], hovertemplate="%{text}<br>flow %{x:,.0f}<br>fresh pending %{y:,.0f}<extra></extra>")
        if m.any():
            li = fpm[m].index.max()
            fig.add_scatter(x=[xx[li] * u], y=[fpm[li] * u], mode="markers+text", text=[c.mlabel(li)], textposition="top center",
                            marker=dict(size=12, color=c.AMBER), textfont=dict(size=10, color=c.AXIS), hoverinfo="skip")
            if pd.notna(row["conv"]):
                mx = float(xx[m].max()) * u
                fig.add_scatter(x=[0, mx], y=[0, mx * row["conv"]], mode="lines", line=dict(color=c.TEAL, dash="dot"), hoverinfo="skip")
        c.style(fig, height=330, legend=False, hovermode="closest", xaxis=dict(title=f"{src} t-{lag} ({un})", color=c.AXIS, gridcolor=c.GRID),
                yaxis=dict(title=f"fresh pending ({un})", color=c.AXIS, gridcolor=c.GRID))
        c.show(fig, "os_scatter")
    with r, st.container(border=True):
        c.head("Grading outcome", "Pending stock (line) and bags passed / failed per week. Pass rate over the window in the legend.")
        d = c.port_daily(port)
        d = d[d["Origin"] == o].set_index("Date")
        wk = d[["Passed", "Failed"]].resample("W-FRI").sum()
        pr = d["Passed"].sum() / max(d["Passed"].sum() + d["Failed"].sum(), 1)
        fig = go.Figure()
        fig.add_bar(x=wk.index, y=wk["Passed"] * u, name=f"Passed ({pr:.0%})", marker_color=c.GREEN, marker_line_width=0)
        fig.add_bar(x=wk.index, y=-wk["Failed"] * u, name="Failed", marker_color=c.RED, marker_line_width=0)
        fig.add_scatter(x=d.index, y=d["Pending"] * u, name="Pending", mode="lines", line=dict(color=c.NAVY, width=1.6))
        c.style(fig, height=330, barmode="relative", bargap=0.1)
        c.show(fig, "os_outcome")

    l, r = st.columns(2, gap="medium")
    for col, (title, ser, desc) in zip((l, r), [
            ("Fresh pending seasonality", fpm, "Fresh pending by calendar month, one line per year: when this origin's crop reaches the grading room."),
            (f"{src} seasonality", x[x.index >= pd.Timestamp("2021-01-01")], "Flow by calendar month, one line per year (unshifted).")]):
        with col, st.container(border=True):
            c.head(title, desc)
            fig = go.Figure()
            yrs = sorted(ser.index.year.unique())
            for i, y in enumerate(yrs):
                s = ser[ser.index.year == y]
                last = i == len(yrs) - 1
                fig.add_scatter(x=s.index.month, y=s * u, name=str(y), mode="lines+markers",
                                line=dict(color=c.YEAR_PAL[-len(yrs):][i] if len(yrs) <= len(c.YEAR_PAL) else c.PAL[i % len(c.PAL)], width=2.6 if last else 1.6),
                                marker=dict(size=4))
            c.style(fig, height=300, xaxis=dict(color=c.AXIS, showgrid=False, tickvals=list(range(1, 13)),
                                                ticktext=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]))
            c.show(fig, f"os_seas_{title[:4]}")
