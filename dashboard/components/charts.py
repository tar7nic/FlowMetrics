import plotly.express as px
import plotly.graph_objects as go

COLORS = ["#00d4aa", "#4f8ef7", "#ff4b6e", "#f59e0b", "#a78bfa", "#34d399"]

LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#c9d1d9", family="monospace"),
    xaxis=dict(gridcolor="#2d3748", zerolinecolor="#2d3748"),
    yaxis=dict(gridcolor="#2d3748", zerolinecolor="#2d3748"),
    margin=dict(l=20, r=20, t=40, b=20),
)


def bar_chart(df, x, y, title, color=None, orientation="v"):
    fig = px.bar(
        df, x=x, y=y, title=title,
        color=color or y,
        color_continuous_scale=["#1a1f2e", "#00d4aa"],
        orientation=orientation,
    )
    fig.update_layout(**LAYOUT)
    fig.update_traces(marker_line_width=0)
    return fig


def line_chart(df, x, y, title, color=None):
    fig = px.line(df, x=x, y=y, title=title, color=color, markers=True)
    fig.update_layout(**LAYOUT)
    fig.update_traces(line_width=2)
    return fig


def pie_chart(df, names, values, title):
    fig = px.pie(
        df, names=names, values=values, title=title,
        color_discrete_sequence=COLORS,
        hole=0.45,
    )
    fig.update_layout(**LAYOUT)
    return fig


def scatter_chart(df, x, y, title, color=None, size=None):
    fig = px.scatter(
        df, x=x, y=y, title=title,
        color=color, size=size,
        color_discrete_sequence=COLORS,
    )
    fig.update_layout(**LAYOUT)
    return fig


def heatmap(df, x, y, z, title):
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0, "#1a1f2e"], [1, "#00d4aa"]],
    ))
    fig.update_layout(title=title, **LAYOUT)
    return fig


def gauge(value, title, min_val=0, max_val=100, threshold=75):
    color = "#00d4aa" if value >= threshold else "#ff4b6e"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"color": "#c9d1d9"}},
        number={"font": {"color": color}},
        gauge={
            "axis": {"range": [min_val, max_val], "tickcolor": "#2d3748"},
            "bar": {"color": color},
            "bgcolor": "#1a1f2e",
            "bordercolor": "#2d3748",
            "steps": [
                {"range": [min_val, threshold], "color": "#2d3748"},
                {"range": [threshold, max_val], "color": "#1a1f2e"},
            ],
            "threshold": {
                "line": {"color": "#f59e0b", "width": 2},
                "thickness": 0.75,
                "value": threshold,
            },
        },
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#c9d1d9"), height=220)
    return fig