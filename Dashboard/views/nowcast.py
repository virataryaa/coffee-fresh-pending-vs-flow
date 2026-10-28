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
    c.page_title(f"Arabica Certs Forecast · {M['where']}", "Fresh pending expected from coffee already shipped")
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

    passed, _ = c.graded_monthly(mk)
    org = [o for o in nc["Origin"] if o in passed]
    pw = c.best_pass_months(mk, tuple(org))        # pass-rate window with the best past match
    pr = c.pass_rate(mk, months=pw)

    # ── new certs per origin = fresh pending forecast x pass rate ──
    crow, ctot, new_o = [], {m: np.nan for m in months}, {}
    for _, r in nc.iterrows():
        o = r["Origin"]
        rate = float(pr.get(o, pr["_all"]))
        vals = [r[m] * rate if pd.notna(r[m]) else np.nan for m in months]
        new_o[o] = dict(zip(months, vals))
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
    chk = c.pass_check(mk, tuple(org), pw)
    idx, exp, used, act = chk.index, chk["Exp"], chk["Used"], chk["Act"]
    ok = act.notna() & exp.notna()
    r_ = float(np.corrcoef(act[ok], exp[ok])[0, 1]) if ok.sum() > 3 else np.nan

    # ── certified stock level: last level x (1 - exit rate) + new certs ──
    em = c.exits_monthly(mk)
    lv = em["L"]
    lvf = lv[lv.index <= full]
    xrate = em.loc[em.index <= full, "rate"]
    p_all = passed.sum(axis=1)
    win = (p_all.index <= full) & (p_all.index > full - pd.DateOffset(months=12))
    fit_p = passed.loc[win, org].sum().sum()
    scale = max(float(p_all[win].sum() / fit_p), 1.0) if fit_p > 0 else 1.0   # origins without a fit still add some certs
    xpred, xscore = c.exit_backtest(mk)
    xm = c.EXIT_METHOD
    frac = c.month_progress(mk, cur)
    use_mtd = cur > full                                     # so far + rest at 6m: never worse than 6m alone, even on day 1
    cur_days = c.certs_daily(mk).loc[lambda d: (d.index >= cur) & (d.index <= cur + pd.offsets.MonthEnd(0))]
    fx = [m for m in fx if m > full]                        # a month already complete is history, not forecast
    rates = {}
    for m in fx:
        r6 = c.exit_rate(xrate, m, xm)
        r0 = c.mtd_rate(cur_days, float(lvf.iloc[-1]), frac, r6) if (m == cur and use_mtd) else r6
        rates[m] = r0 if pd.notna(r0) else c.exit_rate(xrate, m, "Recent 6m")
    p_sofar = float(cur_days["Passed"].sum()) if use_mtd else 0.0
    L, path, adds = float(lvf.iloc[-1]), {}, {}
    for m in fx:
        # this month: certs already passed + the forecast for the part of the month still to come
        adds[m] = p_sofar + (1 - frac) * ctot[m] * scale if (m == cur and use_mtd) else ctot[m] * scale
        L = L * (1 - rates[m]) + adds[m]
        path[m] = L
    # one-month-ahead misses of the whole rule, for the bands: fresh pending from the flow fits (so its error counts too),
    # the pass rate and 6-month leaving rate known the month before
    fits = {r["Origin"]: c.fitted(r["Origin"], r["Source"], int(r["Lag"]), mk) for _, r in nc.iterrows() if r["Origin"] in org}
    res = []
    for m in exp.index:
        pm = m - pd.DateOffset(months=1)
        if pm in lvf.index and m in lvf.index and m in xpred.index and pd.notna(xpred.loc[m, xm]):
            rm = c.pass_rate(mk, pm, pw)
            nf = sum(float(f.get(m, np.nan)) * float(rm.get(o, rm["_all"])) for o, f in fits.items())
            if pd.notna(nf):
                res.append((m, float(lvf[pm] * (1 - xpred.loc[m, xm]) + nf * scale), float(lvf[m])))
    ex_m, ex_pred, ex_act = res[-1] if res else (None, np.nan, np.nan)      # latest tested month, for the explainer
    res = pd.Series([abs(b - a) for _, a, b in res], dtype=float)
    w50, w80 = (res.quantile(.5), res.quantile(.8)) if len(res) > 5 else (0.0, 0.0)
    er = float(np.mean(list(rates.values()))) if rates else 0.0

    now = float(lv.iloc[-1])

    c.bar("Certs forecast")
    with st.container(border=True, key="glow_certs"):
        hl, hr = st.columns([3, 2], vertical_alignment="center")
        with hl:
            c.head("Certified stock: actual and forecast", "Each point = stock at month end · shaded = KC delivery months", keep=True)
        with hr:
            since = st.radio("From", ["6 months", "1 year", "3 years", "All"], index=1, horizontal=True, key="nc_from",
                             label_visibility="collapsed")
        back_m = {"6 months": 6, "1 year": 12, "3 years": 36}.get(since)
        start = full - pd.DateOffset(months=back_m - 1) if back_m else lvf.index.min()
        dtick = {"6 months": "M1", "1 year": "M1", "3 years": "M3"}.get(since, "M12")
        me = lambda ix: pd.DatetimeIndex(ix)                    # noqa: E731  each month sits on its own label; value = stock at its end
        hx = lvf.index[lvf.index >= start]
        end_m = fx[-1] if fx else full
        # one month axis for both charts: same range, same ticks, * on forecast months
        step_m = {"M1": 1, "M2": 2, "M3": 3}.get(dtick, 12)
        all_m = pd.date_range(start, end_m, freq="MS")
        tv = list(all_m[::-1][::step_m][::-1])
        def tlabel(t):                                       # past grey · this month bold violet · ahead italic teal
            if fx and t == fx[0]:
                return f"<b><span style='color:#6a3d9a'>{t:%b-%y}</span></b>"
            if t in fx:
                return f"<i><span style='color:#2a8c8c'>{t:%b-%y}</span></i>"
            return f"<span style='color:#8a94a6'>{t:%b-%y}</span>"
        tt = [tlabel(t) for t in tv]
        xax = dict(color=c.AXIS, showgrid=False, tickvals=tv, ticktext=tt, hoverformat="End of %b-%y",
                   range=[start - pd.Timedelta(days=16), end_m + pd.Timedelta(days=16)])
        fig = go.Figure()
        for y in range(start.year, end_m.year + 1):              # KC delivery months
            for mo in (3, 5, 7, 9, 12):
                m0 = pd.Timestamp(y, mo, 1)
                if start <= m0 <= end_m:
                    fig.add_vrect(x0=m0 - pd.Timedelta(days=15), x1=m0 + pd.Timedelta(days=15), fillcolor="rgba(176,141,87,.05)",
                                  line_width=0, layer="below")
        if path:
            px_ = [lvf.index[-1]] + list(path)
            base = np.array([float(lvf.iloc[-1])] + list(path.values()))
            h = np.sqrt(np.arange(len(px_)))                 # misses add up the further out
            for w, shade, name in [(w80, "rgba(42,140,140,.08)", "80% likely range"), (w50, "rgba(42,140,140,.18)", "50% likely range")]:
                fig.add_scatter(x=me(px_), y=(base + w * h) * u, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False)
                fig.add_scatter(x=me(px_), y=np.clip(base - w * h, 0, None) * u, mode="lines", line=dict(width=0), fill="tonexty",
                                fillcolor=shade, name=name, hoverinfo="skip")
        e_ = em.reindex(hx)
        fig.add_scatter(x=me(hx), y=lvf[hx] * u, name="Actual", mode="lines", line=dict(color=c.NAVY, width=2.5),
                        customdata=np.c_[e_["L0"], e_["P"], e_["X"]] * u,
                        hovertemplate="Actual, month end %{y:,.0f}<br>start %{customdata[0]:,.0f} + passed %{customdata[1]:,.0f}"
                                      " - left %{customdata[2]:,.0f}<extra></extra>")
        if path:
            cd_ = [[np.nan] * 3] + [[base[i], adds[m], base[i] * rates[m]] for i, m in enumerate(path)]
            fig.add_scatter(x=me(px_), y=base * u, name="Forecast", mode="lines+markers", line=dict(color=c.TEAL, width=2.5, dash="dash"),
                            marker=dict(size=7), customdata=np.array(cd_, dtype=float) * u,
                            hovertemplate="Forecast, month end %{y:,.0f}<br>start %{customdata[0]:,.0f} + new %{customdata[1]:,.0f}"
                                          " - leaving %{customdata[2]:,.0f}<extra></extra>")
            fig.add_annotation(x=me([px_[-1]])[0], y=base[-1] * u, text=f"<b>{c.kfmt(base[-1] * u)}</b>", showarrow=False, xanchor="left", xshift=8,
                               font=dict(color=c.TEAL, size=12))
        if lv.index[-1] > full:
            today = c.certs_daily(mk).index.max()
            fig.add_scatter(x=[cur], y=[now * u], name="Today", mode="markers", marker=dict(symbol="diamond", size=11, color=c.AMBER),
                            hovertemplate=f"Today ({today:%d-%b}) %{{y:,.0f}}<extra></extra>")
        c.style(fig, height=380, xaxis=xax)
        c.show(fig, "nc_level")

        # ── by origin: stock per origin (ICE report); each origin leaves at half its own 6-month pace, half the market's,
        #    scaled so the total leaving matches the main forecast ──
        g = c.port_daily(mk)
        g = g[g["Date"] <= full + pd.offsets.MonthEnd(0)]
        mon = g["Date"].dt.to_period("M").dt.to_timestamp()
        is_last = g.groupby(mon)["Date"].transform("max") == g["Date"]
        so = g[is_last].groupby([mon[is_last], "Origin"])["Certs"].sum().unstack().fillna(0.0)
        po = g.groupby([mon, "Origin"])["Passed"].sum().unstack().reindex(so.index).fillna(0.0)
        if not so.empty and path:
            top = list(so.iloc[-1].sort_values(ascending=False).index[:4])
            grp = lambda df: df[top].assign(Rest=df.drop(columns=top).sum(axis=1))   # noqa: E731
            Lo, Po = grp(so), grp(po)
            Xo = Lo.shift(1) + Po - Lo
            l6, x6 = Lo.shift(1).iloc[-6:].sum(), Xo.iloc[-6:].sum()
            own = (x6 / l6.where(l6 > 0)).clip(0, 1)
            S = Lo.iloc[-1].astype(float).to_dict()
            fc_o = {k_: [] for k_ in S}
            det = {}                                             # month -> origin -> (start, fresh pending, pass rate, new, leave %, left, end)
            for m in path:
                add = {o: (float(passed.loc[cur, o]) if (m == cur and use_mtd and o in passed) else 0.0)
                       + (1 - frac if (m == cur and use_mtd) else 1.0) * float(new_o.get(o, {}).get(m, 0.0) or 0.0) for o in top}
                add["Rest"] = max(adds[m] - sum(add.values()), 0.0)
                ro = {k_: (own[k_] + rates[m]) / 2 if S[k_] >= 2000 and pd.notna(own.get(k_)) else rates[m] for k_ in S}
                tot_left = sum(S[k_] for k_ in S) * rates[m]
                raw = sum(S[k_] * ro[k_] for k_ in S)
                kk = tot_left / raw if raw > 0 else 1.0
                det[m] = {}
                for k_ in S:
                    s0, lr = S[k_], min(ro[k_] * kk, 1.0)
                    S[k_] = s0 * (1 - lr) + add[k_]
                    fc_o[k_].append(S[k_])
                    fp_ = float(nc.set_index("Origin").get(m, pd.Series(dtype=float)).get(k_, np.nan)) if k_ != "Rest" else np.nan
                    det[m][k_] = (s0, fp_, float(pr.get(k_, pr["_all"])) if k_ != "Rest" else np.nan, add[k_], lr, s0 * lr, S[k_])
            hist_o = Lo[Lo.index >= start]
            line_c = ["#2b4c8c", "#2a9d8f", "#e0a43a", "#c8553d", "#9aa5b8"]   # distinct hues: navy, teal, amber, terracotta, grey
            rgb = lambda h_, a_: "rgba({},{},{},{})".format(*(int(h_[j:j + 2], 16) for j in (1, 3, 5)), a_)   # noqa: E731
            fm = list(path)
            fig = go.Figure()
            for i, k_ in enumerate(hist_o.columns):            # history: light areas, bold line on each origin's edge
                fig.add_scatter(x=me(hist_o.index), y=hist_o[k_] * u, name=k_, mode="lines", stackgroup="o", legendgroup=k_,
                                line=dict(width=2, color=line_c[i]), fillcolor=rgb(line_c[i], .32),
                                hovertemplate=f"{k_} %{{y:,.0f}}<extra></extra>")
            kf = lambda v: c.kfmt(v * u) if pd.notna(v) else "–"   # noqa: E731

            def card(m):
                """Breakdown card for a forecast month: one row per origin, subtle heat on new certs, leaving and the change."""
                d_ = det[m]
                mx_new = max([v[3] for v in d_.values()] + [1.0])
                mx_lr = max([v[4] for v in d_.values()] + [1e-9])
                rows_ = ""
                for i_, (k2, (s0, fp_, pr_, nw, lr, lf, e1)) in enumerate(d_.items()):
                    ch = e1 / s0 - 1 if s0 > 0 else np.nan
                    chc = "#2e8b57" if ch >= 0 else "#b0413e"
                    rows_ += (f"<tr><td class='o'><span class='dot' style='background:{line_c[i_]}'></span>{k2}</td>"
                              f"<td>{kf(s0)}</td><td>{kf(fp_)}</td>"
                              f"<td>{f'{pr_:.0%}' if pd.notna(pr_) else '–'}</td>"
                              f"<td style='background:rgba(46,139,87,{.05 + .25 * nw / mx_new:.2f})'>+{kf(nw)}</td>"
                              f"<td style='background:rgba(176,65,62,{.05 + .22 * lr / mx_lr:.2f})'>−{kf(lf)} <em>{lr:.0%}</em></td>"
                              f"<td class='e'>{kf(e1)}</td>"
                              f"<td style='color:{chc}'>{'▲' if ch >= 0 else '▼'} {abs(ch):.0%}</td></tr>")
                t0, tn, tl, te = (sum(v[j] for v in d_.values()) for j in (0, 3, 5, 6))
                tch = te / t0 - 1 if t0 > 0 else np.nan
                rows_ += (f"<tr class='t'><td class='o'>Total</td><td>{kf(t0)}</td><td></td><td></td><td>+{kf(tn)}</td><td>−{kf(tl)}</td>"
                          f"<td class='e'>{kf(te)}</td><td style='color:{'#2e8b57' if tch >= 0 else '#b0413e'}'>"
                          f"{'▲' if tch >= 0 else '▼'} {abs(tch):.0%}</td></tr>")
                note = (f"<div class='bk-n'>{m:%b} new certs = passed so far + forecast for the rest of the month ({1 - frac:.0%} to go)</div>"
                        if m == cur and use_mtd else "")
                return (f"<div class='bk'><div class='bk-h'><b>{m:%b-%y}</b> forecast<span>stock at month end · {un}</span></div>"
                        "<table><thead><tr><th class='o'>Origin</th><th>Start</th><th>Fresh pending</th><th>Pass</th><th>+ New certs</th>"
                        f"<th>− Leaving</th><th>= End</th><th>Change</th></tr></thead><tbody>{rows_}</tbody></table>{note}</div>")

            for i, k_ in enumerate(hist_o.columns):            # forecast: stacked bars, one shade
                fig.add_bar(x=me(fm), y=np.array(fc_o[k_]) * u, name=k_, showlegend=False, legendgroup=k_, width=18 * 86400000,
                            marker=dict(color=rgb(line_c[i], .8), line=dict(color="#ffffff", width=1)),
                            hovertemplate=f"{k_} %{{y:,.0f}} (forecast)<extra></extra>")
            tot_x = [hist_o.index[-1]] + fm if len(hist_o) else fm
            tot_y = ([float(hist_o.iloc[-1].sum())] if len(hist_o) else []) + [sum(fc_o[k_][j] for k_ in fc_o) for j in range(len(fm))]
            fig.add_scatter(x=me(tot_x), y=np.array(tot_y) * u, name="Total", mode="lines+markers+text", line=dict(color=c.NAVY, width=2, dash="dot"),
                            marker=dict(size=6, color=c.NAVY), text=[""] + [c.kfmt(v * u) for v in tot_y[1:]], textposition="top center",
                            textfont=dict(size=10, color=c.NAVY), hovertemplate="Total %{y:,.0f}<extra></extra>")
            st.markdown(f"<div class='chart-head' style='margin-top:6px'>By origin</div><div class='card-desc'>Month end</div>",
                        unsafe_allow_html=True)
            c.style(fig, height=320, barmode="stack", xaxis=xax, hovermode="closest")
            c.show(fig, "nc_level_o")
            if fm:
                pick = st.radio("Breakdown for", fm, horizontal=True, key="nc_bk", label_visibility="collapsed",
                                format_func=lambda m: f"{m:%b-%y}" + (" · this month" if m == fm[0] else ""))
                st.markdown(card(pick), unsafe_allow_html=True)
            st.session_state[f"origin_rates_{mk}"] = {k_: (float(own[k_]) if pd.notna(own.get(k_)) else None) for k_ in Lo.columns}
        if path and ex_m is not None:
            k = lambda v: f"{c.kfmt(v * u)}"                 # noqa: E731
            n_ = len(px_) - 1
            lo1, hi1 = base[-1] - w50 * np.sqrt(n_), base[-1] + w50 * np.sqrt(n_)
            lo2, hi2 = max(base[-1] - w80 * np.sqrt(n_), 0), base[-1] + w80 * np.sqrt(n_)
            # shown on the Methodology page (Bands), with this market's numbers
            st.session_state[f"band_html_{mk}"] = (f"""<div class='explain'><div class='ex-f'>Forecast: next month = this month x (1 - share leaving) + new certs</div><div class='ex-g'>
<div class='ex-s'><span>1</span><b>Test the rule on the past</b>We pretend it is the start of each past month and forecast its end.
In {ex_m:%b-%y} the rule said <b>{k(ex_pred)}</b>, the real number was <b>{k(ex_act)}</b>: off by <b>{k(abs(ex_act - ex_pred))}</b>.</div>
<div class='ex-s'><span>2</span><b>Line up all the misses</b>We did this for {len(res)} months. Half missed by less than <b>{k(w50)}</b>: that is the
<b>50% range</b> (dark). 4 in 5 missed by less than <b>{k(w80)}</b>: that is the <b>80% range</b> (light).</div>
<div class='ex-s'><span>3</span><b>Further out, wider</b>Each month adds its own miss, so the band grows: about {k(w50)} one month out,
{k(w50 * np.sqrt(2))} two months out, {k(w50 * np.sqrt(n_))} at {n_} months.</div>
<div class='ex-s'><span>4</span><b>How to read it</b>For {px_[-1]:%b-%y} the forecast is <b>{k(base[-1])}</b>. 50% chance it lands between <b>{k(lo1)} and {k(hi1)}</b>,
80% chance between <b>{k(lo2)} and {k(hi2)}</b>.</div></div></div>""")

    with st.container(border=True):
        c.head("Certs leaving", f"Left = last month's stock + passed - this month's stock{D}shown as % of last month's stock", keep=True)
        left, right = st.columns([2, 1])
        with left:
            h0 = full - pd.DateOffset(months=35)
            hx2 = xrate.index[xrate.index >= h0]
            fig = go.Figure()
            fig.add_bar(x=hx2, y=xrate[hx2], name="Actual", marker_color=c.NAVY, marker_line_width=0)
            for meth, name, col, dash in [(xm, f"{xm} (used ahead)", c.TEAL, "solid"),
                                          ("This month so far", f"This month: so far + rest at 6m ({frac:.0%} in)", c.RED, "solid"),
                                          ("Seasonal", "Seasonal", c.AMBER, "dot")]:
                fig.add_scatter(x=hx2, y=xpred[meth].reindex(hx2), name=name, mode="lines+markers" if meth == "This month so far" else "lines",
                                line=dict(color=col, width=2, dash=dash), marker=dict(size=5),
                                visible=True if meth == "This month so far" else "legendonly")   # others: click the legend to show
            if rates:
                fig.add_bar(x=list(rates), y=list(rates.values()), name="Forecast", marker=dict(color="rgba(42,140,140,.25)",
                            line=dict(color=c.TEAL, width=1.2), pattern=dict(shape="/", fgcolor=c.TEAL, size=6)))
            c.style(fig, height=280, fmt=".0%", yaxis=dict(gridcolor=c.GRID, color=c.AXIS, tickformat=".0%"),
                    xaxis=dict(color=c.AXIS, showgrid=False, dtick="M3", tickformat="%b-%y"))
            c.show(fig, "nc_exit")
        with right:
            sc_ = xscore.sort_values("miss")
            win_ = [xm] + (["This month so far"] if use_mtd else [])
            fig = go.Figure()
            fig.add_bar(y=["This month:<br>so far + rest at 6m" if m_ == "This month so far" else m_ for m_ in sc_.index],
                        x=sc_["miss"] * u, orientation="h", marker_line_width=0,
                        marker_color=[c.TEAL if m_ in win_ else "#c9d2e6" for m_ in sc_.index],
                        text=[f"{c.kfmt(v * u)}" for v in sc_["miss"]], textposition="outside",
                        customdata=sc_["r"], hovertemplate="%{y}<br>avg miss %{x:,.0f}<br>r %{customdata:.2f}<extra></extra>")
            c.style(fig, height=280, legend=False, yaxis=dict(autorange="reversed", color=c.AXIS, tickfont=dict(size=10)),
                    xaxis=dict(color=c.AXIS, showgrid=False, range=[0, float(sc_["miss"].max()) * u * 1.18],
                               title=dict(text=f"Avg miss a month ({un}), smaller = better", font=dict(size=10))))
            st.markdown("<div class='chart-head' style='text-align:center'>Method comparison</div>", unsafe_allow_html=True)
            c.show(fig, "nc_exit_sc")
        with st.expander("How certs leaving works", expanded=False):
            k = lambda v: f"{c.kfmt(v * u)}"                 # noqa: E731
            lm = em.loc[full]
            last6 = xrate.iloc[-6:]
            sc_t = xscore["miss"]
            mtd_txt = ""
            if use_mtd and not cur_days.empty:
                x_so_far = float(lvf.iloc[-1] + cur_days["Passed"].sum() - cur_days["Certs"].iloc[-1])
                so_ = x_so_far / float(lvf.iloc[-1])
                r6_ = c.exit_rate(xrate, cur, xm)
                mtd_txt = (f"<div class='ex-s'><span>3</span><b>This month: what left + the rest at normal pace</b>{cur:%b} started at "
                           f"<b>{k(lvf.iloc[-1])}</b>. So far <b>{k(x_so_far)}</b> has left (<b>{so_:.0%}</b>) with {frac:.0%} of the month done. "
                           f"The other {1 - frac:.0%} of the month is assumed at the 6-month pace: {so_:.0%} + {1 - frac:.0%} x {r6_:.0%} = "
                           f"<b>{rates.get(cur, np.nan):.0%}</b>. On day 1 this is about the 6-month pace; it firms up as the month goes.</div>")
            st.markdown(f"""<div class='explain'><div class='ex-f'>Certs leaving = last month's stock + passed - this month's stock</div><div class='ex-g'>
<div class='ex-s'><span>1</span><b>Measure what left</b>{full:%b-%y} started at <b>{k(lm['L0'])}</b>, <b>{k(lm['P'])}</b> passed grading and it ended at
<b>{k(lm['L'])}</b>. So <b>{k(lm['X'])}</b> left: <b>{lm['rate']:.0%}</b> of the stock.</div>
<div class='ex-s'><span>2</span><b>Next months: last 6 months' average</b>{' · '.join(f"{m:%b} {v:.0%}" for m, v in last6.items())}.
Average <b>{last6.mean():.0%}</b> a month, used for every month after this one.</div>
{mtd_txt}
<div class='ex-s'><span>{4 if mtd_txt else 3}</span><b>Why this way</b>We tested every month since {c.EXIT_TEST_FROM:%Y} ({int(xscore['n'].max())} months).
Avg miss: recent 6m <b>{k(sc_t['Recent 6m'])}</b>, seasonal {k(sc_t['Seasonal'])}, blend {k(sc_t['Blend'])},
this month (so far + rest at 6m) <b>{k(sc_t['This month so far'])}</b>. Simplest that works wins.</div></div></div>""", unsafe_allow_html=True)

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
        c.head("Does pass rate work?", f"Real fresh pending x pass rate vs actual passed{D}rate = last {pw} months before each month", keep=True)
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
        sc_ = c.pass_window_scores(mk, tuple(org))
        fig = go.Figure()
        fig.add_bar(x=sc_["months"], y=sc_["r"], marker_color=[c.TEAL if n == pw else "#c9d2e6" for n in sc_["months"]], marker_line_width=0,
                    text=[f"{v:.2f}" for v in sc_["r"]], textposition="outside", customdata=sc_["miss"] * u,
                    hovertemplate="%{x}-month pass rate<br>r %{y:.2f}<br>avg miss %{customdata:,.0f}<extra></extra>", name="r")
        lo_r = float(sc_["r"].min())
        c.style(fig, height=230, legend=False, fmt=".2f", xaxis=dict(color=c.AXIS, showgrid=False, dtick=1, title=dict(text="Pass rate over the last N months", font=dict(size=10))),
                yaxis=dict(gridcolor=c.GRID, color=c.AXIS, range=[max(lo_r - .05, 0), 1], title=dict(text="Correlation (r)", font=dict(size=10))))
        st.markdown(f"<div class='chart-head' style='margin-top:6px'>Which pass-rate window predicts best?</div><div class='card-desc'>"
                    f"Same check for every window{D}highest bar = used: <b>{pw} months</b></div>", unsafe_allow_html=True)
        c.show(fig, "nc_pw")
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
