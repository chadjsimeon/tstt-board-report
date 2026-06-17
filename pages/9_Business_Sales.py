import streamlit as st

st.set_page_config(page_title="TSTT | Business Sales", page_icon="🏢", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data, get_month_order
from utils.month_selector import focus_month_selector, filter_data_to_month
from utils.charts import inject_css
from utils.rag import rev_var_rag


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
focus_month_selector()
data    = load_all_data()
biz     = data["Business_Sales"]
biz = filter_data_to_month(biz)
biz_mrr = data.get("Business_Sales_MRR", pd.DataFrame())
biz_mrr = filter_data_to_month(biz_mrr)

months    = get_month_order(biz)
sel_month = st.sidebar.selectbox("Focus Month", months, index=len(months) - 1)


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

# Gross Profit = Revenue − Direct Costs, derived from the summed totals.
# The per-row Gross_Profit/GP_AOP columns drift from Rev − COS when summed
# across the month's sub-segment rows, so they are only a fallback.
gp_rev   = (fp_t_rev - dc_rev) if fp_t_rev else _col(biz_latest, "Gross_Profit")
gp_aop_v = ((fp_t_aop - dc_aop) if (fp_t_aop and dc_aop is not None)
            else _col(biz_latest, "GP_AOP"))
gp_py    = ((fp_t_py - dc_py) if (fp_t_py is not None and dc_py is not None)
            else _col(biz_py_snap, "Gross_Profit"))
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
def _parse_pct(s):
    if not s or '|' not in s: return None
    try: return float(s.split('|')[1].split('%')[0].strip())
    except Exception: return None

def fp_r1_card(label, val_str, aop_pct, aop_m_str, yoy_str, accent, spark_series=None, hide_aop=False, py_col=None):
    col = rev_var_rag(aop_pct)
    if hide_aop:
        aop_html = '<span style="color:transparent">&nbsp;</span>'
    else:
        aop_html = (
            f'<span style="color:{col}">{aop_m_str}&nbsp;|&nbsp;{aop_pct:+.1f}%&nbsp;vs&nbsp;AOP</span>'
            if aop_pct is not None else '<span style="color:#445566">— vs AOP</span>'
        )
    _yoy_col = py_col if py_col else rev_var_rag(_parse_pct(yoy_str))
    yoy_html = (
        f'<span style="color:{_yoy_col};font-weight:700">{yoy_str}</span>'
        if yoy_str else '<span style="color:#445566">— vs PY</span>'
    )
    spark_html = (
        f'<div style="margin-top:8px;opacity:0.85">{_sparkline(spark_series, accent)}</div>'
        if spark_series else '<div style="margin-top:8px;height:44px"></div>'
    )
    return (
        f'<div style="background:#161B22;border-radius:10px;padding:7px 12px;'
        f'border:1px solid #252545;border-top:3px solid {accent};height:100%">'
        f'<div style="font-size:28px;color:#6677aa;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:2px">{label}</div>'
        f'<div style="font-size:62px;font-weight:800;color:white;margin-bottom:2px;'
        f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
        f'<div style="font-size:29px;font-weight:600;margin-bottom:0px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{aop_html}</div>'
        f'<div style="font-size:29px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{yoy_html}</div>'
        f'{spark_html}</div>'
    )

def fp_r2_card(label, val_str, aop_str, aop_col, py_str, accent="#4a9eff", py_col=None):
    _py_col = py_col if py_col else rev_var_rag(_parse_pct(py_str))
    return (
        f'<div style="background:#161B22;border-radius:10px;padding:7px 12px;'
        f'border:1px solid #252545;border-top:3px solid {accent};height:100%">'
        f'<div style="font-size:28px;color:#6677aa;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:2px">{label}</div>'
        f'<div style="font-size:62px;font-weight:800;color:white;margin-bottom:2px;'
        f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
        f'<div style="font-size:29px;color:{aop_col};font-weight:600;margin-bottom:0px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{aop_str}</div>'
        f'<div style="font-size:29px;color:{_py_col};font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{py_str}</div>'
        f'</div>'
    )

# ── Pre-compute strings ────────────────────────────────────────────────
dc_vp = _vp(dc_rev, dc_aop)
dc_vm = _vm(dc_rev, dc_aop)
dc_aop_color = rev_var_rag(-(dc_vp or 0))
dc_aop_str   = f"{dc_vm:+.1f} | {dc_vp:+.1f}% vs AOP" if dc_vp is not None else "— vs AOP"
_dc_py_delta = dc_rev - dc_py if dc_py is not None else None
_dc_py_pct   = _dc_py_delta / abs(dc_py) * 100 if (_dc_py_delta is not None and dc_py) else None
dc_py_str    = (f"{_dc_py_delta:+.1f} | {_dc_py_pct:+.1f}% vs PY"
               if _dc_py_pct is not None else "— vs PY")
dc_py_col    = rev_var_rag(-_dc_py_pct) if _dc_py_pct is not None else "#7788aa"

gp_vp = _vp(gp_rev, gp_aop_v)
gp_vm = _vm(gp_rev, gp_aop_v)
gp_aop_color = rev_var_rag(gp_vp)
gp_aop_str   = f"{gp_vm:+.1f} | {gp_vp:+.1f}% vs AOP" if gp_vp is not None else f"{gp_margin_pct:.1f}% margin"
_gp_py_delta = gp_rev - gp_py if gp_py is not None else None
_gp_py_pct   = _gp_py_delta / abs(gp_py) * 100 if (_gp_py_delta is not None and gp_py) else None
gp_py_str    = (f"{_gp_py_delta:+.1f} | {_gp_py_pct:+.1f}% vs PY"
               if _gp_py_pct is not None else f"{gp_margin_pct:.1f}% margin")

subs_str = f"{int(mob_subs)/1000:,.0f}K" if mob_subs else "—"
s_vp = _vp(mob_subs, subs_aop) if (mob_subs and subs_aop) else None
if s_vp is not None:
    s_vm = int(mob_subs - subs_aop)
    subs_aop_str = f"{(s_vm)/1000:+,.1f} | {s_vp:+.1f}% vs AOP"
    subs_aop_col = rev_var_rag(s_vp)
else:
    subs_aop_str, subs_aop_col = "— vs AOP", "#445566"
s_py_pct = _vp(mob_subs, subs_py) if (mob_subs and subs_py) else None
subs_py_str = f"{(int(mob_subs) - int(subs_py))/1000:+,.1f} | {s_py_pct:+.1f}% vs PY" if s_py_pct is not None else "— vs PY"

arpu_str = f"{arpu_val:,.0f}" if arpu_val else "—"
arpu_py  = (mob_py * 1_000_000 / subs_py) if (mob_py and subs_py) else None
arpu_py_str = (f"{arpu_val - arpu_py:+,.0f} | {(arpu_val - arpu_py)/arpu_py*100:+.1f}% vs PY"
               if (arpu_val and arpu_py) else "— vs PY")
arpu_aop_pct = _vp(arpu_val, arpu_aop) if (arpu_val and arpu_aop) else None
arpu_aop_str = (f"{arpu_val - arpu_aop:+,.0f} | {arpu_aop_pct:+.1f}% vs AOP"
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
        (f"{rv_f - py:+.1f} | {(rv_f - py)/py*100:+.1f}% vs PY" if py else None),
        accent, spark_series=trend,
    )

# ── Layout ────────────────────────────────────────────────────────────
_sp = "<div style='height:6px'></div>"

left_area, right_area = st.columns([2, 3])

with left_area:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(fp_r1_card(
            "Total Revenue", f"{fp_t_rev:.1f}",
            fp_tv_pct, f"{fp_tv_m:+.1f}",
            (f"{fp_t_rev - fp_t_py:+.1f} | {(fp_t_rev - fp_t_py)/fp_t_py*100:+.1f}% vs PY"
             if fp_t_py else None),
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
        st.markdown(fp_r2_card("ARPU TT$ -/sub", arpu_str,
                               arpu_aop_str, arpu_aop_col, arpu_py_str,
                               accent=FP_ACCENTS[1]), unsafe_allow_html=True)

with right_area:
    c3, c4, c5 = st.columns(3)

    def _mrr_card(label, rv, py, accent, trend, py_col=None):
        rv_f = rv if rv is not None else 0.0
        return fp_r1_card(
            label,
            f"{rv_f:.1f}" if rv is not None else "—",
            None, "—",
            (f"{rv_f - py:+.1f} | {(rv_f - py)/py*100:+.1f}% vs PY" if py else None),
            accent, spark_series=trend, hide_aop=True, py_col=py_col,
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
                   font=dict(size=30, color="white"), x=0),
        xaxis=dict(showgrid=False, tickfont=dict(size=15), tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)",
                   tickfont=dict(size=15), tickprefix="$"),
        legend=dict(bgcolor="rgba(20,20,40,0.8)", font=dict(size=14, color="white"),
                    orientation="v", x=1.01, y=1, xanchor="left", yanchor="top"),
        margin=dict(l=10, r=100, t=44, b=10),
    )
    st.plotly_chart(fig_lines, use_container_width=True)
