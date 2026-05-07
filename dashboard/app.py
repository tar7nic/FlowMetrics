# dashboard/app.py
# Phase 6 - Streamlit Dashboard — Horizontal Nav + Clean Sidebar Filters

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
DB_PATH = "warehouse/supply_chain.db"

st.set_page_config(
    page_title="FlowMetrics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Sora', sans-serif;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1rem !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #060e1e 0%, #0b1a33 100%);
    border-right: 1px solid #1a2d4a;
    width: 270px !important;
}
section[data-testid="stSidebar"] * { color: white !important; }
section[data-testid="stSidebar"] .stMarkdown p {
    color: #94a3b8 !important;
    font-size: 0.78rem;
}

/* ── Top nav bar ── */
.nav-bar {
    display: flex;
    gap: 6px;
    background: #0b1a33;
    border: 1px solid #1a2d4a;
    border-radius: 14px;
    padding: 6px 8px;
    margin-bottom: 24px;
    width: fit-content;
}
.nav-btn {
    padding: 8px 18px;
    border-radius: 10px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    background: transparent;
    color: #64748b;
    transition: all 0.2s ease;
    white-space: nowrap;
    font-family: 'Sora', sans-serif;
    letter-spacing: 0.3px;
}
.nav-btn:hover { background: #1a2d4a; color: #cbd5e1; }
.nav-btn.active {
    background: linear-gradient(135deg, #1d4ed8, #2563eb);
    color: white;
    box-shadow: 0 2px 12px rgba(37,99,235,0.45);
}

/* ── KPI cards ── */
.kpi-card {
    background: linear-gradient(135deg, #0f2034 0%, #162844 100%);
    border: 1px solid #1e3a5f;
    border-radius: 14px;
    padding: 18px 16px;
    text-align: center;
    margin: 4px 0;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
}
.kpi-label {
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 600;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 1.7rem;
    font-weight: 700;
    color: white;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
}
.kpi-badge {
    display: inline-block;
    margin-top: 6px;
    font-size: 0.68rem;
    padding: 2px 8px;
    border-radius: 20px;
    font-weight: 600;
}
.badge-good    { background: #052e16; color: #4ade80; }
.badge-bad     { background: #2d0a0a; color: #f87171; }
.badge-neutral { background: #1c1a05; color: #facc15; }

/* ── Section headers ── */
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #e2e8f0;
    margin: 20px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e3a5f;
    letter-spacing: 0.3px;
}

/* ── Filter pills ── */
.filter-label {
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: #475569 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    margin-bottom: 2px !important;
}

/* ── Streamlit multiselect override ── */
[data-testid="stMultiSelect"] > div > div {
    background: #0f2034 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 10px !important;
    color: white !important;
    font-size: 0.82rem !important;
}
[data-testid="stMultiSelect"] span {
    background: #1d4ed8 !important;
    color: white !important;
    border-radius: 6px !important;
    font-size: 0.75rem !important;
}

/* ── Page title ── */
.page-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: white;
    margin-bottom: 4px;
}
.page-subtitle {
    font-size: 0.82rem;
    color: #475569;
    margin-bottom: 20px;
}

/* ── Divider ── */
.styled-divider {
    border: none;
    border-top: 1px solid #1a2d4a;
    margin: 16px 0;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #1e3a5f !important;
    border-radius: 10px !important;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# PLOTLY THEME
# ─────────────────────────────────────────
PLOT_LAYOUT = dict(
    plot_bgcolor  = "#0a1628",
    paper_bgcolor = "#0a1628",
    font          = dict(color="#94a3b8", family="Sora, sans-serif", size=11),
    margin        = dict(t=30, b=30, l=10, r=10),
    xaxis         = dict(gridcolor="#1a2d4a", linecolor="#1a2d4a", tickfont=dict(size=10)),
    yaxis         = dict(gridcolor="#1a2d4a", linecolor="#1a2d4a", tickfont=dict(size=10)),
    legend        = dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    hoverlabel    = dict(bgcolor="#0f2034", font_size=12, font_family="Sora"),
)


# ─────────────────────────────────────────
# DB + DATA
# ─────────────────────────────────────────
@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found: {DB_PATH} — run Phase 4 first.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(ttl=300)
def load_base_data(_conn):
    return pd.read_sql_query("""
        SELECT f.*,
               d.year, d.month, d.month_name, d.quarter,
               g.market, g.order_region, g.order_country,
               c.segment,
               p.category, p.product_name,
               s.department_name
        FROM fact_orders f
        LEFT JOIN dim_date      d ON f.date_id     = d.date_id
        LEFT JOIN dim_geography g ON f.geo_id       = g.geo_id
        LEFT JOIN dim_customers c ON f.customer_id  = c.customer_id
        LEFT JOIN dim_products  p ON f.product_id   = p.product_id
        LEFT JOIN dim_suppliers s ON f.supplier_id  = s.supplier_id
    """, _conn)


# ─────────────────────────────────────────
# SIDEBAR — BRAND + FILTERS ONLY
# ─────────────────────────────────────────

# ── 1. STYLE INJECTION (CSS) ──
# Dynamic hover-expansion 
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

    /* ── DYNAMIC SIDEBAR CONSTANTS ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #060e1e 0%, #0b1a33 100%);
        border-right: 1px solid #1a2d4a;
        min-width: 80px !important;
        width: 80px !important;
        transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        overflow-x: hidden !important;
    }

    /* Expand on Hover */
    section[data-testid="stSidebar"]:hover {
        width: 300px !important;
    }

    /* Hide text/filters when collapsed, show on hover */
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
        opacity: 0;
        transition: opacity 0.2s ease-in-out;
    }
    
    section[data-testid="stSidebar"]:hover [data-testid="stVerticalBlock"] > div {
        opacity: 1;
    }

    /* Keep icons visible even when collapsed */
    .filter-label {
        opacity: 1 !important;
        font-size: 1.1rem !important; /* Larger icons for the 'rail' look */
        margin-top: 15px !important;
        display: block;
    }

    /* Fix for multi-select visibility */
    [data-testid="stMultiSelect"] {
        min-width: 250px !important;
    }

    /* ── Existing UI Styles ── */
    .filter-label {
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    [data-testid="stMultiSelect"] > div > div {
        background: #0f2034 !important;
        border: 1px solid #1e3a5f !important;
        border-radius: 10px !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ── 2. SIDEBAR RENDER FUNCTION ──
def render_sidebar(df: pd.DataFrame):
    # Brand Header
    st.sidebar.markdown("""
        <div style='display:flex; align-items:center; gap:15px; margin-bottom:10px;'>
            <img src="https://cdn-icons-png.flaticon.com/512/12503/12503340.png" width="60">
            <div style='min-width:180px;'>
                <span style='font-size:20px; font-weight:700; color:white;'>FlowMetrics</span><br>
                <span style='font-size:15px; color:#475569; letter-spacing:0.5px;'>Supply Chain Intelligence</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<hr style='border-color:#1a2d4a; margin:10px 0;'>", unsafe_allow_html=True)

    # Filter Heading
    st.sidebar.markdown("<p style='font-size:11px; font-weight:700; color:#475569; text-transform:uppercase;'>⚙ &nbsp; Filters</p>", unsafe_allow_html=True)

    # Year Filter
    st.sidebar.markdown("<p class='filter-label'>📅 &nbsp; Year</p>", unsafe_allow_html=True)
    years = sorted(df["year"].dropna().unique().astype(int).tolist())
    sel_years = st.sidebar.multiselect("Year", years, default=years, label_visibility="collapsed")

    # Market Filter
    st.sidebar.markdown("<p class='filter-label'>🌍 &nbsp; Market</p>", unsafe_allow_html=True)
    markets = sorted(df["market"].dropna().unique().tolist())
    sel_markets = st.sidebar.multiselect("Market", markets, default=markets, label_visibility="collapsed")

    # Segment Filter
    st.sidebar.markdown("<p class='filter-label'>👤 &nbsp; Segment</p>", unsafe_allow_html=True)
    segments = sorted(df["segment"].dropna().unique().tolist())
    sel_segs = st.sidebar.multiselect("Segment", segments, default=segments, label_visibility="collapsed")

    # Category Filter
    st.sidebar.markdown("<p class='filter-label'>📦 &nbsp; Category</p>", unsafe_allow_html=True)
    cats = sorted(df["category"].dropna().unique().tolist())
    sel_cats = st.sidebar.multiselect("Category", cats, default=cats, label_visibility="collapsed")

    st.sidebar.markdown("<hr style='border-color:#1a2d4a; margin:20px 0;'>", unsafe_allow_html=True)

    # Footer
    st.sidebar.markdown(
        f"<div style='min-width:200px; text-align:center;'><p style='font-size:10px; color:#1e3a5f;'>"
        f"FlowMetrics v1.0 &nbsp;|&nbsp; {len(df):,} records</p></div>",
        unsafe_allow_html=True
    )

    # Filtering Logic
    if not sel_years:   sel_years = years
    if not sel_markets: sel_markets = markets
    if not sel_segs:    sel_segs = segments
    if not sel_cats:    sel_cats = cats

    mask = (
        df["year"].isin(sel_years) &
        df["market"].isin(sel_markets) &
        df["segment"].isin(sel_segs) &
        df["category"].isin(sel_cats)
    )
    return df[mask].copy()

# ─────────────────────────────────────────
# HORIZONTAL NAV BAR
# ─────────────────────────────────────────
PAGES = [
    "📊 Executive Summary",
    "🏭 Supplier Performance",
    "📦 Inventory & Fulfillment",
    "💰 Cost & Risk",
    "🔄 Pipeline Monitor",
]

def render_nav() -> str:
    if "active_page" not in st.session_state:
        st.session_state.active_page = PAGES[0]

    cols = st.columns(len(PAGES))
    for i, (col, page) in enumerate(zip(cols, PAGES)):
        with col:
            is_active = st.session_state.active_page == page
            btn_style = (
                "background:linear-gradient(135deg,#1d4ed8,#2563eb);"
                "color:white;box-shadow:0 2px 12px rgba(37,99,235,0.4);"
            ) if is_active else (
                "background:#0b1a33;color:#475569;"
            )
            if st.button(
                page,
                key=f"nav_{i}",
                use_container_width=True,
            ):
                st.session_state.active_page = page
                st.rerun()

    st.markdown("<hr style='border-color:#1a2d4a;margin:0 0 20px 0;'>",
                unsafe_allow_html=True)
    return st.session_state.active_page


# ─────────────────────────────────────────
# KPI CARD HELPER
# ─────────────────────────────────────────
def kpi_card(label: str, value: str, status: str = "neutral"):
    badge_map = {
        "good"   : ("badge-good",    "● GOOD"),
        "bad"    : ("badge-bad",     "● AT RISK"),
        "neutral": ("badge-neutral", "● INFO"),
    }
    cls, txt = badge_map.get(status, badge_map["neutral"])
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <span class="kpi-badge {cls}">{txt}</span>
    </div>
    """, unsafe_allow_html=True)


def section(title: str):
    st.markdown(f"<div class='section-title'>{title}</div>",
                unsafe_allow_html=True)


# ─────────────────────────────────────────
# PAGE 1 — EXECUTIVE SUMMARY
# ─────────────────────────────────────────
def page_executive_summary(df: pd.DataFrame):
    st.markdown("<div class='page-title'>📊 Executive Summary</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>High-level KPI overview across all markets and segments</div>", unsafe_allow_html=True)

    total_orders  = df["order_id"].nunique()
    total_revenue = df["sales"].sum()
    total_profit  = df["profit"].sum()
    avg_margin    = df["profit_margin_pct"].mean()
    on_time       = df["on_time_flag"].mean() * 100
    fulfill       = df["is_fulfilled"].mean() * 100
    cancel        = df["is_cancelled"].mean() * 100
    perfect       = df["perfect_order_flag"].mean() * 100
    avg_delay     = df["delivery_delay_days"].mean()
    avg_cost      = df["cost_per_order"].mean()
    rev_at_risk   = df["revenue_at_risk"].sum()
    risk_pct      = (rev_at_risk / total_revenue * 100) if total_revenue > 0 else 0

    # Row 1
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Orders",       f"{total_orders:,}",      "neutral")
    with c2: kpi_card("Total Revenue",      f"${total_revenue:,.0f}", "neutral")
    with c3: kpi_card("Total Profit",       f"${total_profit:,.0f}",  "good" if total_profit > 0 else "bad")
    with c4: kpi_card("Avg Profit Margin",  f"{avg_margin:.1f}%",     "good" if avg_margin > 15 else "bad")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Row 2
    c5, c6, c7, c8 = st.columns(4)
    with c5: kpi_card("On-Time Delivery",   f"{on_time:.1f}%",  "good" if on_time > 70    else "bad")
    with c6: kpi_card("Fulfillment Rate",   f"{fulfill:.1f}%",  "good" if fulfill > 90    else "bad")
    with c7: kpi_card("Cancellation Rate",  f"{cancel:.1f}%",   "good" if cancel < 5      else "bad")
    with c8: kpi_card("Perfect Order Rate", f"{perfect:.1f}%",  "good" if perfect > 70    else "bad")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Row 3
    c9, c10, c11, c12 = st.columns(4)
    with c9:  kpi_card("Avg Delivery Delay",  f"{avg_delay:.1f}d",     "good" if avg_delay <= 0 else "bad")
    with c10: kpi_card("Avg Cost Per Order",  f"${avg_cost:,.0f}",     "neutral")
    with c11: kpi_card("Revenue At Risk",     f"${rev_at_risk:,.0f}",  "bad" if risk_pct > 5 else "good")
    with c12: kpi_card("Risk % of Revenue",   f"{risk_pct:.1f}%",      "bad" if risk_pct > 5 else "good")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Charts
    col_l, col_r = st.columns(2)

    with col_l:
        section("📈 Monthly Revenue & Profit")
        monthly = (
            df.groupby(["year","month"])
            .agg(revenue=("sales","sum"), profit=("profit","sum"))
            .reset_index().sort_values(["year","month"])
        )
        monthly["period"] = (monthly["year"].astype(str) + "-" +
                              monthly["month"].astype(str).str.zfill(2))
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly["period"], y=monthly["revenue"],
                             name="Revenue", marker_color="#2563eb"))
        fig.add_trace(go.Bar(x=monthly["period"], y=monthly["profit"],
                             name="Profit",  marker_color="#4ade80"))
        fig.update_layout(**PLOT_LAYOUT, barmode="group", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        section("🌍 Revenue by Market")
        mkt = (df.groupby("market")
               .agg(revenue=("sales","sum")).reset_index()
               .sort_values("revenue", ascending=False))
        fig2 = px.pie(mkt, values="revenue", names="market", hole=0.5,
                      color_discrete_sequence=["#2563eb","#1d4ed8","#1e40af",
                                               "#1e3a8a","#172554"])
        fig2.update_layout(**PLOT_LAYOUT, height=320)
        fig2.update_traces(textfont_size=11)
        st.plotly_chart(fig2, use_container_width=True)

    section("🚚 Delivery Status Breakdown")
    deliv = (df.groupby("delivery_status").size()
             .reset_index(name="count").sort_values("count"))
    fig3 = px.bar(deliv, x="count", y="delivery_status", orientation="h",
                  color="count", color_continuous_scale="Blues",
                  labels={"count":"Orders","delivery_status":"Status"})
    fig3.update_layout(**PLOT_LAYOUT, height=280, showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────
# PAGE 2 — SUPPLIER PERFORMANCE
# ─────────────────────────────────────────
def page_supplier_performance(df: pd.DataFrame):
    st.markdown("<div class='page-title'>🏭 Supplier Performance</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Lead times, on-time rates, and fulfillment by department</div>", unsafe_allow_html=True)

    sup = (
        df.groupby("department_name")
        .agg(
            total_orders     = ("order_id",            "count"),
            total_revenue    = ("sales",               "sum"),
            avg_delay        = ("delivery_delay_days", "mean"),
            on_time_rate     = ("on_time_flag",        "mean"),
            fulfill_rate     = ("is_fulfilled",        "mean"),
            cancel_rate      = ("is_cancelled",        "mean"),
            perfect_rate     = ("perfect_order_flag",  "mean"),
            avg_lead_time    = ("days_shipping_real",  "mean"),
        ).reset_index()
    )
    for col in ["on_time_rate","fulfill_rate","cancel_rate","perfect_rate"]:
        sup[col.replace("_rate","_pct")] = (sup[col] * 100).round(1)
    sup["avg_lead_time"]  = sup["avg_lead_time"].round(1)
    sup["avg_delay"]      = sup["avg_delay"].round(2)
    sup["total_revenue"]  = sup["total_revenue"].round(0)

    best  = sup.loc[sup["on_time_pct"].idxmax(), "department_name"]
    worst = sup.loc[sup["on_time_pct"].idxmin(), "department_name"]

    c1, c2, c3 = st.columns(3)
    with c1: kpi_card("Total Suppliers",        f"{len(sup)}",  "neutral")
    with c2: kpi_card("Best On-Time Supplier",  best,           "good")
    with c3: kpi_card("Worst On-Time Supplier", worst,          "bad")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        section("✅ On-Time Rate by Supplier")
        fig = px.bar(
            sup.sort_values("on_time_pct"),
            x="on_time_pct", y="department_name", orientation="h",
            color="on_time_pct", color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            labels={"on_time_pct":"On-Time %","department_name":"Supplier"}
        )
        fig.update_layout(**PLOT_LAYOUT, height=440)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section("⏱️ Avg Lead Time by Supplier")
        fig2 = px.bar(
            sup.sort_values("avg_lead_time", ascending=False),
            x="avg_lead_time", y="department_name", orientation="h",
            color="avg_lead_time", color_continuous_scale="Blues",
            labels={"avg_lead_time":"Avg Days","department_name":"Supplier"}
        )
        fig2.update_layout(**PLOT_LAYOUT, height=440)
        st.plotly_chart(fig2, use_container_width=True)

    section("💰 Revenue vs On-Time Rate")
    fig3 = px.scatter(
        sup, x="on_time_pct", y="total_revenue",
        size="total_orders", color="cancel_pct",
        hover_name="department_name",
        color_continuous_scale="RdYlGn_r",
        labels={"on_time_pct":"On-Time %","total_revenue":"Revenue ($)",
                "cancel_pct":"Cancel %","total_orders":"Orders"}
    )
    fig3.update_layout(**PLOT_LAYOUT, height=380)
    st.plotly_chart(fig3, use_container_width=True)

    section("📋 Full Supplier Table")
    st.dataframe(
        sup[[
            "department_name","total_orders","total_revenue",
            "on_time_pct","fulfill_pct","cancel_pct",
            "perfect_pct","avg_lead_time","avg_delay"
        ]].rename(columns={
            "department_name":"Supplier","total_orders":"Orders",
            "total_revenue":"Revenue ($)","on_time_pct":"On-Time %",
            "fulfill_pct":"Fulfillment %","cancel_pct":"Cancel %",
            "perfect_pct":"Perfect %","avg_lead_time":"Lead Time (d)",
            "avg_delay":"Avg Delay (d)"
        }).sort_values("Revenue ($)", ascending=False).reset_index(drop=True),
        use_container_width=True, height=380
    )


# ─────────────────────────────────────────
# PAGE 3 — INVENTORY & FULFILLMENT
# ─────────────────────────────────────────
def page_inventory_fulfillment(df: pd.DataFrame):
    st.markdown("<div class='page-title'>📦 Inventory & Fulfillment</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Product movement, category performance, and fulfillment analysis</div>", unsafe_allow_html=True)

    fulfill = df["is_fulfilled"].mean() * 100
    cancel  = df["is_cancelled"].mean() * 100
    qty     = df["quantity"].sum()
    avg_qty = df["quantity"].mean()

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Fulfillment Rate",    f"{fulfill:.1f}%", "good" if fulfill>90 else "bad")
    with c2: kpi_card("Cancellation Rate",   f"{cancel:.1f}%",  "good" if cancel<5   else "bad")
    with c3: kpi_card("Total Units Sold",    f"{qty:,.0f}",     "neutral")
    with c4: kpi_card("Avg Units Per Order", f"{avg_qty:.1f}",  "neutral")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        section("📊 Units Sold by Category")
        cat_qty = (df.groupby("category")
                   .agg(qty=("quantity","sum"), revenue=("sales","sum"))
                   .reset_index().sort_values("qty", ascending=False))
        fig = px.bar(cat_qty, x="category", y="qty",
                     color="revenue", color_continuous_scale="Blues",
                     labels={"qty":"Units","category":"Category"})
        fig.update_layout(**PLOT_LAYOUT, height=360, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section("🎯 Fulfillment Rate by Category")
        cat_f = (df.groupby("category")
                 .agg(fulfill=("is_fulfilled","mean"))
                 .reset_index())
        cat_f["fulfill_pct"] = (cat_f["fulfill"] * 100).round(1)
        fig2 = px.bar(cat_f.sort_values("fulfill_pct"),
                      x="fulfill_pct", y="category", orientation="h",
                      color="fulfill_pct", color_continuous_scale="RdYlGn",
                      range_color=[80,100],
                      labels={"fulfill_pct":"Fulfillment %","category":"Category"})
        fig2.update_layout(**PLOT_LAYOUT, height=360)
        st.plotly_chart(fig2, use_container_width=True)

    section("📈 Monthly Fulfillment & Cancellation Trend")
    monthly = (df.groupby(["year","month"])
               .agg(fulfill=("is_fulfilled","mean"), cancel=("is_cancelled","mean"))
               .reset_index().sort_values(["year","month"]))
    monthly["period"]      = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
    monthly["fulfill_pct"] = (monthly["fulfill"] * 100).round(2)
    monthly["cancel_pct"]  = (monthly["cancel"]  * 100).round(2)

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=monthly["period"], y=monthly["fulfill_pct"],
                              name="Fulfillment %", mode="lines+markers",
                              line=dict(color="#4ade80", width=2)))
    fig3.add_trace(go.Scatter(x=monthly["period"], y=monthly["cancel_pct"],
                              name="Cancellation %", mode="lines+markers",
                              line=dict(color="#f87171", width=2)))
    fig3.update_layout(**PLOT_LAYOUT, height=320)
    st.plotly_chart(fig3, use_container_width=True)

    section("📋 Order Status Distribution")
    status_df = (df.groupby("order_status")
                 .agg(count=("order_id","count"), revenue=("sales","sum"))
                 .reset_index().sort_values("count", ascending=False))
    fig4 = px.bar(status_df, x="order_status", y="count",
                  color="revenue", color_continuous_scale="Blues",
                  labels={"count":"Orders","order_status":"Status"})
    fig4.update_layout(**PLOT_LAYOUT, height=300)
    st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────
# PAGE 4 — COST & RISK
# ─────────────────────────────────────────
def page_cost_risk(df: pd.DataFrame):
    st.markdown("<div class='page-title'>💰 Cost & Risk Analysis</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Profit margins, cost per order, and revenue at risk</div>", unsafe_allow_html=True)

    total_rev   = df["sales"].sum()
    total_profit= df["profit"].sum()
    avg_margin  = df["profit_margin_pct"].mean()
    rev_risk    = df["revenue_at_risk"].sum()
    risk_pct    = (rev_risk / total_rev * 100) if total_rev > 0 else 0
    avg_cost    = df["cost_per_order"].mean()

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi_card("Total Revenue",     f"${total_rev:,.0f}",   "neutral")
    with c2: kpi_card("Total Profit",      f"${total_profit:,.0f}","good" if total_profit>0 else "bad")
    with c3: kpi_card("Avg Profit Margin", f"{avg_margin:.1f}%",   "good" if avg_margin>15 else "bad")
    with c4: kpi_card("Revenue At Risk",   f"${rev_risk:,.0f}",    "bad"  if risk_pct>5    else "good")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        section("📊 Profit Margin by Category")
        cat_m = (df.groupby("category")
                 .agg(margin=("profit_margin_pct","mean"))
                 .reset_index().sort_values("margin", ascending=False))
        fig = px.bar(cat_m, x="margin", y="category", orientation="h",
                     color="margin", color_continuous_scale="RdYlGn",
                     labels={"margin":"Avg Margin %","category":"Category"})
        fig.update_layout(**PLOT_LAYOUT, height=420)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        section("⚠️ Revenue At Risk by Market")
        risk_m = (df.groupby("market")
                  .agg(at_risk=("revenue_at_risk","sum"), revenue=("sales","sum"))
                  .reset_index())
        risk_m["risk_pct"] = (risk_m["at_risk"] / risk_m["revenue"] * 100).round(2)
        fig2 = px.bar(risk_m.sort_values("at_risk", ascending=False),
                      x="market", y="at_risk", color="risk_pct",
                      color_continuous_scale="Reds",
                      labels={"at_risk":"At Risk ($)","market":"Market","risk_pct":"Risk %"})
        fig2.update_layout(**PLOT_LAYOUT, height=420)
        st.plotly_chart(fig2, use_container_width=True)

    section("🚚 Cost Per Order by Shipping Mode")
    ship = (df.groupby("shipping_mode")
            .agg(avg_cost=("cost_per_order","mean"),
                 avg_margin=("profit_margin_pct","mean"),
                 orders=("order_id","count"))
            .reset_index().sort_values("avg_cost", ascending=False))
    fig3 = px.bar(ship, x="shipping_mode", y="avg_cost",
                  color="avg_margin", color_continuous_scale="RdYlGn",
                  text=ship["avg_cost"].apply(lambda x: f"${x:,.0f}"),
                  labels={"avg_cost":"Avg Cost ($)","shipping_mode":"Mode",
                          "avg_margin":"Avg Margin %"})
    fig3.update_traces(textposition="outside")
    fig3.update_layout(**PLOT_LAYOUT, height=320)
    st.plotly_chart(fig3, use_container_width=True)

    section("📈 Monthly Profit Margin Trend")
    monthly = (df.groupby(["year","month"])
               .agg(margin=("profit_margin_pct","mean"))
               .reset_index().sort_values(["year","month"]))
    monthly["period"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
    fig4 = px.line(monthly, x="period", y="margin", markers=True,
                   color_discrete_sequence=["#4ade80"],
                   labels={"margin":"Avg Margin %","period":"Month"})
    fig4.add_hline(y=monthly["margin"].mean(), line_dash="dash",
                   line_color="#facc15", annotation_text="Avg")
    fig4.update_layout(**PLOT_LAYOUT, height=300)
    st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────
# PAGE 5 — PIPELINE MONITOR
# ─────────────────────────────────────────
# def page_pipeline_monitor(df: pd.DataFrame):
#     st.markdown("<div class='page-title'>🔄 Pipeline Monitor</div>", unsafe_allow_html=True)
#     st.markdown("<div class='page-subtitle'>Data health, order trends, and operational scorecard</div>", unsafe_allow_html=True)

#     section("🩺 Data Health Checks")
#     checks = {
#         "Total Records"        : (len(df),                                      True),
#         "Null order_id"        : (df["order_id"].isnull().sum(),                False),
#         "Null sales"           : (df["sales"].isnull().sum(),                   False),
#         "Negative Profit Rows" : (int((df["profit"] < 0).sum()),                None),
#         "Zero Sales Rows"      : (int((df["sales"] == 0).sum()),                None),
#         "Duplicate Items"      : (int(df.duplicated(subset=["order_item_id"]).sum()), False),
#     }
#     cols = st.columns(len(checks))
#     for col, (label, (val, good_if_zero)) in zip(cols, checks.items()):
#         with col:
#             if good_if_zero is None:
#                 status = "neutral"
#             else:
#                 status = "good" if (val == 0) == good_if_zero else "bad"
#             kpi_card(label, f"{val:,}", status)

#     st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

#     section("📦 Daily Order Volume")
#     daily = (df.assign(date=pd.to_datetime(df["order_date"]).dt.date)
#              .groupby("date")
#              .agg(orders=("order_id","count"))
#              .reset_index())
#     fig = px.line(daily, x="date", y="orders",
#                   color_discrete_sequence=["#2563eb"],
#                   labels={"orders":"Orders","date":"Date"})
#     fig.update_layout(**PLOT_LAYOUT, height=300)
#     st.plotly_chart(fig, use_container_width=True)

#     col1, col2 = st.columns(2)
#     with col1:
#         section("📅 Orders by Day of Week")
#         dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
#         dow = (df.groupby("order_dow").agg(orders=("order_id","count"))
#                .reindex(dow_order).reset_index())
#         fig2 = px.bar(dow, x="order_dow", y="orders",
#                       color="orders", color_continuous_scale="Blues",
#                       labels={"order_dow":"Day","orders":"Orders"})
#         fig2.update_layout(**PLOT_LAYOUT, height=300)
#         st.plotly_chart(fig2, use_container_width=True)

#     with col2:
#         section("🕐 Revenue by Quarter")
#         qtr = (df.groupby(["year","quarter"])
#                .agg(orders=("order_id","count"), revenue=("sales","sum"))
#                .reset_index())
#         qtr["label"] = "Q" + qtr["quarter"].astype(str) + " " + qtr["year"].astype(str)
#         fig3 = px.bar(qtr, x="label", y="revenue",
#                       color="orders", color_continuous_scale="Blues",
#                       labels={"label":"Quarter","revenue":"Revenue ($)","orders":"Orders"})
#         fig3.update_layout(**PLOT_LAYOUT, height=300)
#         st.plotly_chart(fig3, use_container_width=True)

#     section("🎯 KPI Health Scorecard")
#     scorecard = [
#         ("On-Time Delivery Rate",  df["on_time_flag"].mean()*100,      70,  "%", False),
#         ("Fulfillment Rate",       df["is_fulfilled"].mean()*100,       90,  "%", False),
#         ("Cancellation Rate",      df["is_cancelled"].mean()*100,        5,  "%", True),
#         ("Perfect Order Rate",     df["perfect_order_flag"].mean()*100, 70,  "%", False),
#         ("Avg Profit Margin",      df["profit_margin_pct"].mean(),      15,  "%", False),
#     ]
#     hdr = st.columns([3,2,2,2])
#     for h, t in zip(hdr, ["KPI","Value","Target","Status"]):
#         h.markdown(f"<span style='font-size:11px;color:#475569;font-weight:700;"
#                    f"text-transform:uppercase;letter-spacing:1px'>{t}</span>",
#                    unsafe_allow_html=True)
#     st.markdown("<hr style='border-color:#1a2d4a;margin:4px 0 8px'>", unsafe_allow_html=True)

#     for name, val, target, unit, lower_is_better in scorecard:
#         at_risk = val > target if lower_is_better else val < target
#         status_html = (
#             "<span style='color:#f87171;font-weight:600'>🔴 AT RISK</span>"
#             if at_risk else
#             "<span style='color:#4ade80;font-weight:600'>🟢 GOOD</span>"
#         )
#         ca, cb, cc, cd = st.columns([3,2,2,2])
#         ca.markdown(f"<span style='font-size:0.87rem;color:#cbd5e1'>{name}</span>",
#                     unsafe_allow_html=True)
#         cb.markdown(f"<span style='font-family:JetBrains Mono,monospace;"
#                     f"font-size:0.87rem;color:white'>{val:.1f}{unit}</span>",
#                     unsafe_allow_html=True)
#         cc.markdown(f"<span style='font-size:0.87rem;color:#475569'>"
#                     f"{target}{unit}</span>", unsafe_allow_html=True)
#         cd.markdown(status_html, unsafe_allow_html=True)

def page_pipeline_monitor(df: pd.DataFrame):
    st.markdown("<div class='page-title'>🔄 Pipeline Monitor</div>", unsafe_allow_html=True)
    st.markdown("<div class='page-subtitle'>Data health, order trends, and operational scorecard</div>", unsafe_allow_html=True)

    # --- 🩺 Data Health Checks ---
    section("🩺 Data Health Checks")
    checks = {
        "Total Records"        : (len(df),                                      True),
        "Null order_id"        : (df["order_id"].isnull().sum(),                False),
        "Null sales"           : (df["sales"].isnull().sum(),                   False),
        "Negative Profit Rows" : (int((df["profit"] < 0).sum()),                None),
        "Zero Sales Rows"      : (int((df["sales"] == 0).sum()),                None),
        "Duplicate Items"      : (int(df.duplicated(subset=["order_item_id"]).sum()), False),
    }
    cols = st.columns(len(checks))
    for col, (label, (val, good_if_zero)) in zip(cols, checks.items()):
        with col:
            if good_if_zero is None:
                status = "neutral"
            else:
                # Total Records is 'good' if > 0, others are 'good' if == 0
                if label == "Total Records":
                    status = "good" if val > 0 else "bad"
                else:
                    status = "good" if val == 0 else "bad"
            kpi_card(label, f"{val:,}", status)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # --- 📦 Daily Order Volume ---
    section("📦 Daily Order Volume")
    # Ensure order_date is datetime
    df["order_date"] = pd.to_datetime(df["order_date"])
    daily = (df.groupby(df["order_date"].dt.date)
             .agg(orders=("order_id","count"))
             .reset_index()
             .rename(columns={"order_date": "date"}))
    
    fig = px.line(daily, x="date", y="orders",
                  color_discrete_sequence=["#2563eb"],
                  labels={"orders":"Orders","date":"Date"})
    fig.update_layout(**PLOT_LAYOUT, height=300)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    
    # --- 📅 Orders by Day of Week (FIXED KEYERROR) ---
    with col1:
        section("📅 Orders by Day of Week")
        
        # Mapping dict in case Spark saved 'order_dow' as numbers (1-7)
        dow_map = {1:"Sunday", 2:"Monday", 3:"Tuesday", 4:"Wednesday", 5:"Thursday", 6:"Friday", 7:"Saturday"}
        
        # 1. Ensure column exists
        if "order_dow" not in df.columns:
            df["order_dow"] = df["order_date"].dt.day_name()
        
        # 2. If it's numeric, map it to names
        if df["order_dow"].dtype in ['int64', 'float64']:
            df["order_dow"] = df["order_dow"].map(dow_map)

        dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        
        # 3. Group and Reindex safely
        dow = (df.groupby("order_dow").agg(orders=("order_id","count"))
               .reindex(dow_order)
               .fillna(0) # In case a day has 0 orders
               .reset_index())

        fig2 = px.bar(dow, x="order_dow", y="orders",
                      color="orders", color_continuous_scale="Blues",
                      labels={"order_dow":"Day","orders":"Orders"})
        fig2.update_layout(**PLOT_LAYOUT, height=300)
        st.plotly_chart(fig2, use_container_width=True)

    # --- 🕐 Revenue by Quarter ---
    with col2:
        section("🕐 Revenue by Quarter")
        # Ensure year/quarter columns exist (re-calculating to be safe)
        if "year" not in df.columns: df["year"] = df["order_date"].dt.year
        if "quarter" not in df.columns: df["quarter"] = df["order_date"].dt.quarter

        qtr = (df.groupby(["year","quarter"])
               .agg(orders=("order_id","count"), revenue=("sales","sum"))
               .reset_index())
        qtr["label"] = "Q" + qtr["quarter"].astype(str) + " " + qtr["year"].astype(str)
        
        fig3 = px.bar(qtr, x="label", y="revenue",
                      color="orders", color_continuous_scale="Blues",
                      labels={"label":"Quarter","revenue":"Revenue ($)","orders":"Orders"})
        fig3.update_layout(**PLOT_LAYOUT, height=300)
        st.plotly_chart(fig3, use_container_width=True)

    # --- 🎯 KPI Health Scorecard ---
    section("🎯 KPI Health Scorecard")
    
    # Helper to calculate means safely (handles missing columns or NaNs)
    def get_metric(col):
        return df[col].mean() * 100 if col in df.columns else 0.0

    scorecard = [
        ("On-Time Delivery Rate",  get_metric("on_time_flag"),      70,  "%", False),
        ("Fulfillment Rate",       get_metric("is_fulfilled"),       90,  "%", False),
        ("Cancellation Rate",      get_metric("is_cancelled"),        5,  "%", True),
        ("Perfect Order Rate",     get_metric("perfect_order_flag"), 70,  "%", False),
        ("Avg Profit Margin",      df["profit_margin_pct"].mean() if "profit_margin_pct" in df.columns else 0, 15, "%", False),
    ]
    
    hdr = st.columns([3,2,2,2])
    for h, t in zip(hdr, ["KPI","Value","Target","Status"]):
        h.markdown(f"<span style='font-size:11px;color:#475569;font-weight:700;"
                   f"text-transform:uppercase;letter-spacing:1px'>{t}</span>",
                   unsafe_allow_html=True)
    st.markdown("<hr style='border-color:#1a2d4a;margin:4px 0 8px'>", unsafe_allow_html=True)

    for name, val, target, unit, lower_is_better in scorecard:
        # Handle cases where val might be NaN
        val = 0.0 if pd.isna(val) else val
        at_risk = val > target if lower_is_better else val < target
        status_html = (
            "<span style='color:#f87171;font-weight:600'>🔴 AT RISK</span>"
            if at_risk else
            "<span style='color:#4ade80;font-weight:600'>🟢 GOOD</span>"
        )
        ca, cb, cc, cd = st.columns([3,2,2,2])
        ca.markdown(f"<span style='font-size:0.87rem;color:#cbd5e1'>{name}</span>", unsafe_allow_html=True)
        cb.markdown(f"<span style='font-family:JetBrains Mono,monospace;font-size:0.87rem;color:white'>{val:.1f}{unit}</span>", unsafe_allow_html=True)
        cc.markdown(f"<span style='font-size:0.87rem;color:#475569'>{target}{unit}</span>", unsafe_allow_html=True)
        cd.markdown(status_html, unsafe_allow_html=True)
# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    conn = get_connection()
    df   = load_base_data(conn)
    df   = render_sidebar(df)
    page = render_nav()

    dispatch = {
        PAGES[0]: page_executive_summary,
        PAGES[1]: page_supplier_performance,
        PAGES[2]: page_inventory_fulfillment,
        PAGES[3]: page_cost_risk,
        PAGES[4]: page_pipeline_monitor,
    }
    dispatch[page](df)


if __name__ == "__main__":
    main()