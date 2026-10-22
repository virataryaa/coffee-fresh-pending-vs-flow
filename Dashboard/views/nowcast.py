"""Nowcast: flows already shipped imply the fresh pending still to come. Per-origin estimate, total, and the in-sample fit."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core as c

D = " &nbsp;·&nbsp; "


def est_cell(r, m, cur, u):
    """Estimate cell: value (bold this month, '~' and tinted when it rests on a filled flow month), or why it is blank."""
    v = r[m]
    if pd.notna(v):
        if m in r["filled"]:
            return (f"~{c.kfmt(v * u)}", "fill")
        return (c.kfmt(v * u), "b" if m == cur else "")
    need = m - pd.DateOffset(months=int(r["Lag"]))
    return (f"needs {need:%b} flow", "mut")


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
    share = c.certs_share(mk)

    with st.container(border=True):
        fill_txt = f"{D}<b>~ tinted</b> uses filled flow (average of 3 methods, compared below)"
        c.head("By origin", f"Sorted by share of certs{D}Estimate = flow from 'lead' months earlier x conversion{fill_txt}")
        fitted = {r["Origin"]: r for _, r in nc.iterrows()}
        rows = []
        for o in sorted(c.study_origins(mk), key=lambda o: -float(share.get(o, 0.0))):
            sh = f"{share.get(o, 0.0):.1%}"
            mtd = c.kfmt(fpm.loc[cur, o] * u) if o in fpm else "0"
            if o in fitted:
                r = fitted[o]
                cells = [sh, (r["Source"], "l"), f"{r['Lag']}m", f"{r['r']:.2f}", f"{r['Conv']:.0%}"]
                cells += [est_cell(r, m, cur, u) for m in months] + [mtd]
            else:
                b = c.best_fit(o, mk)
                if b:
                    cells = [sh, (b["source"], "l mut"), f"{b['lag']}m", (f"{b['r']:.2f}", "mut"), (f"{b['conv']:.0%}", "mut")]
                    cells += [("weak fit", "mut")] * len(months) + [mtd]
                else:
                    cells = [sh, ("no flow data", "l mut"), "", "", ""] + [("", "mut")] * len(months) + [mtd]
            rows.append((o, cells, ""))
        rows.append(("Total", ["", "", "", "", ""] + [c.kfmt(tot[m] * u) if pd.notna(tot[m]) else "" for m in months]
                     + [c.kfmt(nc["MTD"].sum() * u)], "tot"))
        c.table(["Certs share", "Source", "Lead", "r", "Conversion"] + [f"Est. {m:%b-%y}" for m in months] + [f"MTD {cur:%b}"], rows, corner="Origin")
        st.markdown(f"<div class='note'>Weak fit = r below {c.MIN_R:.1f}, not used for estimates.</div>", unsafe_allow_html=True)

    with st.container(border=True):
        c.head("Fill methods compared", f"Total estimate under each way of filling unpublished flow months{D}<b>Average</b> is what the tables use")
        rows = []
        for meth in c.FILL_METHODS + ["Average", "Off"]:
            t = nc if meth == c.DEFAULT_FILL else c.nowcast_table(mk, meth)
            vals = [t[m].sum(min_count=1) for m in months]
            label = "No fill (published flow only)" if meth == "Off" else meth
            rows.append((label, [(c.FILL_DESC[meth], "l mut")] + [c.kfmt(v * u) if pd.notna(v) else "" for v in vals],
                         "tot" if meth == "Average" else ""))
        c.table(["How"] + [f"Est. {m:%b-%y}" for m in months], rows, corner="Method")

    with st.container(border=True):
        c.head("Fit history", f"<b>Bars</b> actual{D}<b>Line</b> expected from flow{D}<b>Hatched</b> estimate ahead{D}<b>Band</b> middle 60% of past misses{D}<b>Diamond</b> month to date")
        fits = [c.fitted(r["Origin"], r["Source"], int(r["Lag"]), mk).rename(r["Origin"]) for _, r in nc.iterrows()]
        idx = pd.date_range(c.STUDY_START, max(months), freq="MS")
        F = pd.concat(fits, axis=1).reindex(idx)
        act = fpm[nc["Origin"]].sum(axis=1).reindex(idx)
        est = F.sum(axis=1, min_count=1)
        for m in months:                                     # months ahead: the table's estimates (incl. filled flow)
            est[m] = tot[m]
        done = idx <= full
        res = (act[done] - est[done]).dropna()                # past misses: actual - expected
        lo_q, hi_q = (res.quantile(.2), res.quantile(.8)) if len(res) > 5 else (0.0, 0.0)
        fig = go.Figure()
        fig.add_scatter(x=idx, y=(est + hi_q).clip(lower=0) * u, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
        fig.add_scatter(x=idx, y=(est + lo_q).clip(lower=0) * u, mode="lines", line=dict(width=0), fill="tonexty",
                        fillcolor="rgba(42,140,140,.14)", name="Range", hovertemplate="range %{y:,.0f}<extra></extra>")
        fig.add_bar(x=idx[done], y=act[done] * u, name="Actual", marker_color=c.NAVY, marker_line_width=0)
        fig.add_bar(x=idx[~done], y=est[~done] * u, name="Estimate", marker=dict(color="rgba(42,140,140,.25)", line=dict(color=c.TEAL, width=1.2),
                                                                                 pattern=dict(shape="/", fgcolor=c.TEAL, size=6)))
        if (~done).any():
            fig.add_scatter(x=[cur], y=[act[cur] * u], name="MTD", mode="markers", marker=dict(symbol="diamond", size=11, color=c.AMBER))
        fig.add_scatter(x=idx, y=est * u, name="Expected from flow", mode="lines", line=dict(color=c.TEAL, width=2))
        c.style(fig, height=360, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "nc_hist")
        a, e = act[done], est[done]
        ok = a.notna() & e.notna()
        if ok.sum() > 3:
            st.markdown(f"<div class='note'>r {np.corrcoef(a[ok], e[ok])[0, 1]:.2f} · avg error {c.kfmt((a[ok] - e[ok]).abs().mean() * u)} {un}/month "
                        f"· avg actual {c.kfmt(a[ok].mean() * u)} · band = expected {c.kfmt(lo_q * u)} to +{c.kfmt(hi_q * u)}</div>", unsafe_allow_html=True)
