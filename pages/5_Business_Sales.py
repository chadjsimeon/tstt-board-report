import streamlit as st

st.set_page_config(page_title="TSTT | Business Sales", page_icon="🏢", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data, pivot_by_group, get_month_order
from utils.charts import (
    inject_css, page_header,
    line_chart, stacked_bar, grouped_bar, funnel_chart, donut_chart,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
)
from utils.rag import rev_var_rag

TICK  = dict(size=17)
MTICK = dict(color="#8888aa", size=17)
GRID  = "#1e1e3a"
LGND  = dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white", size=16),
             orientation="h", y=1.02, x=1, xanchor="right")


def _boost(fig, height=500):
    """Apply boardroom-scale font sizes to any Plotly figure."""
    fig.update_layout(
        height=height,
        font=dict(color="white"),
        title=dict(font=dict(size=17, color="white")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white", size=16),
                    orientation="h", y=1.02, x=1, xanchor="right"),
    )
    fig.update_xaxes(tickfont=TICK)
    fig.update_yaxes(tickfont=MTICK)
    return fig


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


def _kpi_tile(label, value, sub="", sub_color="#8888aa", accent="#4a9eff"):
    r, g, b = int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)
    return (
        f'<div style="background:#161B22;border-radius:10px;padding:18px 20px;'
        f'border:1px solid #252545;border-top:3px solid {accent}">'
        f'<div style="font-size:13px;color:#6677aa;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:6px">{label}</div>'
        f'<div style="font-size:32px;font-weight:800;color:white;line-height:1.1">{value}</div>'
        + (f'<div style="font-size:15px;color:{sub_color};margin-top:6px;font-weight:600">{sub}</div>' if sub else "")
        + f'</div>'
    )


inject_css()
data     = load_all_data()
biz      = data["Business_Sales"]
biz_mrr  = data.get("Business_Sales_MRR", pd.DataFrame())
pipeline = data["Pipeline"]
renewals = data["Renewals"]

page_header("Business Sales", "ICT Segments · Pipeline · At-Risk Renewals")

# ── Sidebar ───────────────────────────────────────────────────────────────────
months     = get_month_order(biz)
pip_months = get_month_order(pipeline)
sel_month  = st.sidebar.selectbox("Focus Month",    months,     index=len(months) - 1)
pip_month  = st.sidebar.selectbox("Pipeline Month", pip_months, index=len(pip_months) - 1)

