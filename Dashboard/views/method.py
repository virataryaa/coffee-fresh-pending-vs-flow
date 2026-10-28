"""Methodology: how the certs forecast is built, as block diagrams with one real worked example (current market, top origin)."""
import numpy as np
import pandas as pd
import streamlit as st

import core as c


def node(title, sub="", kind=""):
    return f"<div class='fl-node {kind}'><b>{title}</b>{f'<em>{sub}</em>' if sub else ''}</div>"


def arrow(op=""):
    return f"<div class='fl-arrow'>{f'<span>{op}</span>' if op else ''}</div>"


def flow(*parts):
    st.markdown("<div class='fl'>" + "".join(parts) + "</div>", unsafe_allow_html=True)


def step(n, title, line, diagram, note=""):
    with st.container(border=True):
        st.markdown(f"<div class='mt-step'><span>{n}</span>{title}</div><div class='mt-what'>{line}</div>", unsafe_allow_html=True)
        flow(*diagram)
        if note:
            st.markdown(f"<div class='mt-note'>{note}</div>", unsafe_allow_html=True)


def render():
    c.page_title("Methodology", back=True)
    mk = c.market()
    M = c.MARKETS[mk]
    u, un = c.unit_factor(), c.unit_name()
    k = lambda v: f"{c.kfmt(v * u)}"                          # noqa: E731

    c.bar("The idea")
    with st.container(border=True, key="glow_method"):
        flow(node("Coffee shipped", "exports, imports", "src"), arrow("1-3 months later"), node("Fresh pending", "sent to grading"),
             arrow("x pass rate"), node("New certs", "coffee that passed"), arrow("+ to stock"), node("Certified stock", "", "out"))
        flow(node("Stock", "start of month", "src"), arrow("- certs leaving"), arrow("+ new certs"), node("Stock", "end of month", "out"))

    # ── real numbers: first forecast month, the biggest origin ──
    nc = c.nowcast_table(mk)
    if nc.empty:
        st.info("No origin has a usable fit for this market.")
        return
    months = [m for m in nc.columns if isinstance(m, pd.Timestamp)]
    cur = months[0]
    passed, failed = c.graded_monthly(mk)
    org = [o for o in nc["Origin"] if o in passed]
    pw = c.best_pass_months(mk, tuple(org))
    pr = c.pass_rate(mk, months=pw)
    r = nc.iloc[0]
    o, lag, conv = r["Origin"], int(r["Lag"]), float(r["Conv"])
    fm = cur - pd.DateOffset(months=lag)
    fp = float(r[cur])
    flow_v = fp / conv if conv else np.nan
    full = c.last_full_month()
    win = (passed.index <= full) & (passed.index > full - pd.DateOffset(months=pw))
    po, fo = float(passed.loc[win, o].sum()), float(failed.loc[win, o].sum())
    rate_o = float(pr.get(o, pr["_all"]))
    new_o = fp * rate_o
    new_all = sum(float(x[cur]) * float(pr.get(x["Origin"], pr["_all"])) for _, x in nc.iterrows() if pd.notna(x[cur]))
    p_all = passed.sum(axis=1)
    w12 = (p_all.index <= full) & (p_all.index > full - pd.DateOffset(months=12))
    fit_p = passed.loc[w12, org].sum().sum()
    scale = max(float(p_all[w12].sum() / fit_p), 1.0) if fit_p > 0 else 1.0
    em = c.exits_monthly(mk)
    l0 = float(em.loc[full, "L"])
    days = c.certs_daily(mk).loc[lambda d: d.index >= cur]
    frac = c.month_progress(mk)
    left = float(l0 + days["Passed"].sum() - days["Certs"].iloc[-1]) if not days.empty else np.nan
    lrate = c.mtd_rate(days, l0, frac)
    xr = em.loc[em.index <= full, "rate"]
    if pd.isna(lrate):
        lrate = c.exit_rate(xr, cur, c.EXIT_METHOD)
    end = l0 * (1 - lrate) + new_all * scale

    c.bar(f"Worked example · {o} at {M['where']} · {cur:%b-%y}")
    step(1, "Fresh pending: what arrives at grading",
         f"{o}'s fresh pending follows <b>{r['Source']}</b> from <b>{lag} month{'s' if lag != 1 else ''} earlier</b>. "
         f"In the past, <b>{conv:.0%}</b> of that flow turned up at grading.",
         [node(k(flow_v), f"{r['Source']} {fm:%b-%y}", "src"), arrow(f"x {conv:.0%}"), node(k(fp), f"fresh pending {cur:%b-%y}", "out")],
         "Flow and lead are picked per origin: the source and lead (0-3 months) that matched fresh pending best in the past."
         + (" Flow not out yet is filled with an average of recent and seasonal values." if cur in r["filled"] else ""))
    step(2, "Pass rate: how much passes",
         f"Last <b>{pw} months</b>, {o} passed <b>{k(po)}</b> of <b>{k(po + fo)}</b> graded.",
         [node(k(po), "passed", "src"), arrow("/"), node(k(po + fo), "graded", "src"), arrow("="), node(f"{rate_o:.0%}", "pass rate", "out")],
         f"{pw} months is the window that predicted best in the past (tested 1 to 12).")
    step(3, "New certs",
         f"{o}: fresh pending x pass rate. Then add up every origin.",
         [node(k(fp), "fresh pending", "src"), arrow(f"x {rate_o:.0%}"), node(k(new_o), f"{o} new certs"),
          arrow("all origins"), node(k(new_all * scale), "new certs, total", "out")],
         f"Origins with no good flow match still add a little, so the total is scaled up x{scale:.2f}.")
    step(4, "Certs leaving",
         f"{cur:%b} started at <b>{k(l0)}</b>. So far <b>{k(left)}</b> has left with <b>{frac:.0%}</b> of the month done.",
         [node(f"{left / l0:.0%}", "left so far", "src"), arrow(f"/ {frac:.0%} done"), node(f"{lrate:.0%}", "leaving, full month", "out")],
         f"Left = start stock + passed - stock now. For later months: the last 6 months' average, {c.exit_rate(xr, cur, c.EXIT_METHOD):.0%}.")
    step(5, "Certified stock",
         f"Start, take away what leaves, add new certs.",
         [node(k(l0), f"stock end {full:%b}", "src"), arrow(f"x (1 - {lrate:.0%})"), node(k(l0 * (1 - lrate)), "stays"),
          arrow(f"+ {k(new_all * scale)}"), node(k(end), f"stock end {cur:%b}", "out")],
         "Then the same again for each next month, using the 6-month leaving rate.")
    step(6, "Bands",
         "We ran this same rule on every past month and noted the misses.",
         [node("Past misses", "forecast vs actual", "src"), arrow("middle 50% / 80%"), node("Band", "1 month out"),
          arrow("x &radic;months ahead"), node("Band", "further out", "out")],
         "Half the past misses fit in the dark band, 4 in 5 in the light one. Further out it widens, because misses add up.")

    st.markdown(f"<div class='note'>Data: ICE grading and LSEG certs (Daily Miner), origin exports and imports (TDM Pro), Brazil exports "
                f"(Cecafe). Arabica (ICE KC) only. Numbers in {un}.</div>", unsafe_allow_html=True)
