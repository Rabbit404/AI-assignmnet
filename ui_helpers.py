import streamlit as st

CATEGORY_ICONS = {
    "electronics": "📱",
    "computers": "💻",
    "appliances": "🧺",
    "furniture": "🛋️",
    "stationery": "🖊️",
    "auto": "🚗",
    "apparel": "👕",
    "kids": "🧸",
    "construction": "🛠️",
    "sport": "🏋️",
    "medicine": "💊",
    "accessories": "👜",
}
DEFAULT_ICON = "🛍️"


def category_icon(category_code: str) -> str:
    top = str(category_code).split(".")[0]
    return CATEGORY_ICONS.get(top, DEFAULT_ICON)


def inject_theme():
    st.markdown(
        """
        <style>
        :root {
            --brand-ink:     #1B2430;
            --brand-ink-2:   #26333F;
            --brand-teal:    #0E7C7B;
            --brand-teal-d:  #0A5F5E;
            --brand-amber:   #E8A33D;
            --brand-bg:      #F6F7F5;
            --brand-card:    #FFFFFF;
            --brand-line:    #E4E7E4;
            --sidebar-text:  #C7CDD4;
            --sidebar-text-dim: #8891A0;
        }

        .stApp { background-color: var(--brand-bg); }

        /* Force readable text color for body copy - some Streamlit theme
           configs default to white text, which disappears on our light
           background. Scoped to markdown/caption/metric/label containers
           only, so button text and our custom dark header/cards (which set
           their own colors with !important) are untouched. */
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] h4,
        [data-testid="stMarkdownContainer"] h5,
        [data-testid="stMarkdownContainer"] h6,
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] *,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stWidgetLabel"] {
            color: var(--brand-ink) !important;
        }

        /* ==================== SIDEBAR ====================
           The default multipage nav inherits the user's Streamlit theme, so
           on a dark theme it renders dim text on a dark background and
           disappears. Style it explicitly instead of relying on theme
           defaults, so it looks the same and stays readable either way. */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--brand-ink) 0%, var(--brand-ink-2) 100%);
            border-right: 1px solid rgba(255,255,255,0.06);
        }
        section[data-testid="stSidebar"] * {
            color: var(--sidebar-text) !important;
        }
        [data-testid="stSidebarNav"] { padding-top: 0.5rem; }
        [data-testid="stSidebarNav"] ul { padding: 0 0.5rem; }
        [data-testid="stSidebarNav"] a {
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            margin: 0.1rem 0;
            font-weight: 500;
            transition: background 0.15s ease, color 0.15s ease;
        }
        [data-testid="stSidebarNav"] a:hover {
            background: rgba(255,255,255,0.08);
            color: #FFFFFF !important;
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: rgba(232, 163, 61, 0.16);
            color: var(--brand-amber) !important;
            font-weight: 700;
            box-shadow: inset 3px 0 0 var(--brand-amber);
        }
        .sidebar-brand {
            padding: 0.4rem 0.9rem 0.9rem 0.9rem;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            margin-bottom: 0.5rem;
        }
        .sidebar-brand .logo {
            color: white !important;
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: 0.02em;
        }
        .sidebar-brand .logo span { color: var(--brand-amber) !important; }
        .sidebar-brand .tag {
            color: var(--sidebar-text-dim) !important;
            font-size: 0.76rem;
            margin-top: 0.1rem;
        }

        /* ==================== TOP BRAND BAR (main content) ==================== */
        .shopnest-header {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem 1.5rem;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.5rem;
            margin: -1rem -1rem 1.4rem -1rem;
            background: linear-gradient(120deg, var(--brand-ink) 0%, var(--brand-ink-2) 100%);
            border-radius: 0 0 16px 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        }
        .shopnest-logo {
            color: white !important;
            font-size: 1.4rem;
            font-weight: 800;
            letter-spacing: 0.02em;
        }
        .shopnest-logo span { color: var(--brand-amber) !important; }
        .shopnest-tag {
            color: #B9C2CC !important;
            font-size: 0.82rem;
            margin-top: 0.1rem;
        }

        /* ==================== WIDGETS ==================== */
        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stNumberInput input {
            border-radius: 10px !important;
        }

        /* Buttons - text lives inside a stMarkdownContainer/<p>, which the
           readability rule above darkens. These button-scoped rules are more
           specific, so they win and keep button text on-brand and legible
           regardless of button background. Default/secondary buttons get an
           outlined look; primary buttons get a solid teal fill. */
        .stButton > button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            background-color: #FFFFFF !important;
            border: 1.5px solid var(--brand-teal) !important;
            transition: transform 0.1s ease, box-shadow 0.15s ease, background-color 0.15s ease !important;
        }
        .stButton > button,
        .stButton > button p,
        .stButton > button span,
        .stButton > button div {
            color: var(--brand-teal-d) !important;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            background-color: rgba(14, 124, 123, 0.08) !important;
            border-color: var(--brand-teal-d) !important;
            box-shadow: 0 4px 12px rgba(14, 124, 123, 0.18);
        }
        .stButton > button:disabled,
        .stButton > button:disabled * {
            color: #A6ADB6 !important;
            border-color: var(--brand-line) !important;
            background-color: #F6F7F5 !important;
        }
        .stButton > button[kind="primary"] {
            background-color: var(--brand-teal) !important;
            border-color: var(--brand-teal) !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[kind="primary"] p,
        .stButton > button[kind="primary"] span,
        .stButton > button[kind="primary"] div {
            color: #FFFFFF !important;
        }
        .stButton > button[kind="primary"]:hover {
            background-color: var(--brand-teal-d) !important;
            border-color: var(--brand-teal-d) !important;
            box-shadow: 0 4px 12px rgba(14, 124, 123, 0.32);
        }
        hr, [data-testid="stDivider"] { border-color: var(--brand-line) !important; }

        /* ==================== PRODUCT CARD ==================== */
        .pcard {
            background: var(--brand-card);
            border: 1px solid var(--brand-line);
            border-radius: 14px;
            padding: 1rem 1.1rem 1.1rem 1.1rem;
            height: 100%;
            display: flex;
            flex-direction: column;
            transition: box-shadow 0.15s ease, transform 0.15s ease, border-color 0.15s ease;
        }
        .pcard:hover {
            box-shadow: 0 8px 22px rgba(14, 124, 123, 0.16);
            transform: translateY(-3px);
            border-color: rgba(14, 124, 123, 0.35);
        }
        .pcard-icon {
            font-size: 2rem;
            line-height: 1;
            margin-bottom: 0.4rem;
        }
        .pcard-cat {
            color: var(--brand-teal-d);
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .pcard-brand {
            color: #5B6470;
            font-size: 0.82rem;
            margin-top: 0.15rem;
        }
        .pcard-price {
            font-size: 1.2rem;
            font-weight: 800;
            color: var(--brand-ink);
            margin-top: 0.45rem;
        }
        .pcard-id {
            color: #A6ADB6;
            font-size: 0.68rem;
            margin-top: 0.15rem;
        }
        .badge {
            display: inline-block;
            background: rgba(14, 124, 123, 0.12);
            color: var(--brand-teal-d);
            border-radius: 999px;
            padding: 0.15rem 0.6rem;
            font-size: 0.72rem;
            font-weight: 700;
            margin-top: 0.5rem;
            width: fit-content;
        }
        .why-box {
            background: #FBF3E3;
            border-left: 3px solid var(--brand-amber);
            border-radius: 6px;
            padding: 0.55rem 0.75rem;
            font-size: 0.83rem;
            line-height: 1.35;
            color: #4A3B1F;
            margin-top: 0.55rem;
        }
        .section-label {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: var(--brand-teal-d);
            margin-bottom: 0.1rem;
        }

        /* ==================== METRICS ==================== */
        [data-testid="stMetric"] {
            background: var(--brand-card);
            border: 1px solid var(--brand-line);
            border-radius: 12px;
            padding: 0.75rem 1rem;
        }

        /* ==================== FOOTER ==================== */
        .shopnest-footer {
            margin-top: 2.5rem;
            padding-top: 1rem;
            border-top: 1px solid var(--brand-line);
            color: #9AA2AC;
            font-size: 0.78rem;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand():
    """Small branded header pinned above the auto-generated page nav in the sidebar."""
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="logo">Shop<span>Nest</span></div>
            <div class="tag">recommendation prototype</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        """
        <div class="shopnest-footer">
            ShopNest is a demo built on content-based, collaborative &amp; hybrid filtering — not a real store.
        </div>
        """,
        unsafe_allow_html=True,
    )


def header(active_page: str = ""):
    st.markdown(
        f"""
        <div class="shopnest-header">
            <div>
                <div class="shopnest-logo">Shop<span>Nest</span></div>
                <div class="shopnest-tag">recommendation-prototype &middot; {active_page}</div>
            </div>
            <div class="shopnest-tag">🛒 built with content-based, collaborative &amp; hybrid filtering</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def product_card(row, badge_label: str | None = None, why: str | None = None):
    """Render one product as an HTML card. `row` needs product_id, category_code, brand, price."""
    icon = category_icon(row["category_code"])
    price = row.get("price", None)
    price_txt = f"${price:,.2f}" if price is not None and not pd_isna(price) else "—"
    badge_html = f'<div class="badge">{badge_label}</div>' if badge_label else ""
    why_html = f'<div class="why-box">💡 {why}</div>' if why else ""
    st.markdown(
        f"""
        <div class="pcard">
            <div class="pcard-icon">{icon}</div>
            <div class="pcard-cat">{row['category_code']}</div>
            <div class="pcard-brand">Brand: {str(row['brand']).title()}</div>
            <div class="pcard-price">{price_txt}</div>
            <div class="pcard-id">ID: {row['product_id']}</div>
            {badge_html}
            {why_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def pd_isna(v) -> bool:
    try:
        import math
        return v is None or (isinstance(v, float) and math.isnan(v))
    except Exception:
        return v is None