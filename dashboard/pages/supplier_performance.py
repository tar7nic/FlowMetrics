import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components.kpi_cards import render_kpi_row
from components.charts import bar_chart, scatter_chart, heatmap

st.set_page_config(page_title="Supplier Performance", layout="wide")

@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(__file__), "../../data/processed/transformed_orders.parquet")
    return pd.read_parquet(path)

df = load_data()

st.sidebar.header("🔍 Filters")
regions = ["All"] + sorted(df["Order Region"].dropna().unique().tolist())
selected_region = st.sidebar.selectbox("Region", regions)

fdf = df.copy()
if selected_region != "All":
    fdf = fdf[fdf["Order Region"] == selected_region]

st.markdown("## 🏭 Supplier Performance")

# ── KPI cards ─────────────────────────────────────────────────────────────────
avg_delay = fdf["delivery_delay_days"].mean() if "delivery_delay_days" in fdf.columns else 0
on_time   = fdf["on_time_flag"].mean() * 100 if "on_time_flag" in fdf.columns else 0
total_suppliers = fdf["supplier_name"].nunique() if "supplier_name" in fdf.columns else 0
late_shipments = (fdf["delivery_delay_days"] > 0).sum() if "delivery_delay_days" in fdf.columns else 0

render_kpi_row([
    {"label": "Avg Delivery Delay",   "value": f"{avg_delay:.1f}", "suffix": " days", "color": "#f59e0b"},
    {"label": "On-Time Delivery Rate","value": f"{on_time:.1f}",   "suffix": "%",     "color": "#00d4aa"},
    {"label": "Total Suppliers",      "value": str(total_suppliers),                  "color": "#4f8ef7"},
    {"label": "Late Shipments",       "value": f"{late_shipments:,}",                "color": "#ff4b6e"},
])

st.divider()

# ── Supplier delay ranking ────────────────────────────────────────────────────
if "supplier_name" in fdf.columns and "delivery_delay_days" in fdf.columns:
    col1, col2 = st.columns(2)

    with col1:
        sup_delay = (fdf.groupby("supplier_name")
                       .agg(avg_delay=("delivery_delay_days", "mean"),
                            order_count=("Sales", "count"))
                       .reset_index()
                       .sort_values("avg_delay", ascending=False)
                       .head(15))
        sup_delay.columns = ["Supplier", "Avg Delay (days)", "Orders"]
        st.plotly_chart(bar_chart(sup_delay, "Avg Delay (days)", "Supplier",
                                  "⏱️ Top 15 Suppliers by Avg Delay", orientation="h"),
                        use_container_width=True)

    with col2:
        sup_ontime = (fdf.groupby("supplier_name")
                        .agg(on_time_rate=("on_time_flag", "mean"),
                             orders=("Sales", "count"))
                        .reset_index())
        sup_ontime["on_time_rate"] = sup_ontime["on_time_rate"] * 100
        sup_ontime.columns = ["Supplier", "On-Time Rate %", "Orders"]
        st.plotly_chart(scatter_chart(sup_ontime, "Orders", "On-Time Rate %",
                                      "📦 Supplier Volume vs On-Time Rate",
                                      size="Orders"),
                        use_container_width=True)

# ── Heatmap: Region x Shipping Mode ──────────────────────────────────────────
if "Order Region" in fdf.columns and "Shipping Mode" in fdf.columns:
    st.markdown("### 🔥 Avg Delivery Delay: Region × Shipping Mode")
    try:
        st.plotly_chart(heatmap(fdf, "Shipping Mode", "Order Region",
                                "delivery_delay_days",
                                "Avg Delivery Delay (days)"),
                        use_container_width=True)
    except Exception:
        st.warning("Not enough data for heatmap with current filters.")

# ── Raw supplier table ────────────────────────────────────────────────────────
if "supplier_name" in fdf.columns:
    with st.expander("📋 Supplier Detail Table"):
        tbl = (fdf.groupby("supplier_name")
                  .agg(
                      Orders=("Sales", "count"),
                      Avg_Delay=("delivery_delay_days", "mean"),
                      On_Time_Rate=("on_time_flag", "mean"),
                      Avg_Margin=("profit_margin", "mean"),
                  )
                  .reset_index()
                  .sort_values("On_Time_Rate", ascending=False))
        tbl["On_Time_Rate"] = (tbl["On_Time_Rate"] * 100).round(1).astype(str) + "%"
        tbl["Avg_Delay"]    = tbl["Avg_Delay"].round(2)
        tbl["Avg_Margin"]   = (tbl["Avg_Margin"] * 100).round(1).astype(str) + "%"
        st.dataframe(tbl, use_container_width=True)