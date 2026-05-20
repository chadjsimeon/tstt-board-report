import streamlit as st

st.set_page_config(page_title="TSTT | Financial Performance", page_icon="💰", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.rag import rev_var_rag
from utils.charts import (
    inject_css, page_header, styled_metric,
    line_chart, waterfall_chart, grouped_bar, stacked_bar,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
    BLUE_DIM, GREEN_DIM, PURPLE_DIM, WHITE_DIM, WHITE_FAINT, BLUE_MED,
)

inject_css()
data = load_all_data()
fin    = data["Financial_Monthly"]
bridge = data["EBITDA_Bridge"]
pnl    = data["PnL_Breakdown"]

# Compute AOP EBITDA margin from the scaled columns (already in  and %)
fin["EBITDA_Margin_AOP"] = (fin["EBITDA_AOP"] / fin["Revenue_AOP"] * 100)

page_header("Financial Performance", "Revenue · EBITDA · PAT · Bridge")

if fin.empty:
    st.info("No P&L data available. Please populate the P&L_Segments sheet in TSTT_Master_Data_Template.xlsx.")
    st.stop()

# ── Latest-month metrics ──────────────────────────────────────────────────────
latest = fin.iloc[-1]
aop_margin = latest["EBITDA_Margin_AOP"]
m1, m2, m3, m4 = st.columns(4)

def vs(actual, plan, inverse=False):
    if plan and plan != 0:
        pct = (actual - plan) / abs(plan) * 100
        return f"{'↑' if pct > 0 else '↓'} {abs(pct):.1f}% vs AOP"
    return ""

with m1:
    styled_metric("Revenue", f"{latest['Revenue']:,.0f}",
                  vs(latest["Revenue"], latest["Revenue_AOP"]),
                  latest["Revenue"] >= latest["Revenue_AOP"] if latest["Revenue_AOP"] else None,
                  "#00d4a0")
with m2:
    styled_metric("EBITDA", f"{latest['EBITDA']:,.0f}",
                  vs(latest["EBITDA"], latest["EBITDA_AOP"]),
                  latest["EBITDA"] >= latest["EBITDA_AOP"] if latest["EBITDA_AOP"] else None,
                  "#4a9eff")
with m3:
    styled_metric("PAT", f"{latest['PAT']:,.0f}",
                  vs(latest["PAT"], latest["PAT_AOP"]),
                  latest["PAT"] >= latest["PAT_AOP"] if latest["PAT_AOP"] else None,
                  "#aa44ff")
with m4:
    em_delta = latest["EBITDA_Margin"] - aop_margin
    styled_metric("EBITDA Margin", f"{latest['EBITDA_Margin']:.1f}%",
                  f"{em_delta:+.1f}pp vs {aop_margin:.1f}% AOP",
                  em_delta >= 0, "#FF8844")

st.markdown("---")

# ── Trend charts ──────────────────────────────────────────────────────────────
tab0, tab1, tab2, tab3 = st.tabs(["P&L Breakdown", "Revenue & EBITDA", "PAT & Margin", "EBITDA Bridge"])

with tab0:
    GROUPS      = ["CONSUMER SALES", "BUSINESS SALES", "AMPLIA", "DPDI", "OTHER"]
    GRP_COLORS  = [BLUE, GREEN, PURPLE, ORANGE, CYAN]
    GRP_LABELS  = ["Consumer", "Business", "Amplia", "DPDI", "Other"]
    rev_cols    = [f"{g}_Rev"     for g in GROUPS]
    cos_cols    = [f"{g}_COS"     for g in GROUPS]
    rev_aop_cols= [f"{g}_Rev_AOP" for g in GROUPS]

    latest_pnl = pnl.iloc[-1]

    # ── Two-column layout: left = trend charts stacked, right = Rev vs PY ───────
    col_left, col_right = st.columns(2)

    with col_left:
        fig = stacked_bar(
            pnl, x="Month", y_cols=rev_cols,
            title="Revenue by Group — Trend",
            colors=GRP_COLORS,
        )
        for i, trace in enumerate(fig.data):
            trace.name = GRP_LABELS[i] if i < len(GRP_LABELS) else trace.name
        st.plotly_chart(fig, use_container_width=True)

        pnl_abs = pnl.copy()
        for c in cos_cols:
            pnl_abs[c] = pnl_abs[c].abs()
        fig = stacked_bar(
            pnl_abs, x="Month", y_cols=cos_cols,
            title="Cost of Sales by Group (, abs)",
            colors=GRP_COLORS,
        )
        for i, trace in enumerate(fig.data):
            trace.name = GRP_LABELS[i] if i < len(GRP_LABELS) else trace.name
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        _lat_dt  = pd.to_datetime(latest_pnl["Month"], format="%b-%y", errors="coerce")
        _py_mon  = (_lat_dt - pd.DateOffset(months=12)).strftime("%b-%y") if pd.notna(_lat_dt) else None
        _py_pnl  = pnl[pnl["Month"] == _py_mon].iloc[0] if _py_mon and (_py_mon in pnl["Month"].values) else None

        act_vals = [float(latest_pnl[f"{g}_Rev"]) for g in GROUPS]
        py_vals  = [float(_py_pnl[f"{g}_Rev"]) if _py_pnl is not None else 0.0 for g in GROUPS]

        # Drop groups where both current and PY are zero
        _mask    = [not (a == 0.0 and p == 0.0) for a, p in zip(act_vals, py_vals)]
        _labels  = [l for l, m in zip(GRP_LABELS, _mask) if m]
        _colors  = [c for c, m in zip(GRP_COLORS, _mask) if m]
        act_vals = [v for v, m in zip(act_vals, _mask) if m]
        py_vals  = [v for v, m in zip(py_vals,  _mask) if m]
        var_vals = [a - p for a, p in zip(act_vals, py_vals)]

        _var_colors = [rev_var_rag((a - p) / p * 100 if p else None) for a, p in zip(act_vals, py_vals)]

        # Negative actual bars: suppress trace text (goes below axis), use annotation at y=0
        _ACT_OFFSET = 0.18
        _trace_text = [f"{v:+.1f}" if act_vals[i] >= 0 else "" for i, v in enumerate(var_vals)]
        _annotations = [
            dict(
                x=i + _ACT_OFFSET, y=0, xref="x", yref="y",
                text=f"{var_vals[i]:+.1f}",
                showarrow=False, yanchor="bottom", yshift=5,
                font=dict(color=_var_colors[i], size=16),
            )
            for i in range(len(_labels)) if act_vals[i] < 0
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=_labels, y=py_vals,
            name="Prior Year", marker_color="#2a3a5a",
            hovertemplate="%{x}<br>PY: %{y:,.2f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=_labels, y=act_vals,
            name="Actual", marker_color=_colors,
            text=_trace_text,
            textposition="outside",
            textfont=dict(color=_var_colors, size=16),
            cliponaxis=False,
            hovertemplate="%{x}<br>Actual: %{y:,.2f}<extra></extra>",
        ))

        _y_min = min(0, min(act_vals), min(py_vals)) * 1.15
        _y_max = max(max(act_vals), max(py_vals)) * 1.22

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=760, barmode="group",
            bargap=0.25, bargroupgap=0.08,
            title=dict(text=f"<b>{latest_pnl['Month']} Revenue vs PY by Group</b>",
                       font=dict(size=20, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#aaaacc", size=18)),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=18), range=[_y_min, _y_max]),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
                        orientation="h", y=1.02, x=1, xanchor="right"),
            margin=dict(l=10, r=10, t=44, b=10),
            annotations=_annotations,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Latest-month P&L waterfall ────────────────────────────────────
    st.markdown(f"#### {latest_pnl['Month']} — P&L Cascade")
    col5, col6 = st.columns([2, 1])
    with col5:
        total_rev  = latest_pnl["Total_Rev"]
        total_cos  = abs(latest_pnl["Total_COS"])   # stored positive; abs() handles any sign
        gross_prof = total_rev - total_cos
        total_opex = abs(latest_pnl["Total_OPEX"])
        ebitda     = latest_pnl["EBITDA"]

        wf_df = pd.DataFrame([
            {"Category": "Total Revenue",  "Value": total_rev,   "Type": "Absolute",  "Sort_Order": 1},
            {"Category": "Direct Costs",   "Value": -total_cos,  "Type": "Negative",  "Sort_Order": 2},
            {"Category": "Gross Profit",   "Value": gross_prof,  "Type": "Total",     "Sort_Order": 3},
            {"Category": "OPEX",           "Value": -total_opex, "Type": "Negative",  "Sort_Order": 4},
            {"Category": "EBITDA",         "Value": ebitda,      "Type": "Total",     "Sort_Order": 5},
        ])
        fig = waterfall_chart(
            wf_df,
            x_col="Category", y_col="Value", type_col="Type",
            title=f"P&L Waterfall — {latest_pnl['Month']}",
            height=420,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col6:
        gp_margin   = gross_prof / total_rev * 100 if total_rev else 0
        ebi_margin  = ebitda     / total_rev * 100 if total_rev else 0
        st.metric("Total Revenue",  f"{total_rev:,.1f}")
        st.metric("Direct Costs",   f"{total_cos:,.1f}")
        st.metric("Gross Profit",   f"{gross_prof:,.1f}",
                  f"{gp_margin:.1f}% margin")
        st.metric("OPEX",           f"{total_opex:,.1f}")
        st.metric("EBITDA",         f"{ebitda:,.1f}",
                  f"{ebi_margin:.1f}% margin")

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(
            fin, x="Month",
            y_cols=["Revenue", "Revenue_AOP", "Revenue_PY"],
            title="Revenue vs AOP vs PY",
            colors=[BLUE, BLUE_DIM, WHITE_DIM],
            dash_cols=["Revenue_AOP", "Revenue_PY"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = line_chart(
            fin, x="Month",
            y_cols=["EBITDA", "EBITDA_AOP", "EBITDA_PY"],
            title="EBITDA vs AOP vs PY",
            colors=[GREEN, GREEN_DIM, WHITE_DIM],
            dash_cols=["EBITDA_AOP", "EBITDA_PY"],
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
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"), title=""),
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
            y_cols=["PAT", "PAT_AOP", "PAT_PY"],
            title="Profit After Tax",
            colors=[PURPLE, PURPLE_DIM, WHITE_DIM],
            dash_cols=["PAT_AOP", "PAT_PY"],
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
        title="Revenue Actual vs AOP",
        colors=[BLUE, "#334466"],
    )
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("#### EBITDA Bridge — YTD Apr 2026")
    if bridge.empty:
        st.info("No EBITDA Bridge data available.")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = waterfall_chart(
                bridge,
                x_col="Category", y_col="Value", type_col="Type",
                title="EBITDA Bridge: AOP → Actual",
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
                    f"{color} **{row['Category']}** — `{val:,.0f}`"
                )

            aop    = bridge[bridge["Sort_Order"] == 1]["Value"].values[0]
            actual = bridge.iloc[-1]["Value"]
            gap    = actual - aop
            st.markdown("---")
            st.metric("AOP EBITDA",    f"{aop:,.0f}")
            st.metric("Actual EBITDA", f"{actual:,.0f}", delta=f"{gap:+,.0f} vs AOP")
