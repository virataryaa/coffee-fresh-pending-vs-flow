"""Nowcast: flows already shipped imply the fresh pending still to come. Per-origin estimate, total, and how the fit did in the past."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c


def render():
    port = c.PORT
    u, un = c.unit_factor(), c.unit_name()
    c.page_title("Nowcast · flow-implied fresh pending",
                 "Each origin uses its auto fit (source and lead with the best correlation). Estimate = conversion x flow that left / arrived 'lead' months earlier, "
                 "so a 1-2 month lead gives a view on grading before it happens.")
    nc = c.nowcast_table(port)
    if nc.empty:
        st.info("No origin has a usable fit.")
        return
    months = [m for m in nc.columns if isinstance(m, pd.Timestamp)]
    cur = months[0]
    fpm = c.fp_monthly(port)
    full = c.last_full_month(port)

    tot = {m: nc[m].sum(min_count=1) for m in months}
    covered = {m: nc.loc[nc[m].notna(), "Origin"].tolist() for m in months}
    hist_share = fpm[fpm.index <= full][nc["Origin"]].sum().sum() / fpm[fpm.index <= full].sum().sum()
    c.kpis([(f"{m:%b-%y}" + (" (current)" if m == cur else ""), c.kfmt(tot[m] * u),
             f"{len(covered[m])} origins with flow out" + (f", MTD {c.kfmt(fpm.loc[cur].sum() * u)}" if m == cur else ""))
            for m in months if pd.notna(tot[m])] +
           [("Modelled share", f"{hist_share:.0%}", "of Antwerp fresh pending since Aug-23")])

    with st.container(border=True):
        c.head("By origin", "Blank = the lagged flow for that month is not published yet. r and n are from complete months since Aug-2023.")
        rows = []
        for _, r in nc.sort_values("r", ascending=False).iterrows():
            cells = [(r["Source"], "l"), f"{r['Lag']}m", f"{r['r']:.2f}", str(r["n"]), f"{r['Conv']:.0%}"]
            cells += [(c.kfmt(r[m] * u), "b" if m == cur else "") if pd.notna(r[m]) else ("", "mut") for m in months]
            cells += [c.kfmt(r["MTD"] * u)]
            rows.append((r["Origin"], cells, ""))
        rows.append(("Total", ["", "", "", "", ""] + [c.kfmt(tot[m] * u) if pd.notna(tot[m]) else "" for m in months]
                     + [c.kfmt(nc["MTD"].sum() * u)], "tot"))
        c.table(["Source", "Lead", "r", "n", "Conversion"] + [f"Est. {m:%b-%y}" for m in months] + [f"MTD {cur:%b}"], rows, corner="Origin")

    with st.container(border=True):
        c.head("Fit history: modelled origins",
               "Bars: actual fresh pending of the modelled origins. Line: sum of their flow-implied values. Hatched bars: estimates for months not finished yet. "
               "In-sample, so it shows the shape of the fit, not an out-of-sample score.")
        fits = []
        for _, r in nc.iterrows():
            f = c.fitted(r["Origin"], r["Source"], int(r["Lag"]), port)
            fits.append(f.rename(r["Origin"]))
        F = pd.concat(fits, axis=1)
        idx = pd.date_range(c.STUDY_START, max(months), freq="MS")
        F = F.reindex(idx)
        act = fpm[nc["Origin"]].sum(axis=1).reindex(idx)
        est = F.sum(axis=1, min_count=1)
        done = idx <= full
        fig = go.Figure()
        fig.add_bar(x=idx[done], y=act[done] * u, name="Actual", marker_color=c.NAVY, marker_line_width=0)
        fig.add_bar(x=idx[~done], y=est[~done] * u, name="Estimate", marker=dict(color="rgba(42,140,140,.25)", line=dict(color=c.TEAL, width=1.2),
                                                                                 pattern=dict(shape="/", fgcolor=c.TEAL, size=6)))
        if (~done).any() and cur in act.index:
            fig.add_scatter(x=[cur], y=[act[cur] * u], name="MTD", mode="markers", marker=dict(symbol="diamond", size=11, color=c.AMBER))
        fig.add_scatter(x=idx, y=est * u, name="Flow-implied", mode="lines", line=dict(color=c.TEAL, width=2))
        c.style(fig, height=360, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "nc_hist")
        a, e = act[done], est[done]
        ok = a.notna() & e.notna()
        if ok.sum() > 3:
            mae = (a[ok] - e[ok]).abs().mean()
            r = np.corrcoef(a[ok], e[ok])[0, 1]
            st.markdown(f"<div class='note'>Total fit over {ok.sum()} months: r {r:.2f}, mean absolute error {c.kfmt(mae * u)} {un} a month "
                        f"against an average of {c.kfmt(a[ok].mean() * u)}.</div>", unsafe_allow_html=True)
