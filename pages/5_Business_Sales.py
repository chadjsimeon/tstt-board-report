import streamlit as st

st.set_page_config(page_title="TSTT | Business Sales", page_icon="🏢", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data, pivot_by_group, get_month_order
from utils.charts import (
    inject_css, page_header, styled_metric,
    line_chart, stacked_bar, grouped_bar, funnel_chart, donut_chart,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
)


def _sparkline(series, color, height=44):
    vals = [float(v) if pd.notna(v) else 0.0 for v in series]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    w = 220
    pts = []
    for i, v in enumerate(vals):
        x = i * w / max(len(vals) - 1, 1)
        y = height - (v - mn) / rng * height * 0.78 - height * 0.11
        pts.append(f"{x:.1f},{y:.1f}")
    line_pts = " ".join(pts)
    fill_pts = f"0,{height} {line_pts} {w},{height}"
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {w} {height}" '
        f'preserveAspectRatio="none" style="display:block;margin-top:8px">'
        f'<polygon points="{fill_pts}" fill="rgba({r},{g},{b},0.15)"/>'
        f'<polyline points="{line_pts}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
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

tab1, tab2, tab3, tab_fp = st.tabs([
    "Sales Performance", "Pipeline", "Renewals at Risk", "Financial Performance",
])

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

# ─────────────────────────────────────────────────────────────────────────────
# TAB FP — Financial Performance
# ─────────────────────────────────────────────────────────────────────────────
with tab_fp:
    # ── Data prep ─────────────────────────────────────────────────────────
    biz_months_all = get_month_order(biz)
    biz_fp_dt   = pd.to_datetime(sel_month, format="%b-%y", errors="coerce")
    biz_py_mon  = ((biz_fp_dt - pd.DateOffset(months=12)).strftime("%b-%y")
                   if pd.notna(biz_fp_dt) else biz_months_all[0])
    biz_latest  = biz[biz["Month"] == sel_month].copy()
    biz_py_snap = biz[biz["Month"] == biz_py_mon].copy()

    def _col(df, col):
        if col not in df.columns: return None
        v = df[col].sum()
        return float(v) if pd.notna(v) else None

    def _vp(rev, aop): return (rev - aop) / abs(aop) * 100 if aop else None
    def _vm(rev, aop): return rev - aop if aop is not None else None

    # Total Revenue
    fp_t_rev = _col(biz_latest, "Revenue") or 0.0
    fp_t_aop = _col(biz_latest, "Revenue_AOP") or 0.0
    fp_t_py  = _col(biz_py_snap, "Revenue")
    fp_tv_pct = _vp(fp_t_rev, fp_t_aop)
    fp_tv_m   = fp_t_rev - fp_t_aop

    # Mobile
    mob_rev = _col(biz_latest, "Mobile")
    mob_aop = _col(biz_latest, "Mobile_AOP")
    mob_py  = _col(biz_py_snap, "Mobile")

    # MRR
    mrr_rev = _col(biz_latest, "MRR") or 0.0
    mrr_aop = _col(biz_latest, "MRR_AOP")
    mrr_py  = _col(biz_py_snap, "MRR")

    # USAGE
    usg_rev = _col(biz_latest, "USAGE")
    usg_aop = _col(biz_latest, "USAGE_AOP")
    usg_py  = _col(biz_py_snap, "USAGE")

    # OCC
    occ_rev = _col(biz_latest, "OCC")
    occ_aop = _col(biz_latest, "OCC_AOP")
    occ_py  = _col(biz_py_snap, "OCC")

    # Direct Costs
    dc_rev = _col(biz_latest, "Direct_Costs") or 0.0
    dc_aop = _col(biz_latest, "Direct_Costs_AOP")
    dc_py  = _col(biz_py_snap, "Direct_Costs")

    # Gross Profit — use column if present, else derive from Revenue − Direct Costs
    gp_col_v = _col(biz_latest, "Gross_Profit")
    gp_rev   = gp_col_v if gp_col_v is not None else (fp_t_rev - dc_rev)
    gp_aop_v = _col(biz_latest, "GP_AOP")
    if gp_aop_v is None and fp_t_aop and dc_aop is not None:
        gp_aop_v = fp_t_aop - dc_aop
    gp_py = _col(biz_py_snap, "Gross_Profit")
    if gp_py is None and fp_t_py is not None and dc_py is not None:
        gp_py = fp_t_py - dc_py
    gp_margin_pct = gp_rev / fp_t_rev * 100 if fp_t_rev else 0

    # Mobile Subs / ARPU
    mob_subs = _col(biz_latest, "Mobile_Subs")
    subs_aop = _col(biz_latest, "Subs_AOP")
    subs_py  = _col(biz_py_snap, "Mobile_Subs")
    arpu_val = (mob_rev * 1_000_000 / mob_subs) if (mob_rev and mob_subs) else None

    # Sparkline trends (column-based)
    def _trend(col):
        if col not in biz.columns: return None
        return biz.groupby("Month", sort=False)[col].sum().reindex(biz_months_all).fillna(0).tolist()

    fp_total_trend = _trend("Revenue")
    mob_trend = _trend("Mobile")
    mrr_trend = _trend("MRR")
    usg_trend = _trend("USAGE")
    occ_trend = _trend("OCC")

    FP_ACCENTS = ["#00d4a0", "#4a9eff", "#a78bfa", "#f59e0b", "#ff6b6b"]

    # Segment data — used only for revenue mix donut
    seg_rev = (biz_latest[["Segment", "Revenue"]]
               .groupby("Segment", sort=False).sum()
               .sort_values("Revenue", ascending=False))
    all_segs   = seg_rev.index.tolist()
    top_segs   = all_segs[:4]
    other_segs = all_segs[4:]
    other_rev  = float(biz_latest[biz_latest["Segment"].isin(other_segs)]["Revenue"].sum()) if other_segs else 0.0

    # ── Card builders ─────────────────────────────────────────────────────
    def fp_r1_card(label, val_str, aop_pct, aop_m_str, yoy_str, accent, spark_series=None):
        col = "#22c55e" if (aop_pct is not None and aop_pct >= 0) else "#ef4444"
        aop_html = (
            f'<span style="color:{col}">{aop_pct:+.1f}%&nbsp;vs&nbsp;AOP&nbsp;|&nbsp;{aop_m_str}</span>'
            if aop_pct is not None else '<span style="color:#445566">— vs AOP</span>'
        )
        yoy_html = (
            f'<span style="color:#f59e0b;font-weight:700">{yoy_str}</span>'
            if yoy_str else '<span style="color:#445566">— vs PY</span>'
        )
        spark_html = (
            f'<div style="margin-top:8px;opacity:0.85">{_sparkline(spark_series, accent)}</div>'
            if spark_series else '<div style="margin-top:8px;height:44px"></div>'
        )
        return (
            f'<div style="background:#151528;border-radius:10px;padding:14px 12px;'
            f'border:1px solid #252545;border-top:3px solid {accent}">'
            f'<div style="font-size:13px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:8px">{label}</div>'
            f'<div style="font-size:26px;font-weight:800;color:white;margin-bottom:8px;'
            f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
            f'<div style="font-size:14px;font-weight:600;margin-bottom:3px">{aop_html}</div>'
            f'<div style="font-size:14px;font-weight:600">{yoy_html}</div>'
            f'{spark_html}</div>'
        )

    def fp_r2_card(label, val_str, aop_str, aop_col, py_str, accent="#4a9eff"):
        return (
            f'<div style="background:#151528;border-radius:10px;padding:12px 14px;'
            f'border:1px solid #252545;border-top:2px solid {accent};height:100%">'
            f'<div style="font-size:13px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.2px;margin-bottom:5px">{label}</div>'
            f'<div style="font-size:20px;font-weight:800;color:white;margin-bottom:4px">{val_str}</div>'
            f'<div style="font-size:14px;color:{aop_col};font-weight:600;margin-bottom:2px">{aop_str}</div>'
            f'<div style="font-size:14px;color:#f59e0b;font-weight:600">{py_str}</div>'
            f'</div>'
        )

    # ── Pre-compute card display strings ──────────────────────────────────
    # Direct Costs
    dc_vp = _vp(dc_rev, dc_aop)
    dc_vm = _vm(dc_rev, dc_aop)
    dc_aop_color = "#ef4444" if (dc_vp or 0) > 0 else "#22c55e"
    dc_aop_str   = (f"{dc_vp:+.1f}% vs AOP | TT${dc_vm:+.1f}M" if dc_vp is not None else "— vs AOP")
    dc_py_str    = (f"TT${dc_rev - dc_py:+.1f}M vs PY" if dc_py is not None else "— vs PY")

    # Gross Profit
    gp_vp = _vp(gp_rev, gp_aop_v)
    gp_vm = _vm(gp_rev, gp_aop_v)
    gp_aop_color = "#22c55e" if (gp_vp or 0) >= 0 else "#ef4444"
    gp_aop_str   = (f"{gp_vp:+.1f}% vs AOP | TT${gp_vm:+.1f}M" if gp_vp is not None else f"{gp_margin_pct:.1f}% margin")
    gp_py_str    = (f"TT${gp_rev - gp_py:+.1f}M vs PY" if gp_py is not None else f"{gp_margin_pct:.1f}% margin")

    # Mobile Subs
    subs_str = f"{int(mob_subs):,}" if mob_subs is not None else "—"
    if mob_subs is not None and subs_aop is not None:
        s_vp = _vp(mob_subs, subs_aop)
        s_vm = int(mob_subs - subs_aop)
        subs_aop_str = f"{s_vp:+.1f}% vs AOP | {s_vm:+,} subs"
        subs_aop_col = "#22c55e" if (s_vp or 0) >= 0 else "#ef4444"
    else:
        subs_aop_str, subs_aop_col = "— vs AOP", "#445566"
    if mob_subs is not None and subs_py is not None:
        s_py_diff = int(mob_subs - subs_py)
        s_py_pct  = _vp(mob_subs, subs_py)
        subs_py_str = f"{s_py_pct:+.1f}% vs PY | {s_py_diff:+,} subs"
    else:
        subs_py_str = "— vs PY"

    # ARPU
    arpu_str = f"TT${arpu_val:,.0f}" if arpu_val is not None else "—"

    def _r1_col_card(col_name, label, accent, trend):
        rv   = _col(biz_latest, col_name)
        aop  = _col(biz_latest, f"{col_name}_AOP")
        py   = _col(biz_py_snap, col_name)
        rv_f = rv if rv is not None else 0.0
        vp   = _vp(rv_f, aop)
        vm   = _vm(rv_f, aop)
        return fp_r1_card(
            label,
            f"TT${rv_f:.1f}M" if rv is not None else "—",
            vp,
            f"TT${vm:+.1f}M" if vm is not None else "—",
            f"TT${rv_f - py:+.1f}M vs PY" if py is not None else None,
            accent, spark_series=trend,
        )

    # ════════════════════════════════════════════════════════════════════
    # MAIN LAYOUT — left 2/5 (Revenue + Mobile stacks) | right 3/5 (MRR·USAGE·OCC + graph)
    # Each inner column is 1/5 of total page width
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
    _sp = "<div style='height:8px'></div>"

    left_area, right_area = st.columns([2, 3])

    with left_area:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(fp_r1_card(
                "Total Revenue", f"TT${fp_t_rev:.1f}M",
                fp_tv_pct, f"TT${fp_tv_m:+.1f}M",
                f"TT${fp_t_rev - fp_t_py:+.1f}M vs PY" if fp_t_py is not None else None,
                FP_ACCENTS[0], spark_series=fp_total_trend,
            ), unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card(
                "Direct Costs", f"TT${dc_rev:.1f}M",
                dc_aop_str, dc_aop_color, dc_py_str, accent="#ff6b6b",
            ), unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card(
                "Gross Profit", f"TT${gp_rev:.1f}M",
                gp_aop_str, gp_aop_color, gp_py_str, accent="#22c55e",
            ), unsafe_allow_html=True)

        with c2:
            st.markdown(_r1_col_card("Mobile", "Mobile", FP_ACCENTS[1], mob_trend), unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card(
                "Mobile Subs", subs_str,
                subs_aop_str, subs_aop_col, subs_py_str, accent=FP_ACCENTS[0],
            ), unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card(
                "ARPU (Mobile)", arpu_str,
                "Mobile Rev ÷ Subs", "#aaaacc", "— vs PY", accent=FP_ACCENTS[1],
            ), unsafe_allow_html=True)

    with right_area:
        c3, c4, c5 = st.columns(3)
        with c3:
            st.markdown(_r1_col_card("MRR",   "MRR",   FP_ACCENTS[2], mrr_trend), unsafe_allow_html=True)
        with c4:
            st.markdown(_r1_col_card("USAGE", "USAGE", FP_ACCENTS[3], usg_trend), unsafe_allow_html=True)
        with c5:
            st.markdown(_r1_col_card("OCC",   "OCC",   FP_ACCENTS[4], occ_trend), unsafe_allow_html=True)

        # Line graph — starts at Direct Costs / Mobile Subs level, spans down to Gross Profit / ARPU
        st.markdown(_sp, unsafe_allow_html=True)
        _trend_months = biz_months_all
        fig_lines = go.Figure()
        for _name, _vals, _color in [
            ("MRR",   mrr_trend  or [0] * len(_trend_months), FP_ACCENTS[2]),
            ("OCC",   occ_trend  or [0] * len(_trend_months), FP_ACCENTS[4]),
            ("USAGE", usg_trend  or [0] * len(_trend_months), FP_ACCENTS[3]),
        ]:
            fig_lines.add_trace(go.Scatter(
                x=_trend_months, y=_vals,
                mode="lines+markers", name=_name,
                line=dict(color=_color, width=2), marker=dict(size=5),
                hovertemplate=f"<b>{_name}</b>: TT$%{{y:.1f}}M<extra></extra>",
            ))
        fig_lines.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=210,
            title=dict(text="<b>MRR / OCC / USAGE Trend (TT$M)</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(showgrid=False, tickfont=dict(size=13), tickangle=-30),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickfont=dict(size=13), tickprefix="$"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="white"),
                        orientation="h", x=0, y=1.15, yanchor="bottom"),
            margin=dict(l=10, r=10, t=44, b=10),
        )
        st.plotly_chart(fig_lines, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════
    # COMMENTARY — full width at the bottom
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    rev_dir     = "above" if (fp_tv_pct or 0) >= 0 else "below"
    yoy_abs     = abs(fp_t_rev - fp_t_py) if fp_t_py is not None else 0
    yoy_sign    = "increase" if (fp_t_py is not None and fp_t_rev >= fp_t_py) else "decline"
    aop_col_cmt = "#22c55e" if (fp_tv_pct or 0) >= 0 else "#ef4444"

    cmt_parts = [
        f"Business Sales revenue of <strong style='color:white'>TT${fp_t_rev:.1f}M</strong> "
        f"in {sel_month} is "
        f"<strong style='color:{aop_col_cmt}'>{abs(fp_tv_pct or 0):.1f}% {rev_dir} AOP</strong>"
        + (f" (TT${fp_tv_m:+.1f}M)" if fp_t_aop else "")
        + (f", a year-on-year {yoy_sign} of "
           f"<strong style='color:#f59e0b'>TT${yoy_abs:.1f}M</strong>." if fp_t_py is not None else "."),
    ]
    if mob_rev is not None:
        mob_share = mob_rev / fp_t_rev * 100 if fp_t_rev else 0
        cmt_parts.append(
            f" Mobile revenue of <strong style='color:white'>TT${mob_rev:.1f}M</strong> "
            f"({mob_share:.0f}% of total)"
        )
        if arpu_val is not None:
            cmt_parts.append(f" delivers an ARPU of <strong style='color:white'>TT${arpu_val:,.0f}</strong>.")
        else:
            cmt_parts.append(".")
    if mrr_rev:
        mrr_share = mrr_rev / fp_t_rev * 100 if fp_t_rev else 0
        cmt_parts.append(
            f" MRR stands at <strong style='color:white'>TT${mrr_rev:.1f}M</strong> "
            f"({mrr_share:.0f}% of total revenue)."
        )
    cmt_parts.append(
        f" Direct Costs of <strong style='color:white'>TT${dc_rev:.1f}M</strong> yield a "
        f"Gross Profit of <strong style='color:white'>TT${gp_rev:.1f}M</strong> "
        f"({gp_margin_pct:.1f}% margin)."
    )

    st.markdown(
        f'<div style="background:#090f0a;border-radius:12px;padding:18px 22px;'
        f'border:1px solid #1a3520;border-left:4px solid #22c55e">'
        f'<div style="font-size:10px;color:#f59e0b;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:2px;margin-bottom:12px">&#x25A0;&nbsp;Commentary</div>'
        f'<div style="font-size:13px;color:#aaccaa;line-height:1.75">{"".join(cmt_parts)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
