import streamlit as st

st.set_page_config(page_title="TSTT | DPDI", page_icon="💻", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data, get_month_order
from utils.month_selector import focus_month_selector, filter_data_to_month
from utils.charts import inject_css
from utils.rag import rag, rev_var_rag, gp_margin_rag

inject_css()
focus_month_selector()
data = load_all_data()
dpdi = data["DPDI"]
dpdi = filter_data_to_month(dpdi)
months = get_month_order(dpdi)

if not months:
    st.warning("No DPDI data available on or before the selected focus month.")
    st.stop()

# DPDI data can end earlier than the group financials, so the focus month is not
# guaranteed to exist here. `dpdi` is already filtered to months <= focus month,
# so we fall back to its most recent month that actually carries figures —
# trailing months exist as rows but are all zero. "Carries figures" uses the same
# test the product table below applies: non-zero Revenue or Revenue_AOP.
_activity = (dpdi.groupby("Month", sort=False)[["Revenue", "Revenue_AOP"]]
                 .sum().abs().sum(axis=1))
_populated = [m for m in months if _activity.get(m, 0) > 0]

focus_month = st.session_state.get("focus_month")
if focus_month in months:
    sel_month = focus_month
else:
    sel_month = _populated[-1] if _populated else months[-1]

# ── Selected month — exclude products with no revenue and no AOP ──────────────
snap = dpdi[dpdi["Month"] == sel_month].copy()
_agg_cols = ["Revenue", "Revenue_AOP", "Gross_Profit", "EBITDA", "Direct_Costs"]
if "Direct_Costs_AOP" in snap.columns:
    _agg_cols.append("Direct_Costs_AOP")
ytd  = snap.groupby("Product")[_agg_cols].sum()
ytd = ytd[(ytd["Revenue"] != 0) | (ytd["Revenue_AOP"] != 0)]

total_rev    = ytd["Revenue"].sum()
total_aop    = ytd["Revenue_AOP"].sum()
total_gp     = ytd["Gross_Profit"].sum()
total_dc     = ytd["Direct_Costs"].sum()
total_dc_aop = ytd["Direct_Costs_AOP"].sum() if "Direct_Costs_AOP" in ytd.columns else 0.0
total_ebitda = ytd["EBITDA"].sum()

has_egovtt      = "e-GOVTT" in ytd.index
egovtt_rev      = ytd.loc["e-GOVTT", "Revenue"]     if has_egovtt else 0.0
egovtt_aop      = ytd.loc["e-GOVTT", "Revenue_AOP"] if has_egovtt else 0.0
excl_rev        = total_rev  - egovtt_rev
excl_aop        = total_aop  - egovtt_aop
egovtt_pipeline = egovtt_aop

rev_var_pct  = (total_rev - total_aop) / abs(total_aop) * 100 if total_aop else 0
excl_var_pct = (excl_rev  - excl_aop)  / abs(excl_aop)  * 100 if excl_aop  else 0
gp_margin    = total_gp / total_rev * 100 if total_rev else 0

ebitda_display = f"({abs(total_ebitda):.1f})" if total_ebitda < 0 else f"{total_ebitda:.1f}"
_dc_aop_ref    = total_dc_aop if total_dc_aop else total_aop
dc_below_aop   = total_dc < _dc_aop_ref
# Direct Costs use the cost convention: variance = AOP − Actual (underspend positive)
_dc_var_pct    = (_dc_aop_ref - total_dc) / abs(_dc_aop_ref) * 100 if _dc_aop_ref else 0
dc_sub_text    = f"{_dc_var_pct:+.1f}% vs AOP | {(_dc_aop_ref - total_dc)*1000:+,.0f}" if _dc_aop_ref else "— vs AOP"
dc_sub_color   = rev_var_rag(_dc_var_pct)

# ── vs PY / sparkline prep ────────────────────────────────────────────────────
sel_idx      = months.index(sel_month)
py_month     = months[sel_idx - 12] if sel_idx >= 12 else None
trend_months = months[max(0, sel_idx - 12): sel_idx + 1]

snap_py = dpdi[dpdi["Month"] == py_month] if py_month else dpdi.iloc[:0]
ytd_py  = snap_py.groupby("Product")[_agg_cols].sum() if not snap_py.empty else None
py_rev        = ytd_py["Revenue"].sum()       if ytd_py is not None else 0.0
py_egovtt_rev = (ytd_py.loc["e-GOVTT", "Revenue"]
                 if ytd_py is not None and "e-GOVTT" in ytd_py.index else 0.0)
py_excl_rev   = py_rev - py_egovtt_rev
py_gp         = ytd_py["Gross_Profit"].sum()  if ytd_py is not None else 0.0
py_dc         = ytd_py["Direct_Costs"].sum()  if ytd_py is not None else 0.0

rev_py_pct  = (total_rev - py_rev)      / abs(py_rev)      * 100 if py_rev      else None
excl_py_pct = (excl_rev  - py_excl_rev) / abs(py_excl_rev) * 100 if py_excl_rev else None
gp_py_pct   = (total_gp  - py_gp)       / abs(py_gp)       * 100 if py_gp       else None
dc_py_pct   = (py_dc  - total_dc)       / abs(py_dc)       * 100 if py_dc       else None

_tg        = dpdi[dpdi["Month"].isin(trend_months)].groupby("Month")
rev_spark  = _tg["Revenue"].sum().reindex(trend_months, fill_value=0).tolist()
gp_spark   = _tg["Gross_Profit"].sum().reindex(trend_months, fill_value=0).tolist()
dc_spark   = _tg["Direct_Costs"].sum().reindex(trend_months, fill_value=0).tolist()

_excl_tg   = (dpdi[(dpdi["Month"].isin(trend_months)) & (dpdi["Product"] != "e-GOVTT")]
              .groupby("Month"))
excl_spark = _excl_tg["Revenue"].sum().reindex(trend_months, fill_value=0).tolist()

_eg_tg     = (dpdi[(dpdi["Month"].isin(trend_months)) & (dpdi["Product"] == "e-GOVTT")]
              .groupby("Month"))
egovtt_spark = _eg_tg["Revenue"].sum().reindex(trend_months, fill_value=0).tolist()


def _sparkline(series, color, height=44):
    vals = [float(v) for v in series]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    w, pts = 220, []
    for i, v in enumerate(vals):
        x = i * w / max(len(vals) - 1, 1)
        y = height - (v - mn) / rng * height * 0.78 - height * 0.11
        pts.append(f"{x:.1f},{y:.1f}")
    lp = " ".join(pts)
    fp = f"0,{height} {lp} {w},{height}"
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {w} {height}" '
        f'preserveAspectRatio="none" style="display:block;margin-top:8px">'
        f'<polygon points="{fp}" fill="rgba({r},{g},{b},0.15)"/>'
        f'<polyline points="{lp}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
    )


