"""Overview: what is being presented for grading at Antwerp now, who it comes from, and how well each origin's flow explains it."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c


def render():
    port = c.PORT
    u, un = c.unit_factor(), c.unit_name()
    d = c.port_daily(port)
    fpm = c.fp_monthly(port)
    last = d["Date"].max()
    cur = last.to_period("M").to_timestamp()
    full = c.last_full_month(port)

    c.page_title(f"Fresh Pending vs Flow · {port}",
                 f"Arabica newly presented for grading at {port} against coffee shipped to Belgium. Report date {last:%d-%b-%Y}.")

    tot = d.groupby("Date")[["Pending", "Passed", "Failed", "FreshPending"]].sum()
    pend_now = tot["Pending"].iloc[-1]
    pend_5 = tot["Pending"].iloc[-6] if len(tot) > 5 else float("nan")
    last3 = fpm.loc[(fpm.index > full - pd.DateOffset(months=3)) & (fpm.index <= full)].sum(axis=1)
    w90 = tot[tot.index > last - pd.Timedelta(days=90)]
    graded = w90["Passed"].sum() + w90["Failed"].sum()
    nc = c.nowcast_table(port)
    est_cur = nc[cur].sum() if not nc.empty and cur in nc else float("nan")
    c.kpis([
        ("Pending now", c.kfmt(pend_now * u), f"{c.kfmt((pend_now - pend_5) * u)} vs 5 reports ago"),
        ("Fresh pending MTD", c.kfmt(fpm.loc[cur].sum() * u), f"{cur:%b-%Y}, {un}"),
        ("Fresh pending 3m avg", c.kfmt(last3.mean() * u), f"per month, to {full:%b-%y}"),
        ("Pass rate 90d", f"{w90['Passed'].sum() / graded:.0%}" if graded else "–", f"{c.kfmt(graded * u)} {un} graded"),
        ("Flow-implied this month", c.kfmt(est_cur * u), "sum of origin nowcasts"),
    ])

    # ── who feeds Antwerp ────────────────────────────────────────────────────────────────────────────────
    with st.container(border=True):
        c.head("Monthly fresh pending by origin",
               "Bags newly presented for grading each month (change in pending + passed + failed). Line: pending at month end. Last month is month to date.")
        top = list(fpm.sum().sort_values(ascending=False).index[:7])
        x = fpm.index
        fig = go.Figure()
        for i, o in enumerate(top):
            fig.add_bar(x=x, y=fpm[o] * u, name=o, marker_color=c.PAL[i % len(c.PAL)], marker_line_width=0)
        oth = fpm.drop(columns=top).sum(axis=1)
        fig.add_bar(x=x, y=oth * u, name="Others", marker_color="#d5dbe8", marker_line_width=0)
        eom = tot["Pending"].groupby(tot.index.to_period("M").to_timestamp()).last()
        fig.add_scatter(x=eom.index, y=eom * u, name="Pending (eom)", yaxis="y2", mode="lines", line=dict(color="#0a2463", width=2, dash="dot"))
        c.style(fig, height=340, barmode="relative", y2=dict(title=None), xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "ov_stack")

    # ── scorecard ────────────────────────────────────────────────────────────────────────────────────────
    with st.container(border=True):
        c.head("Origin scorecard",
               "Best fit = the flow source and lead (0-3 months) whose monthly volume correlates best with fresh pending. "
               "Conversion = fresh pending / lagged flow over the overlap: the share of what ships to Belgium that turns up for grading. "
               "Latest flow is compared with the average of the same month in the previous 3 years.")
        share = fpm[fpm.index <= full].sum()
        share = share / share.sum()
        rows = []
        for o in c.study_origins(port):
            b = c.best_fit(o, port)
            r = nc[nc["Origin"] == o]
            if b:
                f = c.flow(o, b["source"]).dropna()
                lm = f.index.max()
                avg = f[[lm - pd.DateOffset(years=k) for k in (1, 2, 3) if lm - pd.DateOffset(years=k) in f.index]].mean()
                vs = (f.iloc[-1] / avg - 1) if avg and avg > 0 else float("nan")
                rcls = "s3" if b["r"] >= .7 else "s2" if b["r"] >= .5 else "s1" if b["r"] >= .3 else "mut"
                cells = [f"{share.get(o, 0):.1%}", (b["source"], "l"), f"{b['lag']}m", (f"{b['r']:.2f}", rcls), f"{b['conv']:.0%}",
                         c.mlabel(lm), c.kfmt(f.iloc[-1] * u),
                         (f"{vs:+.0%}" if pd.notna(vs) else "–", "up" if pd.notna(vs) and vs > 0 else "dn" if pd.notna(vs) else "mut"),
                         c.kfmt(r[cur].iloc[0] * u) if len(r) and cur in r and pd.notna(r[cur].iloc[0]) else "–",
                         c.kfmt(fpm.loc[cur, o] * u)]
            else:
                cells = [f"{share.get(o, 0):.1%}", ("no usable flow", "l mut")] + ["–"] * 7 + [c.kfmt(fpm.loc[cur, o] * u)]
            rows.append((o, cells, ""))
        c.table(["Share of FP", "Best source", "Lead", "r", "Conversion", "Flow month", "Latest flow", "vs 3y", f"Est. {cur:%b}", "MTD"],
                rows, corner="Origin")
        st.markdown("<div class='note'>r shading: dark ≥ 0.7, mid ≥ 0.5, light ≥ 0.3. Correlations are on complete months since Aug-2023 "
                    f"(about {len(fpm[fpm.index <= full])} months), so read anything below ~0.4 as noise.</div>", unsafe_allow_html=True)
