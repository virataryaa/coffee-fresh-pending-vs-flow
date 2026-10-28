import sys
import time
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Certs Forecast", layout="wide", initial_sidebar_state="expanded")
sys.path.insert(0, str(Path(__file__).resolve().parent))



def _load():
    """Import the app's own modules. Streamlit Cloud reloads them when a push lands; a session importing at that moment gets a
    KeyError from importlib, so drop the half-loaded modules and try again instead of showing an error page."""
    for attempt in range(5):
        try:
            import core, theme  # noqa: E401
            from views import brazil, data, method, nowcast, origin, overview, spreads
            return core, theme, brazil, data, method, nowcast, origin, overview, spreads
        except KeyError:
            for k in [k for k in sys.modules if k in ("core", "theme", "views") or k.startswith("views.")]:
                sys.modules.pop(k, None)
            time.sleep(0.3 * (attempt + 1))
    raise RuntimeError("App modules failed to load, refresh the page")


core, theme, brazil, data, method, nowcast, origin, overview, spreads = _load()

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
    st.markdown("<div class='sb-title'>Certs<br>Forecast</div><div class='sb-sub'>Arabica (ICE KC) · from fresh pending and flows</div>",
                unsafe_allow_html=True)
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Market</div>", unsafe_allow_html=True)
    st.radio("Market", list(core.MARKETS), horizontal=True, key="market", label_visibility="collapsed",
             format_func=lambda k: {"Belgium": "Antwerp", "Combined": "Both"}.get(k, k))
    st.radio("Unit", ["Bags", "Lots"], horizontal=True, key="unit", label_visibility="collapsed")
    st.markdown("<div class='sb-sep'></div><div class='sb-label'>Study</div>", unsafe_allow_html=True)
    section = st.radio("Section", list(PAGES), index=list(PAGES).index("Nowcast"), key="section", label_visibility="collapsed", format_func=lambda k: LABELS.get(k, k),
                       on_change=lambda: st.session_state.update(method=False))   # leaving Methodology
    m = core.manifest()
    st.markdown(f"<div class='sb-sep'></div><div class='sb-foot'>Built {m['built']}</div>", unsafe_allow_html=True)

(method.render if st.session_state.get("method") else PAGES[section])()   # Methodology: button in each page's title row
