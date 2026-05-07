import streamlit as st

st.set_page_config(page_title="TSTT | DPDI", page_icon="💻", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data, pivot_by_group, get_month_order
from utils.charts import (
    inject_css, page_header,
    line_chart, grouped_bar, stacked_bar, donut_chart, bar_chart,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
)

inject_css()
data = load_all_data()
dpdi = data["DPDI"]

page_header("DPDI — Digital Products", "e-Tender · e-GOVTT · e-Cashbook · e-Health · PAYPR")

# ── Sidebar ───────────────────────────────────────────────────────────────────
months    = get_month_order(dpdi)
products  = dpdi["Product"].unique().tolist()
sel_month = st.sidebar.selectbox("Focus Month", months, index=len(months) - 1)

# ── Summary metrics ───────────────────────────────────────────────────────────
latest = dpdi[dpdi["Month"] == sel_month]
total_rev  = latest["Revenue"].sum()
total_aop  = latest["Revenue_AOP"].sum()
total_gp   = latest["Gross_Profit"].sum()
total_ebitda = latest["EBITDA"].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("DPDI Revenue",  f"TT${total_rev:.2f}M",
          f"{(total_rev - total_aop) / total_aop * 100:+.1f}% vs AOP" if total_aop else "—")
m2.metric("Revenue AOP",   f"TT${total_aop:.2f}M")
m3.metric("Gross Profit",  f"TT${total_gp:.2f}M")
m4.metric("EBITDA",        f"TT${total_ebitda:.2f}M",
          delta_color="inverse" if total_ebitda < 0 else "normal")

st.markdown("---")

# Note about DPDI maturity
st.info(
    "**Portfolio in development stage** — Most DPDI products are pre-revenue or in early "
    "adoption. Revenue and EBITDA are expected to ramp as government contracts activate.",
    icon="ℹ️",
)

# ── Charts ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Revenue & AOP", "Profitability", "Product Detail"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        rev_pivot = pivot_by_group(dpdi, "Month", "Product", "Revenue")
        prod_cols = [c for c in rev_pivot.columns if c != "Month"]
        fig = stacked_bar(
            rev_pivot, x="Month", y_cols=prod_cols,
            title="Revenue by Product (TT$M)",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        aop_pivot = pivot_by_group(dpdi, "Month", "Product", "Revenue_AOP")
        aop_cols  = [c for c in aop_pivot.columns if c != "Month"]
        fig = stacked_bar(
            aop_pivot, x="Month", y_cols=aop_cols,
            title="Revenue AOP by Product (TT$M)",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN],
        )
        st.plotly_chart(fig, use_container_width=True)

    # Revenue vs AOP by product for selected month
    col3, col4 = st.columns(2)
    with col3:
        latest_comp = latest[["Product", "Revenue", "Revenue_AOP"]].copy()
        fig = grouped_bar(
            latest_comp, x="Product", y_cols=["Revenue", "Revenue_AOP"],
            title=f"{sel_month} Revenue vs AOP by Product (TT$M)",
            colors=[BLUE, "#334466"],
            height=340,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        # YTD revenue per product
        ytd_rev = dpdi.groupby("Product", sort=False)["Revenue"].sum().reset_index()
        ytd_rev = ytd_rev.sort_values("Revenue", ascending=False)
        colors_list = [GREEN if v > 0 else RED for v in ytd_rev["Revenue"]]
        fig = go.Figure(go.Bar(
            x=ytd_rev["Product"], y=ytd_rev["Revenue"],
            marker_color=colors_list,
            text=[f"TT${v:.2f}M" for v in ytd_rev["Revenue"]],
            textposition="outside", textfont=dict(color="white", size=10),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=340,
            title=dict(text="<b>YTD Revenue by Product (TT$M)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        ebitda_pivot = pivot_by_group(dpdi, "Month", "Product", "EBITDA")
        eb_cols      = [c for c in ebitda_pivot.columns if c != "Month"]
        fig = line_chart(
            ebitda_pivot, x="Month", y_cols=eb_cols,
            title="EBITDA by Product (TT$M)",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN],
        )
        fig.add_hline(y=0, line_dash="solid", line_color="#3a3a5a")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        gp_pivot = pivot_by_group(dpdi, "Month", "Product", "GP_Margin_Pct")
        gp_cols  = [c for c in gp_pivot.columns if c != "Month"]
        fig = line_chart(
            gp_pivot, x="Month", y_cols=gp_cols,
            title="Gross Profit Margin % by Product",
            colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN],
        )
        st.plotly_chart(fig, use_container_width=True)

    # EBITDA vs GP for selected month
    col3, col4 = st.columns(2)
    with col3:
        ebitda_bar = latest[["Product", "EBITDA", "Gross_Profit"]].copy()
        fig = grouped_bar(
            ebitda_bar, x="Product", y_cols=["Gross_Profit", "EBITDA"],
            title=f"{sel_month} GP vs EBITDA by Product (TT$M)",
            colors=[GREEN, YELLOW],
            height=340,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        # Direct costs
        costs_bar = latest[["Product", "Direct_Costs"]].copy()
        fig = go.Figure(go.Bar(
            x=costs_bar["Product"], y=costs_bar["Direct_Costs"],
            marker_color=ORANGE,
            text=[f"TT${v:.2f}M" for v in costs_bar["Direct_Costs"]],
            textposition="outside", textfont=dict(color="white", size=10),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=340,
            title=dict(text=f"<b>{sel_month} Direct Costs by Product (TT$M)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("##### Per-Product Monthly Data")
    sel_product = st.selectbox("Select Product", products)
    prod_df = dpdi[dpdi["Product"] == sel_product].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("YTD Revenue",  f"TT${prod_df['Revenue'].sum():.2f}M",
              f"AOP: TT${prod_df['Revenue_AOP'].sum():.2f}M")
    c2.metric("YTD GP",       f"TT${prod_df['Gross_Profit'].sum():.2f}M")
    c3.metric("YTD EBITDA",   f"TT${prod_df['EBITDA'].sum():.2f}M")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=prod_df["Month"], y=prod_df["Revenue"],
                         name="Revenue", marker_color=BLUE))
    fig.add_trace(go.Bar(x=prod_df["Month"], y=prod_df["Revenue_AOP"],
                         name="AOP", marker_color="#334466"))
    fig.add_trace(go.Scatter(x=prod_df["Month"], y=prod_df["EBITDA"],
                              name="EBITDA", line=dict(color=GREEN, width=2),
                              mode="lines+markers", marker=dict(size=6)))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=380, barmode="group",
        title=dict(text=f"<b>{sel_product} — Revenue / AOP / EBITDA</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)
