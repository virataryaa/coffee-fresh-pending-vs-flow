"""Data: how fresh each source is. Caveats live in README.md."""
import pandas as pd
import streamlit as st

import core as c


def render():
    m = c.manifest()
    c.page_title("Data", f"Built {m['built']}")
    rows = [("ICE grading report", [m["grading_first"], m["grading_last"], f"{m['grading_days']} report days"], "")]
    rows += [(s, ["", v, "TDM" if ("exports" in s or "imports" in s) else "Cecafe"], "") for s, v in m["flows_last"].items()]
    rows.append(("KC 1/2 spread", ["2015-01", m.get("spread_last", "–"), "Daily Miner"], ""))
    # freshness dot: green = most recent source, red = oldest, amber = in between
    when = {i: pd.to_datetime(r[1][1], errors="coerce") for i, r in enumerate(rows)}
    ok = [t for t in when.values() if pd.notna(t)]
    hi, lo = (max(ok), min(ok)) if ok else (None, None)
    for i, (lbl, cells, rc) in enumerate(rows):
        t = when[i]
        dot = "" if pd.isna(t) else "g" if t == hi else "r" if t == lo else "a"
        cells[1] = (f"<span class='dot {dot}'></span>{cells[1]}" if dot else cells[1], "")
    with st.container(border=True):
        c.head("Sources", "<span class='dot g'></span>most recent &nbsp; <span class='dot a'></span>older &nbsp; <span class='dot r'></span>oldest", keep=True)
        c.table(["From", "Latest", "What"], rows, corner="Source")
