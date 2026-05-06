import streamlit as st
import pandas as pd
import json, os
from datetime import datetime

st.set_page_config(page_title="Pipeline Monitor", layout="wide")

st.markdown("## ⚙️ Pipeline Monitor")

LOG_PATH = os.path.join(os.path.dirname(__file__), "../../pipelines/pipeline_log.json")

@st.cache_data(ttl=30)
def load_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return json.load(f)

log = load_log()

if not log:
    st.warning("No pipeline runs found. Run `pipelines/run_pipeline.py` first.")
else:
    df_log = pd.DataFrame(log)

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    total_runs  = len(df_log)
    success     = (df_log["status"] == "SUCCESS").sum()
    failed      = (df_log["status"] == "FAILED").sum()
    last_run    = df_log["run_time"].max()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Runs",    total_runs)
    col2.metric("✅ Successful", success)
    col3.metric("❌ Failed",     failed)
    col4.metric("Last Run",      last_run[:19] if last_run else "—")

    st.divider()

    # ── Full log table ─────────────────────────────────────────────────────────
    st.markdown("### 📋 Run History")
    st.dataframe(
        df_log.sort_values("run_time", ascending=False).reset_index(drop=True),
        use_container_width=True
    )

    # ── Duration trend ────────────────────────────────────────────────────────
    if "duration_seconds" in df_log.columns:
        import plotly.express as px
        fig = px.bar(df_log.tail(20), x="run_time", y="duration_seconds",
                     color="status",
                     color_discrete_map={"SUCCESS": "#00d4aa", "FAILED": "#ff4b6e"},
                     title="Pipeline Run Duration")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="#c9d1d9"))
        st.plotly_chart(fig, use_container_width=True)

# ── Manual refresh ────────────────────────────────────────────────────────────
if st.button("🔄 Refresh Log"):
    st.cache_data.clear()
    st.rerun()