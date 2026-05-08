import streamlit as st

st.set_page_config(page_title="TSTT | Amplia", page_icon="📶", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data, get_month_order
from utils.charts import (
    inject_css, page_header,
    line_chart, grouped_bar, stacked_bar, donut_chart,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
    BLUE_FAINT, GREEN_FAINT, BLUE_MED, GREEN_MED, dim,
)

inject_css()
data = load_all_data()
amp_fin  = data["AMPLIA_Financial"]
amp_com  = data["AMPLIA_Commercial"]

page_header("Amplia", "Fibre Broadband Subsidiary — Financial & Commercial Performance")

# ── Latest-month metrics ──────────────────────────────────────────────────────
latest_fin = amp_fin.iloc[-1]
prev_fin   = amp_fin.iloc[-2] if len(amp_fin) > 1 else latest_fin

m1, m2, m3, m4 = st.columns(4)
m1.metric("Revenue",
          f"TT${latest_fin['Revenue']:,.0f}M",
          f"TT${latest_fin['Revenue'] - latest_fin['Revenue_AOP']:+,.0f}M vs AOP")
m2.metric("EBITDA",
          f"TT${latest_fin['EBITDA']:,.0f}M",
          f"TT${latest_fin['EBITDA'] - latest_fin['EBITDA_AOP']:+,.0f}M vs AOP")
m3.metric("PAT",
          f"TT${latest_fin['PAT']:,.0f}M",
          f"TT${latest_fin['PAT'] - prev_fin['PAT']:+,.0f}M MoM")
m4.metric("EBITDA Margin",
          f"{latest_fin['EBITDA'] / latest_fin['Revenue'] * 100:.1f}%",
          f"AOP: {latest_fin['EBITDA_AOP'] / latest_fin['Revenue_AOP'] * 100:.1f}%")

st.markdown("---")

tab1, tab2 = st.tabs(["Financial Performance", "Commercial Performance"])

# ── Tab 1: Financial ──────────────────────────────────────────────────────────
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(
            amp_fin, x="Month",
            y_cols=["Revenue", "Revenue_AOP"],
            title="Amplia Revenue vs AOP (TT$M)",
            colors=[BLUE, BLUE_FAINT],
            dash_cols=["Revenue_AOP"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = line_chart(
            amp_fin, x="Month",
            y_cols=["EBITDA", "EBITDA_AOP"],
            title="Amplia EBITDA vs AOP (TT$M)",
            colors=[GREEN, GREEN_FAINT],
            dash_cols=["EBITDA_AOP"],
        )
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig = line_chart(
            amp_fin, x="Month",
            y_cols=["PAT"],
            title="Profit After Tax (TT$M)",
            colors=[PURPLE],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        # EBITDA margin calculation
        amp_fin_copy = amp_fin.copy()
        amp_fin_copy["EBITDA_Margin_Pct"] = (
            amp_fin_copy["EBITDA"] / amp_fin_copy["Revenue"] * 100
        ).round(1)
        amp_fin_copy["EBITDA_AOP_Margin_Pct"] = (
            amp_fin_copy["EBITDA_AOP"] / amp_fin_copy["Revenue_AOP"] * 100
        ).round(1)
        fig = line_chart(
            amp_fin_copy, x="Month",
            y_cols=["EBITDA_Margin_Pct", "EBITDA_AOP_Margin_Pct"],
            title="Amplia EBITDA Margin (%)",
            colors=[YELLOW, dim(YELLOW, 0.40)],
            dash_cols=["EBITDA_AOP_Margin_Pct"],
        )
        st.plotly_chart(fig, use_container_width=True)

    # OPEX vs Direct costs
    col5, col6 = st.columns(2)
    with col5:
        fig = grouped_bar(
            amp_fin, x="Month", y_cols=["OPEX", "Direct_Costs", "Gross_Profit"],
            title="Cost Structure (TT$M)",
            colors=[RED, ORANGE, GREEN],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col6:
        # Revenue waterfall
        fig = go.Figure()
        fig.add_trace(go.Bar(x=amp_fin["Month"], y=amp_fin["Revenue"],
                              name="Revenue", marker_color=BLUE_MED))
        fig.add_trace(go.Bar(x=amp_fin["Month"], y=amp_fin["Gross_Profit"],
                              name="Gross Profit", marker_color=GREEN_MED))
        fig.add_trace(go.Bar(x=amp_fin["Month"], y=amp_fin["EBITDA"],
                              name="EBITDA", marker_color=YELLOW))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=380, barmode="overlay",
            title=dict(text="<b>P&L Waterdown (TT$M)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.02, x=1, xanchor="right"),
            margin=dict(l=10, r=10, t=44, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

# ── Tab 2: Commercial ─────────────────────────────────────────────────────────
with tab2:
    if amp_com.empty:
        st.info("Commercial data not yet available.")
    else:
        # Monthly totals (deduplicate — gross adds & churn are same across channels)
        monthly_com = amp_com.drop_duplicates(subset=["Month"], keep="first").copy()
        channels_df = amp_com.copy()
        channel_months = get_month_order(amp_com)
        sel_com_month  = st.sidebar.selectbox("Commercial Month",
                                              channel_months,
                                              index=len(channel_months) - 1)

        # KPIs from latest commercial month
        latest_com = monthly_com.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ARPU",           f"TT${latest_com['ARPU']:,.0f}")
        c2.metric("Gross Additions", f"{latest_com['Gross_Additions']:,.0f}",
                  f"AOP: {latest_com['Gross_Additions_AOP']:,.0f}")
        c3.metric("Monthly Churn",  f"{latest_com['Monthly_Churn']:,.0f}",
                  f"AOP: {latest_com['Churn_AOP']:,.0f}",
                  delta_color="inverse")
        c4.metric("Net Port",       f"{latest_com['Net_Port']:+,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            fig = grouped_bar(
                monthly_com, x="Month",
                y_cols=["Gross_Additions", "Gross_Additions_AOP"],
                title="Gross Additions vs AOP",
                colors=[GREEN, "#224422"],
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = grouped_bar(
                monthly_com, x="Month",
                y_cols=["Monthly_Churn", "Churn_AOP"],
                title="Monthly Churn vs AOP",
                colors=[RED, "#442222"],
            )
            st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            # Net additions = gross - churn
            monthly_com_copy = monthly_com.copy()
            monthly_com_copy["Net_Additions"] = (
                monthly_com_copy["Gross_Additions"] - monthly_com_copy["Monthly_Churn"]
            )
            colors_list = [GREEN if v >= 0 else RED for v in monthly_com_copy["Net_Additions"]]
            fig = go.Figure(go.Bar(
                x=monthly_com_copy["Month"], y=monthly_com_copy["Net_Additions"],
                marker_color=colors_list,
                text=[f"{v:+,.0f}" for v in monthly_com_copy["Net_Additions"]],
                textposition="outside", textfont=dict(color="white", size=10),
            ))
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"), height=360,
                title=dict(text="<b>Net Subscriber Additions</b>",
                           font=dict(size=13, color="white"), x=0),
                xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                           zeroline=True, zerolinecolor="#3a3a5a"),
                margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col4:
            # ARPU trend
            fig = line_chart(
                monthly_com, x="Month", y_cols=["ARPU"],
                title="ARPU Trend (TT$)",
                colors=[YELLOW],
            )
            st.plotly_chart(fig, use_container_width=True)

        # ── Channel breakdown ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### Channel Performance")

        channel_sel = channels_df[channels_df["Month"] == sel_com_month].copy()

        if not channel_sel.empty:
            col5, col6 = st.columns(2)
            with col5:
                fig = go.Figure(go.Bar(
                    x=channel_sel["Channel"],
                    y=channel_sel["Sales_Count"],
                    marker_color=[BLUE, GREEN, PURPLE][:len(channel_sel)],
                    text=[f"{v:,.0f}" for v in channel_sel["Sales_Count"]],
                    textposition="outside", textfont=dict(color="white", size=11),
                    customdata=channel_sel["Sales_Target"],
                    hovertemplate="<b>%{x}</b><br>Sales: %{y:,.0f}<br>Target: %{customdata:,.0f}<extra></extra>",
                ))
                # Add target markers
                for _, row in channel_sel.iterrows():
                    fig.add_shape(type="line",
                                  x0=row["Channel"], x1=row["Channel"],
                                  y0=row["Sales_Target"] - 50, y1=row["Sales_Target"] + 50,
                                  xref="x", yref="y",
                                  line=dict(color=YELLOW, width=3))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"), height=360,
                    title=dict(text=f"<b>{sel_com_month} Sales by Channel (yellow = target)</b>",
                               font=dict(size=13, color="white"), x=0),
                    xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                    yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                    margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col6:
                channel_sel["vs_target_pct"] = (
                    (channel_sel["Sales_Count"] - channel_sel["Sales_Target"])
                    / channel_sel["Sales_Target"] * 100
                ).round(1)
                colors_t = [GREEN if v >= 0 else RED for v in channel_sel["vs_target_pct"]]
                fig = go.Figure(go.Bar(
                    x=channel_sel["Channel"], y=channel_sel["vs_target_pct"],
                    marker_color=colors_t,
                    text=[f"{v:+.1f}%" for v in channel_sel["vs_target_pct"]],
                    textposition="outside", textfont=dict(color="white", size=11),
                ))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"), height=360,
                    title=dict(text=f"<b>{sel_com_month} Sales vs Target (%)</b>",
                               font=dict(size=13, color="white"), x=0),
                    xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                    yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                               zeroline=True, zerolinecolor="#3a3a5a"),
                    margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

            # Channel detail table
            rows = ""
            for _, r in channel_sel.iterrows():
                vs_t = r["Sales_Count"] - r["Sales_Target"]
                t_class = "green-text" if vs_t >= 0 else "red-text"
                rows += f"""<tr>
                    <td>{r['Channel']}</td>
                    <td style="text-align:right">{r['Sales_Count']:,.0f}</td>
                    <td style="text-align:right">{r['Sales_Target']:,.0f}</td>
                    <td style="text-align:right" class="{t_class}">{vs_t:+,.0f}</td>
                    <td style="text-align:right" class="{t_class}">{r['vs_target_pct']:+.1f}%</td>
                </tr>"""
            st.markdown(f"""
            <table class="data-table">
                <thead><tr>
                    <th>Channel</th>
                    <th style="text-align:right">Sales</th>
                    <th style="text-align:right">Target</th>
                    <th style="text-align:right">Variance</th>
                    <th style="text-align:right">Var %</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>""", unsafe_allow_html=True)
