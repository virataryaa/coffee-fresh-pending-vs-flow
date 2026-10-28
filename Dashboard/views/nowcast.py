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
    c.page_title(f"Certs Forecast · {M['where']}", "Fresh pending expected from coffee already shipped")
    nc = c.nowcast_table(mk)
    if nc.empty:
        st.info("No origin has a usable fit.")
        return
    months = [m for m in nc.columns if isinstance(m, pd.Timestamp)]
    h = st.radio("Months ahead", list(range(1, len(months) + 1)), index=len(months) - 1, horizontal=True, key="nc_h",
                 format_func=lambda k: f"{k}m ahead", label_visibility="collapsed", help="How far out to forecast")
    months = months[:h]
    cur = months[0]
    fpm = c.fp_monthly(mk)
    full = c.last_full_month()
    tot = {m: nc[m].sum(min_count=1) for m in months}
    share = c.certs_share(mk)

    pr = c.pass_rate(mk)
    passed, _ = c.graded_monthly(mk)
    org = [o for o in nc["Origin"] if o in passed]
    st.markdown("<div class='kc-badge'><b>Arabica only (ICE KC)</b> &nbsp;·&nbsp; Robusta (ICE RC, London) is not in this study</div>",
                unsafe_allow_html=True)

    # ── new certs per origin = fresh pending forecast x pass rate ──
    crow, ctot = [], {m: np.nan for m in months}
    for _, r in nc.iterrows():
        o = r["Origin"]
        rate = float(pr.get(o, pr["_all"]))
        vals = [r[m] * rate if pd.notna(r[m]) else np.nan for m in months]
        for m, v in zip(months, vals):
            if pd.notna(v):
                ctot[m] = (0.0 if pd.isna(ctot[m]) else ctot[m]) + v
        got = float(passed.loc[cur, o]) if o in passed and cur in passed.index else 0.0
        crow.append((o, [f"{rate:.0%}"] + [(f"~{c.kfmt(v * u)}", "fill") if pd.notna(v) and m in r["filled"] else
                                            (c.kfmt(v * u), "b" if m == cur else "") if pd.notna(v) else ("", "mut")
                                            for m, v in zip(months, vals)] + [c.kfmt(got * u)], ""))
    got_tot = float(passed.loc[cur, org].sum()) if cur in passed.index else 0.0
    fx = [m for m in months if pd.notna(ctot[m])]

    # ── past check: real fresh pending x the pass rate known the month before ──
    idx = pd.date_range(c.STUDY_START + pd.DateOffset(months=c.PASS_MONTHS), full, freq="MS")
    exp, used = {}, {}
    for m in idx:
        rm = c.pass_rate(mk, m - pd.DateOffset(months=1))
        fp_m = sum(fpm.loc[m, o] for o in org if o in fpm)
        exp[m] = sum(fpm.loc[m, o] * float(rm.get(o, rm["_all"])) for o in org if o in fpm)
        used[m] = exp[m] / fp_m if fp_m > 0 else float(rm["_all"])   # blended rate behind that month's estimate
    exp, used = pd.Series(exp, dtype=float), pd.Series(used, dtype=float)
    act = passed.reindex(idx)[org].sum(axis=1)
    ok = act.notna() & exp.notna()
    r_ = float(np.corrcoef(act[ok], exp[ok])[0, 1]) if ok.sum() > 3 else np.nan

    # ── certified stock level: last level x (1 - exit rate) + new certs ──
    lv = c.certs_level(mk)
    p_all = passed.sum(axis=1)
    lvf = lv[lv.index <= full]
    exits = lvf.shift(1) + p_all.reindex(lvf.index) - lvf
    xrate = (exits / lvf.shift(1)).dropna()
    er = float(xrate.iloc[-6:].mean()) if len(xrate) else 0.0
    win = (p_all.index <= full) & (p_all.index > full - pd.DateOffset(months=12))
    fit_p = passed.loc[win, org].sum().sum()
    scale = max(float(p_all[win].sum() / fit_p), 1.0) if fit_p > 0 else 1.0   # origins without a fit still add some certs
    L, path = float(lvf.iloc[-1]), {}
    for m in fx:
        L = L * (1 - er) + ctot[m] * scale
        path[m] = L
    res = []                                                 # one-month-ahead misses of the same rule, for the bands
    for m in exp.index:
        pm = m - pd.DateOffset(months=1)
        if pm in lvf.index and m in lvf.index:
            e6 = xrate[xrate.index < m].iloc[-6:].mean()
            if pd.notna(e6):
                res.append(abs(float(lvf[m] - (lvf[pm] * (1 - e6) + exp[m] * scale))))
    res = pd.Series(res, dtype=float)
    w50, w80 = (res.quantile(.5), res.quantile(.8)) if len(res) > 5 else (0.0, 0.0)

    now = float(lv.iloc[-1])

    c.bar("Certs forecast")
    with st.container(border=True, key="glow_certs"):
        c.head("Certified stock: actual and forecast", f"Next month = this month x (1 - {er:.0%} leaving) + new certs", keep=True)
        hx = lvf.index[lvf.index >= c.STUDY_START]
        fig = go.Figure()
        if path:
            px_ = [lvf.index[-1]] + list(path)
            base = np.array([float(lvf.iloc[-1])] + list(path.values()))
            h = np.sqrt(np.arange(len(px_)))                 # misses add up the further out
            for w, shade, name in [(w80, "rgba(42,140,140,.08)", "4 in 5 past misses"), (w50, "rgba(42,140,140,.18)", "1 in 2 past misses")]:
                fig.add_scatter(x=px_, y=(base + w * h) * u, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
                fig.add_scatter(x=px_, y=np.clip(base - w * h, 0, None) * u, mode="lines", line=dict(width=0), fill="tonexty",
                                fillcolor=shade, name=name, hoverinfo="skip")
        fig.add_scatter(x=hx, y=lvf[hx] * u, name="Actual", mode="lines", line=dict(color=c.NAVY, width=2.5))
        if path:
            fig.add_scatter(x=px_, y=base * u, name="Forecast", mode="lines+markers", line=dict(color=c.TEAL, width=2.5, dash="dash"),
                            marker=dict(size=7))
            fig.add_annotation(x=px_[-1], y=base[-1] * u, text=f"<b>{c.kfmt(base[-1] * u)}</b>", showarrow=False, xanchor="left", xshift=8,
                               font=dict(color=c.TEAL, size=12))
        if lv.index[-1] > full:
            fig.add_scatter(x=[lv.index[-1]], y=[now * u], name="Today", mode="markers", marker=dict(symbol="diamond", size=11, color=c.AMBER))
        c.style(fig, height=360, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "nc_level")
        st.markdown(f"<div class='note'><b>Bands:</b> we ran the same rule on every past month and noted how far off it was. "
                    f"Dark = half the misses were smaller than {c.kfmt(w50 * u)} {un}. Light = 4 in 5 were smaller than {c.kfmt(w80 * u)}. "
                    f"They widen each month ahead because misses pile up.</div>", unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left, st.container(border=True):
        c.head("New certs by origin", f"Fresh pending forecast x pass rate{D}~ = uses estimated flow", keep=True)
        rows = crow + [("Total", [f"{pr['_all']:.0%}"] + [c.kfmt(ctot[m] * u) if pd.notna(ctot[m]) else "" for m in months]
                        + [c.kfmt(got_tot * u)], "tot")]
        c.table(["Pass rate"] + [f"{m:%b-%y}" for m in months] + [f"{cur:%b} so far"], rows, corner="Origin")
    with right, st.container(border=True):
        c.head("New certs a month", "Actual passed and forecast", keep=True)
        hist = pd.date_range(full - pd.DateOffset(months=17), full, freq="MS")
        fig = go.Figure()
        fig.add_bar(x=hist, y=passed.reindex(hist)[org].sum(axis=1) * u, name="Actual", marker_color=c.NAVY, marker_line_width=0)
        fig.add_bar(x=fx, y=[ctot[m] * u for m in fx], name="Forecast", marker=dict(color="rgba(42,140,140,.25)", line=dict(color=c.TEAL, width=1.2),
                                                                                  pattern=dict(shape="/", fgcolor=c.TEAL, size=6)))
        if got_tot > 0:
            fig.add_scatter(x=[cur], y=[got_tot * u], name="So far", mode="markers", marker=dict(symbol="diamond", size=11, color=c.AMBER))
        c.style(fig, height=300, xaxis=dict(color=c.AXIS, showgrid=False, dtick="M3", tickformat="%b-%y"))
        c.show(fig, "nc_certs_fc")

    with st.container(border=True):
        c.head("Does pass rate work?", f"Real fresh pending x pass rate vs actual passed{D}rate = last {c.PASS_MONTHS} months before each month", keep=True)
        left, right = st.columns([2, 1])
        with left:
            fig = go.Figure()
            fig.add_bar(x=idx, y=act * u, name="Actual passed", marker_color=c.NAVY, marker_line_width=0)
            fig.add_scatter(x=idx, y=exp * u, name="Fresh pending x pass rate", mode="lines", line=dict(color=c.TEAL, width=2))
            fig.add_scatter(x=idx, y=used, name="Pass rate used", mode="lines", yaxis="y2", line=dict(color=c.AMBER, width=1.5, dash="dot"),
                            hovertemplate="%{y:.0%}")
            c.style(fig, height=300, y2=dict(tickformat=".0%", range=[0, 1]), xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
            c.show(fig, "nc_certs")
        with right:
            top = float(max(act[ok].max(), exp[ok].max())) * u * 1.05 if ok.any() else 1.0
            sc = go.Figure()
            sc.add_scatter(x=[0, top], y=[0, top], mode="lines", name="Perfect match", line=dict(color=c.AXIS, width=1, dash="dash"), hoverinfo="skip")
            sc.add_scatter(x=exp[ok] * u, y=act[ok] * u, mode="markers", name="Month", text=[f"{m:%b-%y}" for m in exp[ok].index],
                           marker=dict(color=c.NAVY, size=8, opacity=.8), hovertemplate="%{text}<br>Expected %{x:,.0f}<br>Actual %{y:,.0f}<extra></extra>")
            if pd.notna(r_):
                sc.add_annotation(x=0.03, y=0.97, xref="paper", yref="paper", xanchor="left", yanchor="top", showarrow=False, align="left",
                                  text=f"<b>r {r_:.2f}</b><br><b>R² {r_ ** 2:.2f}</b>", font=dict(color=c.NAVY, size=12),
                                  bgcolor="rgba(255,255,255,.85)", bordercolor="rgba(10,36,99,.15)", borderpad=4)
            c.style(sc, height=300, hovermode="closest", legend=False,
                    xaxis=dict(color=c.AXIS, showgrid=False, title=dict(text="Fresh pending x pass rate", font=dict(size=10))),
                    yaxis=dict(gridcolor=c.GRID, color=c.AXIS, title=dict(text="Actual passed", font=dict(size=10))))
            c.show(sc, "nc_certs_sc")
        if ok.sum() > 3:
            st.markdown(f"<div class='note'>r {r_:.2f}{D}R² {r_ ** 2:.2f}{D}avg miss {c.kfmt((act[ok] - exp[ok]).abs().mean() * u)} {un} a month"
                        f"{D}pass rate now {pr['_all']:.0%}</div>", unsafe_allow_html=True)

    c.bar("Fresh pending forecast")
    with st.container(border=True):
        fill_txt = f"{D}<b>~ tinted</b> uses filled flow (average of 3 methods, compared below)"
        c.head("Fresh pending by origin", f"Forecast = flow from 'lead' months earlier x conversion{D}~ = uses estimated flow", keep=True)
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

    with st.expander("Missing flow months: how each fill method changes the total"):
        rows = []
        for meth in c.FILL_METHODS + ["Average", "Off"]:
            t = nc if meth == c.DEFAULT_FILL else c.nowcast_table(mk, meth)
            vals = [t[m].sum(min_count=1) for m in months]
            label = "No fill (published flow only)" if meth == "Off" else meth
            rows.append((label, [(c.FILL_DESC[meth], "l mut")] + [c.kfmt(v * u) if pd.notna(v) else "" for v in vals],
                         "tot" if meth == "Average" else ""))
        c.table(["How"] + [f"Fcst {m:%b-%y}" for m in months], rows, corner="Method")

    with st.container(border=True):
        c.head("Fresh pending: actual vs expected from flow", "Bands = past misses", keep=True)
        view = st.radio("Group by", ["Month", "Rolling 3 months", "Quarter"], index=2, horizontal=True, key="nc_view", label_visibility="collapsed",
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
