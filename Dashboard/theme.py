"""Look of the SnD apps (Hardmine/Fundamental/SnD/Dashboard/theme.py): strict light theme, navy pills, glass sidebar,
white cards. .streamlit/config.toml pins base="light"."""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600&family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea {
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important; -webkit-font-smoothing: antialiased; }
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
.sb-title { font-family: 'Fraunces', Georgia, serif; font-size: 1.4rem; font-weight: 600; color: #0a2463 !important; line-height: 1.15; margin-bottom: 4px; }
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
.page-title { color: #0a2463 !important; font-weight: 700; font-size: 1.15rem; margin: 0 0 2px 0; letter-spacing: -.01em; }
.chart-head { color: #0a2463; font-weight: 600; font-size: .9rem; margin-bottom: 2px; letter-spacing: -.005em; }
.card-desc { color: #5a6688; font-size: .78rem; margin-top: 0; margin-bottom: 6px; line-height: 1.4; }
.note { color: #64748b; font-size: 12px; line-height: 1.5; }
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
table.st td.b { font-weight: 700; }
table.st td.s3 { background: #dfe8f7; } table.st td.s2 { background: #edf2fb; } table.st td.s1 { background: #f7f9fd; }
table.st tr.tot td { background: #eef1f8; font-weight: 700; color: #0a2463; border-top: 1px solid #e3e7f0; }
</style>
"""
