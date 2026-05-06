import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components.kpi_cards import render_kpi_row
from components.charts import bar_chart, line_chart, gauge

st.set_page_config(page_title="Inventory & Fulfillment", layout="wide")

@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(__file__), "../../data/processed/transformed_orders.parquet")
    return pd.read_parquet(path)

df = load_data()

st.sidebar.header("🔍 Filters")
categories = ["All"] + sorted(df["Category Name"].dropna().unique().tolist())
selected_cat = st.sidebar.selectbox("Category", categories)

fdf = df.copy()
if selected_cat != "All":
    fdf = fdf[fdf["Category Name"] == selected_cat]

st.markdown("## 📦 Inventory & Fulfillment")

# ── KPIs ──────────────────────────────────────────────────────────────────────
fulfillment_rate = fdf["fulfillment_rate"].mean() * 100 if "fulfillment_rate" in fdf.columns else 0
cancelled_rate   = (fdf["Order Status"] == "CANCELED").mean() * 100 if "Order Status" in fdf.columns else 0
avg_qty_ordered  = fdf["Order Item Quantity"].mean() if "Order Item Quantity" in fdf.columns else 0
total_orders     = len(fdf)

render_kpi_row([
    {"label": "Fulfillment Rate",      "value": f"{fulfillment_rate:.1f}", "suffix": "%", "color": "#00d4aa"},
    {"label": "Cancelled Order Rate",  "value": f"{cancelled_rate:.1f}",  "suffix": "%",
     "color": "#ff4b6e" if cancelled_rate > 5 else "#00d4aa"},
    {"label": "Avg Order Qty",         "value": f"{avg_qty_ordered:.1f}", "color": "#4f8ef7"},
    {"label": "Total Orders",          "value": f"{total_orders:,}",      "color": "#a78bfa"},
])

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(gauge(fulfillment_rate, "Fulfillment Rate (%)", threshold=80), use_container_width=True)

with col2:
    if "Order Status" in fdf.columns:
        status_df = fdf["Order Status"].value_counts().reset_index()
        status_df.columns = ["Status", "Count"]
        st.plotly_chart(bar_chart(status_df, "Status", "Count", "📋 Orders by Status"),
                        use_container_width=True)

# ── Fulfillment trend ─────────────────────────────────────────────────────────
if "order date (DateOrders)" in fdf.columns and "fulfillment_rate" in fdf.columns:
    fdf["order_month"] = pd.to_datetime(fdf["order date (DateOrders)"], errors="coerce").dt.to_period("M").astype(str)
    monthly_fill = fdf.groupby("order_month")["fulfillment_rate"].mean().mul(100).reset_index().tail(18)
    monthly_fill.columns = ["Month", "Fulfillment Rate %"]
    st.plotly_chart(line_chart(monthly_fill, "Month", "Fulfillment Rate %",
                               "📈 Monthly Fulfillment Rate Trend"), use_container_width=True)

# ── Category breakdown ────────────────────────────────────────────────────────
if "Category Name" in fdf.columns:
    cat_fill = (fdf.groupby("Category Name")["fulfillment_rate"]
                   .mean().mul(100).reset_index()
                   .sort_values("fulfillment_rate", ascending=True))
    cat_fill.columns = ["Category", "Fulfillment Rate %"]
    st.plotly_chart(bar_chart(cat_fill, "Fulfillment Rate %", "Category",
                              "🗂️ Fulfillment Rate by Category", orientation="h"),
                    use_container_width=True)