# ── KPI cards ─────────────────────────────────────────────────────────────────
def _dpdi_kpi(label, value, line1, l1_col, line2, l2_col, accent, spark=None):
    sp_html = (
        f'<div style="margin-top:8px;opacity:0.85">{_sparkline(spark, accent, 44)}</div>'
    ) if spark else ""
    return (
        f'<div style="background:#F6F8FA;border-radius:10px;padding:7px 12px;'
        f'border:1px solid #D0D7DE;border-top:3px solid {accent};height:100%">'
        f'<div style="font-size:28px;color:#5B6675;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:2px">{label}</div>'
        f'<div style="font-size:62px;font-weight:800;color:#1F2328;margin-bottom:2px;'
        f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
        f'{value}</div>'
        f'<div style="font-size:29px;color:{l1_col};font-weight:600;margin-bottom:0px;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{line1}</div>'
        f'<div style="font-size:29px;color:{l2_col};font-weight:600;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{line2}</div>'
        f'{sp_html}'
        f'</div>'
    )

_vc = lambda p: rev_var_rag(p) if p is not None else "#5B6675"
_vl = lambda p: (f"{p:+.1f}% vs PY" if p is not None else "— vs PY")

K = 1000

# Make the lag explicit so these figures are never read as the focus month's.
if focus_month and focus_month != sel_month:
    st.markdown(
        f'<div style="background:#FDF6E3;border:1px solid #E8D9A8;border-left:4px solid #A16207;'
        f'border-radius:8px;padding:10px 16px;margin-bottom:12px;font-size:22px;color:#6B5310">'
        f'Latest DPDI figures are <b>{sel_month}</b> — showing {sel_month}, '
        f'not the {focus_month} focus month.</div>',
        unsafe_allow_html=True,
    )

c1, c2, c3, c4, c5 = st.columns(5)
_rev_rag  = rev_var_rag(rev_var_pct)
_excl_rag = rev_var_rag(excl_var_pct)
_gp_rag   = gp_margin_rag(gp_margin)

