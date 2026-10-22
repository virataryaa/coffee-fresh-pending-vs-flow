"""Origin study: one origin, one flow source, one lead. Overlay, lead-lag profile, scatter, grading outcome and seasonality."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render():
    mk = c.market()
    M = c.MARKETS[mk]
    u, un = c.unit_factor(), c.unit_name()
    c.page_title(f"Origin Study · {M['where']}")
    origins = c.study_origins(mk)
    o = st.radio("Origin", origins, horizontal=True, key=f"os_origin_{mk}", label_visibility="collapsed")
    b = c.best_fit(o, mk)
    srcs = c.sources_for(o, mk)
    if not srcs:
        st.info(f"No flow data from {o} to {M['dest']}.")
        return
    a1, a2, _ = st.columns([2.6, 2.2, 2])
    src = a1.radio("Flow source", ["Auto"] + srcs, horizontal=True, key=f"os_src_{mk}_{o}")
    src = b.get("source", srcs[0]) if src == "Auto" else src
    lc = c.lag_corr(o, src, mk)
    ok = lc[(lc["lag"] <= c.AUTO_MAX_LAG) & (lc["n"] >= 3)].dropna(subset=["r"])
    dflt = int(ok.loc[ok["r"].idxmax(), "lag"]) if not ok.empty else 1
    if b.get("source") == src:
        dflt = b["lag"]
    lag = a2.radio("Lead (months)", list(range(0, c.MAX_LAG + 1)), index=dflt, horizontal=True, key=f"os_lag_{mk}_{o}_{src}")

    fpm = c.fp_monthly(mk)[o]
    full = c.last_full_month()
    x = c.flow(o, src, mk)
    row = lc[lc["lag"] == lag].iloc[0]
    fit = c.fitted(o, src, lag, mk)
    rtxt = f"{row['r']:.2f}" if pd.notna(row["r"]) else "–"
    ctxt = f"{row['conv']:.0%}" if pd.notna(row["conv"]) else "–"
    st.markdown(f"<div class='card-desc'>r <b>{rtxt}</b> · conversion <b>{ctxt}</b> · {int(row['n'])} months</div>", unsafe_allow_html=True)

    l, r = st.columns([2.3, 1], gap="medium")
    with l, st.container(border=True):
        c.head(f"{o}: fresh pending vs {src.lower()}, +{lag}m", "Bars: fresh pending. Line: flow. Dotted: flow-implied.")
        xs = x.shift(lag, freq="MS")
        xs = xs[xs.index >= c.STUDY_START - pd.DateOffset(months=6)]
        fig = go.Figure()
        fig.add_bar(x=fpm.index, y=fpm * u, name="Fresh pending", marker_color=[c.NAVY if m <= full else "#9fb0d4" for m in fpm.index], marker_line_width=0)
        fig.add_scatter(x=xs.index, y=xs * u, name=f"Flow (+{lag}m)", yaxis="y2", mode="lines+markers", line=dict(color=c.AMBER, width=2), marker=dict(size=4))
        ff = fit[fit.index >= c.STUDY_START]
        fig.add_scatter(x=ff.index, y=ff * u, name="Flow-implied", mode="lines", line=dict(color=c.TEAL, width=2, dash="dot"))
        c.style(fig, height=360, y2=dict(rangemode="tozero"), xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "os_overlay")
    with r, st.container(border=True):
        c.head("Lead-lag", "r by lead. The peak is the transit time.")
        fig = go.Figure(go.Bar(x=lc["lag"], y=lc["r"], marker_color=[c.NAVY if k == lag else "#b9c3de" for k in lc["lag"]],
                               text=[f"{v:.2f}" if pd.notna(v) else "" for v in lc["r"]], textposition="outside", textfont=dict(size=10, color=c.AXIS),
                               cliponaxis=False, hovertemplate="lead %{x}m: r %{y:.2f}<extra></extra>"))
        c.style(fig, height=360, legend=False, fmt=".2f", hovermode="closest",
                xaxis=dict(color=c.AXIS, showgrid=False, dtick=1, title="months"), yaxis=dict(range=[-1, 1.1], gridcolor=c.GRID, color=c.AXIS, tickfont=dict(size=10)))
        c.show(fig, "os_lag")

    l, r = st.columns(2, gap="medium")
    with l, st.container(border=True):
        d = c.port_daily(mk)
        d = d[d["Origin"] == o].groupby("Date")[["Pending", "Passed", "Failed"]].sum()
        wk = d[["Passed", "Failed"]].resample("W-FRI").sum()
        pr = d["Passed"].sum() / max(d["Passed"].sum() + d["Failed"].sum(), 1)
        c.head("Grading outcome", f"Weekly passed / failed. Pass rate {pr:.0%}.")
        fig = go.Figure()
        fig.add_bar(x=wk.index, y=wk["Passed"] * u, name="Passed", marker_color=c.GREEN, marker_line_width=0)
        fig.add_bar(x=wk.index, y=-wk["Failed"] * u, name="Failed", marker_color=c.RED, marker_line_width=0)
        fig.add_scatter(x=d.index, y=d["Pending"] * u, name="Pending", mode="lines", line=dict(color=c.NAVY, width=1.6))
        c.style(fig, height=330, barmode="relative", bargap=0.1)
        c.show(fig, "os_outcome")

    with r, st.container(border=True):
        c.head("Fresh pending by month", "One line per year.")
        fig = go.Figure()
        yrs = sorted(fpm.index.year.unique())
        pal = c.YEAR_PAL[-len(yrs):] if len(yrs) <= len(c.YEAR_PAL) else c.PAL
        for i, y in enumerate(yrs):
            s = fpm[fpm.index.year == y]
            fig.add_scatter(x=s.index.month, y=s * u, name=str(y), mode="lines+markers",
                            line=dict(color=pal[i % len(pal)], width=2.6 if i == len(yrs) - 1 else 1.6), marker=dict(size=4))
        c.style(fig, height=330, xaxis=dict(color=c.AXIS, showgrid=False, tickvals=list(range(1, 13)), ticktext=MONTHS))
        c.show(fig, "os_seas")
