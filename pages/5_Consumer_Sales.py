import streamlit as st

st.set_page_config(page_title="TSTT | Consumer Sales", page_icon="📱", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import (load_all_data, load_prepaid_arpu, load_prepaid_data_usage,
                               load_postpaid_plans, load_wttx_categories,
                               pivot_by_group, get_month_order)
from utils.month_selector import focus_month_selector, filter_data_to_month
from utils.charts import (
    inject_css, page_header,
    line_chart, stacked_bar, grouped_bar, donut_chart, dim,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN, ACCENT,
)
from utils.rag import rag, rev_var_rag, churn_prepaid_rag, churn_postpaid_rag, churn_wttx_rag
from utils.consumer_common import _sparkline

inject_css()
focus_month_selector()

data     = load_all_data()
consumer = data["Consumer_Sales"]
consumer = filter_data_to_month(consumer)

months   = get_month_order(consumer)
prepaid  = consumer[consumer["Segment"] == "Prepaid"].copy()
postpaid = consumer[consumer["Segment"] == "Postpaid"].copy()
wttx     = consumer[consumer["Segment"] == "WTTx"].copy()
sel_month = st.session_state.get("focus_month", months[-1] if months else None)


# ── Data prep ─────────────────────────────────────────────────────────
v2_latest  = consumer[consumer["Month"] == sel_month].copy()
v2_sel_dt  = pd.to_datetime(sel_month, format="%b-%y", errors="coerce")
v2_py_mon  = (v2_sel_dt - pd.DateOffset(months=12)).strftime("%b-%y") if pd.notna(v2_sel_dt) else months[0]
v2_py_snap = consumer[consumer["Month"] == v2_py_mon].copy()

def _v2rv(seg):
    r = v2_latest[v2_latest["Segment"] == seg]["Revenue"]
    return float(r.values[0]) if not r.empty else 0.0

def _v2ra(seg):
    r = v2_latest[v2_latest["Segment"] == seg]["Revenue_AOP"]
    if r.empty: return None
    v = r.values[0]
    return float(v) if pd.notna(v) and v != 0 else None

def _v2rpy(seg):
    # Prefer Revenue_PY column on the current month's row
    cur = v2_latest[v2_latest["Segment"] == seg]
    if not cur.empty and "Revenue_PY" in cur.columns:
        _v = cur["Revenue_PY"].values[0]
        if pd.notna(_v) and float(_v) != 0:
            return float(_v)
    # Fall back to actual prior-year row
    r = v2_py_snap[v2_py_snap["Segment"] == seg]["Revenue"]
    return float(r.values[0]) if not r.empty else None

def _v2vp(rev, aop): return (rev - aop) / abs(aop) * 100 if aop else None
def _v2vm(rev, aop): return rev - aop if aop is not None else None

v2_t_rev = float(v2_latest["Revenue"].sum())
v2_t_aop = float(v2_latest["Revenue_AOP"].sum())
# Total Consumer PY: use P&L_Segments Consumer Sales figure (authoritative)
# Consumer_Products Apr-25 misses Residential Security → gives 80.3M vs 91.1M
_v2_pnlbd   = data["PnL_Breakdown"]
_v2_pnl_py  = _v2_pnlbd[_v2_pnlbd["Month"] == v2_py_mon]
_cs_rev_col = "CONSUMER SALES_Rev"
v2_t_py = (
    float(_v2_pnl_py[_cs_rev_col].values[0])
    if not _v2_pnl_py.empty and _cs_rev_col in _v2_pnl_py.columns
    and pd.notna(_v2_pnl_py[_cs_rev_col].values[0])
    else (float(v2_py_snap["Revenue"].sum()) if not v2_py_snap.empty else None)
)
v2_tv_pct = _v2vp(v2_t_rev, v2_t_aop)
v2_tv_m   = v2_t_rev - v2_t_aop

pp_rev = _v2rv("Postpaid"); pp_aop = _v2ra("Postpaid"); pp_py_v = _v2rpy("Postpaid")
pr_rev = _v2rv("Prepaid");  pr_aop = _v2ra("Prepaid");  pr_py_v = _v2rpy("Prepaid")
wx_rev = _v2rv("WTTx");     wx_aop = _v2ra("WTTx");     wx_py_v = _v2rpy("WTTx")

_v2_main       = ["Prepaid", "Postpaid", "WTTx"]
v2_other_cons  = consumer[~consumer["Segment"].isin(_v2_main)]
v2_other_by_mo = v2_other_cons.groupby("Month", sort=False)["Revenue"].sum()
v2_other_rev   = v2_other_by_mo.get(sel_month, 0.0)
v2_other_aop   = v2_other_cons[v2_other_cons["Month"] == sel_month]["Revenue_AOP"].sum()
v2_other_var   = (v2_other_rev - v2_other_aop) / v2_other_aop * 100 if v2_other_aop else None
v2_other_py    = v2_other_by_mo.get(v2_py_mon, None)

# EBITDA Margin from Financial_Monthly
v2_fin     = data["Financial_Monthly"]
v2_fin_sel = v2_fin[v2_fin["Month"] == sel_month]
ebi_m = ebi_m_aop = ebi_m_py = None
if not v2_fin_sel.empty:
    fr = v2_fin_sel.iloc[0]
    def _fn(col): v = fr.get(col, None); return float(v) if v is not None and pd.notna(v) else None
    ebi_m     = _fn("EBITDA_Margin")
    ebi_aop_v = _fn("EBITDA_AOP")
    rev_aop_v = _fn("Revenue_AOP")
    ebi_m_aop = ebi_aop_v / rev_aop_v * 100 if (ebi_aop_v and rev_aop_v) else None
    ebi_py_v  = _fn("EBITDA_PY")
    rev_py_v  = _fn("Revenue_PY")
    ebi_m_py  = ebi_py_v / rev_py_v * 100 if (ebi_py_v and rev_py_v) else None

# Monthly totals for sparkline + donut
_spark_months  = months[-13:]
v2_all_months  = _spark_months
v2_total_trend = consumer.groupby("Month")["Revenue"].sum().reindex(_spark_months, fill_value=0).tolist()
v2_post_trend  = postpaid.groupby("Month")["Revenue"].sum().reindex(_spark_months, fill_value=0).tolist()
v2_pre_trend   = prepaid.groupby("Month")["Revenue"].sum().reindex(_spark_months, fill_value=0).tolist()
v2_wx_trend    = wttx.groupby("Month")["Revenue"].sum().reindex(_spark_months, fill_value=0).tolist()
v2_other_trend = v2_other_by_mo.reindex(_spark_months, fill_value=0).tolist()

# Direct Costs and Gross Profit from PnL_Breakdown (real COS data)
v2_pnl     = data["PnL_Breakdown"]
v2_pnl_sel = v2_pnl[v2_pnl["Month"] == sel_month]
v2_pnl_py  = v2_pnl[v2_pnl["Month"] == v2_py_mon]

def _pnl(row, col):
    v = row[col].values[0] if col in row.columns and not row.empty else None
    return float(v) if v is not None and pd.notna(v) and v != 0 else None

if not v2_pnl_sel.empty:
    dc_act     = float(v2_pnl_sel["CONSUMER SALES_COS"].values[0])
    cs_rev_pnl = float(v2_pnl_sel["CONSUMER SALES_Rev"].values[0])
    gp_act     = cs_rev_pnl - dc_act
    dc_is_ph   = gp_is_ph = False
    dc_aop     = _pnl(v2_pnl_sel, "CONSUMER SALES_COS_AOP")
    gp_aop     = _pnl(v2_pnl_sel, "CONSUMER SALES_GP_AOP")
else:
    dc_act   = v2_t_rev * 0.58
    gp_act   = v2_t_rev * 0.42
    dc_is_ph = gp_is_ph = True
    dc_aop = gp_aop = None

dc_py = gp_py = None
if not v2_pnl_py.empty:
    dc_py_v     = float(v2_pnl_py["CONSUMER SALES_COS"].values[0])
    cs_rev_py_v = float(v2_pnl_py["CONSUMER SALES_Rev"].values[0])
    dc_py       = dc_py_v
    gp_py       = cs_rev_py_v - dc_py_v

dc_aop_pct  = (dc_act - dc_aop) / abs(dc_aop) * 100 if dc_aop else None
gp_aop_pct  = (gp_act - gp_aop) / abs(gp_aop) * 100 if gp_aop else None
dc_aop_str  = f"{dc_act - dc_aop:+.1f} | {dc_aop_pct:+.1f}% vs AOP" if dc_aop_pct is not None else "— vs AOP"
gp_aop_str  = f"{gp_act - gp_aop:+.1f} | {gp_aop_pct:+.1f}% vs AOP" if gp_aop_pct is not None else "— vs AOP"
dc_aop_col  = rag(dc_aop_pct, 0, 10, higher=False) if dc_aop_pct is not None else "#7788aa"
gp_aop_col  = rev_var_rag(gp_aop_pct)

dc_delta = dc_act - dc_py if dc_py is not None else None
dc_pct   = dc_delta / abs(dc_py) * 100 if (dc_delta is not None and dc_py) else None
dc_trend = (f"{dc_delta:+.1f} | {dc_pct:+.1f}% vs PY"
            if dc_pct is not None else "—")
dc_col   = rev_var_rag(-dc_pct) if dc_pct is not None else "#7788aa"

gp_delta = gp_act - gp_py if gp_py is not None else None
gp_pct   = gp_delta / abs(gp_py) * 100 if (gp_delta is not None and gp_py) else None
gp_trend = (f"{gp_delta:+.1f} | {gp_pct:+.1f}% vs PY"
            if gp_pct is not None else "—")
gp_col   = rev_var_rag(gp_pct) if gp_pct is not None else "#8899bb"

# Usage metrics — MoU from no available source yet; GB/Sub from Prepaid_Data_Usage
_du = load_prepaid_data_usage()
_du_sel = _du[_du["Month"] == sel_month] if not _du.empty else pd.DataFrame()

def _du_val(col):
    if _du_sel.empty or col not in _du_sel.columns:
        return None, True
    v = _du_sel[col].values[0]
    if pd.isna(v) or v == 0:
        return None, True
    return float(v), False

pp_mou, pp_mou_ph   = None, True
pre_mou, pre_mou_ph = _du_val("mou_per_user")
pre_gb, pre_gb_ph   = _du_val("gb_per_user")

pp_mou_trend, pp_mou_col   = "", "#8899bb"
pre_mou_trend, pre_mou_col = "", "#8899bb"
pre_gb_trend,  pre_gb_col  = "", "#8899bb"

pp_mou_str  = f"{pp_mou:.0f} mins" if pp_mou else "Data Pending"
pre_mou_str = f"{pre_mou:.0f} mins" if pre_mou else "Data Pending"
pre_gb_str  = f"{pre_gb:.2f} GB"    if pre_gb else "Data Pending"

seg_vars_cmt = {
    "Postpaid": _v2vp(pp_rev, pp_aop),
    "Prepaid":  _v2vp(pr_rev, pr_aop),
    "WTTx":     _v2vp(wx_rev, wx_aop),
}
sv_clean = {k: v for k, v in seg_vars_cmt.items() if v is not None}
v2_best  = max(sv_clean, key=sv_clean.get) if sv_clean else "Postpaid"
v2_worst = min(sv_clean, key=sv_clean.get) if sv_clean else "Prepaid"

v2_wttx_mons = list(wttx["Month"].unique())
wx_prev_rev  = wttx[wttx["Month"] == v2_wttx_mons[-2]]["Revenue"].sum() if len(v2_wttx_mons) >= 2 else wx_rev
wx_mom       = wx_rev - wx_prev_rev

# ── Card builders ─────────────────────────────────────────────────────
def r1_card(label, val_str, aop_pct, aop_m_str, yoy_str, accent, spark_series=None, yoy_val=None, yoy_neg_col="#f59e0b", yoy_force_col=None):
    col = rev_var_rag(aop_pct)
    aop_html = (
        f'<span style="color:{col}">{aop_m_str}&nbsp;|&nbsp;{aop_pct:+.1f}%&nbsp;vs&nbsp;AOP</span>'
        if aop_pct is not None
        else '<span style="color:#445566">— vs AOP</span>'
    )
    yoy_col = yoy_force_col if yoy_force_col else (
        ("#22c55e" if (yoy_val or 0) >= 0 else yoy_neg_col) if yoy_val is not None else "#f59e0b"
    )
    yoy_html = (
        f'<span style="color:{yoy_col};font-weight:700">{yoy_str}</span>'
        if yoy_str else '<span style="color:#445566">— vs PY</span>'
    )
    spark_html = (
        f'<div style="margin-top:8px;opacity:0.85">{_sparkline(spark_series, accent)}</div>'
        if spark_series else ""
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
        f'{spark_html}'
        f'</div>'
    )

_AMBER_DOT = (
    '<span style="width:7px;height:7px;border-radius:50%;background:#f59e0b;'
    'display:inline-block;margin-left:6px;flex-shrink:0;vertical-align:middle" '
    'title="Estimated — not sourced from live data"></span>'
)

def r2_card(label, val_str, line1, line1_col, line2="", line2_col="#7788aa",
           is_ph=False, accent="#4a9eff", note="", val_size="52px", min_height=""):
    dot = _AMBER_DOT if is_ph else ""
    note_h = (f'<div style="font-size:13px;color:#f59e0b;margin-top:4px;font-style:italic">'
              f'{note}</div>') if note else ""
    l2_h = (f'<div style="font-size:27px;color:{line2_col};font-weight:600;margin-top:1px;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{line2}</div>') if line2 else ""
    l1_h = (f'<div style="font-size:27px;color:{line1_col};font-weight:600;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{line1}</div>') if line1 else ""
    mh = f"min-height:{min_height};" if min_height else ""
    return (
        f'<div style="background:#161B22;border-radius:10px;padding:7px 14px;'
        f'border:1px solid #252545;border-top:3px solid {accent};height:100%;{mh}">'
        f'<div style="font-size:26px;color:#6677aa;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:3px;display:flex;align-items:center">{label}{dot}</div>'
        f'<div style="font-size:58px;font-weight:800;color:white;margin-bottom:3px;'
        f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
        f'{l1_h}{l2_h}{note_h}</div>'
    )

# ════════════════════════════════════════════════════════════════════
# ROW 1 — 5 KPI cards
# ════════════════════════════════════════════════════════════════════
c1, c2, c3, c4, c5 = st.columns(5)

c1.markdown(r1_card(
    "Total Revenue", f"{v2_t_rev:.1f}",
    v2_tv_pct, f"{v2_tv_m:+.1f}",
    (f"{v2_t_rev - v2_t_py:+.1f} | {(v2_t_rev - v2_t_py) / v2_t_py * 100:+.1f}% vs PY"
     if v2_t_py else None),
    "#00d4a0", spark_series=v2_total_trend,
    yoy_force_col=rev_var_rag((v2_t_rev - v2_t_py) / v2_t_py * 100) if v2_t_py else None,
), unsafe_allow_html=True)

c2.markdown(r1_card(
    "Prepaid", f"{pr_rev:.1f}",
    _v2vp(pr_rev, pr_aop),
    f"{_v2vm(pr_rev, pr_aop):+.1f}" if _v2vm(pr_rev, pr_aop) is not None else "—",
    (f"{pr_rev - pr_py_v:+.1f} | {(pr_rev - pr_py_v) / pr_py_v * 100:+.1f}% vs PY"
     if pr_py_v else None),
    "#a78bfa", spark_series=v2_pre_trend,
    yoy_force_col=rev_var_rag((pr_rev - pr_py_v) / pr_py_v * 100) if pr_py_v else None,
), unsafe_allow_html=True)

c3.markdown(r1_card(
    "Postpaid", f"{pp_rev:.1f}",
    _v2vp(pp_rev, pp_aop),
    f"{_v2vm(pp_rev, pp_aop):+.1f}" if _v2vm(pp_rev, pp_aop) is not None else "—",
    (f"{pp_rev - pp_py_v:+.1f} | {(pp_rev - pp_py_v) / pp_py_v * 100:+.1f}% vs PY"
     if pp_py_v else None),
    "#4a9eff", spark_series=v2_post_trend,
    yoy_force_col=rev_var_rag((pp_rev - pp_py_v) / pp_py_v * 100) if pp_py_v else None,
), unsafe_allow_html=True)

c4.markdown(r1_card(
    "WTTx", f"{wx_rev:.1f}",
    _v2vp(wx_rev, wx_aop),
    f"{_v2vm(wx_rev, wx_aop):+.1f}" if _v2vm(wx_rev, wx_aop) is not None else "—",
    (f"{wx_rev - wx_py_v:+.1f} | {(wx_rev - wx_py_v) / wx_py_v * 100:+.1f}% vs PY"
     if wx_py_v else None),
    "#f59e0b", spark_series=v2_wx_trend,
    yoy_force_col=rev_var_rag((wx_rev - wx_py_v) / wx_py_v * 100) if wx_py_v else None,
), unsafe_allow_html=True)

c5.markdown(r1_card(
    "Other Revenue", f"{v2_other_rev:.1f}",
    v2_other_var,
    f"{v2_other_rev - v2_other_aop:+.1f}" if v2_other_aop else "—",
    (f"{v2_other_rev - v2_other_py:+.1f} | {(v2_other_rev - v2_other_py) / v2_other_py * 100:+.1f}% vs PY"
     if v2_other_py else None),
    "#ff6b6b", spark_series=v2_other_trend,
    yoy_force_col=rev_var_rag((v2_other_rev - v2_other_py) / v2_other_py * 100) if v2_other_py else None,
), unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# ROW 2 — [1,2,2]: DC+GP (1/5 = Total Rev width) | rev mix | empty
# ════════════════════════════════════════════════════════════════════
st.markdown("<div style='margin:14px 0 8px'></div>", unsafe_allow_html=True)
col_AB, col_C, _ = st.columns([1, 2, 2])

with col_AB:
    _dc_html  = r2_card(
        "Direct Costs", f"{dc_act:.1f}",
        dc_aop_str, dc_aop_col,
        dc_trend, dc_col,
        is_ph=dc_is_ph, accent="#ef4444",
        note="est. (58% proxy)" if dc_is_ph else "",
    )
    _gp_html  = r2_card(
        "Gross Profit", f"{gp_act:.1f}",
        gp_aop_str, gp_aop_col,
        gp_trend, gp_col,
        is_ph=gp_is_ph, accent="#22c55e",
        note="est. (42% proxy)" if gp_is_ph else "",
    )
    st.markdown(
        f'<div style="display:flex;flex-direction:column;gap:8px;">'
        f'{_dc_html}'
        f'{_gp_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

with col_C:
    # Revenue Mix donut — 4 consolidated segments
    d_segs  = ["Prepaid", "Postpaid", "WTTx", "Other"]
    d_clrs  = ["#a78bfa", "#4a9eff", "#f59e0b", "#6b7280"]
    d_vals  = [max(pr_rev, 0), max(pp_rev, 0), max(wx_rev, 0), max(v2_other_rev, 0)]
    d_total = sum(d_vals)
    d_pcts  = [v / d_total * 100 if d_total else 0 for v in d_vals]
    fig_d = go.Figure(go.Pie(
        labels=d_segs,
        values=d_vals,
        hole=0.45,
        sort=False,
        marker=dict(
            colors=d_clrs,
            line=dict(color="rgba(255,255,255,0.35)", width=2),
        ),
        textinfo="percent",
        textfont=dict(size=22, color="white"),
        insidetextorientation="radial",
        customdata=d_segs,
        hovertemplate="<b>%{customdata}</b><br>%{value:.1f} (%{percent})<extra></extra>",
        title=dict(
            text=f"<b>{d_total:.1f}</b>",
            font=dict(size=36, color="white"),
            position="middle center",
        ),
    ))
    fig_d.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=427,
        title=dict(text=f"<b>{sel_month} Revenue Mix</b>",
                   font=dict(size=26, color="white"), x=0),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=22, color="white"),
            orientation="h",
            x=0.5, y=-0.12,
            xanchor="center",
            yanchor="top",
        ),
        margin=dict(l=10, r=10, t=44, b=60),
    )
    st.plotly_chart(fig_d, use_container_width=True)
