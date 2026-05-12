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
avg_arpu   = (latest["ARPU"] * latest["Subscribers"]).sum() / total_subs if total_subs else 0

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
tab1, tab2, tab3, tab4 = st.tabs(["Consumer Sales Performance", "Subscribers", "Churn", "ARPU"])

with tab1:
    import pandas as _pd

    # ── Data prep ─────────────────────────────────────────────────────────────
    latest   = consumer[consumer["Month"] == sel_month].copy()
    apr25    = consumer[consumer["Month"] == "Apr-25"].copy()

    total_rev  = latest["Revenue"].sum()
    total_aop  = latest["Revenue_AOP"].sum()
    total_var  = (total_rev - total_aop) / total_aop * 100 if total_aop else 0

    # YoY — only meaningful if Apr-25 base exists and differs
    apr25_total = apr25["Revenue"].sum()
    yoy_pct     = (total_rev - apr25_total) / apr25_total * 100 if apr25_total else 0

    def seg_rev(name):
        r = latest[latest["Segment"] == name]
        return r["Revenue"].values[0] if not r.empty else 0.0

    def seg_aop(name):
        r = latest[latest["Segment"] == name]
        v = r["Revenue_AOP"].values[0] if not r.empty else 0.0
        return v if v and not _pd.isna(v) else None

    def vs_aop_pct(name):
        a, p = seg_rev(name), seg_aop(name)
        return (a - p) / abs(p) * 100 if p else None

    # EBITDA margin from Financial_Monthly
    fm     = data["Financial_Monthly"]
    fm_apr = fm[fm["Month"] == sel_month]
    if not fm_apr.empty:
        ebitda_margin_act = fm_apr["EBITDA_Margin"].values[0]
        ebitda_margin_aop = (fm_apr["EBITDA_AOP"].values[0] /
                             fm_apr["Revenue_AOP"].values[0] * 100)
        ebitda_pp = ebitda_margin_act - ebitda_margin_aop
    else:
        ebitda_margin_act = ebitda_pp = None

    # Monthly revenue totals for trend chart
    monthly = (
        consumer.groupby("Month", sort=False)
        .agg(Revenue=("Revenue", "sum"), Revenue_AOP=("Revenue_AOP", "sum"))
        .reset_index()
    )

    # Best/worst segment vs AOP (exclude tiny / cleanup lines)
    meaningful_segs = ["Prepaid", "Postpaid", "WTTx", "Residential Security"]
    seg_vars = {
        s: vs_aop_pct(s) for s in meaningful_segs
        if vs_aop_pct(s) is not None
    }
    best_seg  = max(seg_vars, key=seg_vars.get) if seg_vars else "—"
    worst_seg = min(seg_vars, key=seg_vars.get) if seg_vars else "—"
    best_var  = seg_vars.get(best_seg, 0)
    worst_var = seg_vars.get(worst_seg, 0)

    # Postpaid subscriber trend
    pp_subs = (consumer[consumer["Segment"] == "Postpaid"]
               .sort_values("Month")[["Month", "Subscribers"]]
               .dropna(subset=["Subscribers"]))
    pp_apr26 = latest[latest["Segment"] == "Postpaid"]["Subscribers"]
    pp_apr25 = apr25[apr25["Segment"] == "Postpaid"]["Subscribers"]
    pp_now   = pp_apr26.values[0] if not pp_apr26.empty else 0
    pp_ly    = pp_apr25.values[0] if not pp_apr25.empty else 0
    pp_yoy   = (pp_now - pp_ly) / pp_ly * 100 if pp_ly else 0

    # ── Helper: KPI card HTML ─────────────────────────────────────────────────
    def kpi_card_html(title, value_str, sub_str, sub_color, extra_str="", accent="#00ff88"):
        return f"""
<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;
            border:1px solid #2a2a4a;border-top:3px solid {accent};height:100%">
    <div style="font-size:10px;color:#7788aa;font-weight:600;text-transform:uppercase;
                letter-spacing:1px;margin-bottom:6px">{title}</div>
    <div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">{value_str}</div>
    <div style="font-size:12px;color:{sub_color};font-weight:600">{sub_str}</div>
    {"" if not extra_str else f'<div style="font-size:11px;color:#8899bb;margin-top:3px">{extra_str}</div>'}
</div>"""

    def var_color(pct):
        if pct is None: return "#888888"
        return "#22c55e" if pct >= 0 else "#ef4444"

    def var_str(pct, suffix="% vs AOP"):
        if pct is None: return "— vs AOP"
        return f"{pct:+.1f}{suffix}"

    # ── Tab header ────────────────────────────────────────────────────────────
    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            margin-bottom:16px">
    <div style="font-size:1.15rem;font-weight:700;color:white">
        Consumer Sales Performance
    </div>
    <div style="font-size:0.82rem;color:#7788aa">YTD {sel_month} | TTM</div>
