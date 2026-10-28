"""Methodology: how the certs forecast is built, step by step, as block diagrams."""
import streamlit as st

import core as c


def node(title, sub="", kind=""):
    return f"<div class='fl-node {kind}'><b>{title}</b>{f'<em>{sub}</em>' if sub else ''}</div>"


def arrow(op=""):
    return f"<div class='fl-arrow'>{f'<span>{op}</span>' if op else ''}</div>"


def flow(*parts):
    st.markdown("<div class='fl'>" + "".join(parts) + "</div>", unsafe_allow_html=True)


def step(n, title, line, diagram, how):
    with st.container(border=True, key=f"mt_step{n}"):
        st.markdown(f"<div class='mt-step'><span>{n}</span>{title}</div><div class='mt-what'>{line}</div>", unsafe_allow_html=True)
        flow(*diagram)
        st.markdown("<ul class='mt-how'>" + "".join(f"<li>{h}</li>" for h in how) + "</ul>", unsafe_allow_html=True)


def render():
    c.page_title("Methodology", back=True)

    c.bar("Methodology")
    with st.container(border=True, key="glow_method"):
        flow(node("Coffee shipped", "exports, imports", "src"), arrow("0-3 months later"), node("Fresh pending", "sent to grading"),
             arrow("x pass rate"), node("New certs", "coffee that passed"), arrow("+ to stock"), node("Certified stock", "", "out"))
        flow(node("Stock", "start of month", "src"), arrow("- certs leaving"), arrow("+ new certs"), node("Stock", "end of month", "out"))

    c.bar("Step by step")
    step(1, "Fresh pending", "New coffee sent to ICE grading each month.",
         [node("Flow", "lead months earlier", "src"), arrow("x conversion"), node("Fresh pending", "per origin"),
          arrow("add up"), node("Fresh pending", "all origins", "out")],
         ["<b>Measured</b> from the daily ICE report: change in pending + passed + failed.",
          "<b>Matched</b> per origin to the flow (exports, imports or Cecafe) and lead (0-3 months) that moved most like it in the past.",
          "<b>Conversion</b> = the share of that flow that turned up at grading in the past.",
          "<b>Flow not out yet</b> is filled with an average of recent and seasonal values (shown with ~)."])
    step(2, "Pass rate", "The share of graded coffee that passes.",
         [node("Passed", "last N months", "src"), arrow("/"), node("Graded", "last N months", "src"), arrow("="),
          node("Pass rate", "per origin", "out")],
         ["<b>N</b> is the window (1-12 months) that predicted best in the past.",
          "Origins graded too little to trust use the market-wide rate."])
    step(3, "New certs", "Coffee that will become certified.",
         [node("Fresh pending", "forecast", "src"), arrow("x pass rate"), node("New certs", "per origin"),
          arrow("add up"), node("New certs", "all origins", "out")],
         ["Origins with no good flow match still add a little, so the total is scaled up by their past share."])
    step(4, "Certs leaving", "Stock that goes out each month.",
         [node("Left so far", "this month", "src"), arrow("+ rest of month at 6m pace"), node("Leaving", "this month", "out"),
          "<div class='fl-gap'></div>",
          node("Last 6 months", "% leaving", "src"), arrow("average"), node("Leaving", "later months", "out")],
         ["<b>Measured</b>: start stock + passed - end stock, as a % of start stock.",
          "<b>This month</b>: what has left so far + the rest of the month at the 6-month pace. Day 1 is about the 6-month pace; it firms up daily.",
          "<b>Later months</b>: the last 6 months' average. Tested since 2016 against 3-month, seasonal and blended: as good and simplest."])
    step(5, "Certified stock", "Rolled forward one month at a time.",
         [node("Stock", "this month", "src"), arrow("x (1 - leaving)"), node("Stays"), arrow("+ new certs"),
          node("Stock", "next month", "out"), arrow("repeat"), node("Stock", "months ahead", "out")],
         ["Starts from the last full month's stock."])
    step(6, "Bands", "How sure we are.",
         [node("Past forecasts", "vs what happened", "src"), arrow("misses"), node("50% / 80%", "of past misses"),
          arrow("x &radic;months ahead"), node("Bands", "around the forecast", "out")],
         ["The same rule is run on every past month and the misses noted.",
          "Half the misses fit in the dark band, 4 in 5 in the light one. It widens further out because misses add up."])
    band = st.session_state.get(f"band_html_{c.market()}")
    with st.container(border=True):
        st.markdown(f"<div class='mt-step'><span>&#9679;</span>How the bands work: {c.MARKETS[c.market()]['where']}, real numbers</div>",
                    unsafe_allow_html=True)
        st.markdown(band or "<div class='mt-what'>Open Arabica Certs Forecast once for this market to see its numbers here.</div>",
                    unsafe_allow_html=True)

    st.markdown("<div class='note'>Data: ICE grading and LSEG certs (Daily Miner), origin exports and imports (TDM Pro), Brazil exports "
                "(Cecafe). Arabica (ICE KC) only.</div>", unsafe_allow_html=True)
