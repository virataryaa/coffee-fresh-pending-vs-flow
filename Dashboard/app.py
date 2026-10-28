import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Fresh Pending vs Flow", layout="wide", initial_sidebar_state="expanded")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import core  # noqa: E402
import theme  # noqa: E402
from views import brazil, data, method, nowcast, origin, overview, spreads  # noqa: E402

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
          "Nowcast": "Arabica Certs Forecast", "Spreads": "Spread Impact", "Data": "Data Sources"}

with st.sidebar:
    st.markdown("<div class='sb-title'>Fresh Pending<br>vs Flow</div><div class='sb-sub'>Arabica (ICE KC) grading vs origin flows</div>",
                unsafe_allow_html=True)
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Market</div>", unsafe_allow_html=True)
    st.radio("Market", list(core.MARKETS), horizontal=True, key="market", label_visibility="collapsed",
             format_func=lambda k: {"Belgium": "Antwerp", "Combined": "Both"}.get(k, k))
    st.radio("Unit", ["Bags", "Lots"], horizontal=True, key="unit", label_visibility="collapsed")
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Study</div>", unsafe_allow_html=True)
    section = st.radio("Section", list(PAGES), key="section", label_visibility="collapsed", format_func=lambda k: LABELS.get(k, k),
                       on_change=lambda: st.query_params.clear())          # leaving Methodology
    m = core.manifest()
    st.markdown(f"<div class='sb-sep'></div><div class='sb-foot'>Built {m['built']}</div>", unsafe_allow_html=True)

# Methodology: a link pinned top right; ?page=method opens it
on_method = st.query_params.get("page") == "method"
st.markdown(f"<a class='top-method{' on' if on_method else ''}' href='?page=method' target='_self'>Methodology</a>", unsafe_allow_html=True)
(method.render if on_method else PAGES[section])()