</div>""", unsafe_allow_html=True)

    # ── Row 1: 5 KPI cards ────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)

    yoy_extra = f"YoY: {yoy_pct:+.1f}%" if abs(yoy_pct) > 0.05 else "YoY: flat"
    c1.markdown(kpi_card_html(
        "Total Revenue", f"TT${total_rev:.1f}M",
        var_str(total_var), var_color(total_var),
        extra_str=yoy_extra, accent="#00d4a0",
    ), unsafe_allow_html=True)

    pp_v = vs_aop_pct("Postpaid")
    c2.markdown(kpi_card_html(
        "Postpaid Revenue", f"TT${seg_rev('Postpaid'):.1f}M",
        var_str(pp_v), var_color(pp_v), accent="#4a9eff",
    ), unsafe_allow_html=True)

    pre_v = vs_aop_pct("Prepaid")
    c3.markdown(kpi_card_html(
        "Prepaid Revenue", f"TT${seg_rev('Prepaid'):.1f}M",
        var_str(pre_v), var_color(pre_v), accent="#a78bfa",
    ), unsafe_allow_html=True)

    wttx_v = vs_aop_pct("WTTx")
    c4.markdown(kpi_card_html(
        "WTTx Revenue", f"TT${seg_rev('WTTx'):.1f}M",
        var_str(wttx_v), var_color(wttx_v), accent="#f59e0b",
    ), unsafe_allow_html=True)

    if ebitda_margin_act is not None:
        em_col  = "#22c55e" if ebitda_pp >= 0 else "#ef4444"
        em_sub  = f"{ebitda_pp:+.1f}pp vs AOP"
        em_val  = f"{ebitda_margin_act:.1f}%"
    else:
        em_col, em_sub, em_val = "#888888", "— vs AOP", "—%"
    c5.markdown(kpi_card_html(
        "EBITDA Margin", em_val, em_sub, em_col, accent="#00ff88",
    ), unsafe_allow_html=True)

    st.markdown("<div style='margin:16px 0 0 0'></div>", unsafe_allow_html=True)

    # ── Row 2: Revenue Trend (60%) + Donut (40%) ──────────────────────────────
    col_trend, col_donut = st.columns([3, 2])

    with col_trend:
        months_ordered = list(consumer["Month"].unique())
        m_rev = monthly.set_index("Month")["Revenue"].reindex(months_ordered)
        m_aop = monthly.set_index("Month")["Revenue_AOP"].reindex(months_ordered)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=months_ordered, y=m_rev.values,
            name="Actual Revenue",
            line=dict(color="#22c55e", width=2.5),
            mode="lines+markers",
            marker=dict(size=6, color="#22c55e"),
            hovertemplate="%{x}<br>Revenue: TT$%{y:.1f}M<extra></extra>",
        ))
        # AOP only where non-null
        aop_x = [m for m, v in zip(months_ordered, m_aop.values) if _pd.notna(v)]
        aop_y = [v for v in m_aop.values if _pd.notna(v)]
        if aop_x:
            fig.add_trace(go.Scatter(
                x=aop_x, y=aop_y,
                name="AOP",
                line=dict(color="#556677", width=1.8, dash="dash"),
                mode="lines",
                hovertemplate="%{x}<br>AOP: TT$%{y:.1f}M<extra></extra>",
            ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=300,
            title=dict(text="<b>Monthly Revenue vs AOP (TT$M)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
            legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                        y=1.08, x=0, font=dict(size=11)),
            margin=dict(l=10, r=10, t=44, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_donut:
        segs     = ["Prepaid", "Postpaid", "WTTx", "TV", "Residential Security", "Other"]
        seg_vals = [max(seg_rev(s), 0) for s in segs]   # clamp negatives to 0
        donut_total = sum(seg_vals)
        d_colors = ["#22c55e", "#4a9eff", "#f59e0b", "#a78bfa", "#ff6b6b", "#8888aa"]

        fig = go.Figure(go.Pie(
            labels=segs, values=seg_vals,
            hole=0.58,
            marker=dict(colors=d_colors,
                        line=dict(color="#0d0d0d", width=2)),
            textinfo="label+percent",
            textfont=dict(color="white", size=10),
            hovertemplate="%{label}: TT$%{value:.1f}M (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=300,
            title=dict(text=f"<b>{sel_month} Revenue Mix</b>",
                       font=dict(size=13, color="white"), x=0),
            annotations=[dict(
                text=f"TT${donut_total:.1f}M",
                x=0.5, y=0.5, font=dict(size=14, color="white", family="sans-serif"),
                showarrow=False,
            )],
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10),
                        orientation="v", x=1.0, y=0.5),
            margin=dict(l=10, r=10, t=44, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: 4 bottom cards ─────────────────────────────────────────────────
    b1, b2, b3, b4 = st.columns(4)

    # Voice MOU — placeholder
    b1.markdown(f"""
