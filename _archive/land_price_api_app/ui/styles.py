"""
ui/styles.py
アプリ全体のカスタム CSS を定数として管理する。
Streamlit の st.markdown(DARK_THEME_CSS, unsafe_allow_html=True) で注入する。
"""

DARK_THEME_CSS = """
<style>
/* ── ベース ── */
.stApp {
    background-color: #0d1b2a;
    color: #e2e8f0;
}

/* ── サイドバー非表示 ── */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: none !important;
}

/* ── タブバー ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #132035;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    color: #b8d0e8;
    border-radius: 7px;
    padding: 6px 18px;
    font-size: 0.92rem;
    font-weight: 500;
    background: transparent;
    border: none;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #e8f4ff;
    background-color: #1a2e47;
}
.stTabs [aria-selected="true"] {
    color: #e8f4ff !important;
    background-color: #1e3a5a !important;
    border-bottom: 3px solid #4fc3f7 !important;
}

/* ── メトリクスカード ── */
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #132035 0%, #1a2e4a 100%);
    border: 1px solid #243d5e;
    border-radius: 12px;
    padding: 14px 18px;
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    color: #b8d0e8 !important;
    font-size: 0.82rem;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #e8f4ff;
    font-size: 1.5rem;
    font-weight: 700;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] svg {
    display: none;
}

/* ── ヘッダー ── */
h1, h2, h3 {
    color: #c8dff0;
}

/* ── ボタン ── */
.stButton > button {
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #1565c0, #0d47a1);
    border: none;
    color: #fff;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(90deg, #1976d2, #1565c0);
    box-shadow: 0 4px 12px rgba(21, 101, 192, 0.4);
}

/* ── セレクト・スライダー ── */
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"] > div {
    background-color: #132035;
    border-color: #243d5e;
    border-radius: 8px;
    color: #e2e8f0;
}

/* ── DataTable ── */
.stDataFrame {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #243d5e;
}
[data-testid="stDataFrameContainer"] {
    background-color: #0f2035;
}

/* ── expander ── */
[data-testid="stExpander"] {
    background-color: #0f2035;
    border: 1px solid #243d5e;
    border-radius: 10px;
}

/* ── info / warning / error ── */
[data-testid="stAlert"] {
    border-radius: 8px;
}

/* ── progress bar ── */
[data-testid="stProgressBar"] > div {
    background: linear-gradient(90deg, #1565c0, #4fc3f7);
    border-radius: 4px;
}

/* ── Widget labels (selectbox / slider / number_input / checkbox 等) ── */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
.stSelectbox label, .stMultiSelect label,
.stSlider label, .stNumberInput label,
.stTextInput label, .stCheckbox label,
.stRadio label {
    color: #d0e4f0 !important;
}

/* ── Caption ── */
.stCaption p,
[data-testid="stCaptionContainer"] p {
    color: #a8c8e0 !important;
}

/* ── Markdown 本文 ── */
.stMarkdown p {
    color: #d8ecf8;
}

/* ── Code / log ブロック ── */
.stCode, .stCode code,
pre, pre code,
[data-testid="stCode"] pre {
    background-color: #0a1c30 !important;
    color: #c8e8f8 !important;
    border: 1px solid #1e3a5a !important;
    border-radius: 6px;
}

/* ── アラートボックス (info/warning/success/error) ── */
[data-testid="stAlert"] p,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p {
    color: #e8f4ff !important;
}

/* ── Selectbox 選択値・ドロップダウン項目 ── */
[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
[data-baseweb="select"] span,
[data-baseweb="popover"] li span {
    color: #e2e8f0 !important;
}

/* ── DataTable セル文字 ── */
[data-testid="stDataFrame"] td,
[data-testid="stDataFrame"] th {
    color: #d8ecf8 !important;
}

/* ── caption / text_input ── */
.stTextInput > div > input {
    background-color: #132035;
    border-color: #243d5e;
    color: #e2e8f0;
    border-radius: 8px;
}

/* ── スライダー ── */
[data-testid="stSlider"] [data-baseweb="slider"] {
    padding: 8px 0;
}
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background-color: #4fc3f7;
    border: 2px solid #1a3a5a;
}
[data-testid="stSlider"] [data-baseweb="slider"] div[class*="Track"] {
    background-color: #1e3a5a;
}

/* ── number_input ── */
[data-testid="stNumberInput"] input {
    background-color: #132035;
    border-color: #243d5e;
    color: #e2e8f0;
    border-radius: 8px;
    font-variant-numeric: tabular-nums;
}

/* ── メトリクス数値フォント ── */
[data-testid="stMetricValue"] {
    font-variant-numeric: tabular-nums;
    letter-spacing: 0;
}

/* ── hr / divider ── */
hr {
    border-color: #243d5e;
}

/* ── st.status ウィジェット ── */
[data-testid="stStatusWidget"],
[data-testid="stStatus"] {
    background-color: #0f2035 !important;
    border: 1px solid #243d5e !important;
    border-radius: 10px !important;
    color: #d8ecf8 !important;
}
[data-testid="stStatusWidget"] p,
[data-testid="stStatus"] p,
[data-testid="stStatus"] span,
[data-testid="stStatus"] li {
    color: #d8ecf8 !important;
}

/* ── メトリクス（property_tab 等）強化 ── */
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] span {
    color: #a8c8e0 !important;
    font-size: 0.82rem !important;
}
[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] span {
    color: #e8f4ff !important;
}

/* ── divider ── */
[data-testid="stDivider"] hr {
    border-color: #243d5e !important;
}

/* ── Alert 背景 (info / warning / success / error) ── */
[data-testid="stAlert"][data-baseweb="notification"] {
    border-radius: 8px;
}
div[data-testid="stAlert"] > div[role="alert"][aria-label*="info"],
div[data-testid="stAlert"][kind="info"],
.stAlert[data-type="info"] {
    background: rgba(21, 101, 192, 0.15) !important;
    border: 1px solid rgba(21, 101, 192, 0.4) !important;
}
div[data-testid="stAlert"][kind="warning"],
.stAlert[data-type="warning"] {
    background: rgba(245, 124, 0, 0.12) !important;
    border: 1px solid rgba(245, 124, 0, 0.35) !important;
}
div[data-testid="stAlert"][kind="success"],
.stAlert[data-type="success"] {
    background: rgba(56, 142, 60, 0.15) !important;
    border: 1px solid rgba(56, 142, 60, 0.4) !important;
}
div[data-testid="stAlert"][kind="error"],
.stAlert[data-type="error"] {
    background: rgba(198, 40, 40, 0.15) !important;
    border: 1px solid rgba(198, 40, 40, 0.4) !important;
}

/* ── セカンダリボタン ── */
.stButton > button[kind="secondary"] {
    background: #132035;
    border: 1px solid #243d5e;
    color: #e2e8f0;
    border-radius: 8px;
}
.stButton > button[kind="secondary"]:hover {
    background: #1a2e47;
    border-color: #4fc3f7;
}

/* ── ダウンロードボタン ── */
[data-testid="stDownloadButton"] > button {
    background: #132035;
    border: 1px solid #243d5e;
    color: #e2e8f0;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #1a2e47;
    border-color: #4fc3f7;
}

/* ── Input / Select フォーカス状態 ── */
.stTextInput > div > input:focus,
[data-testid="stNumberInput"] input:focus {
    border-color: #4fc3f7 !important;
    outline: none;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within {
    border-color: #4fc3f7 !important;
}

/* ── Textarea ── */
.stTextArea > div > textarea {
    background-color: #132035;
    border-color: #243d5e;
    color: #e2e8f0;
    border-radius: 8px;
}
.stTextArea > div > textarea:focus {
    border-color: #4fc3f7 !important;
    outline: none;
}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label {
    color: #d0e4f0 !important;
}
[data-testid="stCheckbox"] [data-baseweb="checkbox"] span {
    background-color: #132035 !important;
    border-color: #243d5e !important;
    border-radius: 4px;
}
[data-testid="stCheckbox"] [data-baseweb="checkbox"] [aria-checked="true"] span {
    background-color: #1565c0 !important;
    border-color: #1565c0 !important;
}

/* ── Radio ── */
[data-testid="stRadio"] [data-baseweb="radio"] span {
    background-color: #132035 !important;
    border-color: #243d5e !important;
}

/* ── Top page navigation (radio used as lazy tab replacement) ── */
[data-testid="stRadio"] > div[role="radiogroup"] {
    background-color: #132035;
    border: 1px solid #243d5e;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
    margin-bottom: 10px;
}
[data-testid="stRadio"] > div[role="radiogroup"] label {
    background: transparent;
    border-radius: 7px;
    padding: 6px 14px;
    margin: 0;
}
[data-testid="stRadio"] > div[role="radiogroup"] label:hover {
    background-color: #1a2e47;
}
[data-testid="stRadio"] > div[role="radiogroup"] label:has(input:checked) {
    background-color: #1e3a5a;
    box-shadow: inset 0 -3px 0 #4fc3f7;
}
[data-testid="stRadio"] > div[role="radiogroup"] label > div:first-child {
    display: none;
}
[data-testid="stRadio"] > div[role="radiogroup"] label p {
    color: #b8d0e8 !important;
    font-size: 0.92rem;
    font-weight: 500;
}
[data-testid="stRadio"] > div[role="radiogroup"] label:has(input:checked) p,
[data-testid="stRadio"] > div[role="radiogroup"] label:hover p {
    color: #e8f4ff !important;
}
[data-testid="stRadio"] [data-baseweb="radio"] [aria-checked="true"] span {
    border-color: #4fc3f7 !important;
}
[data-testid="stRadio"] [data-baseweb="radio"] [aria-checked="true"] span::before {
    background-color: #4fc3f7 !important;
}

/* ── リンク ── */
.stMarkdown a,
[data-testid="stMarkdownContainer"] a {
    color: #7fc3ea;
}
.stMarkdown a:hover,
[data-testid="stMarkdownContainer"] a:hover {
    color: #4fc3f7;
}

/* ── CSS変数（デザイントークン） ── */
:root {
    --clr-bg-primary: #0d1b2a;
    --clr-bg-card: #132035;
    --clr-bg-card2: #1a2e4a;
    --clr-border: #243d5e;
    --clr-text-primary: #e8f4ff;
    --clr-text-muted: #a8c8e0;
    --clr-text-dim: #6a90aa;
    --clr-accent: #4fc3f7;
    --clr-positive: #81c784;
    --clr-negative: #ef9a9a;
    --clr-warning: #ffcc80;
    --radius-card: 12px;
    --radius-sm: 8px;
}

/* ── section-header ── */
.section-header {
    color: var(--clr-text-primary);
    font-size: 1.05rem;
    font-weight: 700;
    margin: 20px 0 10px 0;
    padding-bottom: 6px;
    border-bottom: 2px solid var(--clr-border);
}

/* ── metric-card ── */
.metric-card {
    background: linear-gradient(135deg, var(--clr-bg-card) 0%, var(--clr-bg-card2) 100%);
    border: 1px solid var(--clr-border);
    border-radius: var(--radius-card);
    padding: 12px 14px;
}
.metric-card-label {
    color: var(--clr-text-muted);
    font-size: 0.75rem;
}
.metric-card-value {
    color: var(--clr-text-primary);
    font-size: 1.15rem;
    font-weight: 700;
    margin-top: 4px;
}

/* ── property summary panels ── */
.property-summary-panel {
    background: linear-gradient(135deg, #102138 0%, #152842 100%);
    border: 1px solid #243d5e;
    border-radius: 10px;
    padding: 12px 14px;
    min-height: 100%;
}
.property-summary-panel-title {
    color: #cfe4f4;
    font-size: 0.92rem;
    font-weight: 700;
    margin: 0 0 10px 0;
}
.property-summary-grid {
    display: grid;
    gap: 8px;
}
.property-summary-grid.cols-1 {
    grid-template-columns: 1fr;
}
.property-summary-grid.cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}
.property-summary-grid.cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}
.property-summary-grid.cols-4 {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}
.property-summary-item {
    background: rgba(10, 28, 48, 0.55);
    border: 1px solid rgba(36, 61, 94, 0.9);
    border-radius: 8px;
    padding: 8px 10px;
    min-width: 0;
}
.property-summary-item-label {
    color: #95b8cf;
    font-size: 0.72rem;
    line-height: 1.2;
    margin: 0 0 4px 0;
}
.property-summary-item-value {
    color: #e8f4ff;
    font-size: 0.98rem;
    font-weight: 600;
    line-height: 1.25;
    letter-spacing: 0;
    word-break: break-word;
}
.property-summary-item-note {
    color: #7fc3ea;
    font-size: 0.7rem;
    line-height: 1.2;
    margin-top: 4px;
}
</style>
"""
