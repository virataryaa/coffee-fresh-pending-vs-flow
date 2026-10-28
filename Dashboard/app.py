import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Fresh Pending vs Flow", layout="wide", initial_sidebar_state="expanded")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402
import theme  # noqa: E402
from views import brazil, data, nowcast, origin, overview, spreads  # noqa: E402

st.markdown(theme.CSS, unsafe_allow_html=True)


@st.cache_resource
def _data_state() -> dict:
    return {}


# Cached frames survive a redeploy: drop them whenever a Database file changes, else new code meets old data.
_ver = tuple(sorted((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in core.DB.glob("*.*")))
if _data_state().get("ver") != _ver:
    st.cache_data.clear()
    _data_state()["ver"] = _ver

PAGES = {"Overview": overview.render, "Origin Study": origin.render, "Brazil": brazil.render,
         "Spreads": spreads.render, "Data": data.render, "Nowcast": nowcast.render}   # Forecast last, glowing (theme.py)
LABELS = {"Overview": "Grading Overview", "Origin Study": "Origin Deep Dive", "Brazil": "Brazil Focus",
          "Nowcast": "Certs Forecast", "Spreads": "Spread Impact", "Data": "Data Sources"}

with st.sidebar:
    st.markdown("<div class='sb-title'>Fresh Pending<br>vs Flow</div><div class='sb-sub'>KC grading vs origin flows</div>",
                unsafe_allow_html=True)
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Section</div>", unsafe_allow_html=True)
    section = st.radio("Section", list(PAGES), key="section", label_visibility="collapsed", format_func=lambda k: LABELS.get(k, k))
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Market</div>", unsafe_allow_html=True)
    st.radio("Market", list(core.MARKETS), horizontal=True, key="market", label_visibility="collapsed",
             format_func=lambda k: {"Combined": "BE + US"}.get(k, k))
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Unit</div>", unsafe_allow_html=True)
    st.radio("Unit", ["Bags", "Lots"], horizontal=True, key="unit", label_visibility="collapsed")
    m = core.manifest()
    st.markdown(f"<div class='sb-sep'></div><div class='sb-foot'>ICE report {m['grading_last']}<br>Built {m['built']}</div>", unsafe_allow_html=True)

PAGES[section]()
