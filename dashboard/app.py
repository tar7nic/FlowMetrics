# dashboard/app.py
# Phase 6 - Streamlit Dashboard for Supply Chain KPI Monitor

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
DB_PATH = "warehouse/supply_chain.db"

st.set_page_config(
    page_title = "FlowMetrics",
    page_icon  = "📦",
    layout     = "wide",
    initial_sidebar_state = "expanded"
)

# ─────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────
st.markdown("""
<style>
    .kpi-card {
        background: linear-gradient(135deg, #1e3a5f, #2d6a9f);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: white;
        margin: 5px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 8px 0;
    }
    .kpi-label {
        font-size: 0.85rem;
        opacity: 0.85;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .kpi-delta {
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .good  { color: #00e676; }
    .bad   { color: #ff5252; }
    .neutral { color: #ffeb3b; }
    section[data-testid="stSidebar"] {
        background-color: #0f2034;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────
@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found at {DB_PATH}. Run Phase 4 first.")
        st.stop()
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(ttl=300)
def query(_conn, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, _conn)


# ─────────────────────────────────────────
# LOAD BASE DATA
# ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_base_data(_conn):
    orders = query(_conn, """
        SELECT f.*, 
               d.year, d.month, d.month_name, d.quarter,
               g.market, g.order_region, g.order_country,
               c.segment, c.customer_country,
               p.category, p.product_name,
               s.department_name
        FROM fact_orders f
        LEFT JOIN dim_date      d ON f.date_id      = d.date_id
        LEFT JOIN dim_geography g ON f.geo_id        = g.geo_id
        LEFT JOIN dim_customers c ON f.customer_id   = c.customer_id
        LEFT JOIN dim_products  p ON f.product_id    = p.product_id
        LEFT JOIN dim_suppliers s ON f.supplier_id   = s.supplier_id
    """)
    return orders


# ─────────────────────────────────────────
# SIDEBAR FILTERS
# ─────────────────────────────────────────
def render_sidebar(df: pd.DataFrame):
    col1, col2 = st.sidebar.columns([1, 2.5])
    with col1:
        st.image(
            "https://cdn-icons-png.flaticon.com/512/12503/12503340.png",
            width=80
        )
    with col2:
        st.markdown("""
            <div style='display:flex; align-items:center; height:100%; padding-top:10px;'>
                <div>
                    <span style='font-size:25px; font-weight:700; color:white;'>FlowMetrics</span><br>
                    <span style='font-size:15px; color:#a0aec0;'>Supply Chain Intelligence</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Filters")

    # Year filter
    years = sorted(df["year"].dropna().unique().astype(int).tolist())
    sel_years = st.sidebar.multiselect(
        "Year", years, default=years
    )

    # Market filter
    markets = sorted(df["market"].dropna().unique().tolist())
    sel_markets = st.sidebar.multiselect(
        "Market", markets, default=markets
    )

    # Segment filter
    segments = sorted(df["segment"].dropna().unique().tolist())
    sel_segments = st.sidebar.multiselect(
        "Customer Segment", segments, default=segments
    )

    # Category filter
    categories = sorted(df["category"].dropna().unique().tolist())
    sel_cats = st.sidebar.multiselect(
        "Product Category", categories, default=categories
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Total records: {len(df):,}")

    # Apply filters
    mask = (
        df["year"].isin(sel_years) &
        df["market"].isin(sel_markets) &
        df["segment"].isin(sel_segments) &
        df["category"].isin(sel_cats)
    )
    return df[mask].copy()


# ─────────────────────────────────────────
# KPI CARD HELPER
# ─────────────────────────────────────────
def kpi_card(label, value, good=True, suffix=""):
    color_class = "good" if good else "bad"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}{suffix}</div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────
# PAGE 1 — EXECUTIVE SUMMARY
# ─────────────────────────────────────────
def page_executive_summary(df: pd.DataFrame):
    st.title("📊 Executive Summary")
    st.caption("High-level KPI overview across all markets and segments")
    st.markdown("---")

    # ── Row 1: Core KPIs
    c1, c2, c3, c4 = st.columns(4)

    total_orders  = df["order_id"].nunique()
    total_revenue = df["sales"].sum()
    total_profit  = df["profit"].sum()
    avg_margin    = df["profit_margin_pct"].mean()

    with c1:
        kpi_card("Total Orders", f"{total_orders:,}")
    with c2:
        kpi_card("Total Revenue", f"${total_revenue:,.0f}")
    with c3:
        kpi_card("Total Profit", f"${total_profit:,.0f}")
    with c4:
        kpi_card("Avg Profit Margin", f"{avg_margin:.1f}%",
                 good=avg_margin > 15)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Operational KPIs
    c5, c6, c7, c8 = st.columns(4)

    on_time_rate    = df["on_time_flag"].mean() * 100
    fulfill_rate    = df["is_fulfilled"].mean() * 100
    cancel_rate     = df["is_cancelled"].mean() * 100
    perfect_rate    = df["perfect_order_flag"].mean() * 100

    with c5:
        kpi_card("On-Time Delivery", f"{on_time_rate:.1f}%",
                 good=on_time_rate > 70)
    with c6:
        kpi_card("Fulfillment Rate", f"{fulfill_rate:.1f}%",
                 good=fulfill_rate > 90)
    with c7:
        kpi_card("Cancellation Rate", f"{cancel_rate:.1f}%",
                 good=cancel_rate < 5)
    with c8:
        kpi_card("Perfect Order Rate", f"{perfect_rate:.1f}%",
                 good=perfect_rate > 70)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 3: Risk KPIs
    c9, c10, c11, c12 = st.columns(4)

    avg_delay      = df["delivery_delay_days"].mean()
    avg_cost       = df["cost_per_order"].mean()
    rev_at_risk    = df["revenue_at_risk"].sum()
    risk_pct       = (rev_at_risk / total_revenue * 100) if total_revenue > 0 else 0

    with c9:
        kpi_card("Avg Delivery Delay", f"{avg_delay:.1f} days",
                 good=avg_delay <= 0)
    with c10:
        kpi_card("Avg Cost Per Order", f"${avg_cost:,.0f}")
    with c11:
        kpi_card("Revenue At Risk", f"${rev_at_risk:,.0f}",
                 good=risk_pct < 5)
    with c12:
        kpi_card("Risk % of Revenue", f"{risk_pct:.1f}%",
                 good=risk_pct < 5)

    st.markdown("---")

    # ── Charts Row
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 Monthly Revenue & Profit")
        monthly = (
            df.groupby(["year", "month", "month_name"])
            .agg(revenue=("sales", "sum"), profit=("profit", "sum"))
            .reset_index()
            .sort_values(["year", "month"])
        )
        monthly["period"] = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["period"], y=monthly["revenue"],
            name="Revenue", marker_color="#2d6a9f"
        ))
        fig.add_trace(go.Bar(
            x=monthly["period"], y=monthly["profit"],
            name="Profit", marker_color="#00e676"
        ))
        fig.update_layout(
            barmode="group", height=350,
            plot_bgcolor="#0f2034", paper_bgcolor="#0f2034",
            font_color="white", legend=dict(orientation="h")
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🌍 Revenue by Market")
        mkt = (
            df.groupby("market")
            .agg(revenue=("sales","sum"), orders=("order_id","nunique"))
            .reset_index()
            .sort_values("revenue", ascending=False)
        )
        fig2 = px.pie(
            mkt, values="revenue", names="market",
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        fig2.update_layout(
            height=350,
            plot_bgcolor="#0f2034", paper_bgcolor="#0f2034",
            font_color="white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Delivery status breakdown
    st.subheader("🚚 Delivery Status Breakdown")
    deliv = (
        df.groupby("delivery_status")
        .size().reset_index(name="count")
        .sort_values("count", ascending=True)
    )
    fig3 = px.bar(
        deliv, x="count", y="delivery_status",
        orientation="h",
        color="count",
        color_continuous_scale="Blues",
        labels={"count": "Orders", "delivery_status": "Status"}
    )
    fig3.update_layout(
        height=300,
        plot_bgcolor="#0f2034", paper_bgcolor="#0f2034",
        font_color="white", showlegend=False
    )
    st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────
# PAGE 2 — SUPPLIER PERFORMANCE
# ─────────────────────────────────────────
def page_supplier_performance(df: pd.DataFrame):
    st.title("🏭 Supplier Performance")
    st.caption("Lead times, on-time rates, and fulfillment by supplier/department")
    st.markdown("---")

    supplier = (
        df.groupby("department_name")
        .agg(
            total_orders    = ("order_id", "count"),
            total_revenue   = ("sales", "sum"),
            avg_delay       = ("delivery_delay_days", "mean"),
            on_time_rate    = ("on_time_flag", "mean"),
            fulfillment_rate= ("is_fulfilled", "mean"),
            cancel_rate     = ("is_cancelled", "mean"),
            perfect_rate    = ("perfect_order_flag", "mean"),
            avg_lead_time   = ("days_shipping_real", "mean"),
        )
        .reset_index()
    )
    supplier["on_time_pct"]     = (supplier["on_time_rate"] * 100).round(1)
    supplier["fulfill_pct"]     = (supplier["fulfillment_rate"] * 100).round(1)
    supplier["cancel_pct"]      = (supplier["cancel_rate"] * 100).round(1)
    supplier["perfect_pct"]     = (supplier["perfect_rate"] * 100).round(1)
    supplier["avg_lead_time"]   = supplier["avg_lead_time"].round(1)
    supplier["avg_delay"]       = supplier["avg_delay"].round(2)
    supplier["total_revenue"]   = supplier["total_revenue"].round(0)

    # ── KPI cards for best/worst supplier
    best  = supplier.loc[supplier["on_time_pct"].idxmax(), "department_name"]
    worst = supplier.loc[supplier["on_time_pct"].idxmin(), "department_name"]

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Total Suppliers", f"{len(supplier)}")
    with c2:
        kpi_card("Best On-Time Supplier", best, good=True)
    with c3:
        kpi_card("Worst On-Time Supplier", worst, good=False)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── On-time rate by supplier
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("✅ On-Time Rate by Supplier")
        fig = px.bar(
            supplier.sort_values("on_time_pct"),
            x="on_time_pct", y="department_name",
            orientation="h",
            color="on_time_pct",
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            labels={"on_time_pct": "On-Time %", "department_name": "Supplier"}
        )
        fig.update_layout(
            height=450, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("⏱️ Avg Lead Time by Supplier")
        fig2 = px.bar(
            supplier.sort_values("avg_lead_time", ascending=False),
            x="avg_lead_time", y="department_name",
            orientation="h",
            color="avg_lead_time",
            color_continuous_scale="Blues",
            labels={"avg_lead_time": "Avg Days", "department_name": "Supplier"}
        )
        fig2.update_layout(
            height=450, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Supplier scatter: revenue vs on-time rate
    st.subheader("💰 Revenue vs On-Time Rate (Bubble = Total Orders)")
    fig3 = px.scatter(
        supplier,
        x="on_time_pct", y="total_revenue",
        size="total_orders", color="cancel_pct",
        hover_name="department_name",
        color_continuous_scale="RdYlGn_r",
        labels={
            "on_time_pct"   : "On-Time Rate (%)",
            "total_revenue" : "Total Revenue ($)",
            "cancel_pct"    : "Cancellation %"
        }
    )
    fig3.update_layout(
        height=400, plot_bgcolor="#0f2034",
        paper_bgcolor="#0f2034", font_color="white"
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Supplier table
    st.subheader("📋 Full Supplier Metrics Table")
    display_cols = {
        "department_name": "Supplier",
        "total_orders"   : "Orders",
        "total_revenue"  : "Revenue ($)",
        "on_time_pct"    : "On-Time %",
        "fulfill_pct"    : "Fulfillment %",
        "cancel_pct"     : "Cancellation %",
        "perfect_pct"    : "Perfect Order %",
        "avg_lead_time"  : "Avg Lead Time (days)",
        "avg_delay"      : "Avg Delay (days)",
    }
    st.dataframe(
        supplier[list(display_cols.keys())]
        .rename(columns=display_cols)
        .sort_values("Revenue ($)", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
        height=400
    )


# ─────────────────────────────────────────
# PAGE 3 — INVENTORY & FULFILLMENT
# ─────────────────────────────────────────
def page_inventory_fulfillment(df: pd.DataFrame):
    st.title("📦 Inventory & Fulfillment")
    st.caption("Product movement, category performance, and fulfillment analysis")
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    fulfill_rate = df["is_fulfilled"].mean() * 100
    cancel_rate  = df["is_cancelled"].mean() * 100
    total_qty    = df["quantity"].sum()
    avg_qty      = df["quantity"].mean()

    with c1: kpi_card("Fulfillment Rate",    f"{fulfill_rate:.1f}%", good=fulfill_rate>90)
    with c2: kpi_card("Cancellation Rate",   f"{cancel_rate:.1f}%",  good=cancel_rate<5)
    with c3: kpi_card("Total Units Sold",    f"{total_qty:,.0f}")
    with c4: kpi_card("Avg Units Per Order", f"{avg_qty:.1f}")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Units Sold by Category")
        cat_qty = (
            df.groupby("category")
            .agg(qty=("quantity","sum"), revenue=("sales","sum"))
            .reset_index()
            .sort_values("qty", ascending=False)
        )
        fig = px.bar(
            cat_qty, x="category", y="qty",
            color="revenue", color_continuous_scale="Blues",
            labels={"qty": "Units Sold", "category": "Category"}
        )
        fig.update_layout(
            height=380, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white",
            xaxis_tickangle=-35
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🎯 Fulfillment Rate by Category")
        cat_fulfill = (
            df.groupby("category")
            .agg(fulfill=("is_fulfilled","mean"),
                 cancel=("is_cancelled","mean"))
            .reset_index()
        )
        cat_fulfill["fulfill_pct"] = (cat_fulfill["fulfill"] * 100).round(1)
        cat_fulfill["cancel_pct"]  = (cat_fulfill["cancel"]  * 100).round(1)

        fig2 = px.bar(
            cat_fulfill.sort_values("fulfill_pct"),
            x="fulfill_pct", y="category",
            orientation="h",
            color="fulfill_pct",
            color_continuous_scale="RdYlGn",
            range_color=[80, 100],
            labels={"fulfill_pct": "Fulfillment %", "category": "Category"}
        )
        fig2.update_layout(
            height=380, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Order status breakdown
    st.subheader("📋 Order Status Distribution")
    status_df = (
        df.groupby("order_status")
        .agg(count=("order_id","count"), revenue=("sales","sum"))
        .reset_index()
        .sort_values("count", ascending=False)
    )
    fig3 = px.bar(
        status_df, x="order_status", y="count",
        color="revenue", color_continuous_scale="Blues",
        labels={"count": "Orders", "order_status": "Status",
                "revenue": "Revenue ($)"}
    )
    fig3.update_layout(
        height=350, plot_bgcolor="#0f2034",
        paper_bgcolor="#0f2034", font_color="white"
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Monthly fulfillment trend
    st.subheader("📈 Monthly Fulfillment & Cancellation Trend")
    monthly = (
        df.groupby(["year", "month"])
        .agg(
            fulfill_rate=("is_fulfilled", "mean"),
            cancel_rate =("is_cancelled", "mean"),
        )
        .reset_index()
        .sort_values(["year","month"])
    )
    monthly["period"]       = monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2)
    monthly["fulfill_pct"]  = (monthly["fulfill_rate"] * 100).round(2)
    monthly["cancel_pct"]   = (monthly["cancel_rate"]  * 100).round(2)

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=monthly["period"], y=monthly["fulfill_pct"],
        name="Fulfillment %", line=dict(color="#00e676", width=2), mode="lines+markers"
    ))
    fig4.add_trace(go.Scatter(
        x=monthly["period"], y=monthly["cancel_pct"],
        name="Cancellation %", line=dict(color="#ff5252", width=2), mode="lines+markers"
    ))
    fig4.update_layout(
        height=350, plot_bgcolor="#0f2034",
        paper_bgcolor="#0f2034", font_color="white",
        legend=dict(orientation="h")
    )
    st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────
# PAGE 4 — COST & RISK
# ─────────────────────────────────────────
def page_cost_risk(df: pd.DataFrame):
    st.title("💰 Cost & Risk Analysis")
    st.caption("Profit margins, cost per order, and revenue at risk")
    st.markdown("---")

    total_rev    = df["sales"].sum()
    total_profit = df["profit"].sum()
    avg_margin   = df["profit_margin_pct"].mean()
    rev_at_risk  = df["revenue_at_risk"].sum()
    risk_pct     = (rev_at_risk / total_rev * 100) if total_rev > 0 else 0
    avg_cost     = df["cost_per_order"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Revenue",      f"${total_rev:,.0f}")
    with c2: kpi_card("Total Profit",       f"${total_profit:,.0f}")
    with c3: kpi_card("Avg Profit Margin",  f"{avg_margin:.1f}%", good=avg_margin>15)
    with c4: kpi_card("Revenue At Risk",    f"${rev_at_risk:,.0f}", good=risk_pct<5)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Profit Margin by Category")
        cat_margin = (
            df.groupby("category")
            .agg(
                revenue=("sales","sum"),
                profit =("profit","sum"),
                margin =("profit_margin_pct","mean")
            )
            .reset_index()
            .sort_values("margin", ascending=False)
        )
        fig = px.bar(
            cat_margin, x="margin", y="category",
            orientation="h",
            color="margin",
            color_continuous_scale="RdYlGn",
            labels={"margin": "Avg Margin %", "category": "Category"}
        )
        fig.update_layout(
            height=420, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("⚠️ Revenue At Risk by Market")
        risk_market = (
            df.groupby("market")
            .agg(
                at_risk  =("revenue_at_risk","sum"),
                revenue  =("sales","sum"),
            )
            .reset_index()
        )
        risk_market["risk_pct"] = (
            risk_market["at_risk"] / risk_market["revenue"] * 100
        ).round(2)

        fig2 = px.bar(
            risk_market.sort_values("at_risk", ascending=False),
            x="market", y="at_risk",
            color="risk_pct",
            color_continuous_scale="Reds",
            labels={"at_risk": "Revenue At Risk ($)",
                    "market": "Market", "risk_pct": "Risk %"}
        )
        fig2.update_layout(
            height=420, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Cost per order by shipping mode
    st.subheader("🚚 Avg Cost Per Order by Shipping Mode")
    ship_cost = (
        df.groupby("shipping_mode")
        .agg(
            avg_cost   =("cost_per_order","mean"),
            avg_margin =("profit_margin_pct","mean"),
            total_orders=("order_id","count")
        )
        .reset_index()
        .sort_values("avg_cost", ascending=False)
    )
    fig3 = px.bar(
        ship_cost, x="shipping_mode", y="avg_cost",
        color="avg_margin",
        color_continuous_scale="RdYlGn",
        text=ship_cost["avg_cost"].apply(lambda x: f"${x:,.0f}"),
        labels={"avg_cost": "Avg Cost ($)",
                "shipping_mode": "Shipping Mode",
                "avg_margin": "Avg Margin %"}
    )
    fig3.update_traces(textposition="outside")
    fig3.update_layout(
        height=350, plot_bgcolor="#0f2034",
        paper_bgcolor="#0f2034", font_color="white"
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ── Monthly profit trend
    st.subheader("📈 Monthly Profit Margin Trend")
    monthly = (
        df.groupby(["year","month"])
        .agg(margin=("profit_margin_pct","mean"),
             revenue=("sales","sum"),
             profit =("profit","sum"))
        .reset_index()
        .sort_values(["year","month"])
    )
    monthly["period"] = (
        monthly["year"].astype(str) + "-" +
        monthly["month"].astype(str).str.zfill(2)
    )
    fig4 = px.line(
        monthly, x="period", y="margin",
        markers=True,
        labels={"margin": "Avg Margin %", "period": "Month"},
        color_discrete_sequence=["#00e676"]
    )
    fig4.add_hline(
        y=monthly["margin"].mean(),
        line_dash="dash", line_color="#ffeb3b",
        annotation_text="Avg"
    )
    fig4.update_layout(
        height=350, plot_bgcolor="#0f2034",
        paper_bgcolor="#0f2034", font_color="white"
    )
    st.plotly_chart(fig4, use_container_width=True)


# ─────────────────────────────────────────
# PAGE 5 — PIPELINE MONITOR
# ─────────────────────────────────────────
def page_pipeline_monitor(df: pd.DataFrame):
    st.title("🔄 Pipeline Monitor")
    st.caption("Data freshness, order trends, and operational health checks")
    st.markdown("---")

    # ── Data health checks
    st.subheader("🩺 Data Health Checks")

    checks = {
        "Total Records"         : len(df),
        "Null order_id"         : df["order_id"].isnull().sum(),
        "Null sales"            : df["sales"].isnull().sum(),
        "Null delivery_status"  : df["delivery_status"].isnull().sum(),
        "Negative profit rows"  : (df["profit"] < 0).sum(),
        "Zero sales rows"       : (df["sales"] == 0).sum(),
        "Duplicate order_items" : df.duplicated(subset=["order_item_id"]).sum(),
    }

    ch1, ch2, ch3, ch4 = st.columns(4)
    cols = [ch1, ch2, ch3, ch4]
    for i, (label, val) in enumerate(checks.items()):
        with cols[i % 4]:
            good = val == 0 if "Null" in label or "Duplicate" in label else True
            kpi_card(label, f"{val:,}", good=good)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Order volume over time
    st.subheader("📦 Daily Order Volume")
    daily = (
        df.assign(date=pd.to_datetime(df["order_date"]).dt.date)
        .groupby("date")
        .agg(orders=("order_id","count"), revenue=("sales","sum"))
        .reset_index()
    )
    fig = px.line(
        daily, x="date", y="orders",
        labels={"orders": "Orders", "date": "Date"},
        color_discrete_sequence=["#2d6a9f"]
    )
    fig.update_layout(
        height=320, plot_bgcolor="#0f2034",
        paper_bgcolor="#0f2034", font_color="white"
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📅 Orders by Day of Week")
        dow_order = ["Monday","Tuesday","Wednesday",
                     "Thursday","Friday","Saturday","Sunday"]
        dow = (
            df.groupby("order_dow")
            .agg(orders=("order_id","count"))
            .reindex(dow_order)
            .reset_index()
        )
        fig2 = px.bar(
            dow, x="order_dow", y="orders",
            color="orders", color_continuous_scale="Blues",
            labels={"order_dow": "Day", "orders": "Orders"}
        )
        fig2.update_layout(
            height=320, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white"
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("🕐 Orders by Quarter")
        qtr = (
            df.groupby(["year","quarter"])
            .agg(orders=("order_id","count"),
                 revenue=("sales","sum"))
            .reset_index()
        )
        qtr["label"] = "Q" + qtr["quarter"].astype(str) + " " + qtr["year"].astype(str)
        fig3 = px.bar(
            qtr, x="label", y="revenue",
            color="orders", color_continuous_scale="Blues",
            labels={"label": "Quarter", "revenue": "Revenue ($)",
                    "orders": "Orders"}
        )
        fig3.update_layout(
            height=320, plot_bgcolor="#0f2034",
            paper_bgcolor="#0f2034", font_color="white"
        )
        st.plotly_chart(fig3, use_container_width=True)

    # ── KPI health scorecard
    st.subheader("🎯 KPI Health Scorecard")

    scorecard = {
        "On-Time Delivery Rate"  : (df["on_time_flag"].mean()*100,   70, "%"),
        "Fulfillment Rate"       : (df["is_fulfilled"].mean()*100,    90, "%"),
        "Cancellation Rate"      : (df["is_cancelled"].mean()*100,     5, "%"),
        "Perfect Order Rate"     : (df["perfect_order_flag"].mean()*100, 70, "%"),
        "Avg Profit Margin"      : (df["profit_margin_pct"].mean(),   15, "%"),
    }

    for kpi_name, (value, threshold, unit) in scorecard.items():
        if "Cancellation" in kpi_name:
            status = "🟢 GOOD" if value < threshold else "🔴 AT RISK"
            color  = "green"   if value < threshold else "red"
        else:
            status = "🟢 GOOD" if value >= threshold else "🔴 AT RISK"
            color  = "green"   if value >= threshold else "red"

        col_a, col_b, col_c, col_d = st.columns([3,2,2,2])
        with col_a: st.write(f"**{kpi_name}**")
        with col_b: st.write(f"{value:.1f}{unit}")
        with col_c: st.write(f"Target: {threshold}{unit}")
        with col_d: st.markdown(f":{color}[{status}]")


# ─────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────
def main():
    conn = get_connection()
    df   = load_base_data(conn)
    df   = render_sidebar(df)

    pages = {
        "📊 Executive Summary"      : page_executive_summary,
        "🏭 Supplier Performance"   : page_supplier_performance,
        "📦 Inventory & Fulfillment": page_inventory_fulfillment,
        "💰 Cost & Risk"            : page_cost_risk,
        "🔄 Pipeline Monitor"       : page_pipeline_monitor,
    }

    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 Pages")
    page = st.sidebar.radio(
        "Navigate", list(pages.keys()), label_visibility="collapsed"
    )

    pages[page](df)

    st.sidebar.markdown("---")
    st.sidebar.caption("FlowMetrics v1.0")


if __name__ == "__main__":
    main()