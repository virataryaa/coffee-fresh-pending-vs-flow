"""Nowcast: flows already shipped imply the fresh pending still to come. Per-origin estimate, total, and the in-sample fit."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c


def render():
    mk = c.market()
    M = c.MARKETS[mk]
    u, un = c.unit_factor(), c.unit_name()
    c.page_title(f"Nowcast · {M['where']}", "Fresh pending expected from coffee already shipped")
    nc = c.nowcast_table(mk)
    if nc.empty:
        st.info("No origin has a usable fit.")
        return
    months = [m for m in nc.columns if isinstance(m, pd.Timestamp)]
    cur = months[0]
    fpm = c.fp_monthly(mk)
    full = c.last_full_month()
    tot = {m: nc[m].sum(min_count=1) for m in months}

    with st.container(border=True):
        c.head("By origin", "Blank = flow data not out yet")
        rows = []
        for _, r in nc.sort_values("r", ascending=False).iterrows():
            cells = [(r["Source"], "l"), f"{r['Lag']}m", f"{r['r']:.2f}", f"{r['Conv']:.0%}"]
            cells += [(c.kfmt(r[m] * u), "b" if m == cur else "") if pd.notna(r[m]) else ("", "mut") for m in months]
            cells += [c.kfmt(r["MTD"] * u)]
            rows.append((r["Origin"], cells, ""))
        rows.append(("Total", ["", "", "", ""] + [c.kfmt(tot[m] * u) if pd.notna(tot[m]) else "" for m in months]
                     + [c.kfmt(nc["MTD"].sum() * u)], "tot"))
        c.table(["Source", "Lead", "r", "Conversion"] + [f"Est. {m:%b-%y}" for m in months] + [f"MTD {cur:%b}"], rows, corner="Origin")

    with st.container(border=True):
        c.head("Fit history", "<b>Bars</b> actual &nbsp;·&nbsp; <b>Line</b> expected from flow &nbsp;·&nbsp; <b>Hatched</b> estimate ahead")
        fits = [c.fitted(r["Origin"], r["Source"], int(r["Lag"]), mk).rename(r["Origin"]) for _, r in nc.iterrows()]
        idx = pd.date_range(c.STUDY_START, max(months), freq="MS")
        F = pd.concat(fits, axis=1).reindex(idx)
        act = fpm[nc["Origin"]].sum(axis=1).reindex(idx)
        est = F.sum(axis=1, min_count=1)
        done = idx <= full
        fig = go.Figure()
        fig.add_bar(x=idx[done], y=act[done] * u, name="Actual", marker_color=c.NAVY, marker_line_width=0)
        fig.add_bar(x=idx[~done], y=est[~done] * u, name="Estimate", marker=dict(color="rgba(42,140,140,.25)", line=dict(color=c.TEAL, width=1.2),
                                                                                 pattern=dict(shape="/", fgcolor=c.TEAL, size=6)))
        if (~done).any():
            fig.add_scatter(x=[cur], y=[act[cur] * u], name="MTD", mode="markers", marker=dict(symbol="diamond", size=11, color=c.AMBER))
        fig.add_scatter(x=idx, y=est * u, name="Flow-implied", mode="lines", line=dict(color=c.TEAL, width=2))
        c.style(fig, height=360, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "nc_hist")
        a, e = act[done], est[done]
        ok = a.notna() & e.notna()
        if ok.sum() > 3:
            st.markdown(f"<div class='note'>r {np.corrcoef(a[ok], e[ok])[0, 1]:.2f} · avg error {c.kfmt((a[ok] - e[ok]).abs().mean() * u)} {un}/month "
                        f"· avg actual {c.kfmt(a[ok].mean() * u)}</div>", unsafe_allow_html=True)
