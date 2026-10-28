"""Methodology: how the certs forecast is built, step by step, with block diagrams."""
import streamlit as st

import core as c


def node(title, sub="", kind=""):
    return f"<div class='fl-node {kind}'><b>{title}</b>{f'<em>{sub}</em>' if sub else ''}</div>"


def arrow(op=""):
    return f"<div class='fl-arrow'>{f'<span>{op}</span>' if op else ''}</div>"


def flow(*parts):
    st.markdown("<div class='fl'>" + "".join(parts) + "</div>", unsafe_allow_html=True)


def step(n, title, what, how, diagram):
    with st.container(border=True):
        st.markdown(f"<div class='mt-step'><span>{n}</span>{title}</div><div class='mt-what'>{what}</div>", unsafe_allow_html=True)
        diagram()
        st.markdown("<ul class='mt-how'>" + "".join(f"<li>{h}</li>" for h in how) + "</ul>", unsafe_allow_html=True)


def render():
    c.page_title("Methodology")

    c.bar("The whole idea")
    with st.container(border=True, key="glow_method"):
        flow(node("Coffee shipped", "origin exports, imports, Cecafe", "src"), arrow("weeks at sea"),
             node("Fresh pending", "new coffee sent to grading"), arrow("x pass rate"),
             node("New certs", "coffee that passes"), arrow("+ add"),
             node("Certified stock", "next month", "out"))
        flow(node("Certified stock", "this month", "src"), arrow("x (1 - share leaving)"), node("Stock that stays"), arrow("+ new certs"),
             node("Certified stock", "next month", "out"))
        st.markdown("<div class='mt-what' style='text-align:center'>Coffee shipped today shows up at grading a month or two later. "
                    "Part of it passes and becomes certs. Every month part of the stock leaves. Repeat month by month.</div>",
                    unsafe_allow_html=True)

    c.bar("Step by step")
    step(1, "Fresh pending", "How much new coffee is sent to ICE grading each month.",
         ["<b>Measured</b> from the daily ICE report: change in pending + passed + failed, per origin and port.",
          "<b>Matched to flows</b>: for each origin we try every flow source (origin exports, Belgian / US imports, Cecafe) and a lead "
          "of 0 to 3 months, and keep the one that moves most like fresh pending (highest correlation). A lead of 1+ months wins "
          "if it is nearly as good, because only a lead lets us see ahead.",
          "<b>Conversion</b> = fresh pending / flow over the past: the share of shipped coffee that turns up at grading.",
          "<b>Forecast</b> = flow from 'lead' months ago x conversion.",
          "<b>Flow not published yet?</b> Filled with the average of three guesses: same month last year x this year's pace, "
          "last month repeated, last 3 months' average. These cells show with a ~."],
         lambda: flow(node("Flow", "lead months ago", "src"), arrow("x conversion"), node("Fresh pending", "per origin"),
                      arrow("sum"), node("Fresh pending", "all origins", "out")))

    step(2, "Pass rate", "The share of graded coffee that passes.",
         ["<b>Pass rate</b> = passed / (passed + failed), per origin.",
          "<b>Window</b>: we test averages over the last 1 to 12 months and use the one that predicted best in the past "
          "(6 months for Antwerp).",
          "Origins graded too little to trust (under 3,000 bags) use the market-wide rate."],
         lambda: flow(node("Passed", "last N months", "src"), arrow("/"), node("Passed + failed", "last N months", "src"),
                      arrow("="), node("Pass rate", "per origin", "out")))

    step(3, "New certs", "How much coffee will become certified each month.",
         ["<b>New certs</b> = fresh pending forecast x pass rate, per origin, then summed.",
          "Origins with no reliable flow match still add some certs, so the total is scaled up by their past share."],
         lambda: flow(node("Fresh pending", "forecast", "src"), arrow("x pass rate"), node("New certs", "per origin"),
                      arrow("sum + small origins"), node("New certs", "all", "out")))

    step(4, "Certs leaving", "How much of the stock goes out each month (decerts, deliveries, transfers).",
         ["<b>Measured</b>: last month's stock + passed - this month's stock. Shown as a % of last month's stock.",
          "<b>Next months</b>: average of the last 6 months. Tested since 2016 against 3-month, seasonal and blended versions: "
          "it is as good as any and the simplest.",
          "<b>This month</b>: what has already left so far, scaled to a full month (left so far / share of month done). "
          "This is about 4x more accurate than any average."],
         lambda: flow(node("Left so far", "this month", "src"), arrow("/ share of month done"), node("Leaving", "this month", "out"),
                      "<div class='fl-gap'></div>", node("Last 6 months", "% leaving", "src"), arrow("average"),
                      node("Leaving", "next months", "out")))

    step(5, "Certified stock", "Where the stock ends each month.",
         ["<b>Next month</b> = this month x (1 - share leaving) + new certs.",
          "Starts from the last full month's stock and rolls forward one month at a time."],
         lambda: flow(node("Stock", "this month", "src"), arrow("x (1 - leaving)"), node("Stays"), arrow("+ new certs"),
                      node("Stock", "next month", "out"), arrow("repeat"), node("Stock", "4 months ahead", "out")))

    step(6, "Bands", "How sure we are.",
         ["We run the same rule on every past month and note how far off it was.",
          "<b>50% range</b>: half the past misses were smaller. <b>80% range</b>: 4 in 5 were smaller.",
          "Further ahead the band widens (x square root of months ahead) because misses pile up."],
         lambda: flow(node("Past forecasts", "vs what happened", "src"), arrow("misses"), node("Middle 50%", "and 80%"),
                      arrow("x &radic;months ahead"), node("Bands", "around the forecast", "out")))

    c.bar("Data")
    with st.container(border=True):
        c.table(["What", "Used for"], [
            ("Daily Miner (ICE grading report)", ["Pending, passed, failed, certs by origin and port", "fresh pending, pass rate"], ""),
            ("Daily Miner (LSEG certs, from 2010)", ["Certified stock and passed by port", "certs leaving, stock"], ""),
            ("TDM Pro", ["Origin exports, Belgian and US imports", "flow"], ""),
            ("Cecafe Daily", ["Brazil exports by destination", "flow"], ""),
        ], corner="Source")
        st.markdown("<div class='note'>Arabica (ICE KC) only. US = Houston, Miami, New Orleans, New York (no Virginia in the LSEG history).</div>",
                    unsafe_allow_html=True)
