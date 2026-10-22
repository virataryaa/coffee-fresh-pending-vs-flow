"""Data: how fresh each source is. Caveats live in README.md."""
import streamlit as st

import core as c


def render():
    m = c.manifest()
    c.page_title("Data", f"Built {m['built']}")
    rows = [("ICE grading report", [m["grading_first"], m["grading_last"], f"{m['grading_days']} report days"], "")]
    rows += [(s, ["", v, "TDM" if ("exports" in s or "imports" in s) else "Cecafe"], "") for s, v in m["flows_last"].items()]
    rows.append(("KC 1/2 spread", ["2015-01", m.get("spread_last", "–"), "Daily Miner"], ""))
    with st.container(border=True):
        c.head("Sources")
        c.table(["From", "Latest", "What"], rows, corner="Source")
