import streamlit as st

st.set_page_config(page_title="TSTT | Consumer", page_icon="📱", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data, pivot_by_group, get_month_order
from utils.charts import (
    inject_css, page_header,
    line_chart, stacked_bar, grouped_bar, donut_chart, dim,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN, ACCENT,
)

SEG_COLORS = ACCENT

inject_css()
data = load_all_data()
consumer = data["Consumer_Sales"]

page_header("Consumer", "Prepaid · Postpaid · WTTx — Revenue, Subscribers, Churn, ARPU")

# ── Sidebar filter ────────────────────────────────────────────────────────────
months   = get_month_order(consumer)
segments = consumer["Segment"].unique().tolist()
sel_month = st.sidebar.selectbox("Focus Month", months, index=len(months) - 1)

# ── Latest-month snapshot ─────────────────────────────────────────────────────
latest = consumer[consumer["Month"] == sel_month]
total_rev  = latest["Revenue"].sum()
total_subs = latest["Subscribers"].sum()
avg_churn  = latest["Churn_Pct"].mean()
avg_arpu   = (latest["Revenue"] * latest["Subscribers"]).sum() / total_subs if total_subs else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Revenue",    f"TT${total_rev:,.0f}M")
m2.metric("Total Subscribers",f"{total_subs:,.0f}")
m3.metric("Avg Churn",        f"{avg_churn:.1f}%")
m4.metric("Blended ARPU",     f"TT${avg_arpu:,.0f}")

st.markdown("---")

# ── Per-segment KPIs for selected month ──────────────────────────────────────
st.markdown(f"#### {sel_month} — Segment Breakdown")
seg_cols = st.columns(len(segments))
for col, seg in zip(seg_cols, segments):
    row = latest[latest["Segment"] == seg]
    if row.empty:
        continue
    row = row.iloc[0]
    aop_pct = (row["Revenue"] - row["Revenue_AOP"]) / row["Revenue_AOP"] * 100 if row["Revenue_AOP"] else 0
    col.metric(
        f"{seg} Revenue",
        f"TT${row['Revenue']:,.0f}M",
        f"{aop_pct:+.1f}% vs AOP",
    )

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["Revenue", "Subscribers", "Churn", "ARPU"])

with tab1:
    rev_pivot = pivot_by_group(consumer, "Month", "Segment", "Revenue")
    seg_cols_pivot = [c for c in rev_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = stacked_bar(
            rev_pivot, x="Month", y_cols=seg_cols_pivot,
            title="Revenue by Segment — Stacked (TT$M)",
            colors=SEG_COLORS,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Revenue vs AOP by segment for selected month
        aop_pivot = pivot_by_group(consumer, "Month", "Segment", "Revenue_AOP")
        latest_rev = {seg: rev_pivot[rev_pivot["Month"] == sel_month][seg].values[0]
                      for seg in seg_cols_pivot if seg in rev_pivot.columns}
        latest_aop = {seg: aop_pivot[aop_pivot["Month"] == sel_month][seg].values[0]
                      for seg in seg_cols_pivot if seg in aop_pivot.columns}

        fig = go.Figure()
        for i, seg in enumerate(seg_cols_pivot):
            color = SEG_COLORS[i % len(SEG_COLORS)]
            fig.add_trace(go.Bar(
                x=[seg], y=[latest_rev.get(seg, 0)],
                name=f"{seg} Actual", marker_color=color,
            ))
            fig.add_trace(go.Bar(
                x=[seg], y=[latest_aop.get(seg, 0)],
                name=f"{seg} AOP", marker_color=dim(color),
                marker_pattern_shape="/",
            ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=380, barmode="group",
            title=dict(text=f"<b>{sel_month} Revenue vs AOP (TT$M)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
                        orientation="h", y=1.02, x=1, xanchor="right"),
            margin=dict(l=10, r=10, t=44, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Revenue share donut for selected month
    col3, col4 = st.columns(2)
    with col3:
        rev_vals = [latest_rev.get(seg, 0) for seg in seg_cols_pivot]
        fig = donut_chart(seg_cols_pivot, rev_vals,
                          title=f"{sel_month} Revenue Mix",
                          height=320)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        yoy_pivot = pivot_by_group(consumer, "Month", "Segment", "YoY_Change_Pct")
        yoy_cols  = [c for c in yoy_pivot.columns if c != "Month"]
        fig = line_chart(
            yoy_pivot, x="Month", y_cols=yoy_cols,
            title="YoY Revenue Change (%)",
            colors=SEG_COLORS,
        )
        fig.add_hline(y=0, line_dash="solid", line_color="#3a3a5a")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    subs_pivot = pivot_by_group(consumer, "Month", "Segment", "Subscribers")
    subs_cols  = [c for c in subs_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = stacked_bar(
            subs_pivot, x="Month", y_cols=subs_cols,
            title="Subscribers by Segment",
            colors=SEG_COLORS,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = line_chart(
            subs_pivot, x="Month", y_cols=subs_cols,
            title="Subscriber Trend by Segment",
            colors=SEG_COLORS,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Latest subscriber mix
    col3, _ = st.columns([1, 1])
    with col3:
        latest_subs = {seg: subs_pivot[subs_pivot["Month"] == sel_month][seg].values[0]
                       for seg in subs_cols if seg in subs_pivot.columns}
        fig = donut_chart(
            list(latest_subs.keys()), list(latest_subs.values()),
            title=f"{sel_month} Subscriber Mix",
            height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    churn_pivot = pivot_by_group(consumer, "Month", "Segment", "Churn_Pct")
    churn_cols  = [c for c in churn_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(
            churn_pivot, x="Month", y_cols=churn_cols,
            title="Monthly Churn Rate by Segment (%)",
            colors=SEG_COLORS,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        churn_bar = consumer[consumer["Month"] == sel_month][["Segment", "Churn_Pct"]].copy()
        fig = go.Figure(go.Bar(
            x=churn_bar["Segment"], y=churn_bar["Churn_Pct"],
            marker_color=SEG_COLORS[:len(churn_bar)],
            text=[f"{v:.1f}%" for v in churn_bar["Churn_Pct"]],
            textposition="outside", textfont=dict(color="white", size=11),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=380,
            title=dict(text=f"<b>{sel_month} Churn by Segment (%)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"), ticksuffix="%"),
            margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    arpu_pivot = pivot_by_group(consumer, "Month", "Segment", "ARPU")
    arpu_cols  = [c for c in arpu_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(
            arpu_pivot, x="Month", y_cols=arpu_cols,
            title="ARPU by Segment (TT$)",
            colors=SEG_COLORS,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        arpu_bar = consumer[consumer["Month"] == sel_month][["Segment", "ARPU"]].copy()
        fig = go.Figure(go.Bar(
            x=arpu_bar["Segment"], y=arpu_bar["ARPU"],
            marker_color=SEG_COLORS[:len(arpu_bar)],
            text=[f"TT${v:,.0f}" for v in arpu_bar["ARPU"]],
            textposition="outside", textfont=dict(color="white", size=11),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=380,
            title=dict(text=f"<b>{sel_month} ARPU by Segment (TT$)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
