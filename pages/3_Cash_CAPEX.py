import streamlit as st

st.set_page_config(page_title="TSTT | Cash & CAPEX", page_icon="💵", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import (
    inject_css, page_header,
    line_chart, grouped_bar,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, WHITE_FAINT,
)

inject_css()
data = load_all_data()
cc = data["Cash_CAPEX"]

page_header("Cash & CAPEX", "Liquidity · Net Debt · Capital Expenditure · Free Cash Flow")

# ── Latest-month metrics ──────────────────────────────────────────────────────
latest = cc.iloc[-1]
prev   = cc.iloc[-2] if len(cc) > 1 else latest

m1, m2, m3, m4 = st.columns(4)
m1.metric("Cash Balance",     f"TT${latest['Cash_Balance']:,.0f}M",
          f"TT${latest['Cash_Balance'] - prev['Cash_Balance']:+,.0f}M MoM")
m2.metric("Net Debt",         f"TT${latest['Net_Debt']:,.0f}M",
          f"TT${latest['Net_Debt'] - prev['Net_Debt']:+,.0f}M MoM",
          delta_color="inverse")
m3.metric("Collections",      f"{latest['Collections_Pct']:.1f}%",
          f"{latest['Collections_Pct'] - prev['Collections_Pct']:+.1f}pp MoM")
m4.metric("Free Cash Flow",   f"TT${latest['FCF']:,.0f}M",
          f"TT${latest['FCF'] - prev['FCF']:+,.0f}M MoM")

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    fig = line_chart(
        cc, x="Month",
        y_cols=["Cash_Balance"],
        title="Cash Balance (TT$M)",
        colors=[GREEN],
    )
    fig.add_hline(y=700, line_dash="dot", line_color=WHITE_FAINT,
                  annotation_text="Min Threshold TT$700M", annotation_font_color="#7788aa",
                  annotation_position="bottom right")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = line_chart(
        cc, x="Month",
        y_cols=["Net_Debt"],
        title="Net Debt (TT$M)",
        colors=[RED],
    )
    st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    fig = grouped_bar(
        cc, x="Month", y_cols=["CAPEX_Actual", "CAPEX_Plan"],
        title="CAPEX: Actual vs Plan (TT$M)",
        colors=[BLUE, "#334466"],
    )
    st.plotly_chart(fig, use_container_width=True)

with col4:
    fig = line_chart(
        cc, x="Month",
        y_cols=["FCF"],
        title="Free Cash Flow (TT$M)",
        colors=[YELLOW],
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Collections & CAPEX efficiency ───────────────────────────────────────────
col5, col6 = st.columns(2)

with col5:
    fig = line_chart(
        cc, x="Month",
        y_cols=["Collections_Pct"],
        title="Collections Rate (%)",
        colors=[PURPLE],
    )
    fig.add_hline(y=90, line_dash="dot", line_color=WHITE_FAINT,
                  annotation_text="Target 90%", annotation_font_color="#7788aa",
                  annotation_position="bottom right")
    st.plotly_chart(fig, use_container_width=True)

with col6:
    # CAPEX variance
    cc_copy = cc.copy()
    cc_copy["CAPEX_Var"] = cc_copy["CAPEX_Actual"] - cc_copy["CAPEX_Plan"]
    colors_list = [GREEN if v <= 0 else RED for v in cc_copy["CAPEX_Var"]]
    fig = go.Figure(go.Bar(
        x=cc_copy["Month"], y=cc_copy["CAPEX_Var"],
        marker_color=colors_list,
        text=[f"TT${v:+,.0f}M" for v in cc_copy["CAPEX_Var"]],
        textposition="outside", textfont=dict(color="white", size=10),
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=380,
        title=dict(text="<b>CAPEX Variance vs Plan (TT$M)</b>", font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                   zeroline=True, zerolinecolor="#3a3a5a"),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Full data table ───────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("Full Cash & CAPEX Data Table"):
    display = cc.copy()
    display["CAPEX_Var"] = display["CAPEX_Actual"] - display["CAPEX_Plan"]
    rows = ""
    for _, r in display.iterrows():
        vc = "red-text" if r["CAPEX_Var"] > 0 else "green-text"
        rows += f"""<tr>
            <td>{r['Month']}</td>
            <td style="text-align:right">TT${r['Cash_Balance']:,.0f}M</td>
            <td style="text-align:right">TT${r['Net_Debt']:,.0f}M</td>
            <td style="text-align:right">{r['Collections_Pct']:.1f}%</td>
            <td style="text-align:right">TT${r['FCF']:,.0f}M</td>
            <td style="text-align:right">TT${r['CAPEX_Actual']:,.0f}M</td>
            <td style="text-align:right">TT${r['CAPEX_Plan']:,.0f}M</td>
            <td style="text-align:right" class="{vc}">TT${r['CAPEX_Var']:+,.0f}M</td>
        </tr>"""
    st.markdown(f"""
    <table class="data-table">
        <thead><tr>
            <th>Month</th><th style="text-align:right">Cash</th>
            <th style="text-align:right">Net Debt</th>
            <th style="text-align:right">Collections</th>
            <th style="text-align:right">FCF</th>
            <th style="text-align:right">CAPEX Act</th>
            <th style="text-align:right">CAPEX Plan</th>
            <th style="text-align:right">CAPEX Var</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)