c1.markdown(_dpdi_kpi(
    "Total Revenue", f"{total_rev*K:,.0f}",
    f"{rev_var_pct:+.1f}% vs AOP", _rev_rag,
    _vl(rev_py_pct), _vc(rev_py_pct),
    "#0B6BCB", rev_spark,
), unsafe_allow_html=True)
c2.markdown(_dpdi_kpi(
    "Excl. e-GOVTT", f"{excl_rev*K:,.0f}",
    f"{excl_var_pct:+.1f}% vs AOP", _excl_rag,
    _vl(excl_py_pct), _vc(excl_py_pct),
    "#6D28D9", excl_spark,
), unsafe_allow_html=True)
_dc_py_str = (f"{dc_py_pct:+.1f}% vs PY" if dc_py_pct is not None else "— vs PY")
_dc_py_col = rev_var_rag(dc_py_pct) if dc_py_pct is not None else "#5B6675"
c3.markdown(_dpdi_kpi(
    "Direct Costs", f"{total_dc*K:,.0f}",
    dc_sub_text, dc_sub_color,
    _dc_py_str, _dc_py_col,
    "#C53030", dc_spark,
), unsafe_allow_html=True)
c4.markdown(_dpdi_kpi(
    "Gross Profit", f"{total_gp*K:,.0f}",
    f"GP Margin: {gp_margin:.1f}%", _gp_rag,
    _vl(gp_py_pct), _vc(gp_py_pct),
    "#15803D", gp_spark,
), unsafe_allow_html=True)
c5.markdown(_dpdi_kpi(
    "e-GOVTT Pipeline", f"{egovtt_pipeline*K:,.0f}",
    "Key opportunity →", "#00875A",
    f"Actual: {egovtt_rev*K:,.0f}" if egovtt_rev else "No revenue YTD", "#7A8494",
    "#00875A", egovtt_spark,
), unsafe_allow_html=True)
st.markdown("<div style='margin-bottom:1.5rem'></div>", unsafe_allow_html=True)

# ── Two-column charts ─────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    products_list = ytd.index.tolist()
    actual_vals   = [ytd.loc[p, "Revenue"]     * K for p in products_list]
    aop_vals      = [ytd.loc[p, "Revenue_AOP"] * K for p in products_list]

    safe_max = max(max(actual_vals + [0.001]), max(aop_vals + [0.001]))
    max_x    = safe_max * 1.6

    annotations = [
        dict(
            x=max(av, bv) + safe_max * 0.06,
            y=prod,
            text=f"<b>{av:,.0f}</b> / {bv:,.0f}",
            showarrow=False,
            font=dict(color="#3B4351", size=16, family="Inter, sans-serif"),
            xanchor="left",
            yanchor="middle",
        )
        for prod, av, bv in zip(products_list, actual_vals, aop_vals)
    ]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=products_list, x=aop_vals, name="AOP Target",
        orientation="h",
        marker=dict(color="rgba(21,128,61,0.12)", line=dict(color="#15803D", width=1.5)),
    ))
    fig_bar.add_trace(go.Bar(
        y=products_list, x=actual_vals, name="YTD Actual",
        orientation="h",
        marker_color="#00875A",
    ))
    fig_bar.update_layout(
        barmode="overlay",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1F2328", family="Inter, sans-serif", size=16),
        height=380,
        title=dict(text="<b>Revenue by Product — YTD vs AOP</b>",
                   font=dict(size=20, color="#1F2328"), x=0),
        xaxis=dict(gridcolor="#E6EAF0", tickfont=dict(color="#7A8494", size=15),
                   range=[0, max_x], showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(color="#1F2328", size=15), showgrid=False,
                   autorange="reversed"),
        margin=dict(l=10, r=160, t=70, b=30),
        annotations=annotations,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#5B6675", size=15),
                    orientation="h", y=1.12, x=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    trend_df  = (
        dpdi[dpdi["Month"].isin(trend_months)]
        .groupby("Month")[["Revenue", "Revenue_AOP"]]
        .sum()
        .reindex(trend_months)
    )
    t_rev  = [v * K for v in trend_df["Revenue"].tolist()]
    t_aop  = [v * K for v in trend_df["Revenue_AOP"].tolist()]

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend_months, y=t_aop, name="AOP Target",
        mode="lines",
        line=dict(color="#15803D", width=2, dash="dot"),
    ))
    fig_trend.add_trace(go.Scatter(
        x=trend_months, y=t_rev, name="Actual Revenue",
        mode="lines+markers",
        line=dict(color="#00875A", width=2.5),
        marker=dict(size=6, color="#00875A"),
    ))
    fig_trend.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1F2328", family="Inter, sans-serif", size=16),
        height=380,
        title=dict(text="<b>Revenue Trend — 13 Months vs AOP</b>",
                   font=dict(size=20, color="#1F2328"), x=0),
        xaxis=dict(gridcolor="#E6EAF0", tickfont=dict(color="#7A8494", size=15),
                   showline=False, zeroline=False),
        yaxis=dict(gridcolor="#E6EAF0", tickfont=dict(color="#5B6675", size=15),
                   zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#5B6675", size=15),
                    orientation="h", y=1.12, x=0),
        margin=dict(l=10, r=10, t=70, b=30),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Confidential footer ───────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:0.62rem;color:#D0D7DE;margin-top:2rem;
            padding-top:0.9rem;border-top:1px solid #F6F8FA;letter-spacing:2px">
  CONFIDENTIAL — FOR BOARD OF DIRECTORS USE ONLY
</div>
""", unsafe_allow_html=True)
