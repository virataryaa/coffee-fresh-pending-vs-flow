"""Data: freshness of each source, report-day coverage, and the caveats that matter when reading the study."""
import streamlit as st

import core as c

NOTES = [
    ("Fresh pending", "Change in pending + passed + failed, per day."),
    ("Missing days", "A missing ICE file loses that day's passed + failed."),
    ("HS 0901.11", "TDM mixes Arabica and Robusta. Use Cecafe for Brazil."),
    ("Imports", "Booked at customs. EU transit coffee can land in another country."),
    ("US", "Consumer market: only a few % of flow gets graded."),
    ("Nicaragua", "TDM exports stop Dec-2023."),
    ("Sample", "About 38 months, seasonal. Leads capped at 0-3m."),
]


def render():
    m = c.manifest()
    c.page_title("Data", f"Built {m['built']}")
    rows = [("ICE grading report", [m["grading_first"], m["grading_last"], f"{m['grading_days']} report days"], "")]
    rows += [(s, ["", v, "TDM" if ("exports" in s or "imports" in s) else "Cecafe"], "") for s, v in m["flows_last"].items()]
    rows.append(("KC 1/2 spread", ["2015-01", m.get("spread_last", "–"), "Daily Miner"], ""))
    with st.container(border=True):
        c.head("Sources")
        c.table(["From", "Latest", "What"], rows, corner="Source")

    with st.container(border=True):
        c.head("Caveats")
        c.table(["Note"], [(k, [(v, "l")], "") for k, v in NOTES], corner="Topic", cls="wrap")
