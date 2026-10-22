"""Overview: fresh pending by origin, and how well each origin's flow explains it."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c


def render():
    mk = c.market()
    M = c.MARKETS[mk]
    u = c.unit_factor()
    d = c.port_daily(mk)
    fpm = c.fp_monthly(mk)
    last = d["Date"].max()
    cur = last.to_period("M").to_timestamp()
    full = c.last_full_month()
    c.page_title(f"Fresh Pending vs Flow · {M['where']}", f"Report {last:%d-%b-%Y}")

    with st.container(border=True):
        c.head("Monthly fresh pending by origin", "New bags sent to grading. Dotted: pending at month end.")
        top = list(fpm.sum().sort_values(ascending=False).index[:7])
        fig = go.Figure()
        for i, o in enumerate(top):
            fig.add_bar(x=fpm.index, y=fpm[o] * u, name=o, marker_color=c.PAL[i % len(c.PAL)], marker_line_width=0)
        fig.add_bar(x=fpm.index, y=fpm.drop(columns=top).sum(axis=1) * u, name="Others", marker_color="#d5dbe8", marker_line_width=0)
        tot = d.groupby("Date")["Pending"].sum()
        eom = tot.groupby(tot.index.to_period("M").to_timestamp()).last()
        fig.add_scatter(x=eom.index, y=eom * u, name="Pending", yaxis="y2", mode="lines", line=dict(color="#0a2463", width=2, dash="dot"))
        c.style(fig, height=340, barmode="relative", y2=dict(title=None), xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "ov_stack")

    with st.container(border=True):
        c.head("Origin scorecard", "Conversion = share of flow that reaches grading. vs avg = latest flow vs same month, averaged over past years.")
        yrs = st.radio("Compare latest flow with", [1, 2, 3, 5], index=2, horizontal=True, key="ov_yrs",
                       format_func=lambda n: "last year" if n == 1 else f"{n}y avg")
        nc = c.nowcast_table(mk)
        share = fpm[fpm.index <= full].sum()
        share = share / share.sum()
        rows = []
        for o in c.study_origins(mk):
            b = c.best_fit(o, mk)
            r = nc[nc["Origin"] == o] if not nc.empty else nc
            if b:
                f = c.flow(o, b["source"], mk).dropna()
                lm = f.index.max()
                avg = f[[lm - pd.DateOffset(years=k) for k in range(1, yrs + 1) if lm - pd.DateOffset(years=k) in f.index]].mean()
                vs = (f.iloc[-1] / avg - 1) if avg and avg > 0 else float("nan")
                rcls = "s3" if b["r"] >= .7 else "s2" if b["r"] >= .5 else "s1" if b["r"] >= .3 else "mut"
                est = r[cur].iloc[0] if len(r) and cur in r and pd.notna(r[cur].iloc[0]) else float("nan")
                cells = [f"{share.get(o, 0):.1%}", (b["source"], "l"), f"{b['lag']}m", (f"{b['r']:.2f}", rcls), f"{b['conv']:.0%}",
                         c.mlabel(lm), c.kfmt(f.iloc[-1] * u),
                         (f"{vs:+.0%}" if pd.notna(vs) else "–", "up" if pd.notna(vs) and vs > 0 else "dn" if pd.notna(vs) else "mut"),
                         c.kfmt(est * u), c.kfmt(fpm.loc[cur, o] * u)]
            else:
                cells = [f"{share.get(o, 0):.1%}", ("no flow data", "l mut")] + ["–"] * 7 + [c.kfmt(fpm.loc[cur, o] * u)]
            rows.append((o, cells, ""))
        c.table(["Share", "Best source", "Lead", "r", "Conversion", "Flow month", "Flow", "vs last yr" if yrs == 1 else f"vs {yrs}y avg", f"Est. {cur:%b}", "MTD"], rows, corner="Origin")
        st.markdown("<div class='note'>Shading: r ≥ 0.7 / 0.5 / 0.3. Under 0.4 is likely noise.</div>", unsafe_allow_html=True)
