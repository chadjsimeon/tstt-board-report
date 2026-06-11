import streamlit as st

st.set_page_config(page_title="TSTT | Postpaid Revenue", page_icon="📱", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import (load_all_data, load_prepaid_arpu, load_prepaid_data_usage,
                               load_postpaid_plans, load_wttx_categories,
                               pivot_by_group, get_month_order)
from utils.charts import (
    inject_css, page_header,
    line_chart, stacked_bar, grouped_bar, donut_chart, dim,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN, ACCENT,
)
from utils.rag import rag, rev_var_rag, churn_prepaid_rag, churn_postpaid_rag, churn_wttx_rag
from utils.consumer_common import _pre_kpi, _fmt_k, _latest_row_with

inject_css()
data     = load_all_data()
consumer = data["Consumer_Sales"]

months   = get_month_order(consumer)
prepaid  = consumer[consumer["Segment"] == "Prepaid"].copy()
postpaid = consumer[consumer["Segment"] == "Postpaid"].copy()
wttx     = consumer[consumer["Segment"] == "WTTx"].copy()


# ── Data prep ────────────────────────────────────────────────────────────
pp_mons   = months[-13:]
# Latest postpaid month with booked revenue (was hardcoded to Apr-26)
_pp_rev_by_mon  = postpaid.groupby("Month")["Revenue"].sum()
pp_latest_month = next(
    (m for m in reversed(pp_mons)
     if pd.notna(_pp_rev_by_mon.get(m)) and _pp_rev_by_mon.get(m, 0) > 0),
    pp_mons[-1],
)
pp_py_month = (pd.to_datetime(pp_latest_month, format="%b-%y")
               - pd.DateOffset(months=12)).strftime("%b-%y")
pp_latest = postpaid[postpaid["Month"] == pp_latest_month]
pp_apr25  = postpaid[postpaid["Month"] == pp_py_month]

# Revenue
pp26_rev  = float(pp_latest["Revenue"].sum())  if not pp_latest.empty else 0.0
# Prefer Revenue_PY column; fall back to Apr-25 row lookup
_pp_py_col = None
if not pp_latest.empty and "Revenue_PY" in pp_latest.columns:
    _v = pp_latest["Revenue_PY"].values[0]
    if pd.notna(_v) and float(_v) != 0:
        _pp_py_col = float(_v)
pp25_rev = _pp_py_col if _pp_py_col is not None else (
    float(pp_apr25["Revenue"].sum()) if not pp_apr25.empty else 0.0)
_pp_aop_r = pp_latest["Revenue_AOP"].values[0] if not pp_latest.empty else None
pp_aop_v  = (float(_pp_aop_r)
             if _pp_aop_r is not None and pd.notna(_pp_aop_r) else None)
pp_aop_pct = (pp26_rev - pp_aop_v) / pp_aop_v * 100 if pp_aop_v else None
pp_aop_m   = pp26_rev - pp_aop_v if pp_aop_v else None
pp_py_m    = pp26_rev - pp25_rev if pp25_rev else None

# Subscribers
pp_subs_row = _latest_row_with(postpaid, "Subscribers")
pp_subs_lat = float(pp_subs_row["Subscribers"]) if pp_subs_row is not None else 0.0
pp_subs_25  = float(pp_apr25["Subscribers"].sum()) if not pp_apr25.empty else 0.0
_pp_churn_r = pp_latest["Churn_Pct"].values[0] if not pp_latest.empty else None
pp_churn    = (float(_pp_churn_r)
               if _pp_churn_r is not None and pd.notna(_pp_churn_r) else None)
_pp_saop    = "Subscribers_AOP"
pp_subs_aop = (float(pp_latest[_pp_saop].values[0])
               if not pp_latest.empty and _pp_saop in pp_latest.columns
               and pd.notna(pp_latest[_pp_saop].values[0]) else None)
pp_subs_aop_pct = (pp_subs_lat - pp_subs_aop) / pp_subs_aop * 100 if pp_subs_aop else None
pp_subs_py_pct  = (pp_subs_lat - pp_subs_25) / pp_subs_25 * 100 if pp_subs_25 else None

# ARPU
pp_arpu_row = _latest_row_with(postpaid, "ARPU")
pp_arpu_lat = float(pp_arpu_row["ARPU"]) if pp_arpu_row is not None else 0.0
pp_arpu_25  = (float(pp_apr25["ARPU"].mean())
               if not pp_apr25.empty and pp_apr25["ARPU"].sum() > 0 else 0.0)
_pp_aaop    = "ARPU_AOP"
pp_arpu_aop = (float(pp_latest[_pp_aaop].values[0])
               if not pp_latest.empty and _pp_aaop in pp_latest.columns
               and pd.notna(pp_latest[_pp_aaop].values[0]) else None)
pp_arpu_aop_pct = (pp_arpu_lat - pp_arpu_aop) / pp_arpu_aop * 100 if pp_arpu_aop else None
pp_arpu_py_pct  = (pp_arpu_lat - pp_arpu_25) / pp_arpu_25 * 100 if pp_arpu_25 else None

# Sparklines
pp_rev_spark  = postpaid.set_index("Month")["Revenue"].reindex(pp_mons).fillna(0).tolist()
pp_subs_spark = postpaid.set_index("Month")["Subscribers"].reindex(pp_mons).fillna(0).tolist()
pp_arpu_spark = postpaid.set_index("Month")["ARPU"].reindex(pp_mons).fillna(0).tolist()


# ── Subscriber movement for card (mirrors chart logic exactly) ───────────
_pp_sub_sorted = postpaid.copy()
_pp_sub_sorted["_dt"] = pd.to_datetime(_pp_sub_sorted["Month"], format="%b-%y", errors="coerce")
_pp_sub_sorted = _pp_sub_sorted.sort_values("_dt").reset_index(drop=True)
_pp_subs_mon   = _pp_sub_sorted.iloc[-1]["Month"] if not _pp_sub_sorted.empty else "Apr-26"
pp_subs_close  = float(_pp_sub_sorted.iloc[-1]["Subscribers"]) if not _pp_sub_sorted.empty else pp_subs_lat
pp_subs_open   = float(_pp_sub_sorted.iloc[-2]["Subscribers"]) if len(_pp_sub_sorted) >= 2 else pp_subs_close
_pp_latest_row   = _pp_sub_sorted.iloc[-1] if not _pp_sub_sorted.empty else None
_pp_gross_raw    = float(_pp_latest_row["Gross_Adds"]) if (_pp_latest_row is not None and "Gross_Adds" in _pp_latest_row and pd.notna(_pp_latest_row["Gross_Adds"])) else 0.0
_pp_churn_cnt    = float(_pp_latest_row["Churn_Count"]) if (_pp_latest_row is not None and "Churn_Count" in _pp_latest_row and pd.notna(_pp_latest_row["Churn_Count"])) else None
if _pp_gross_raw > 0:
    pp_subs_gross_c = _pp_gross_raw
    pp_subs_disc_c  = _pp_churn_cnt if _pp_churn_cnt is not None else 0.0
else:
    pp_subs_disc_c  = pp_subs_open * pp_churn / 100 if (pp_churn and pp_subs_open > 0) else 0.0
    pp_subs_gross_c = max(0.0, pp_subs_close - pp_subs_open + pp_subs_disc_c)
pp_churn_derived = pp_churn if pp_churn else 0.0

# ── 4 KPI boxes ──────────────────────────────────────────────────────────
pp_r_aop_col = rev_var_rag(pp_aop_pct)
pp_r_l1 = (f"{pp_aop_m:+.1f} | {pp_aop_pct:+.1f}% vs AOP"
           if pp_aop_pct is not None else "— vs AOP")
pp_py_pct   = pp_py_m / pp25_rev * 100 if (pp_py_m is not None and pp25_rev) else None
pp_r_l2    = (f"{pp_py_m:+.1f} | {pp_py_pct:+.1f}% vs PY"
              if pp_py_pct is not None else "— vs PY")
pp_r_py_col = rev_var_rag(pp_py_pct) if pp_py_pct is not None else "#7788aa"

pp_a_l1_col = rev_var_rag(pp_arpu_aop_pct)
pp_a_l1 = (f"${pp_arpu_lat - pp_arpu_aop:+.0f} | {pp_arpu_aop_pct:+.1f}% vs AOP"
           if pp_arpu_aop_pct is not None else "— vs AOP")
pp_arpu_py_delta = pp_arpu_lat - pp_arpu_25 if pp_arpu_25 else None
pp_a_l2_col = rev_var_rag(pp_arpu_py_pct) if pp_arpu_py_pct is not None else "#7788aa"
pp_a_l2 = (f"${pp_arpu_py_delta:+.0f} | {pp_arpu_py_pct:+.1f}% vs PY"
           if pp_arpu_py_pct is not None else "— vs PY")

_pp_s_l1_col = rev_var_rag(pp_subs_aop_pct)
_pp_s_l1 = (f"{(pp_subs_close - pp_subs_aop)/1000:+.1f}K | {pp_subs_aop_pct:+.1f}% vs AOP"
            if pp_subs_aop_pct is not None else "— vs AOP")
pp_subs_py_delta = (pp_subs_close - pp_subs_25) / 1000 if pp_subs_25 else None
_pp_s_l2_col = rev_var_rag(pp_subs_py_pct) if pp_subs_py_pct is not None else "#7788aa"
_pp_s_l2 = (f"{pp_subs_py_delta:+.1f}K | {pp_subs_py_pct:+.1f}% vs PY"
            if pp_subs_py_pct is not None else "— vs PY")

_pp_c1     = _pre_kpi("Postpaid Revenue", f"{pp26_rev:.1f}",
                       pp_r_l1, pp_r_aop_col, pp_r_l2, pp_r_py_col, "#4a9eff", pp_rev_spark)
_pp_c3     = _pre_kpi("ARPU (TT$ -/subscriber)", f"{pp_arpu_lat:.0f}",
                       pp_a_l1, pp_a_l1_col, pp_a_l2, pp_a_l2_col, "#f59e0b", pp_arpu_spark)
_pp_c_subs = _pre_kpi("Subscribers", _fmt_k(pp_subs_close),
                       _pp_s_l1, _pp_s_l1_col, _pp_s_l2, _pp_s_l2_col, "#22c55e", pp_subs_spark)

_pp_churn_lbl  = f"Churn ({pp_churn_derived:.1f}%)"
_pp_mov_rows   = [
    ("Opening",     f"{pp_subs_open/1000:.1f}K",     "#aabbcc"),
    ("Gross Adds",  f"+{pp_subs_gross_c/1000:.1f}K", "#22c55e"),
    (_pp_churn_lbl, f"−{pp_subs_disc_c/1000:.1f}K",  "#ef4444"),
    ("Closing",     f"{pp_subs_close/1000:.1f}K",    "white"),
]
_pp_mov_html = "".join(
    f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
    f'border-bottom:1px solid #1e2a4a;">'
    f'<span style="font-size:29px;color:#7788aa">{lbl}</span>'
    f'<span style="font-size:29px;font-weight:700;color:{col}">{val}</span>'
    f'</div>'
    for lbl, val, col in _pp_mov_rows
)
_pp_c2 = (
    f'<div style="background:#161B22;border-radius:10px;padding:16px 16px;'
    f'border:1px solid #2a2a4a;border-top:3px solid #22c55e;height:100%">'
    f'<div style="font-size:28px;color:#6677aa;font-weight:700;text-transform:uppercase;'
    f'letter-spacing:1.5px;margin-bottom:10px">Subscriber Movements</div>'
    f'{_pp_mov_html}'
    f'</div>'
)

st.markdown(
    f'<div style="display:flex;gap:12px;margin-bottom:16px">'
    f'<div style="flex:1">{_pp_c1}</div>'
    f'<div style="flex:1">{_pp_c3}</div>'
    f'<div style="flex:1">{_pp_c_subs}</div>'
    f'<div style="flex:1">{_pp_c2}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ── Avg daily revenue calc ────────────────────────────────────────────────
# ── Subscriber Net Movement data ──────────────────────────────────────────
pp_sorted = postpaid.copy()
pp_sorted["_dt"] = pd.to_datetime(pp_sorted["Month"], format="%b-%y", errors="coerce")
pp_sorted = pp_sorted.sort_values("_dt").reset_index(drop=True)

_mov_rows = []
for _i in range(1, len(pp_sorted)):
    _prev = pp_sorted.iloc[_i - 1]
    _curr = pp_sorted.iloc[_i]
    _open = float(_prev["Subscribers"])
    _clos = float(_curr["Subscribers"])
    _chv  = _curr["Churn_Pct"]
    _chrt = (float(_chv) if pd.notna(_chv) and float(_chv) > 0 else 1.5)
    _disc = _open * _chrt / 100
    _gros = max(0.0, (_clos - _open) + _disc)
    _mov_rows.append({
        "Month":   _curr["Month"],
        "Opening": _open,
        "Gross":   _gros,
        "Disc":    _disc,
        "Closing": _clos,
        "Net":     _clos - _open,
    })
mov_df   = pd.DataFrame(_mov_rows)
mov_mons = mov_df["Month"].tolist()
_op_v    = mov_df["Opening"].tolist()
_gr_v    = mov_df["Gross"].tolist()
_dc_v    = mov_df["Disc"].tolist()
_cl_v    = mov_df["Closing"].tolist()

# AOP implied subscriber base: Revenue_AOP × 1M ÷ ARPU ()
pp_aop_subs = (pp_aop_v * 1_000_000 / pp_arpu_lat
               if pp_aop_v is not None and pp_arpu_lat > 0 else None)

# Y range: zoom to subscriber range so movement bars are visible
_all_y = _op_v + _cl_v + [o + g for o, g in zip(_op_v, _gr_v)] + [o - d for o, d in zip(_op_v, _dc_v)]
if pp_aop_subs:
    _all_y.append(pp_aop_subs)
_mov_ymin = min(_all_y) * 0.996
_mov_ymax = max(_all_y) * 1.014

# ── Active Plans — Postpaid by active Plan sheet ──────────────────────────
_pp_plans_df = load_postpaid_plans()
if not _pp_plans_df.empty:
    _active = _pp_plans_df[_pp_plans_df["Type"] == "Active"].sort_values("Sub_Count", ascending=False)
    _legacy = _pp_plans_df[_pp_plans_df["Type"] == "Legacy"]
    _top5   = _active.head(5)
    _other  = _active.iloc[5:]
    pp_plan_names = list(_top5["Plan"]) + ["Other Active", "Legacy"]
    pp_plan_vals  = _top5["Sub_Count"].tolist() + [
        _other["Sub_Count"].sum(), _legacy["Sub_Count"].sum()
    ]
    _pp_dummy = False
else:
    pp_plan_names = ["$295 Plan", "$450 Plan", "Shared Member", "Shared Owner", "$625 Plan", "Other Active", "Legacy"]
    pp_plan_vals  = [0] * 7
    _pp_dummy = True

# ── Charts: Active Plans  |  Revenue by Bundle Type ─────────────────────
ml, mr = st.columns([55, 45])

with ml:
    _pp_total = sum(pp_plan_vals)
    _pp_pcts  = [v / _pp_total * 100 if _pp_total else 0 for v in pp_plan_vals]
    _pp_lbls  = [f"{n}  {p:.1f}%" for n, p in zip(pp_plan_names, _pp_pcts)]
    _pp_clrs  = ["#0101D3", "#1e40af", "#3b82f6", "#60a5fa", "#93c5fd", "#94a3b8", "#4b5563"]
    _pp_dw    = 0.48
    fig = go.Figure(go.Pie(
        labels=_pp_lbls, values=pp_plan_vals, hole=0.48, sort=False,
        domain=dict(x=[0, _pp_dw]),
        marker=dict(colors=_pp_clrs, line=dict(color="rgba(255,255,255,0.3)", width=2)),
        textinfo="none",
        customdata=pp_plan_names,
        hovertemplate="<b>%{customdata}</b><br>%{value:,.0f} subs (%{percent})<extra></extra>",
        title=dict(
            text=f"<b>{_pp_total/1_000:.1f}K</b>",
            font=dict(size=28, color="white"),
            position="middle center",
        ),
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=427,
        title=dict(
            text="<b>Subscribers by Active Plan</b>"
                 + (" <span style='color:#f87171'> ⚠ no data</span>" if _pp_dummy else ""),
            font=dict(size=28, color="white"), x=0,
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=20, color="white"),
                    x=_pp_dw + 0.04, y=0.5, xanchor="left", yanchor="middle"),
        margin=dict(l=10, r=10, t=44, b=6),
    )
    st.plotly_chart(fig, use_container_width=True)

with mr:
    pass
