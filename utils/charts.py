import plotly.graph_objects as go
import streamlit as st

# ── Palette ──────────────────────────────────────────────────────────────────
GREEN  = "#00ff88"
RED    = "#FF4444"
BLUE   = "#4488ff"
YELLOW = "#FFD700"
PURPLE = "#aa44ff"
ORANGE = "#FF8844"
CYAN   = "#44EEFF"

def dim(hex_color, alpha=0.33):
    """Convert #rrggbb + alpha to rgba() — Plotly rejects 8-char hex."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

# Pre-computed alpha variants
BLUE_DIM    = dim(BLUE,   0.40)
GREEN_DIM   = dim(GREEN,  0.40)
PURPLE_DIM  = dim(PURPLE, 0.40)
WHITE_DIM   = "rgba(255,255,255,0.27)"
WHITE_FAINT = "rgba(255,255,255,0.20)"
BLUE_FAINT  = dim(BLUE,   0.33)
GREEN_FAINT = dim(GREEN,  0.33)
BLUE_MED    = dim(BLUE,   0.67)
GREEN_MED   = dim(GREEN,  0.67)

ACCENT = [BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW, RED]
BG      = "rgba(0,0,0,0)"
CARD_BG = "#161B22"
GRID    = "#1e1e3a"
TEXT    = "white"
MUTED   = "#8888aa"

# ── Base layout ──────────────────────────────────────────────────────────────
_BASE = dict(
    plot_bgcolor=BG,
    paper_bgcolor=BG,
    font=dict(color=TEXT, family="Inter, sans-serif", size=12),
    xaxis=dict(gridcolor=GRID, color=MUTED, showline=True, linecolor=GRID,
               tickfont=dict(color=MUTED, size=13)),
    yaxis=dict(gridcolor=GRID, color=MUTED, showline=False,
               tickfont=dict(color=MUTED, size=13)),
    margin=dict(l=10, r=10, t=44, b=10),
    legend=dict(bgcolor=BG, font=dict(color=TEXT, size=12),
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    hoverlabel=dict(bgcolor="#111128", font_color=TEXT, bordercolor="#333366"),
)


def _layout(fig, title="", height=380):
    layout = dict(_BASE)
    layout["title"] = dict(text=f"<b>{title}</b>", font=dict(size=13, color=TEXT), x=0, pad=dict(b=8))
    layout["height"] = height
    fig.update_layout(**layout)
    return fig


# ── Chart builders ───────────────────────────────────────────────────────────

def line_chart(df, x, y_cols, title="", colors=None, dash_cols=None, height=380, yformat=None):
    colors = colors or ACCENT
    dash_cols = dash_cols or []
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        is_ref = col in dash_cols
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col],
            name=col.replace("_", " "),
            mode="lines+markers",
            line=dict(color=colors[i % len(colors)], width=2 if not is_ref else 1,
                      dash="dot" if is_ref else "solid"),
            marker=dict(size=4 if is_ref else 6),
            opacity=0.55 if is_ref else 1.0,
        ))
    _layout(fig, title, height)
    if yformat:
        fig.update_yaxes(tickformat=yformat)
    return fig


def bar_chart(df, x, y, title="", color=BLUE, height=380, text=True, orientation="v"):
    vals = df[y].round(1)
    if orientation == "h":
        fig = go.Figure(go.Bar(y=df[x], x=df[y], orientation="h",
                               marker_color=color,
                               text=vals if text else None, textposition="outside",
                               textfont=dict(color=TEXT, size=12)))
    else:
        fig = go.Figure(go.Bar(x=df[x], y=df[y], marker_color=color,
                               text=vals if text else None, textposition="outside",
                               textfont=dict(color=TEXT, size=12)))
    _layout(fig, title, height)
    return fig


def grouped_bar(df, x, y_cols, title="", colors=None, height=380):
    colors = colors or ACCENT
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Bar(x=df[x], y=df[col], name=col.replace("_", " "),
                             marker_color=colors[i % len(colors)]))
    fig.update_layout(barmode="group")
    _layout(fig, title, height)
    return fig


def stacked_bar(df, x, y_cols, title="", colors=None, height=380):
    colors = colors or ACCENT
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Bar(x=df[x], y=df[col], name=col.replace("_", " "),
                             marker_color=colors[i % len(colors)]))
    fig.update_layout(barmode="stack")
    _layout(fig, title, height)
    return fig


def waterfall_chart(df, x_col, y_col, type_col, title="", height=440):
    measure_map = {"Absolute": "absolute", "Positive": "relative",
                   "Negative": "relative", "Total": "total"}
    measures = [measure_map.get(t, "relative") for t in df[type_col]]
    texts = []
    for v, m in zip(df[y_col], measures):
        if m == "relative":
            texts.append(f"{v:+,.0f}")
        else:
            texts.append(f"{v:,.0f}")
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=df[x_col],
        y=df[y_col],
        text=texts,
        textposition="outside",
        textfont=dict(color=TEXT, size=12),
        connector=dict(line=dict(color="#2a2a5a", width=1, dash="dot")),
        increasing=dict(marker=dict(color=GREEN)),
        decreasing=dict(marker=dict(color=RED)),
        totals=dict(marker=dict(color=BLUE)),
    ))
    _layout(fig, title, height)
    fig.update_layout(showlegend=False)
    return fig


def funnel_chart(stages, values, title="", height=380):
    fig = go.Figure(go.Funnel(
        y=stages, x=values,
        textinfo="value+percent initial",
        marker=dict(color=ACCENT[:len(stages)]),
        connector=dict(fillcolor=CARD_BG),
    ))
    _layout(fig, title, height)
    fig.update_layout(showlegend=False)
    return fig


def donut_chart(labels, values, title="", height=340):
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=ACCENT[:len(labels)], line=dict(color=CARD_BG, width=2)),
        textinfo="label+percent",
        textfont=dict(color=TEXT, size=11),
    ))
    _layout(fig, title, height)
    return fig


def variance_heatmap(df, index_col, columns_col, value_col, title="", height=320):
    pivot = df.pivot_table(index=index_col, columns=columns_col, values=value_col, aggfunc="first")
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[str(c) for c in pivot.columns],
        y=pivot.index.tolist(),
        colorscale=[[0, RED], [0.5, "#161B22"], [1, GREEN]],
        zmid=0,
        text=[[f"{v:.1f}%" if v == v else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(color=TEXT, size=11),
        showscale=True,
        colorbar=dict(tickfont=dict(color=TEXT),
                      title=dict(text="%", font=dict(color=TEXT))),
    ))
    _layout(fig, title, height)
    fig.update_yaxes(autorange="reversed")
    return fig


# ── CSS injection helper ──────────────────────────────────────────────────────

def inject_css():
    with open("assets/style.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def page_header(title, subtitle="", period="Apr-26"):
    st.markdown(f"""
    <div class="page-header">
        <div class="header-title">
            <span class="logo-mark">TSTT</span>
            <div>
                <h1 class="header-h1">{title}</h1>
                <p class="subtitle">{subtitle}</p>
            </div>
        </div>
        <div class="header-meta">
            <span class="period-badge">Period: {period}</span>
            <p class="subtitle" style="margin-top:4px;text-align:right">YTD FY2026</p>
        </div>
    </div>""", unsafe_allow_html=True)


def styled_metric(title, value_str, delta_str="", delta_positive=None, accent="#4488ff"):
    """Drop-in st.metric() replacement with a unique top-border accent colour."""
    if delta_str:
        if delta_positive is True:
            dc = "#00ff88"
        elif delta_positive is False:
            dc = "#FF4444"
        else:
            dc = "#7788aa"
        dh = (f'<div style="font-size:0.875rem;color:{dc};font-weight:600;'
              f'margin-top:4px">{delta_str}</div>')
    else:
        dh = ""
    st.markdown(f"""