tab1, tab2, tab3, tab_fp = st.tabs([
    "Sales Performance", "Pipeline", "Renewals at Risk", "Financial Performance",
])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Sales Performance
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    rev_pivot = pivot_by_group(biz, "Month", "Segment", "Revenue")
    seg_cols  = [c for c in rev_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = stacked_bar(rev_pivot, x="Month", y_cols=seg_cols,
                          title="Revenue by Segment — Stacked",
                          colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW])
        _boost(fig, 500)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        gp_pivot = pivot_by_group(biz, "Month", "Segment", "GP_Margin_Pct")
        gp_cols  = [c for c in gp_pivot.columns if c != "Month"]
        fig = line_chart(gp_pivot, x="Month", y_cols=gp_cols,
                         title="GP Margin % by Segment",
                         colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW])
        _boost(fig, 500)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        latest_rev = biz[biz["Month"] == sel_month][["Segment", "Revenue", "Revenue_AOP"]].copy()
        fig = grouped_bar(latest_rev, x="Segment", y_cols=["Revenue", "Revenue_AOP"],
                          title=f"{sel_month} — Revenue vs AOP",
                          colors=[BLUE, "#334466"], height=460)
        _boost(fig, 460)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        rev_vals = biz[biz["Month"] == sel_month][["Segment", "Revenue"]].copy()
        fig = donut_chart(rev_vals["Segment"].tolist(), rev_vals["Revenue"].tolist(),
                          title=f"{sel_month} Revenue Mix", height=460)
        _boost(fig, 460)
        fig.update_traces(textfont=dict(size=16))
        st.plotly_chart(fig, use_container_width=True)

    mrr_pivot = pivot_by_group(biz, "Month", "Segment", "MRR")
    mrr_cols  = [c for c in mrr_pivot.columns if c != "Month"]
    fig = stacked_bar(mrr_pivot, x="Month", y_cols=mrr_cols,
                      title="Monthly Recurring Revenue by Segment",
                      colors=[BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW])
    _boost(fig, 420)
    st.plotly_chart(fig, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — Pipeline
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    pip_latest = pipeline[pipeline["Month"] == pip_month].copy()
    won        = pip_latest[pip_latest["Stage"] == "Won"]
    total_deals = int(pip_latest["Deal_Count"].sum())
    pip_val     = float(pip_latest["Value_TTD_M"].sum())
    won_deals   = int(won["Deal_Count"].sum()) if not won.empty else 0

    # Summary tiles
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown(_kpi_tile("Total Deals", f"{total_deals:,}", accent=BLUE), unsafe_allow_html=True)
    with t2:
        st.markdown(_kpi_tile("Pipeline Value", f"{pip_val:,.0f}", accent=ORANGE), unsafe_allow_html=True)
    with t3:
        st.markdown(_kpi_tile("Won Deals", f"{won_deals:,}", accent=GREEN), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        fig = funnel_chart(stages=pip_latest["Stage"].tolist(),
                           values=pip_latest["Deal_Count"].tolist(),
                           title=f"{pip_month} Pipeline — Deal Count", height=480)
        _boost(fig, 480)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = funnel_chart(stages=pip_latest["Stage"].tolist(),
                           values=pip_latest["Value_TTD_M"].tolist(),
                           title=f"{pip_month} Pipeline — Value", height=480)
        _boost(fig, 480)
        st.plotly_chart(fig, use_container_width=True)

    pip_value    = pipeline.groupby(["Month", "Stage"], sort=False)["Value_TTD_M"].sum().reset_index()
    pip_by_stage = pip_value.pivot_table(index="Month", columns="Stage", values="Value_TTD_M", aggfunc="sum")
    month_order  = get_month_order(pipeline)
    pip_by_stage = pip_by_stage.reindex(month_order).reset_index()
    stage_cols   = [c for c in pip_by_stage.columns if c != "Month"]
    fig = stacked_bar(pip_by_stage, x="Month", y_cols=stage_cols,
                      title="Pipeline Value by Stage over Time",
                      colors=[BLUE, GREEN, PURPLE, ORANGE, YELLOW])
    _boost(fig, 420)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"<div style='font-size:18px;font-weight:700;color:white;margin:16px 0 10px'>"
                f"{pip_month} Pipeline Detail</div>", unsafe_allow_html=True)
    rows = ""
    for _, r in pip_latest.iterrows():
        win = f"{r['Win_Rate_Pct']:.1f}%" if r["Win_Rate_Pct"] == r["Win_Rate_Pct"] else "—"
        rows += f"""<tr>
            <td style="font-size:16px">{r['Stage']}</td>
            <td style="text-align:right;font-size:16px">{r['Deal_Count']:,.0f}</td>
            <td style="text-align:right;font-size:16px">{r['Value_TTD_M']:,.0f}</td>
            <td style="text-align:right;font-size:16px">{r['Avg_Deal_Size']:,.1f}</td>
            <td style="text-align:right;font-size:16px">{win}</td>
        </tr>"""
    st.markdown(f"""
    <table class="data-table">
        <thead><tr style="font-size:15px">
            <th>Stage</th><th style="text-align:right">Deals</th>
            <th style="text-align:right">Value</th>
            <th style="text-align:right">Avg Deal</th>
            <th style="text-align:right">Win Rate</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — Renewals at Risk
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    total_acv = renewals["ACV_TTD_M"].sum()
    high_risk = renewals[renewals["Risk_Level"] == "High"]["ACV_TTD_M"].sum()
    secured   = renewals[renewals["Status"] == "Secured"]["ACV_TTD_M"].sum()

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown(_kpi_tile("Total Renewal ACV", f"{total_acv:,.1f}", accent="#4a9eff"),
                    unsafe_allow_html=True)
    with r2:
        hr_pct = high_risk / total_acv * 100 if total_acv else 0
        st.markdown(_kpi_tile("High-Risk ACV", f"{high_risk:,.1f}",
                              sub=f"{hr_pct:.1f}% of portfolio", sub_color="#ef4444",
                              accent="#ef4444"), unsafe_allow_html=True)
    with r3:
        sec_pct = secured / total_acv * 100 if total_acv else 0
        st.markdown(_kpi_tile("Secured ACV", f"{secured:,.1f}",
                              sub=f"{sec_pct:.1f}% secured", sub_color="#22c55e",
                              accent="#22c55e"), unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        risk_counts = renewals["Risk_Level"].value_counts()
        fig = donut_chart(risk_counts.index.tolist(), risk_counts.values.tolist(),
                          title="Renewals by Risk Level (count)", height=380)
        _boost(fig, 380)
        fig.update_traces(textfont=dict(size=17))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        risk_acv = renewals.groupby("Risk_Level")["ACV_TTD_M"].sum()
        fig = donut_chart(risk_acv.index.tolist(), risk_acv.values.tolist(),
                          title="Renewals by Risk Level (ACV )", height=380)
        _boost(fig, 380)
        fig.update_traces(textfont=dict(size=17))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<div style='font-size:18px;font-weight:700;color:white;margin:16px 0 10px'>"
                "All At-Risk Renewals</div>", unsafe_allow_html=True)
    rows = ""
    for _, r in renewals.sort_values(["Risk_Level", "ACV_TTD_M"], ascending=[True, False]).iterrows():
        risk_class   = {"High": "risk-high", "Medium": "risk-medium", "Low": "risk-low"}.get(r["Risk_Level"], "")
        status_class = {"Secured": "status-secured", "In Progress": "status-in-progress"}.get(r["Status"], "")
        rows += f"""<tr>
            <td style="font-size:16px"><strong>{r['Customer']}</strong></td>
            <td style="font-size:16px">{r['Product_Service']}</td>
            <td style="text-align:right;font-size:16px">{r['ACV_TTD_M']:,.1f}</td>
            <td style="font-size:16px">{r['Expiry_Date']}</td>
            <td class="{risk_class}" style="font-size:16px">{r['Risk_Level']}</td>
            <td class="{status_class}" style="font-size:16px">{r['Status']}</td>
            <td style="font-size:14px;color:#aaaacc">{r['Action_Plan']}</td>
        </tr>"""
    st.markdown(f"""
    <table class="data-table">
        <thead><tr style="font-size:15px">
            <th>Customer</th><th>Product / Service</th>
            <th style="text-align:right">ACV</th>
            <th>Expiry</th><th>Risk</th><th>Status</th><th>Action Plan</th>
        </tr></thead>
        <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB FP — Financial Performance
# ═════════════════════════════════════════════════════════════════════════════
with tab_fp:
    biz_months_all = get_month_order(biz)
    biz_fy_months  = biz_months_all[:-1] if len(biz_months_all) > 12 else biz_months_all
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

    fp_t_rev  = _col(biz_latest, "Revenue")  or 0.0
    fp_t_aop  = _col(biz_latest, "Revenue_AOP") or 0.0
    fp_t_py   = _col(biz_py_snap, "Revenue")
    fp_tv_pct = _vp(fp_t_rev, fp_t_aop)
    fp_tv_m   = fp_t_rev - fp_t_aop

    mob_rev = _col(biz_latest, "Mobile");  mob_aop = _col(biz_latest, "Mobile_AOP");  mob_py  = _col(biz_py_snap, "Mobile")
    dc_rev  = _col(biz_latest, "Direct_Costs") or 0.0
    dc_aop  = _col(biz_latest, "Direct_Costs_AOP")
    dc_py   = _col(biz_py_snap, "Direct_Costs")

    # MRR / USAGE / OCC sourced from Business_Sales_MRR sheet (no AOP)
    def _mrr_col(df, col):
        if df.empty or col not in df.columns: return None
        v = df[col].sum()
        return float(v) if pd.notna(v) and v != 0 else None

    mrr_sel = biz_mrr[biz_mrr["Month"] == sel_month]  if not biz_mrr.empty else pd.DataFrame()
    mrr_py_snap = biz_mrr[biz_mrr["Month"] == biz_py_mon] if not biz_mrr.empty else pd.DataFrame()
    mrr_rev = _mrr_col(mrr_sel, "MRR")
    usg_rev = _mrr_col(mrr_sel, "USAGE")
    occ_rev = _mrr_col(mrr_sel, "OCC")
    mrr_py  = _mrr_col(mrr_py_snap, "MRR")
    usg_py  = _mrr_col(mrr_py_snap, "USAGE")
    occ_py  = _mrr_col(mrr_py_snap, "OCC")

    gp_col_v = _col(biz_latest, "Gross_Profit")
    gp_rev   = gp_col_v if gp_col_v is not None else (fp_t_rev - dc_rev)
    gp_aop_v = _col(biz_latest, "GP_AOP")
    if gp_aop_v is None and fp_t_aop and dc_aop is not None:
        gp_aop_v = fp_t_aop - dc_aop
    gp_py = _col(biz_py_snap, "Gross_Profit")
    if gp_py is None and fp_t_py is not None and dc_py is not None:
        gp_py = fp_t_py - dc_py
    gp_margin_pct = gp_rev / fp_t_rev * 100 if fp_t_rev else 0

    mob_subs  = _col(biz_latest, "Mobile_Subs")
    subs_aop  = _col(biz_latest, "Mobile_Subs_AOP")
    arpu_aop  = _col(biz_latest, "Mobile_ARPU_AOP")
    subs_py   = _col(biz_py_snap, "Mobile_Subs")
    arpu_val  = (mob_rev * 1_000_000 / mob_subs) if (mob_rev and mob_subs) else None

    def _trend(col, df=None):
        src = df if df is not None else biz
        if col not in src.columns: return None
        all_months = get_month_order(src) if df is not None else biz_months_all
        months_ref = all_months[-13:]
        return src.groupby("Month", sort=False)[col].sum().reindex(months_ref).fillna(0).tolist()

    fp_total_trend = _trend("Revenue")
    mob_trend      = _trend("Mobile")
    mrr_trend      = _trend("MRR",   biz_mrr) if not biz_mrr.empty else None
    usg_trend      = _trend("USAGE", biz_mrr) if not biz_mrr.empty else None
    occ_trend      = _trend("OCC",   biz_mrr) if not biz_mrr.empty else None

    FP_ACCENTS = ["#00d4a0", "#4a9eff", "#a78bfa", "#f59e0b", "#ff6b6b"]

    # ── Card builders ─────────────────────────────────────────────────────
    def fp_r1_card(label, val_str, aop_pct, aop_m_str, yoy_str, accent, spark_series=None, hide_aop=False):
        col = rev_var_rag(aop_pct)
        if hide_aop:
            aop_html = '<span style="color:transparent">&nbsp;</span>'
        else:
            aop_html = (
                f'<span style="color:{col}">{aop_pct:+.1f}%&nbsp;vs&nbsp;AOP&nbsp;|&nbsp;{aop_m_str}</span>'
                if aop_pct is not None else '<span style="color:#445566">— vs AOP</span>'
            )
        _yoy_col = "#22c55e" if (yoy_str and yoy_str.startswith('+')) else "#ef4444"
        yoy_html = (
            f'<span style="color:{_yoy_col};font-weight:700">{yoy_str}</span>'
            if yoy_str else '<span style="color:#445566">— vs PY</span>'
        )
        spark_html = (
            f'<div style="margin-top:8px;opacity:0.85">{_sparkline(spark_series, accent)}</div>'
            if spark_series else '<div style="margin-top:8px;height:44px"></div>'
        )
        return (
            f'<div style="background:#161B22;border-radius:10px;padding:16px 14px;'
            f'border:1px solid #252545;border-top:3px solid {accent}">'
            f'<div style="font-size:16px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:8px">{label}</div>'
            f'<div style="font-size:42px;font-weight:800;color:white;margin-bottom:8px;'
            f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
            f'<div style="font-size:19px;font-weight:600;margin-bottom:4px">{aop_html}</div>'
            f'<div style="font-size:19px;font-weight:600">{yoy_html}</div>'
            f'{spark_html}</div>'
        )

    def fp_r2_card(label, val_str, aop_str, aop_col, py_str, accent="#4a9eff", py_col=None):
        _py_col = py_col if py_col else (
            "#22c55e" if (py_str and py_str.startswith('+')) else "#ef4444"
        )
        return (
            f'<div style="background:#161B22;border-radius:10px;padding:14px 16px;'
            f'border:1px solid #252545;border-top:2px solid {accent};height:100%">'
            f'<div style="font-size:16px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.2px;margin-bottom:5px">{label}</div>'
            f'<div style="font-size:38px;font-weight:800;color:white;margin-bottom:6px">{val_str}</div>'
            f'<div style="font-size:19px;color:{aop_col};font-weight:600;margin-bottom:3px">{aop_str}</div>'
            f'<div style="font-size:19px;color:{_py_col};font-weight:600">{py_str}</div>'
            f'</div>'
        )

    # ── Pre-compute strings ────────────────────────────────────────────────
    dc_vp = _vp(dc_rev, dc_aop)
    dc_vm = _vm(dc_rev, dc_aop)
    dc_aop_color = "#ef4444" if (dc_vp or 0) > 0 else "#22c55e"
    dc_aop_str   = f"{dc_vp:+.1f}% vs AOP | {dc_vm:+.1f}" if dc_vp is not None else "— vs AOP"
    dc_py_str    = f"{dc_rev - dc_py:+.1f} vs PY" if dc_py is not None else "— vs PY"
    dc_py_col    = ("#ef4444" if (dc_py is not None and dc_rev >= dc_py) else "#22c55e") if dc_py is not None else "#7788aa"

    gp_vp = _vp(gp_rev, gp_aop_v)
    gp_vm = _vm(gp_rev, gp_aop_v)
    gp_aop_color = rev_var_rag(gp_vp)
    gp_aop_str   = f"{gp_vp:+.1f}% vs AOP | {gp_vm:+.1f}" if gp_vp is not None else f"{gp_margin_pct:.1f}% margin"
    gp_py_str    = f"{gp_rev - gp_py:+.1f} vs PY" if gp_py is not None else f"{gp_margin_pct:.1f}% margin"

    subs_str = f"{int(mob_subs):,}" if mob_subs else "—"
    s_vp = _vp(mob_subs, subs_aop) if (mob_subs and subs_aop) else None
    if s_vp is not None:
        s_vm = int(mob_subs - subs_aop)
        subs_aop_str = f"{s_vp:+.1f}% vs AOP | {s_vm:+,}"
        subs_aop_col = rev_var_rag(s_vp)
    else:
        subs_aop_str, subs_aop_col = "— vs AOP", "#445566"
    s_py_pct = _vp(mob_subs, subs_py) if (mob_subs and subs_py) else None
    subs_py_str = (f"{s_py_pct:+.1f}% vs PY | {int(mob_subs - subs_py):+,}"
                   if s_py_pct is not None else "— vs PY")

    arpu_str = f"{arpu_val:,.0f}" if arpu_val else "—"
    arpu_py  = (mob_py * 1_000_000 / subs_py) if (mob_py and subs_py) else None
    arpu_py_str = (f"{arpu_val - arpu_py:+,.0f} vs PY | {(arpu_val - arpu_py)/arpu_py*100:+.1f}%"
                   if (arpu_val and arpu_py) else "— vs PY")
    arpu_aop_pct = _vp(arpu_val, arpu_aop) if (arpu_val and arpu_aop) else None
    arpu_aop_str = (f"{arpu_val - arpu_aop:+,.0f} vs AOP | {arpu_aop_pct:+.1f}%"
                    if arpu_aop_pct is not None else "— vs AOP")
    arpu_aop_col = rev_var_rag(arpu_aop_pct)

    def _r1_col_card(col_name, label, accent, trend):
        rv  = _col(biz_latest, col_name)
        aop = _col(biz_latest, f"{col_name}_AOP")
        py  = _col(biz_py_snap, col_name)
        rv_f = rv if rv is not None else 0.0
        vp = _vp(rv_f, aop); vm = _vm(rv_f, aop)
        return fp_r1_card(
            label,
            f"{rv_f:.1f}" if rv is not None else "—",
            vp,
            f"{vm:+.1f}" if vm is not None else "—",
            f"{rv_f - py:+.1f} vs PY" if py is not None else None,
            accent, spark_series=trend,
        )

    # ── Layout ────────────────────────────────────────────────────────────
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
    _sp = "<div style='height:10px'></div>"

    left_area, right_area = st.columns([2, 3])

    with left_area:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(fp_r1_card(
                "Total Revenue", f"{fp_t_rev:.1f}",
                fp_tv_pct, f"{fp_tv_m:+.1f}",
                f"{fp_t_rev - fp_t_py:+.1f} vs PY" if fp_t_py is not None else None,
                FP_ACCENTS[0], spark_series=fp_total_trend,
            ), unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card("Direct Costs", f"{dc_rev:.1f}",
                                   dc_aop_str, dc_aop_color, dc_py_str, accent="#ff6b6b", py_col=dc_py_col),
                        unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card("Gross Profit", f"{gp_rev:.1f}",
                                   gp_aop_str, gp_aop_color, gp_py_str, accent="#22c55e"),
                        unsafe_allow_html=True)

        with c2:
            st.markdown(_r1_col_card("Mobile", "Mobile", FP_ACCENTS[1], mob_trend),
                        unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card("Mobile Subs", subs_str,
                                   subs_aop_str, subs_aop_col, subs_py_str,
                                   accent=FP_ACCENTS[0]), unsafe_allow_html=True)
            st.markdown(_sp, unsafe_allow_html=True)
            st.markdown(fp_r2_card("ARPU (Mobile)", arpu_str,
                                   arpu_aop_str, arpu_aop_col, arpu_py_str,
                                   accent=FP_ACCENTS[1]), unsafe_allow_html=True)

    with right_area:
        c3, c4, c5 = st.columns(3)

        def _mrr_card(label, rv, py, accent, trend):
            rv_f = rv if rv is not None else 0.0
            return fp_r1_card(
                label,
                f"{rv_f:.1f}" if rv is not None else "—",
                None, "—",
                f"{rv_f - py:+.1f} vs PY" if py is not None else None,
                accent, spark_series=trend, hide_aop=True,
            )

        with c3:
            st.markdown(_mrr_card("MRR",   mrr_rev, mrr_py, FP_ACCENTS[2], mrr_trend), unsafe_allow_html=True)
        with c4:
            st.markdown(_mrr_card("USAGE", usg_rev, usg_py, FP_ACCENTS[3], usg_trend), unsafe_allow_html=True)
        with c5:
            st.markdown(_mrr_card("OCC", occ_rev, occ_py, FP_ACCENTS[4], occ_trend), unsafe_allow_html=True)

        st.markdown(_sp, unsafe_allow_html=True)
        _trend_months = (get_month_order(biz_mrr)[-13:] if not biz_mrr.empty else biz_months_all[-13:])
        fig_lines = go.Figure()
        for _name, _vals, _color in [
            ("MRR",   mrr_trend  or [0] * len(_trend_months), FP_ACCENTS[2]),
            ("OCC",   occ_trend  or [0] * len(_trend_months), FP_ACCENTS[4]),
            ("USAGE", usg_trend  or [0] * len(_trend_months), FP_ACCENTS[3]),
        ]:
            fig_lines.add_trace(go.Scatter(
                x=_trend_months, y=_vals,
                mode="lines+markers", name=_name,
                line=dict(color=_color, width=2.5), marker=dict(size=6),
                hovertemplate=f"<b>{_name}</b>: %{{y:.1f}}<extra></extra>",
            ))
        fig_lines.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=420,
            title=dict(text="<b>MRR / OCC / USAGE Trend</b>",
                       font=dict(size=15, color="white"), x=0),
            xaxis=dict(showgrid=False, tickfont=dict(size=15), tickangle=-30),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                       tickfont=dict(size=15), tickprefix="$"),
            legend=dict(bgcolor="rgba(20,20,40,0.8)", font=dict(size=14, color="white"),
                        orientation="v", x=1.01, y=1, xanchor="left", yanchor="top"),
            margin=dict(l=10, r=100, t=44, b=10),
        )
        st.plotly_chart(fig_lines, use_container_width=True)

    # ── Commentary ────────────────────────────────────────────────────────
    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

    rev_dir     = "above" if (fp_tv_pct or 0) >= 0 else "below"
    yoy_abs     = abs(fp_t_rev - fp_t_py) if fp_t_py is not None else 0
    yoy_sign    = "increase" if (fp_t_py is not None and fp_t_rev >= fp_t_py) else "decline"
    aop_col_cmt = rev_var_rag(fp_tv_pct)

    cmt_parts = [
        f"Business Sales revenue of <strong style='color:white'>{fp_t_rev:.1f}</strong> "
        f"in {sel_month} is "
        f"<strong style='color:{aop_col_cmt}'>{abs(fp_tv_pct or 0):.1f}% {rev_dir} AOP</strong>"
        + (f" ({fp_tv_m:+.1f})" if fp_t_aop else "")
        + (f", a year-on-year {yoy_sign} of "
           f"<strong style='color:#f59e0b'>{yoy_abs:.1f}</strong>." if fp_t_py is not None else "."),
    ]
    if mob_rev is not None:
        mob_share = mob_rev / fp_t_rev * 100 if fp_t_rev else 0
        cmt_parts.append(
            f" Mobile revenue of <strong style='color:white'>{mob_rev:.1f}</strong> "
            f"({mob_share:.0f}% of total)"
        )
        if arpu_val is not None:
            cmt_parts.append(f" delivers an ARPU of <strong style='color:white'>{arpu_val:,.0f}</strong>.")
        else:
            cmt_parts.append(".")
    if mrr_rev:
        mrr_share = mrr_rev / fp_t_rev * 100 if fp_t_rev else 0
        cmt_parts.append(
            f" MRR stands at <strong style='color:white'>{mrr_rev:.1f}</strong> "
            f"({mrr_share:.0f}% of total revenue)."
        )
    cmt_parts.append(
        f" Direct Costs of <strong style='color:white'>{dc_rev:.1f}</strong> yield a "
        f"Gross Profit of <strong style='color:white'>{gp_rev:.1f}</strong> "
        f"({gp_margin_pct:.1f}% margin)."
    )

    st.markdown(
        f'<div style="background:#161B22;border-radius:12px;padding:20px 24px;'
        f'border:1px solid #1a3520;border-left:4px solid #22c55e">'
        f'<div style="font-size:11px;color:#f59e0b;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:2px;margin-bottom:12px">&#x25A0;&nbsp;Commentary</div>'
        f'<div style="font-size:15px;color:#aaccaa;line-height:1.8">{"".join(cmt_parts)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
