"""Look of the SnD apps (Hardmine/Fundamental/SnD/Dashboard/theme.py): strict light theme, navy pills, glass sidebar,
white cards. .streamlit/config.toml pins base="light"."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea {
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, 'Segoe UI', sans-serif !important; -webkit-font-smoothing: antialiased; }
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
[data-testid="stHeader"] { background: transparent !important; height: 2.6rem !important; min-height: 0 !important; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; letter-spacing: -.01em; }
body, .main { color: #1a1a2e; }
.block-container { padding-top: 2.9rem; max-width: 1500px; }

/* Radio as pill / segmented control */
div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688 !important; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }

button[kind="pills"], button[kind="segmented_control"] {
    background: #ffffff !important; border: 1px solid #dfe3ee !important; border-radius: 999px !important; min-height: 26px !important; padding: 1px 11px !important; }
button[kind="pills"] p, button[kind="segmented_control"] p { color: #3a4466 !important; font-size: 11.5px !important; }
button[kind="pills"]:hover, button[kind="segmented_control"]:hover { border-color: #9db3e6 !important; }
button[kind="pillsActive"], button[kind="segmented_controlActive"] {
    background: #0a2463 !important; border: 1px solid #0a2463 !important; border-radius: 999px !important; min-height: 26px !important; padding: 1px 11px !important; }
button[kind="pillsActive"] p, button[kind="segmented_controlActive"] p { color: #ffffff !important; font-size: 11.5px !important; }

[data-baseweb="popover"] [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="popover"] [data-baseweb="menu"] li, [data-baseweb="popover"] [data-baseweb="menu"] li * { color: #1a1a2e !important; }
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; color: #1a1a2e !important; border-color: #e3e7f0 !important; }
[data-baseweb="tag"] { background: #0a2463 !important; }
[data-baseweb="tag"] span, [data-baseweb="tag"] div { color: #ffffff !important; }
[data-baseweb="tag"] svg { fill: #ffffff !important; }
[data-testid="stWidgetLabel"] p { font-size: 10.5px !important; font-weight: 700; color: #0a2463 !important; text-transform: uppercase; letter-spacing: .09em; }

/* Pill tabs */
.stTabs, .stTabs > div, .stTabs [data-baseweb="tab-list"] { overflow: visible !important; }
.stTabs [data-baseweb="tab-list"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; width: fit-content; max-width: 100%; flex-wrap: wrap; margin: 0 0 2px; }
.stTabs [data-baseweb="tab"] { border-radius: 999px; padding: 3px 14px; height: auto; min-height: 0; background: transparent; }
.stTabs [data-baseweb="tab"] p { font-size: 13px !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 6px !important; }
.stTabs [aria-selected="true"] { background: #0a2463 !important; color: #ffffff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: .55rem; }

/* Glass sidebar */
[data-testid="stSidebar"] { width: 240px !important; min-width: 240px !important; max-width: 240px !important;
  background: linear-gradient(160deg, rgba(246,248,253,.92) 0%, rgba(233,238,248,.88) 55%, rgba(240,236,246,.9) 100%) !important;
  -webkit-backdrop-filter: blur(24px) saturate(160%); backdrop-filter: blur(24px) saturate(160%);
  border-right: 1px solid rgba(255,255,255,.75) !important; box-shadow: inset -1px 0 0 rgba(10,36,99,.06), 6px 0 28px rgba(10,36,99,.06); }
[data-testid="stSidebarUserContent"] { padding-top: 1rem !important; }
.sb-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.45rem; font-weight: 800; letter-spacing: -.02em; color: #0a2463 !important; line-height: 1.15; margin-bottom: 4px; }
.sb-sub { font-size: 11px; color: #5a6688; margin-bottom: 8px; }
.sb-label, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
    font-size: 10.5px !important; font-weight: 700; color: #0a2463 !important; text-transform: uppercase; letter-spacing: .11em; margin: 10px 0 6px; }
.sb-sep { border-top: 1px solid rgba(10,36,99,.08); box-shadow: 0 1px 0 rgba(255,255,255,.8); margin: 14px 0 10px; }
.sb-foot { font-size: 10.5px; color: #8a94a8; line-height: 1.5; }
[data-testid="stSidebar"] div[role="radiogroup"] { background: rgba(255,255,255,.55) !important; border: 1px solid rgba(255,255,255,.85);
  box-shadow: 0 1px 2px rgba(10,36,99,.05), inset 0 1px 0 rgba(255,255,255,.9); }
[data-testid="stSidebar"] div[role="radiogroup"] label:not(:has(input:checked)):hover { background: rgba(10,36,99,.06) !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) { background: linear-gradient(180deg, #13307a, #0a2463) !important;
  box-shadow: 0 2px 8px rgba(10,36,99,.28), inset 0 1px 0 rgba(255,255,255,.18); }
.st-key-section div[role="radiogroup"] { background: none !important; border: 0 !important; box-shadow: none !important; padding: 0 !important;
  display: flex !important; flex-direction: column; gap: 2px; width: 100%; }
.st-key-section div[role="radiogroup"] label { border-radius: 9px !important; padding: 6px 12px !important; width: 100%; }
.st-key-section div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 13px !important; }

/* Page text and cards */
.page-title { color: #0a2463 !important; font-weight: 700; font-size: 1.15rem; margin: 0 0 14px 0; letter-spacing: -.01em; }
.chart-head { color: #0a2463; font-weight: 700; font-size: 1.02rem; margin-bottom: 3px; letter-spacing: -.005em; }
.card-desc { color: #2b3452; font-size: .9rem; margin-top: 0; margin-bottom: 8px; line-height: 1.45; }
.card-desc b { color: #0a2463; }
[data-testid="stMain"] [data-baseweb="select"], [data-testid="stMain"] [data-testid="stSelectbox"] > div { background: transparent !important; box-shadow: none !important; }
/* Glass dropdowns (main area): frosted pill, soft navy glow on hover / focus, frosted menu */
[data-testid="stMain"] [data-baseweb="select"] > div {
  background: linear-gradient(180deg, rgba(255,255,255,.78), rgba(238,242,250,.62)) !important;
  -webkit-backdrop-filter: blur(14px) saturate(170%); backdrop-filter: blur(14px) saturate(170%);
  border: 1px solid rgba(255,255,255,.9) !important; border-radius: 999px !important; min-height: 34px;
  box-shadow: 0 1px 2px rgba(10,36,99,.06), 0 6px 18px rgba(10,36,99,.08), inset 0 1px 0 rgba(255,255,255,.95);
  transition: box-shadow .18s, transform .18s; padding-left: 6px; }
[data-testid="stMain"] [data-baseweb="select"] > div:hover {
  box-shadow: 0 0 0 3px rgba(10,36,99,.07), 0 8px 22px rgba(10,36,99,.14), inset 0 1px 0 rgba(255,255,255,.95); transform: translateY(-1px); }
[data-testid="stMain"] [data-baseweb="select"] > div:focus-within { box-shadow: 0 0 0 3px rgba(123,30,58,.16), 0 8px 22px rgba(10,36,99,.14) !important; }
[data-testid="stMain"] [data-baseweb="select"] div[value], [data-testid="stMain"] [data-baseweb="select"] span { color: #0a2463 !important; font-weight: 600; font-size: 13px; }
[data-testid="stMain"] [data-baseweb="select"] svg { fill: #7b1e3a !important; }
[data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul {
  background: rgba(255,255,255,.82) !important; -webkit-backdrop-filter: blur(18px) saturate(170%); backdrop-filter: blur(18px) saturate(170%);
  border: 1px solid rgba(255,255,255,.9) !important; border-radius: 14px !important; box-shadow: 0 14px 40px rgba(10,36,99,.18) !important; }
[data-baseweb="popover"] li[aria-selected="true"] { background: rgba(123,30,58,.10) !important; }
[data-baseweb="popover"] li:hover { background: rgba(10,36,99,.06) !important; }
/* Sub-tabs: wine, so they read apart from the navy option switches */
[class*="st-key-subtab_"] div[role="radiogroup"] { background: #f6eef1; border: 1px solid #ead7de; padding: 4px; margin-bottom: 4px; }
[class*="st-key-subtab_"] div[role="radiogroup"] label { padding: 5px 16px !important; }
[class*="st-key-subtab_"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 13px !important; color: #6b2a3f !important; }
[class*="st-key-subtab_"] div[role="radiogroup"] label:has(input:checked) { background: #7b1e3a !important; box-shadow: 0 2px 6px rgba(123,30,58,.25); }
[class*="st-key-subtab_"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
.grp { margin: 18px 0 4px; padding: 0 0 6px 12px; border-left: 4px solid #b08d57; }
.grp span { display: block; color: #0a2463; font-size: 1.08rem; font-weight: 700; letter-spacing: .01em; }
.grp em { display: block; color: #3a4466; font-size: .86rem; font-style: normal; margin-top: 1px; }
.note { color: #3a4466; font-size: 13px; line-height: 1.5; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff; border: 1px solid #e3e7f0 !important; border-radius: 14px; box-shadow: 0 1px 3px rgba(10,36,99,0.06); }

       border-top: 3px solid #0a2463; }

/* Compact tables */
.tw { overflow-x: auto; }
table.st { border-collapse: collapse; font-size: 12px; width: 100%; background: #ffffff; }
table.st th { background: #0a2463; color: #ffffff; font-weight: 600; padding: 6px 9px; text-align: right; white-space: nowrap; font-size: 11px;
              border-bottom: 2px solid #b08d57; }
table.st th.l { text-align: left; border-radius: 8px 0 0 0; }
table.st th:last-child { border-radius: 0 8px 0 0; }
table.st td { padding: 4px 9px; border-bottom: 1px solid #f1f3f8; text-align: right; white-space: nowrap; color: #1a1a2e; }
table.st td.lbl { text-align: left; color: #3a4466; font-weight: 500; }
table.st td.l { text-align: left; }
table.st td.up { color: #1f8a5c; } table.st td.dn { color: #c0392b; }
table.st td.mut { color: #8a94a8; }
table.st td.fill { color: #2a8c8c; font-style: italic; background: #f1f8f7; }
table.st td.b { font-weight: 700; }
table.st td.s3 { background: #dfe8f7; } table.st td.s2 { background: #edf2fb; } table.st td.s1 { background: #f7f9fd; }
table.st tr.tot td { background: #eef1f8; font-weight: 700; color: #0a2463; border-top: 1px solid #e3e7f0; }
/* Forecast: last in the sidebar, glowing */
@keyframes fc-glow { 0%, 100% { box-shadow: 0 0 0 1px rgba(42,140,140,.35), 0 0 10px rgba(42,140,140,.25); }
                     50% { box-shadow: 0 0 0 1px rgba(42,140,140,.6), 0 0 18px rgba(42,140,140,.45); } }
.st-key-section div[role="radiogroup"] label:last-child { margin-top: 8px !important; background: rgba(42,140,140,.08) !important;
  animation: fc-glow 2.6s ease-in-out infinite; }
.st-key-section div[role="radiogroup"] label:last-child p { color: #0f5e5e !important; font-weight: 700 !important; }
.st-key-glow_certs { box-shadow: 0 0 0 1px rgba(42,140,140,.45), 0 0 26px rgba(42,140,140,.22) !important; border-radius: 12px; }
.kc-badge { display: inline-block; background: #fff7e8; border: 1px solid #e8cf9f; color: #6b4e16; font-size: 12.5px; border-radius: 999px;
  padding: 4px 12px; margin: -6px 0 12px; }
.kc-badge b { color: #0a2463; }
.sec-bar { text-align: center; text-transform: uppercase; letter-spacing: .22em; font-size: 12.5px; font-weight: 700; color: #0a2463;
  margin: 22px 0 10px; padding: 9px 0; border-radius: 10px; border: 1px solid rgba(255,255,255,.9);
  background: linear-gradient(90deg, rgba(214,232,245,0) 0%, rgba(200,226,242,.85) 30%, rgba(222,240,248,.95) 50%, rgba(200,226,242,.85) 70%, rgba(214,232,245,0) 100%);
  box-shadow: 0 2px 14px rgba(120,170,210,.15), inset 0 1px 0 rgba(255,255,255,.9); }
.page-title .asof { float: right; font-size: 11.5px; font-weight: 600; color: #3a5596; background: rgba(200,226,242,.55);
  border: 1px solid rgba(255,255,255,.9); border-radius: 999px; padding: 3px 10px; letter-spacing: 0; }
.st-key-section div[role="radiogroup"] label:last-child { position: relative; margin-top: 30px !important; }
.st-key-section div[role="radiogroup"] label:last-child::before { content: "OUTPUT"; position: absolute; top: -20px; left: 2px;
  font-size: 10.5px; font-weight: 700; letter-spacing: .18em; color: #6b7391; }
.st-key-unit { margin-top: -6px; }
.explain { margin: 6px 0 2px; padding: 16px 18px; border-radius: 14px; border: 1px solid rgba(255,255,255,.9);
  background: linear-gradient(135deg, #eaf4fb 0%, #e4f3f1 45%, #f1eefb 100%); box-shadow: 0 6px 24px rgba(10,36,99,.08), inset 0 1px 0 #fff; }
.explain .ex-t { text-align: center; text-transform: uppercase; letter-spacing: .2em; font-size: 12px; font-weight: 700; color: #0a2463; margin-bottom: 12px; }
.explain .ex-g { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; }
.explain .ex-s { background: rgba(255,255,255,.62); border: 1px solid rgba(255,255,255,.95); border-radius: 11px; padding: 11px 13px;
  font-size: 13px; line-height: 1.5; color: #2b3452; }
.explain .ex-s > b:first-of-type { display: block; color: #0a2463; font-size: 13.5px; margin-bottom: 3px; }
.explain .ex-s span { display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 50%;
  background: linear-gradient(135deg, #2a8c8c, #3a5596); color: #fff; font-size: 11px; font-weight: 700; margin-bottom: 6px; }
.explain .ex-s b { color: #0f5e5e; }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 7px; vertical-align: middle; }
.dot.g { background: #2e9e5b; box-shadow: 0 0 6px rgba(46,158,91,.55); }
.dot.a { background: #e0a23a; box-shadow: 0 0 6px rgba(224,162,58,.5); }
.dot.r { background: #d1495b; box-shadow: 0 0 6px rgba(209,73,91,.5); }
.explain .ex-f { text-align: center; color: #0a2463; font-size: 13.5px; font-weight: 600; margin-bottom: 12px; }
.page-title { margin-bottom: 0 !important; }
.page-title .asof { float: none !important; margin-left: 12px; vertical-align: middle; }
.st-key-btn_method button, .st-key-btn_back button { border-radius: 999px !important; font-size: 12px !important; font-weight: 700 !important;
  letter-spacing: .12em; text-transform: uppercase; color: #0a2463 !important; border: 1px solid rgba(255,255,255,.95) !important;
  background: linear-gradient(135deg, #e4f0fa, #e2f3f0) !important; box-shadow: 0 2px 12px rgba(10,36,99,.12); min-height: 34px; }
.st-key-btn_method button:hover, .st-key-btn_back button:hover { background: linear-gradient(135deg, #0a2463, #2a8c8c) !important; color: #fff !important; }
.st-key-btn_method button p, .st-key-btn_back button p { font-size: 12px !important; font-weight: 700 !important; color: inherit !important; }
.mt-note { color: #6b7391; font-size: 12.5px; text-align: center; margin-top: 2px; }
.st-key-glow_method { box-shadow: 0 0 0 1px rgba(42,140,140,.45), 0 0 26px rgba(42,140,140,.22) !important; border-radius: 12px; }
.fl { display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 6px 0; margin: 10px 0; }
.fl-node { min-width: 130px; max-width: 190px; text-align: center; padding: 10px 14px; border-radius: 12px; background: #fff;
  border: 1px solid #dfe3ee; box-shadow: 0 2px 10px rgba(10,36,99,.06); }
.fl-node b { display: block; color: #0a2463; font-size: 13.5px; }
.fl-node em { display: block; color: #6b7391; font-size: 11.5px; font-style: normal; margin-top: 2px; }
.fl-node.src { background: linear-gradient(135deg, #eef4fb, #f4f7fc); }
.fl-node.out { background: linear-gradient(135deg, #e2f3f0, #e4f0fa); border-color: rgba(42,140,140,.5); box-shadow: 0 0 14px rgba(42,140,140,.18); }
.fl-node.out b { color: #0f5e5e; }
.fl-arrow { position: relative; width: 120px; height: 2px; background: linear-gradient(90deg, #b9c3de, #2a8c8c); margin: 0 4px; }
.fl-arrow::after { content: ""; position: absolute; right: -2px; top: -5px; border: 6px solid transparent; border-left: 8px solid #2a8c8c; border-right: 0; }
.fl-arrow span { position: absolute; left: 50%; transform: translate(-50%, -125%); white-space: nowrap; font-size: 11.5px; font-weight: 600;
  color: #0f5e5e; background: #fafafa; padding: 0 4px; }
.fl-gap { flex-basis: 100%; height: 6px; }
.mt-step { color: #0a2463; font-weight: 700; font-size: 1.02rem; display: flex; align-items: center; gap: 9px; }
.mt-step span { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%;
  background: linear-gradient(135deg, #2a8c8c, #3a5596); color: #fff; font-size: 12px; }
.mt-what { color: #3a4466; font-size: 13.5px; margin: 4px 0 2px 33px; }
.mt-how { color: #2b3452; font-size: 13.5px; line-height: 1.6; margin: 4px 0 0 14px; }
.mt-how b { color: #0a2463; }
@media (max-width: 700px) { .fl-arrow { width: 60px; } }
.st-key-glow_method { padding: 26px 18px !important; }
.st-key-glow_method .fl { margin: 18px 0; gap: 10px 0; }
.st-key-glow_method .fl-node { min-width: 150px; padding: 14px 18px; }
.st-key-glow_method .fl-node b { font-size: 14.5px; }
.st-key-glow_method .fl-arrow { width: 140px; }
[class*="st-key-mt_step"] { padding: 18px 16px !important; }
[class*="st-key-mt_step"] .fl { margin: 16px 0; }
.bk { margin: 4px 0 2px; border-radius: 14px; overflow: hidden; border: 1px solid rgba(255,255,255,.95);
  background: linear-gradient(135deg, #f3f8fd 0%, #eef7f5 55%, #f5f2fb 100%); box-shadow: 0 6px 24px rgba(10,36,99,.08); }
.bk-h { padding: 11px 16px; color: #0a2463; font-size: 14.5px; background: linear-gradient(90deg, rgba(200,226,242,.75), rgba(222,240,248,.55), rgba(235,228,246,.6)); }
.bk-h b { font-weight: 800; color: #6a3d9a; }
.bk-h span { float: right; color: #6b7391; font-size: 12px; margin-top: 2px; }
.bk table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13.5px; }
.bk th { text-align: right; padding: 8px 12px; color: #6b7391; font-weight: 600; font-size: 11.5px; letter-spacing: .04em; text-transform: uppercase;
  border-bottom: 1px solid rgba(10,36,99,.08); }
.bk td { text-align: right; padding: 8px 12px; color: #1d2a4d; border-bottom: 1px solid rgba(10,36,99,.05); font-variant-numeric: tabular-nums; }
.bk .o { text-align: left; font-weight: 600; }
.bk td.e { font-weight: 800; color: #0a2463; }
.bk td em { font-style: normal; color: #8a5a58; font-size: 12px; margin-left: 4px; }
.bk tr.t td { font-weight: 800; color: #0a2463; background: rgba(255,255,255,.55); border-bottom: 0; }
.bk .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 8px; vertical-align: middle; }
.bk-n { padding: 8px 16px 11px; color: #6b7391; font-size: 12.5px; }
.st-key-nc_bk div[role="radiogroup"] { margin: 6px 0 2px; }
</style>
"""