<div style="background:#161B22;border-radius:10px;padding:14px 16px;
            border:1px solid #2a2a4a;border-top:3px solid {accent};
            margin-bottom:0.5rem">
    <div style="font-size:0.82rem;font-weight:600;color:#7788aa;text-transform:uppercase;
                letter-spacing:0.9px;margin-bottom:4px">{title}</div>
    <div style="font-size:1.4rem;font-weight:700;color:white;line-height:1.2">{value_str}</div>
    {dh}
</div>""", unsafe_allow_html=True)


def kpi_card(name, actual, unit, vs_aop_pct, vs_py_pct, status_emoji="", accent_color=None):
    """Renders a styled KPI card using st.markdown.

    accent_color: hex string (e.g. '#00d4a0') — overrides status-based border colour
                  so each metric can have a unique visual identity.
    """
    if accent_color:
        border_style = f"border-top: 3px solid {accent_color} !important;"
        border_class = ""
    else:
        status = str(status_emoji)
        if "🟢" in status:
            border = "green"
        elif "🔴" in status:
            border = "red"
        elif "🟡" in status:
            border = "yellow"
        else:
            border = "blue"
        border_class = f"{border}-border"
        border_style = ""

    from utils.rag import rev_var_rag
    aop_class = "green-text" if vs_aop_pct >= 0 else "red-text"
    py_color  = rev_var_rag(vs_py_pct)

    try:
        val_str = f"{actual:,.0f}"
    except (ValueError, TypeError):
        val_str = str(actual)

    st.markdown(f"""
    <div class="kpi-card {border_class}" style="{border_style}">
        <div class="kpi-name">{name}</div>
        <div class="kpi-value">{val_str}<span class="kpi-unit"> {unit}</span></div>
        <div class="kpi-meta">
            <span class="{aop_class}">AOP: {vs_aop_pct:+.1f}%</span>
            &nbsp;&nbsp;
            <span style="color:{py_color};font-weight:600">PY: {vs_py_pct:+.1f}%</span>
        </div>
    </div>""", unsafe_allow_html=True)
