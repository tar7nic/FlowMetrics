import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components.kpi_cards import render_kpi_row
from components.charts import bar_chart, line_chart, pie_chart, gauge

st.set_page_config(page_title="Executive Summary", layout="wide")

# ── Load data ────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(__file__), "../../data/processed/transformed_orders.parquet")
    return pd.read_parquet(path)

df = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filters")
regions = ["All"] + sorted(df["Order Region"].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Region", regions)

categories = ["All"] + sorted(df["Category Name"].dropna().unique().tolist())
selected_cat = st.sidebar.selectbox("Category", categories)

# Apply filters
fdf = df.copy()
if selected_region != "All":
    fdf = fdf[fdf["Order Region"] == selected_region]
if selected_cat != "All":
    fdf = fdf[fdf["Category Name"] == selected_cat]

# ── KPIs ──────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Executive Summary")
st.caption(f"Showing **{len(fdf):,}** orders · Region: `{selected_region}` · Category: `{selected_cat}`")

on_time_rate = fdf["on_time_flag"].mean() * 100 if "on_time_flag" in fdf.columns else 0
fulfillment_rate = fdf["fulfillment_rate"].mean() * 100 if "fulfillment_rate" in fdf.columns else 0
avg_delay = fdf["delivery_delay_days"].mean() if "delivery_delay_days" in fdf.columns else 0
profit_margin = fdf["profit_margin"].mean() * 100 if "profit_margin" in fdf.columns else 0
total_revenue = fdf["Sales"].sum() if "Sales" in fdf.columns else 0
cancelled = (fdf["Order Status"] == "CANCELED").mean() * 100 if "Order Status" in fdf.columns else 0

render_kpi_row([
    {"label": "On-Time Delivery Rate", "value": f"{on_time_rate:.1f}", "suffix": "%",
     "color": "#00d4aa" if on_time_rate >= 75 else "#ff4b6e"},
    {"label": "Fulfillment Rate",      "value": f"{fulfillment_rate:.1f}", "suffix": "%", "color": "#4f8ef7"},
    {"label": "Avg Delivery Delay",    "value": f"{avg_delay:.1f}", "suffix": " days", "color": "#f59e0b"},
    {"label": "Profit Margin",         "value": f"{profit_margin:.1f}", "suffix": "%", "color": "#a78bfa"},
    {"label": "Total Revenue",         "value": f"${total_revenue/1e6:.1f}M", "color": "#34d399"},
    {"label": "Cancelled Order Rate",  "value": f"{cancelled:.1f}", "suffix": "%",
     "color": "#ff4b6e" if cancelled > 5 else "#00d4aa"},
])

st.divider()

# ── Charts row 1 ──────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1.5, 1.5, 1])

with col1:
    if "order_month" not in fdf.columns and "order date (DateOrders)" in fdf.columns:
        fdf["order_month"] = pd.to_datetime(fdf["order date (DateOrders)"], errors="coerce").dt.to_period("M").astype(str)
    if "order_month" in fdf.columns:
        monthly = fdf.groupby("order_month")["Sales"].sum().reset_index().tail(18)
        st.plotly_chart(line_chart(monthly, "order_month", "Sales", "📈 Monthly Revenue Trend"), use_container_width=True)

with col2:
    if "Order Region" in fdf.columns:
        region_rev = fdf.groupby("Order Region")["Sales"].sum().reset_index().sort_values("Sales", ascending=False).head(10)
        st.plotly_chart(bar_chart(region_rev, "Order Region", "Sales", "🌍 Revenue by Region"), use_container_width=True)

with col3:
    if "Order Status" in fdf.columns:
        status_cnt = fdf["Order Status"].value_counts().reset_index()
        status_cnt.columns = ["Status", "Count"]
        st.plotly_chart(pie_chart(status_cnt, "Status", "Count", "🔄 Order Status Mix"), use_container_width=True)

# ── Charts row 2 ──────────────────────────────────────────────────────────────
col4, col5 = st.columns(2)

with col4:
    st.plotly_chart(gauge(on_time_rate, "On-Time Delivery Rate (%)", threshold=75), use_container_width=True)

with col5:
    if "Category Name" in fdf.columns:
        cat_margin = fdf.groupby("Category Name")["profit_margin"].mean().mul(100).reset_index()
        cat_margin.columns = ["Category", "Avg Profit Margin %"]
        cat_margin = cat_margin.sort_values("Avg Profit Margin %", ascending=True).tail(10)
        st.plotly_chart(bar_chart(cat_margin, "Avg Profit Margin %", "Category",
                                  "💰 Profit Margin by Category", orientation="h"), use_container_width=True)