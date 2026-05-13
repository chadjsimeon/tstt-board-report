import streamlit as st

st.set_page_config(page_title="TSTT | Business Sales", page_icon="🏢", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data, pivot_by_group, get_month_order
from utils.charts import (
    inject_css, page_header, styled_metric,
    line_chart, stacked_bar, grouped_bar, funnel_chart, donut_chart,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
)

inject_css()
data = load_all_data()
biz      = data["Business_Sales"]
pipeline = data["Pipeline"]
renewals = data["Renewals"]

page_header("Business Sales", "ICT Segments · Pipeline · At-Risk Renewals")

# ── Sidebar ───────────────────────────────────────────────────────────────────
months    = get_month_order(biz)
pip_months = get_month_order(pipeline)
sel_month  = st.sidebar.selectbox("Focus Month", months, index=len(months) - 1)
pip_month  = st.sidebar.selectbox("Pipeline Month", pip_months, index=len(pip_months) - 1)

# ── Summary metrics ───────────────────────────────────────────────────────────
latest = biz[biz["Month"] == sel_month]
total_rev   = latest["Revenue"].sum()
total_gp    = latest["Gross_Profit"].sum()
avg_gp_pct  = total_gp / total_rev * 100 if total_rev else 0
total_mrr   = latest["MRR"].sum()
total_aop   = latest["Revenue_AOP"].sum()
vs_aop      = (total_rev - total_aop) / total_aop * 100 if total_aop else 0

m1, m2, m3, m4 = st.columns(4)
with m1:
    styled_metric("Business Revenue", f"TT${total_rev:,.0f}M",
                  f"{vs_aop:+.1f}% vs AOP", vs_aop >= 0, "#00d4a0")
with m2:
    styled_metric("Gross Profit", f"TT${total_gp:,.0f}M",
                  f"{avg_gp_pct:.1f}% margin", None, "#4a9eff")
with m3:
    styled_metric("Monthly Recurring", f"TT${total_mrr:,.0f}M", accent="#aa44ff")
with m4:
    pip_val = pipeline[pipeline["Month"] == pip_month]["Value_TTD_M"].sum()
    styled_metric("Pipeline", f"TT${pip_val:,.0f}M", accent="#FF8844")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Sales Performance", "Pipeline", "Renewals at Risk"])

# ── Tab 1: Sales ──────────────────────────────────────────────────────────────
with tab1:
    rev_pivot = pivot_by_group(biz, "Month", "Segment", "Revenue")
    seg_cols  = [c for c in rev_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = stacked_bar(
            rev_pivot, x="Month", y_cols=seg_cols,
            title="Revenue by Segment — Stacked (TT$M)",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        gp_pivot  = pivot_by_group(biz, "Month", "Segment", "GP_Margin_Pct")
        gp_cols   = [c for c in gp_pivot.columns if c != "Month"]
        fig = line_chart(
            gp_pivot, x="Month", y_cols=gp_cols,
            title="GP Margin % by Segment",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW],
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        latest_rev = biz[biz["Month"] == sel_month][["Segment", "Revenue", "Revenue_AOP"]].copy()
        fig = grouped_bar(
            latest_rev, x="Segment", y_cols=["Revenue", "Revenue_AOP"],
            title=f"{sel_month} — Revenue vs AOP (TT$M)",
            colors=[BLUE, "#334466"],
            height=360,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        rev_vals = biz[biz["Month"] == sel_month][["Segment", "Revenue"]].copy()
        fig = donut_chart(
            rev_vals["Segment"].tolist(), rev_vals["Revenue"].tolist(),
            title=f"{sel_month} Revenue Mix",
            height=340,
        )
        st.plotly_chart(fig, use_container_width=True)

    # MRR trend
    mrr_pivot = pivot_by_group(biz, "Month", "Segment", "MRR")
    mrr_cols  = [c for c in mrr_pivot.columns if c != "Month"]
    fig = stacked_bar(
        mrr_pivot, x="Month", y_cols=mrr_cols,
        title="Monthly Recurring Revenue by Segment (TT$M)",
        colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW],
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Pipeline ───────────────────────────────────────────────────────────
with tab2:
    pip_latest = pipeline[pipeline["Month"] == pip_month].copy()

    col1, col2 = st.columns(2)
    with col1:
        p1, p2, p3 = st.columns(3)
        p1.metric("Total Deals",  f"{pip_latest['Deal_Count'].sum():,.0f}")
        p2.metric("Pipeline Value", f"TT${pip_latest['Value_TTD_M'].sum():,.0f}M")
        won = pip_latest[pip_latest["Stage"] == "Won"]
        p3.metric("Won Deals",    f"{won['Deal_Count'].sum():,.0f}" if not won.empty else "0")

        fig = funnel_chart(
            stages=pip_latest["Stage"].tolist(),
            values=pip_latest["Deal_Count"].tolist(),
            title=f"{pip_month} Pipeline — Deal Count",
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = funnel_chart(
            stages=pip_latest["Stage"].tolist(),
            values=pip_latest["Value_TTD_M"].tolist(),
            title=f"{pip_month} Pipeline — Value (TT$M)",
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Pipeline trend over months
    pip_value = pipeline.groupby(["Month", "Stage"], sort=False)["Value_TTD_M"].sum().reset_index()
    pip_by_stage = pip_value.pivot_table(index="Month", columns="Stage", values="Value_TTD_M", aggfunc="sum")
    month_order  = get_month_order(pipeline)
    pip_by_stage = pip_by_stage.reindex(month_order).reset_index()
    stage_cols   = [c for c in pip_by_stage.columns if c != "Month"]
    fig = stacked_bar(
        pip_by_stage, x="Month", y_cols=stage_cols,
        title="Pipeline Value by Stage over Time (TT$M)",
        colors=[BLUE, GREEN, PURPLE, ORANGE, YELLOW],
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.markdown(f"##### {pip_month} Pipeline Detail")
    rows = ""
    for _, r in pip_latest.iterrows():
        win = f"{r['Win_Rate_Pct']:.1f}%" if r["Win_Rate_Pct"] == r["Win_Rate_Pct"] else "—"
        rows += f"""<tr>
            <td>{r['Stage']}</td>
            <td style="text-align:right">{r['Deal_Count']:,.0f}</td>
            <td style="text-align:right">TT${r['Value_TTD_M']:,.0f}M</td>
            <td style="text-align:right">TT${r['Avg_Deal_Size']:,.1f}M</td>
            <td style="text-align:right">{win}</td>
        </tr>"""
    st.markdown(f"""
    <table class="data-table">
        <thead><tr>
            <th>Stage</th><th style="text-align:right">Deals</th>
            <th style="text-align:right">Value</th>
            <th style="text-align:right">Avg Deal</th>
            <th style="text-align:right">Win Rate</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

# ── Tab 3: Renewals ───────────────────────────────────────────────────────────
with tab3:
    r1, r2, r3 = st.columns(3)
    total_acv  = renewals["ACV_TTD_M"].sum()
    high_risk  = renewals[renewals["Risk_Level"] == "High"]["ACV_TTD_M"].sum()
    secured    = renewals[renewals["Status"] == "Secured"]["ACV_TTD_M"].sum()
    r1.metric("Total Renewal ACV",  f"TT${total_acv:,.1f}M")
    r2.metric("High-Risk ACV",       f"TT${high_risk:,.1f}M",
              delta=f"{high_risk / total_acv * 100:.1f}% of portfolio", delta_color="inverse")
    r3.metric("Secured ACV",         f"TT${secured:,.1f}M",
              delta=f"{secured / total_acv * 100:.1f}% secured")

    col1, col2 = st.columns(2)
    with col1:
        risk_counts = renewals["Risk_Level"].value_counts()
        fig = donut_chart(
            risk_counts.index.tolist(), risk_counts.values.tolist(),
            title="Renewals by Risk Level (count)",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        risk_acv = renewals.groupby("Risk_Level")["ACV_TTD_M"].sum()
        fig = donut_chart(
            risk_acv.index.tolist(), risk_acv.values.tolist(),
            title="Renewals by Risk Level (ACV TT$M)",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Renewals table
    st.markdown("##### All At-Risk Renewals")
    rows = ""
    for _, r in renewals.sort_values(["Risk_Level", "ACV_TTD_M"], ascending=[True, False]).iterrows():
        risk_class = {
            "High": "risk-high", "Medium": "risk-medium", "Low": "risk-low"
        }.get(r["Risk_Level"], "")
        status_class = {
            "Secured": "status-secured", "In Progress": "status-in-progress"
        }.get(r["Status"], "")
        rows += f"""<tr>
            <td><strong>{r['Customer']}</strong></td>
            <td>{r['Product_Service']}</td>
            <td style="text-align:right">TT${r['ACV_TTD_M']:,.1f}M</td>
            <td>{r['Expiry_Date']}</td>
            <td class="{risk_class}">{r['Risk_Level']}</td>
            <td class="{status_class}">{r['Status']}</td>
            <td style="font-size:0.78rem;color:#aaaacc">{r['Action_Plan']}</td>
        </tr>"""
    st.markdown(f"""
    <table class="data-table">
        <thead><tr>
            <th>Customer</th><th>Product / Service</th>
            <th style="text-align:right">ACV</th>
            <th>Expiry</th><th>Risk</th><th>Status</th><th>Action Plan</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)
