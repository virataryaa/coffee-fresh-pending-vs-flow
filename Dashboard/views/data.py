"""Data: freshness of each source, report-day coverage, and the caveats that matter when reading the study."""
import plotly.graph_objects as go
import streamlit as st

import core as c

NOTES = [
    ("Fresh pending", "Change in Pending + Passed + Failed, per origin, from the ICE daily certified-stock report (Daily Miner kc_grading.parquet). "
                      "Coffee presented for grading that day. Small negatives happen when lots are withdrawn from the queue."),
    ("Missing report days", "When a daily ICE file is missing, that day's Passed and Failed are lost, so fresh pending for the month is understated. "
                            "The coverage chart shows report days found / business days; Aug-Nov 2023 and Oct-Nov 2025 have gaps."),
    ("HS 0901.11 mixes Arabica and Robusta", "TDM green coffee is not split by species. Fine for the Central and South American milds; "
                                             "Uganda, India, Tanzania and Brazil (TDM) include Robusta, so their conversion looks low. For Brazil use Cecafe Arabica."),
    ("Origin exports vs Belgian imports", "Exports are dated at loading and lead grading by transit + queue time. Belgian imports are dated at "
                                          "customs clearance; coffee shipped via Rotterdam or Hamburg and trucked in can be booked to another EU country, "
                                          "which is why some origins fit badly on Belgian imports."),
    ("Nicaragua", "Nicaragua's own export data in TDM stops at Dec-2023, so it can only use Belgian imports."),
    ("Short sample", "About 38 complete months since Aug-2023. Both series are seasonal, so part of every correlation is shared seasonality; "
                     "the auto fit only looks at leads of 0-3 months to avoid matching one season to the next."),
]


def render():
    m = c.manifest()
    c.page_title("Data & method", f"Database built {m['built']} by Code/build_db.py from the local Daily Miner, TDM Pro and Cecafe Daily projects.")
    rows = [("ICE grading report", [m["grading_first"], m["grading_last"], f"{m['grading_days']} report days"], "")]
    rows += [(s, ["", v, c.SOURCE_DESC.get(s, "Cecafe, all destinations: denominator for Belgium's share")], "") for s, v in m["flows_last"].items()]
    rows.append(("KC 1/2 spread", ["2015-01", m.get("spread_last", "–"), "Daily Miner price link: Rollex active 1/2 spread, C1-C2 fallback (c/lb)"], ""))
    with st.container(border=True):
        c.head("Sources")
        c.table(["From", "Latest", "What"], rows, corner="Source")
    with st.container(border=True):
        c.head("Report-day coverage at Antwerp", "Days with an ICE report / business days in the month.")
        cov = c.coverage(c.PORT)
        fig = go.Figure(go.Bar(x=cov.index, y=cov * 100, marker_color=[c.NAVY if v >= .8 else c.AMBER if v >= .5 else c.RED for v in cov],
                               marker_line_width=0, hovertemplate="%{x|%b-%y}: %{y:.0f}%<extra></extra>"))
        c.style(fig, height=230, legend=False, fmt=".0f", yaxis=dict(range=[0, 105], ticksuffix="%", gridcolor=c.GRID, color=c.AXIS),
                xaxis=dict(color=c.AXIS, showgrid=False, dtick="M2", tickformat="%b-%y"))
        c.show(fig, "dt_cov")
    with st.container(border=True):
        c.head("Read before trusting a number")
        c.table(["Note"], [(k, [(v, "l")], "") for k, v in NOTES], corner="Topic", cls="wrap")
