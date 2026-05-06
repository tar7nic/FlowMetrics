import streamlit as st

def render_kpi_card(label, value, delta=None, prefix="", suffix="", color="#00d4aa"):
    delta_html = ""
    if delta is not None:
        arrow = "▲" if delta >= 0 else "▼"
        delta_color = "#00d4aa" if delta >= 0 else "#ff4b6e"
        delta_html = f'<div style="color:{delta_color};font-size:0.8rem;margin-top:4px;">{arrow} {abs(delta):.1f}% vs last period</div>'

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid {color}33;
        border-left: 4px solid {color};
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 8px;
    ">
        <div style="color:#8892a4;font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;">{label}</div>
        <div style="color:#f0f4f8;font-size:1.8rem;font-weight:700;margin-top:6px;">{prefix}{value}{suffix}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_kpi_row(kpis: list):
    """
    kpis: list of dicts with keys: label, value, delta (opt), prefix, suffix, color (opt)
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            render_kpi_card(
                label=kpi.get("label", ""),
                value=kpi.get("value", "—"),
                delta=kpi.get("delta", None),
                prefix=kpi.get("prefix", ""),
                suffix=kpi.get("suffix", ""),
                color=kpi.get("color", "#00d4aa"),
            )