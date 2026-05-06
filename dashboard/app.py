import streamlit as st

st.set_page_config(
    page_title="FlowMetrics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0d1117;
    color: #c9d1d9;
}
h1, h2, h3 { font-family: 'JetBrains Mono', monospace; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #161b27 0%, #0d1117 100%);
    border-right: 1px solid #2d3748;
}
[data-testid="stSidebar"] .css-1d391kg { padding-top: 2rem; }

div[data-testid="metric-container"] {
    background: #1a1f2e;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 12px;
}

.stPlotlyChart { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar branding ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 16px 0 24px 0;">
        <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; font-weight:700; color:#00d4aa;">
            📦 SC-KPI Monitor
        </div>
        <div style="color:#4a5568; font-size:0.7rem; margin-top:4px;">DataCo Global · v1.0</div>
    </div>
    """, unsafe_allow_html=True)

# ── Home page ────────────────────────────────────────────────────────────────
st.markdown("## 📦 FlowMetrics")
st.markdown("Select a page from the sidebar to begin exploring.")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("**Executive Summary**\nTop-level KPIs and health indicators")
with col2:
    st.info("**Supplier Performance**\nLead times, delays, and on-time rates")
with col3:
    st.info("**Inventory & Fulfillment**\nStock, order rates, and fill metrics")

col4, col5 = st.columns(2)
with col4:
    st.info("**Cost & Risk**\nMargin, cost-per-order, and revenue at risk")
with col5:
    st.info("**Pipeline Monitor**\nIngestion logs and pipeline health")