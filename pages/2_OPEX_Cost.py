import streamlit as st

st.set_page_config(page_title="TSTT | OPEX & Cost", page_icon="📊", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import inject_css, page_header, GREEN, RED

inject_css()

# ── Viewport-fill CSS ─────────────────────────────────────────────────────────
# Strips bottom padding so the two panels reach the foot of the screen.
st.markdown("""
<style>
.main .block-container {
    padding-bottom: 0.5rem !important;
    min-height: calc(100vh - 60px) !important;
}
[data-testid="column"] { min-height: calc(100vh - 220px); }
</style>
""", unsafe_allow_html=True)

data = load_all_data()
opex = data["OPEX"]

page_header("OPEX & Cost Management", "Actual vs Plan · Cost-Out Tracking")

# ── Sidebar ───────────────────────────────────────────────────────────────────
months    = opex["Month"].unique().tolist()
sel_month = st.sidebar.selectbox("Focus Month", months, index=len(months) - 1)

latest       = opex[opex["Month"] == sel_month].copy()
total_actual = latest["Actual"].sum()
total_plan   = latest["Plan"].sum()
total_var    = total_actual - total_plan
var_pct      = total_var / total_plan * 100 if total_plan else 0

# ── Period badge ──────────────────────────────────────────────────────────────
st.markdown(
    f'<span style="background:#1a2744;color:#7eb8f7;padding:5px 14px;border-radius:12px;'
    f'font-size:13px;font-weight:600;border:1px solid #2a4080">Period: {sel_month}</span>',
    unsafe_allow_html=True,
)
st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

# ── Two-column layout ─────────────────────────────────────────────────────────
col_left, col_right = st.columns([3, 2])

# ════════════════════════════════════════════════════════════════════════════════
# LEFT — Horizontal bullet chart
# Chart height targets 32 px bar + 20 px gap per row.
# With figure margins (t=44, b=30) and legend (≈30 px):
#   slot_px = (height - 104) / n_cats
#   plan_width=0.70 → plan bar ≈ 0.70 × slot_px
#   actual_width=0.42 → actual bar ≈ 0.42 × slot_px  ≈ 33 px at target height
# ════════════════════════════════════════════════════════════════════════════════
with col_left:
    st.markdown("#### Category Breakdown — Actual vs Plan")

    cats       = latest.sort_values("Plan", ascending=True).copy()
    n          = len(cats)
    # 84 px per slot + 40 px fixed overhead gives ~33 px bars at 0.42 width
    fig_height = max(560, n * 84 + 40)
    bar_colors = ["#22c55e" if v <= 0 else "#ef4444" for v in cats["Variance"]]

    fig = go.Figure()

    # Plan bar — wide grey reference drawn first so Actual overlays it
    fig.add_trace(go.Bar(
        y=cats["Category"],
        x=cats["Plan"],
        orientation="h",
        name="Plan (AOP)",
        marker_color="rgba(90,90,130,0.28)",
        marker_line=dict(color="rgba(140,140,180,0.55)", width=1),
        width=0.70,
        hovertemplate="%{y}<br>Plan: TT$%{x:,.2f}M<extra></extra>",
    ))

    # Actual bar — narrower, coloured, value label outside
    fig.add_trace(go.Bar(
        y=cats["Category"],
        x=cats["Actual"],
        orientation="h",
        name="Actual",
        marker_color=bar_colors,
        width=0.42,
        text=[f"TT${v:,.2f}M" for v in cats["Actual"]],
        textposition="outside",
        textfont=dict(color="white", size=12),
        hovertemplate="%{y}<br>Actual: TT$%{x:,.2f}M<extra></extra>",
    ))

    fig.update_layout(
        barmode="overlay",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=fig_height,
        legend=dict(
            bgcolor="rgba(0,0,0,0)", orientation="h",
            y=1.05, x=0, xanchor="left", font=dict(size=13),
        ),
        xaxis=dict(
            gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=11),
            title=dict(text="TT$M", font=dict(color="#8888aa", size=11)),
            zeroline=True, zerolinecolor="#3a3a5a",
        ),
        yaxis=dict(
            gridcolor="#1e1e3a",
            tickfont=dict(color="white", size=13),
        ),
        margin=dict(l=10, r=120, t=44, b=30),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary line — amber label, variance in its own colour
    sign    = "+" if var_pct > 0 else ""
    var_col = "#ef4444" if total_var > 0 else "#22c55e"
    st.markdown(
        f'<p style="font-size:16px;font-weight:700;color:#f59e0b;margin-top:2px">'
        f'Total OPEX: TT${total_actual:,.2f}M &nbsp;vs Plan&nbsp; TT${total_plan:,.2f}M'
        f'&nbsp;(<span style="color:{var_col}">{sign}{var_pct:.1f}%</span>)'
        f'</p>',
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════════════════════════
# RIGHT — Top 5 movements + Cost-Out Programme
# ════════════════════════════════════════════════════════════════════════════════
with col_right:
    st.markdown("#### Top 5 Cost Movements")

    top5 = (
        latest
        .assign(_abs=latest["Variance"].abs())
        .sort_values("_abs", ascending=False)
        .head(5)
    )

    for rank, (_, row) in enumerate(top5.iterrows(), 1):
        var      = row["Variance"]
        vpct     = row["Variance_Pct"]
        color    = "#ef4444" if var > 0 else "#22c55e"
        badge_bg = "#3a1212" if var > 0 else "#0f2e1a"
        label    = "above plan" if var > 0 else "below plan"
        sign     = "+" if var > 0 else ""

        st.markdown(f"""
<div style="display:flex;align-items:center;margin-bottom:14px;padding:14px 16px;
            background:rgba(255,255,255,0.04);border-radius:10px;
            border-left:4px solid {color}">
    <div style="background:{badge_bg};color:{color};font-weight:800;font-size:13px;
                padding:5px 10px;border-radius:50%;min-width:30px;text-align:center;
                margin-right:14px;border:1px solid {color};flex-shrink:0">{rank}</div>
    <div style="flex:1;min-width:0">
        <div style="font-weight:700;font-size:15px;color:white;
                    margin-bottom:5px">{row['Category']}</div>
        <div style="font-size:12px;color:#8888aa;line-height:1.4">
            {abs(vpct):.1f}% {label} — TT${abs(row['Plan']):,.2f}M planned
        </div>
    </div>
    <div style="font-weight:800;font-size:15px;color:{color};
                text-align:right;white-space:nowrap;margin-left:12px">
        {sign}TT${var:,.2f}M
    </div>
</div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    st.markdown("---")

    # ── Cost-Out Programme ────────────────────────────────────────────────────
    st.markdown("#### Cost-Out Programme")
    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    # YTD: sum favorable variances (Plan > Actual) across all months
    ytd         = opex.groupby("Category", sort=False).agg(
        Actual=("Actual", "sum"), Plan=("Plan", "sum")
    ).reset_index()
    ytd_savings = (ytd["Plan"] - ytd["Actual"]).clip(lower=0).sum()
    ytd_oversp  = (ytd["Actual"] - ytd["Plan"]).clip(lower=0).sum()
    ytd_plan    = ytd["Plan"].sum()
    progress    = min(ytd_savings / ytd_plan * 100, 100) if ytd_plan else 0

    oversp_line = (
        f'<div style="margin-top:10px;font-size:12px;color:#ef4444;font-weight:600">'
        f'&#9650; TT${ytd_oversp:,.2f}M overspend across some categories</div>'
        if ytd_oversp > 0 else ""
    )

    st.markdown(f"""
<div style="background:rgba(255,255,255,0.04);border-radius:12px;padding:20px 20px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <span style="color:#aaaacc;font-size:14px;font-weight:500">YTD Savings vs AOP Budget</span>
        <span style="color:#22c55e;font-weight:800;font-size:22px">{progress:.1f}%</span>
    </div>
    <div style="background:#1e1e3a;border-radius:8px;height:20px;overflow:hidden;margin-bottom:14px">
        <div style="background:linear-gradient(90deg,#16a34a,#22c55e);
                    width:{progress:.1f}%;height:100%;border-radius:8px"></div>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:baseline">
        <div>
            <div style="color:#22c55e;font-size:18px;font-weight:700">TT${ytd_savings:,.2f}M</div>
            <div style="color:#6688aa;font-size:12px;margin-top:2px">saved YTD</div>
        </div>
        <div style="text-align:right">
            <div style="color:#aaaacc;font-size:18px;font-weight:700">TT${ytd_plan:,.2f}M</div>
            <div style="color:#6688aa;font-size:12px;margin-top:2px">AOP target</div>
        </div>
    </div>
    {oversp_line}
</div>""", unsafe_allow_html=True)