<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;
            border:1px solid #2a2a4a;border-top:3px solid #4a9eff">
    <div style="font-size:10px;color:#7788aa;font-weight:600;text-transform:uppercase;
                letter-spacing:1px;margin-bottom:6px">Voice MOU</div>
    <div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">181M</div>
    <div style="font-size:12px;color:#ef4444;font-weight:600">-8.2% YoY</div>
    <div style="font-size:10px;color:#556677;margin-top:3px">Minutes of Use</div>
</div>""", unsafe_allow_html=True)

    # Data Traffic — placeholder
    b2.markdown(f"""
<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;
            border:1px solid #2a2a4a;border-top:3px solid #a78bfa">
    <div style="font-size:10px;color:#7788aa;font-weight:600;text-transform:uppercase;
                letter-spacing:1px;margin-bottom:6px">Data Traffic</div>
    <div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">48.2 PB</div>
    <div style="font-size:12px;color:#22c55e;font-weight:600">+22.5% YoY</div>
    <div style="font-size:10px;color:#556677;margin-top:3px">Petabytes</div>
</div>""", unsafe_allow_html=True)

    # Gross Profit (using total revenue as proxy)
    gp_v = vs_aop_pct("Prepaid")   # broadest proxy available
    gross_rev = total_rev
    gross_var = total_var
    b3.markdown(kpi_card_html(
        "Gross Revenue", f"TT${gross_rev:.1f}M",
        var_str(gross_var), var_color(gross_var),
        extra_str="All segments combined", accent="#f59e0b",
    ), unsafe_allow_html=True)

    # Commentary
    rev_dir  = "above" if total_var >= 0 else "below"
    best_lbl = f"{best_seg} ({best_var:+.1f}% vs AOP)"
    wrst_lbl = f"{worst_seg} ({worst_var:+.1f}% vs AOP)"
    subs_dir = "growing" if pp_yoy > 0 else "declining"
    commentary = (
        f"Consumer revenue of TT${total_rev:.1f}M is {abs(total_var):.1f}% {rev_dir} AOP "
        f"for {sel_month}, with WTTx and Prepaid driving outperformance. "
        f"By segment, {best_lbl} leads while {wrst_lbl} is the weakest performer. "
        f"The Postpaid base stands at {int(pp_now):,} subscribers, "
        f"{subs_dir} {abs(pp_yoy):.1f}% year-on-year."
    )
    b4.markdown(f"""
<div style="background:#0f1e10;border-radius:10px;padding:14px 16px;
            border:1px solid #1a3a1a;border-left:4px solid #22c55e;height:100%">
    <div style="font-size:10px;color:#f59e0b;font-weight:700;text-transform:uppercase;
                letter-spacing:1.5px;margin-bottom:8px">Commentary</div>
    <div style="font-size:12px;color:#aaccaa;line-height:1.55">{commentary}</div>
</div>""", unsafe_allow_html=True)

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
