import streamlit as st

st.set_page_config(page_title="TSTT | OPEX & Cost", page_icon="📊", layout="wide")

import pandas as pd
from utils.data_loader import load_all_data, pivot_by_group
from utils.charts import (
    inject_css, page_header,
    stacked_bar, grouped_bar, variance_heatmap, bar_chart,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
)

inject_css()
data = load_all_data()
opex = data["OPEX"]

page_header("OPEX & Cost Management", "Actual vs Plan · Variance Analysis")

# ── Sidebar filter ────────────────────────────────────────────────────────────
months = opex["Month"].unique().tolist()
sel_month = st.sidebar.selectbox("Focus Month", months, index=len(months) - 1)

# ── Summary metrics ───────────────────────────────────────────────────────────
latest = opex[opex["Month"] == sel_month]
total_actual = latest["Actual"].sum()
total_plan   = latest["Plan"].sum()
total_var    = total_actual - total_plan
var_pct      = total_var / total_plan * 100 if total_plan else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total OPEX (Actual)", f"TT${total_actual:,.0f}M")
m2.metric("Total OPEX (Plan)",   f"TT${total_plan:,.0f}M")
m3.metric("Variance",            f"TT${total_var:+,.0f}M",  delta=f"{var_pct:+.1f}%",
          delta_color="inverse")
over = latest[latest["Variance"] > 0]["Variance"].sum()
m4.metric("Overspend Categories", f"{(latest['Variance'] > 0).sum()}",
          delta=f"TT${over:+,.0f}M over plan", delta_color="inverse")

st.markdown("---")

# ── Tab layout ────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Monthly Trend", "Actual vs Plan", "Variance Heatmap"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        rev_pivot = pivot_by_group(opex, "Month", "Category", "Actual")
        cat_cols  = [c for c in rev_pivot.columns if c != "Month"]
        fig = stacked_bar(
            rev_pivot, x="Month", y_cols=cat_cols,
            title="OPEX by Category — Actual (TT$M)",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        plan_pivot = pivot_by_group(opex, "Month", "Category", "Plan")
        cat_cols   = [c for c in plan_pivot.columns if c != "Month"]
        fig = stacked_bar(
            plan_pivot, x="Month", y_cols=cat_cols,
            title="OPEX by Category — Plan (TT$M)",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW],
        )
        st.plotly_chart(fig, use_container_width=True)

    # Total actual vs plan trend
    monthly_totals = opex.groupby("Month", sort=False).agg(
        Actual=("Actual", "sum"),
        Plan=("Plan", "sum"),
    ).reset_index()
    fig = grouped_bar(
        monthly_totals, x="Month", y_cols=["Actual", "Plan"],
        title="Total OPEX: Actual vs Plan (TT$M)",
        colors=[BLUE, "#334466"],
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown(f"#### {sel_month} — Actual vs Plan by Category")
    col1, col2 = st.columns(2)

    with col1:
        fig = grouped_bar(
            latest, x="Category", y_cols=["Actual", "Plan"],
            title=f"Actual vs Plan — {sel_month} (TT$M)",
            colors=[BLUE, "#334466"],
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Variance bar
        var_df = latest[["Category", "Variance", "Variance_Pct"]].copy()
        var_df = var_df.sort_values("Variance")
        colors_list = [GREEN if v <= 0 else RED for v in var_df["Variance"]]
        import plotly.graph_objects as go
        fig = go.Figure(go.Bar(
            x=var_df["Variance"], y=var_df["Category"],
            orientation="h",
            marker_color=colors_list,
            text=[f"TT${v:+,.0f}M ({p:+.1f}%)" for v, p in zip(var_df["Variance"], var_df["Variance_Pct"])],
            textposition="outside",
            textfont=dict(color="white", size=10),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=400,
            title=dict(text=f"<b>OPEX Variance — {sel_month} (TT$M)</b>", font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"), zeroline=True, zerolinecolor="#3a3a5a"),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            margin=dict(l=10, r=10, t=44, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Detail table
    st.markdown(f"##### {sel_month} OPEX Detail")
    display = latest[["Category", "Actual", "Plan", "Variance", "Variance_Pct"]].copy()
    rows = ""
    for _, r in display.iterrows():
        v_class = "red-text" if r["Variance"] > 0 else "green-text"
        rows += f"""<tr>
            <td>{r['Category']}</td>
            <td style="text-align:right">TT${r['Actual']:,.0f}M</td>
            <td style="text-align:right">TT${r['Plan']:,.0f}M</td>
            <td style="text-align:right" class="{v_class}">TT${r['Variance']:+,.0f}M</td>
            <td style="text-align:right" class="{v_class}">{r['Variance_Pct']:+.1f}%</td>
        </tr>"""
    st.markdown(f"""
    <table class="data-table">
        <thead><tr>
            <th>Category</th><th style="text-align:right">Actual</th>
            <th style="text-align:right">Plan</th>
            <th style="text-align:right">Variance</th>
            <th style="text-align:right">Var %</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

with tab3:
    fig = variance_heatmap(
        opex,
        index_col="Category",
        columns_col="Month",
        value_col="Variance_Pct",
        title="OPEX Variance % vs Plan (Green = Under, Red = Over)",
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Monthly trend of total variance
    monthly_var = opex.groupby("Month", sort=False).agg(
        Variance=("Variance", "sum"),
        Variance_Pct_Avg=("Variance_Pct", "mean"),
    ).reset_index()
    col1, col2 = st.columns(2)
    with col1:
        import plotly.graph_objects as go
        colors_list = [GREEN if v <= 0 else RED for v in monthly_var["Variance"]]
        fig = go.Figure(go.Bar(
            x=monthly_var["Month"], y=monthly_var["Variance"],
            marker_color=colors_list,
            text=[f"TT${v:+,.0f}M" for v in monthly_var["Variance"]],
            textposition="outside", textfont=dict(color="white", size=10),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=320,
            title=dict(text="<b>Total OPEX Variance (TT$M)</b>", font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                       zeroline=True, zerolinecolor="#3a3a5a"),
            margin=dict(l=10, r=10, t=44, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("##### YTD OPEX Summary by Category")
        ytd = opex.groupby("Category", sort=False).agg(
            Actual=("Actual", "sum"),
            Plan=("Plan", "sum"),
        ).reset_index()
        ytd["Variance"] = ytd["Actual"] - ytd["Plan"]
        ytd["Var%"] = (ytd["Variance"] / ytd["Plan"] * 100).round(1)
        rows = ""
        for _, r in ytd.iterrows():
            v_class = "red-text" if r["Variance"] > 0 else "green-text"
            rows += f"""<tr>
                <td>{r['Category']}</td>
                <td style="text-align:right">TT${r['Actual']:,.0f}M</td>
                <td style="text-align:right">TT${r['Plan']:,.0f}M</td>
                <td style="text-align:right" class="{v_class}">{r['Var%']:+.1f}%</td>
            </tr>"""
        st.markdown(f"""
        <table class="data-table">
            <thead><tr>
                <th>Category</th><th style="text-align:right">Actual</th>
                <th style="text-align:right">Plan</th>
                <th style="text-align:right">Var%</th>
            </tr></thead>
            <tbody>{rows}</tbody>
        </table>""", unsafe_allow_html=True)
