import streamlit as st

st.set_page_config(page_title="TSTT | Financial Performance", page_icon="💰", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import (
    inject_css, page_header,
    line_chart, waterfall_chart, grouped_bar,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE,
    BLUE_DIM, GREEN_DIM, PURPLE_DIM, WHITE_DIM, WHITE_FAINT, BLUE_MED,
)

inject_css()
data = load_all_data()
fin    = data["Financial_Monthly"]
bridge = data["EBITDA_Bridge"]

# Compute AOP EBITDA margin from the scaled columns (already in TT$M and %)
fin["EBITDA_Margin_AOP"] = (fin["EBITDA_AOP"] / fin["Revenue_AOP"] * 100)

page_header("Financial Performance", "Revenue · EBITDA · PAT · Bridge")

# ── Latest-month metrics ──────────────────────────────────────────────────────
latest = fin.iloc[-1]
aop_margin = latest["EBITDA_Margin_AOP"]
m1, m2, m3, m4 = st.columns(4)

def vs(actual, plan, inverse=False):
    if plan and plan != 0:
        pct = (actual - plan) / abs(plan) * 100
        return f"{'↑' if pct > 0 else '↓'} {abs(pct):.1f}% vs AOP"
    return ""

m1.metric("Revenue",       f"TT${latest['Revenue']:,.0f}M",  vs(latest["Revenue"],  latest["Revenue_AOP"]))
m2.metric("EBITDA",        f"TT${latest['EBITDA']:,.0f}M",   vs(latest["EBITDA"],   latest["EBITDA_AOP"]))
m3.metric("PAT",           f"TT${latest['PAT']:,.0f}M",      vs(latest["PAT"],      latest["PAT_AOP"]))
m4.metric("EBITDA Margin", f"{latest['EBITDA_Margin']:.1f}%", f"{latest['EBITDA_Margin'] - aop_margin:+.1f}pp vs {aop_margin:.1f}% AOP")

st.markdown("---")

# ── Trend charts ──────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Revenue & EBITDA", "PAT & Margin", "EBITDA Bridge"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(
            fin, x="Month",
            y_cols=["Revenue", "Revenue_AOP", "Revenue_LY"],
            title="Revenue vs AOP vs LY (TT$M)",
            colors=[BLUE, BLUE_DIM, WHITE_DIM],
            dash_cols=["Revenue_AOP", "Revenue_LY"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = line_chart(
            fin, x="Month",
            y_cols=["EBITDA", "EBITDA_AOP", "EBITDA_LY"],
            title="EBITDA vs AOP vs LY (TT$M)",
            colors=[GREEN, GREEN_DIM, WHITE_DIM],
            dash_cols=["EBITDA_AOP", "EBITDA_LY"],
        )
        st.plotly_chart(fig, use_container_width=True)

    # Revenue vs EBITDA combined — secondary y-axis
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=fin["Month"], y=fin["Revenue"],
        name="Revenue", marker_color=BLUE_MED, yaxis="y1",
    ))
    fig2.add_trace(go.Scatter(
        x=fin["Month"], y=fin["EBITDA"],
        name="EBITDA", line=dict(color=GREEN, width=2),
        mode="lines+markers", marker=dict(size=6), yaxis="y1",
    ))
    fig2.add_trace(go.Scatter(
        x=fin["Month"], y=fin["EBITDA_Margin"],
        name="EBITDA Margin %", line=dict(color=YELLOW, width=2, dash="dot"),
        mode="lines+markers", marker=dict(size=5), yaxis="y2",
    ))
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=400,
        title=dict(text="<b>Revenue / EBITDA / Margin</b>", font=dict(size=13, color="white"), x=0),
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"), title="TT$M"),
        yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                    tickfont=dict(color="#8888aa"), showgrid=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=44, b=10),
        barmode="overlay",
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(
            fin, x="Month",
            y_cols=["PAT", "PAT_AOP", "PAT_LY"],
            title="Profit After Tax (TT$M)",
            colors=[PURPLE, PURPLE_DIM, WHITE_DIM],
            dash_cols=["PAT_AOP", "PAT_LY"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = line_chart(
            fin, x="Month",
            y_cols=["EBITDA_Margin"],
            title="EBITDA Margin (%)",
            colors=[YELLOW],
        )
        fig.add_hline(y=aop_margin, line_dash="dot", line_color=WHITE_FAINT,
                      annotation_text=f"AOP {aop_margin:.1f}%", annotation_font_color="#7788aa",
                      annotation_position="bottom right")
        st.plotly_chart(fig, use_container_width=True)

    # Revenue waterfall breakdown (actual vs AOP gap)
    fin_copy = fin.copy()
    fin_copy["Revenue_Gap"] = fin_copy["Revenue"] - fin_copy["Revenue_AOP"]
    fig = grouped_bar(
        fin_copy, x="Month",
        y_cols=["Revenue", "Revenue_AOP"],
        title="Revenue Actual vs AOP (TT$M)",
        colors=[BLUE, "#334466"],
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("#### EBITDA Bridge — YTD Apr 2026 (TT$M)")
    col1, col2 = st.columns([2, 1])
    with col1:
        fig = waterfall_chart(
            bridge,
            x_col="Category", y_col="Value", type_col="Type",
            title="EBITDA Bridge: AOP → Actual (TT$M)",
            height=460,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Bridge Components**")
        for _, row in bridge.iterrows():
            val = row["Value"]
            t   = row["Type"]
            if t == "Absolute":
                color = "🔵"
            elif t == "Positive":
                color = "🟢"
            elif t == "Negative":
                color = "🔴"
            else:
                color = "🔵"
            st.markdown(
                f"{color} **{row['Category']}** — `TT${val:,.0f}M`"
            )

        aop    = bridge[bridge["Sort_Order"] == 1]["Value"].values[0]
        actual = bridge.iloc[-1]["Value"]
        gap    = actual - aop
        st.markdown("---")
        st.metric("AOP EBITDA",    f"TT${aop:,.0f}M")
        st.metric("Actual EBITDA", f"TT${actual:,.0f}M", delta=f"TT${gap:+,.0f}M vs AOP")
