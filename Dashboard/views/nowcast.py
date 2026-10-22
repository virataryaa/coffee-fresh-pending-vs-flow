"""Forecast: flows already shipped imply the fresh pending still to come. Per-origin estimate, total, and the in-sample fit."""
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
    c.page_title(f"Forecast · {M['where']}", "Fresh pending expected from coffee already shipped")
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
        c.head("By origin", f"Sorted by share of certs{D}Forecast = flow from 'lead' months earlier x conversion{fill_txt}")
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
        c.table(["Certs share", "Source", "Lead", "r", "Conversion"] + [f"Fcst {m:%b-%y}" for m in months] + [f"MTD {cur:%b}"], rows, corner="Origin")
        st.markdown(f"<div class='note'>Weak fit = r below {c.MIN_R:.1f}, not used for forecasts.</div>", unsafe_allow_html=True)

    with st.container(border=True):
        c.head("Fill methods compared", f"Total forecast under each way of filling unpublished flow months{D}<b>Average</b> is what the tables use")
        rows = []
        for meth in c.FILL_METHODS + ["Average", "Off"]:
            t = nc if meth == c.DEFAULT_FILL else c.nowcast_table(mk, meth)
            vals = [t[m].sum(min_count=1) for m in months]
            label = "No fill (published flow only)" if meth == "Off" else meth
            rows.append((label, [(c.FILL_DESC[meth], "l mut")] + [c.kfmt(v * u) if pd.notna(v) else "" for v in vals],
                         "tot" if meth == "Average" else ""))
        c.table(["How"] + [f"Fcst {m:%b-%y}" for m in months], rows, corner="Method")

    with st.container(border=True):
        c.head("Fit history", f"<b>Bars</b> actual{D}<b>Line</b> expected from flow{D}<b>Hatched</b> forecast ahead{D}<b>Diamond</b> so far this period"
                              f"{D}<b>Dark band</b> 1 in 4 past periods landed inside it{D}<b>Light band</b> 1 in 2 did")
        view = st.radio("Group by", ["Month", "Rolling 3 months", "Quarter"], horizontal=True, key="nc_view",
                        help="Grouping smooths out coffee that is graded a few weeks earlier or later than expected")
        fits = [c.fitted(r["Origin"], r["Source"], int(r["Lag"]), mk).rename(r["Origin"]) for _, r in nc.iterrows()]
        idx = pd.date_range(c.STUDY_START, max(months), freq="MS")
        F = pd.concat(fits, axis=1).reindex(idx)
        act = fpm[nc["Origin"]].sum(axis=1).reindex(idx)
        est = F.sum(axis=1, min_count=1)
        for m in months:                                     # months ahead: the table's estimates (incl. filled flow)
            est[m] = tot[m]
        done = pd.Series(idx <= full, index=idx)
        blend = act.where(done, est)                          # actual where the month is over, estimate after
        so_far = act.where(done, 0.0)                         # actual graded so far (current month = month to date)
        so_far[cur] = act[cur]
        if view == "Month":
            A, E, B, SF, ok_done = act, est, blend, so_far, done
            fmt, dt, per = "%b-%y", "M2", "month"
        elif view == "Rolling 3 months":
            A, E, B, SF = (x.rolling(3).sum() for x in (act, est, blend, so_far))
            ok_done = done.rolling(3).min().fillna(0).astype(bool)
            fmt, dt, per = "%b-%y", "M2", "3 months"
        else:
            q = idx.to_period("Q")
            full_q = pd.Series(1, index=idx).groupby(q).count() == 3
            g = lambda x: x.groupby(q).sum(min_count=1)       # noqa: E731
            A, E, B, SF = g(act), g(est), g(blend), g(so_far)
            ok_done = done.groupby(q).all()
            keep = full_q | ok_done                           # drop a trailing quarter the estimates only partly cover
            A, E, B, SF, ok_done = (x[keep] for x in (A, E, B, SF, ok_done))
            A.index = E.index = B.index = SF.index = ok_done.index = A.index.to_timestamp()
            fmt, dt, per = "Q%q-%y", "M3", "quarter"
        x = E.index
        res = (A[ok_done] - E[ok_done]).dropna()             # past misses: actual - expected
        w25, w50 = (res.abs().quantile(.25), res.abs().quantile(.5)) if len(res) > 5 else (0.0, 0.0)
        fig = go.Figure()
        for w, shade, name in [(w50, "rgba(42,140,140,.07)", f"±{c.kfmt(w50 * u)}"), (w25, "rgba(42,140,140,.17)", f"±{c.kfmt(w25 * u)}")]:
            fig.add_scatter(x=x, y=(E + w) * u, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
            fig.add_scatter(x=x, y=(E - w).clip(lower=0) * u, mode="lines", line=dict(width=0), fill="tonexty",
                            fillcolor=shade, name=name, hoverinfo="skip")
        fig.add_bar(x=x[ok_done.values], y=A[ok_done] * u, name="Actual", marker_color=c.NAVY, marker_line_width=0)
        fig.add_bar(x=x[~ok_done.values], y=B[~ok_done] * u, name="Forecast", marker=dict(color="rgba(42,140,140,.25)", line=dict(color=c.TEAL, width=1.2),
                                                                                          pattern=dict(shape="/", fgcolor=c.TEAL, size=6)))
        cur_x = [p_ for p_ in x[~ok_done.values] if SF.get(p_, 0) > 0][:1]
        if cur_x:
            fig.add_scatter(x=cur_x, y=[SF[cur_x[0]] * u], name="So far", mode="markers", marker=dict(symbol="diamond", size=11, color=c.AMBER))
        fig.add_scatter(x=x, y=E * u, name="Expected from flow", mode="lines", line=dict(color=c.TEAL, width=2))
        c.style(fig, height=360, xaxis=dict(color=c.AXIS, showgrid=False, dtick=dt, tickformat=fmt))
        c.show(fig, "nc_hist")
        a, e = A[ok_done], E[ok_done]
        ok = a.notna() & e.notna()
        if ok.sum() > 3:
            st.markdown(f"<div class='note'>r {np.corrcoef(a[ok], e[ok])[0, 1]:.2f} · avg miss {c.kfmt((a[ok] - e[ok]).abs().mean() * u)} {un} per {per} "
                        f"· avg actual {c.kfmt(a[ok].mean() * u)} · dark band ±{c.kfmt(w25 * u)} · light band ±{c.kfmt(w50 * u)}</div>", unsafe_allow_html=True)
