import streamlit as st
import pandas as pd
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from components.kpi_cards import render_kpi_row
from components.charts import bar_chart, scatter_chart, line_chart

st.set_page_config(page_title="Cost & Risk", layout="wide")

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

st.markdown("## 💰 Cost & Risk Analysis")

# ── KPIs ──────────────────────────────────────────────────────────────────────
profit_margin   = fdf["profit_margin"].mean() * 100 if "profit_margin" in fdf.columns else 0
cost_per_order  = (fdf["Order Item Total"].sum() / len(fdf)) if "Order Item Total" in fdf.columns else 0
revenue_at_risk = fdf.loc[fdf.get("delivery_delay_days", pd.Series(0)) > 3, "Sales"].sum() \
                  if "delivery_delay_days" in fdf.columns else 0
total_benefit   = fdf["Benefit per order"].sum() if "Benefit per order" in fdf.columns else 0

render_kpi_row([
    {"label": "Avg Profit Margin",  "value": f"{profit_margin:.1f}",  "suffix": "%",
     "color": "#00d4aa" if profit_margin > 0 else "#ff4b6e"},
    {"label": "Cost Per Order",     "value": f"${cost_per_order:.2f}",                 "color": "#4f8ef7"},
    {"label": "Revenue at Risk",    "value": f"${revenue_at_risk/1e3:.1f}K",           "color": "#ff4b6e"},
    {"label": "Total Benefit",      "value": f"${total_benefit/1e6:.2f}M",             "color": "#34d399"},
])

st.divider()

col1, col2 = st.columns(2)

with col1:
    if "Category Name" in fdf.columns and "profit_margin" in fdf.columns:
        cat_margin = (fdf.groupby("Category Name")["profit_margin"]
                        .mean().mul(100).reset_index()
                        .sort_values("profit_margin", ascending=True))
        cat_margin.columns = ["Category", "Profit Margin %"]
        st.plotly_chart(bar_chart(cat_margin, "Profit Margin %", "Category",
                                  "💰 Profit Margin by Category", orientation="h"),
                        use_container_width=True)

with col2:
    if "Sales" in fdf.columns and "profit_margin" in fdf.columns:
        sample = fdf.sample(min(3000, len(fdf)), random_state=42)
        st.plotly_chart(scatter_chart(sample, "Sales", "profit_margin",
                                      "📊 Sales vs Profit Margin",
                                      color="Category Name" if "Category Name" in fdf.columns else None),
                        use_container_width=True)

# ── Revenue at risk trend ─────────────────────────────────────────────────────
if "order date (DateOrders)" in fdf.columns and "delivery_delay_days" in fdf.columns:
    fdf["order_month"] = pd.to_datetime(fdf["order date (DateOrders)"], errors="coerce").dt.to_period("M").astype(str)
    risk_df = (fdf[fdf["delivery_delay_days"] > 3]
                  .groupby("order_month")["Sales"]
                  .sum()
                  .reset_index()
                  .tail(18))
    risk_df.columns = ["Month", "Revenue at Risk ($)"]
    st.plotly_chart(line_chart(risk_df, "Month", "Revenue at Risk ($)",
                               "⚠️ Monthly Revenue at Risk (Delayed >3 Days)"),
                    use_container_width=True)