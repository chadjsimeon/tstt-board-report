import streamlit as st

st.set_page_config(page_title="TSTT | WTTx Revenue", page_icon="📱", layout="wide")

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
wx_mons   = months[-13:]
wx_latest = wttx[wttx["Month"] == "Apr-26"]
wx_apr25  = wttx[wttx["Month"] == "Apr-25"]

# Revenue
wx26_rev  = float(wx_latest["Revenue"].sum())  if not wx_latest.empty else 0.0
# Prefer Revenue_PY column; fall back to Apr-25 row lookup
_wx_py_col = None
if not wx_latest.empty and "Revenue_PY" in wx_latest.columns:
    _v = wx_latest["Revenue_PY"].values[0]
    if pd.notna(_v) and float(_v) != 0:
        _wx_py_col = float(_v)
wx25_rev = _wx_py_col if _wx_py_col is not None else (
    float(wx_apr25["Revenue"].sum()) if not wx_apr25.empty else 0.0)
_wx_aop_r = wx_latest["Revenue_AOP"].values[0] if not wx_latest.empty else None
wx_aop_v  = (float(_wx_aop_r)
             if _wx_aop_r is not None and pd.notna(_wx_aop_r) else None)
wx_aop_pct = (wx26_rev - wx_aop_v) / wx_aop_v * 100 if wx_aop_v else None
wx_aop_m   = wx26_rev - wx_aop_v if wx_aop_v else None
wx_py_m    = wx26_rev - wx25_rev if wx25_rev else None

# Subscribers
wx_subs_row = _latest_row_with(wttx, "Subscribers")
wx_subs_lat = float(wx_subs_row["Subscribers"]) if wx_subs_row is not None else 0.0
wx_subs_25  = float(wx_apr25["Subscribers"].sum()) if not wx_apr25.empty else 0.0
_wx_churn_r = wx_latest["Churn_Pct"].values[0] if not wx_latest.empty else None
wx_churn    = (float(_wx_churn_r)
               if _wx_churn_r is not None and pd.notna(_wx_churn_r) else None)
_wx_saop    = "Subscribers_AOP"
wx_subs_aop = (float(wx_latest[_wx_saop].values[0])
               if not wx_latest.empty and _wx_saop in wx_latest.columns
               and pd.notna(wx_latest[_wx_saop].values[0]) else None)
wx_subs_aop_pct = (wx_subs_lat - wx_subs_aop) / wx_subs_aop * 100 if wx_subs_aop else None
wx_subs_py_pct  = (wx_subs_lat - wx_subs_25) / wx_subs_25 * 100 if wx_subs_25 else None

# ARPU
wx_arpu_row = _latest_row_with(wttx, "ARPU")
wx_arpu_lat = float(wx_arpu_row["ARPU"]) if wx_arpu_row is not None else 0.0
wx_arpu_25  = (float(wx_apr25["ARPU"].mean())
               if not wx_apr25.empty and wx_apr25["ARPU"].sum() > 0 else 0.0)
_wx_aaop    = "ARPU_AOP"
wx_arpu_aop = (float(wx_latest[_wx_aaop].values[0])
               if not wx_latest.empty and _wx_aaop in wx_latest.columns
               and pd.notna(wx_latest[_wx_aaop].values[0]) else None)
wx_arpu_aop_pct = (wx_arpu_lat - wx_arpu_aop) / wx_arpu_aop * 100 if wx_arpu_aop else None
wx_arpu_py_pct  = (wx_arpu_lat - wx_arpu_25) / wx_arpu_25 * 100 if wx_arpu_25 else None

# Sparklines
wx_rev_spark  = wttx.set_index("Month")["Revenue"].reindex(wx_mons).fillna(0).tolist()
wx_subs_spark = wttx.set_index("Month")["Subscribers"].reindex(wx_mons).fillna(0).tolist()
wx_arpu_spark = wttx.set_index("Month")["ARPU"].reindex(wx_mons).fillna(0).tolist()


# ── Subscriber movement for card (mirrors chart logic exactly) ───────────
_wx_sub_sorted = wttx.copy()
_wx_sub_sorted["_dt"] = pd.to_datetime(_wx_sub_sorted["Month"], format="%b-%y", errors="coerce")
_wx_sub_sorted = _wx_sub_sorted.sort_values("_dt").reset_index(drop=True)
_wx_subs_mon   = _wx_sub_sorted.iloc[-1]["Month"] if not _wx_sub_sorted.empty else "Apr-26"
wx_subs_close  = float(_wx_sub_sorted.iloc[-1]["Subscribers"]) if not _wx_sub_sorted.empty else wx_subs_lat
wx_subs_open   = float(_wx_sub_sorted.iloc[-2]["Subscribers"]) if len(_wx_sub_sorted) >= 2 else wx_subs_close
_wx_latest_row  = _wx_sub_sorted.iloc[-1] if not _wx_sub_sorted.empty else None
_wx_gross_raw   = float(_wx_latest_row["Gross_Adds"]) if (_wx_latest_row is not None and "Gross_Adds" in _wx_latest_row and pd.notna(_wx_latest_row["Gross_Adds"])) else 0.0
_wx_churn_cnt   = float(_wx_latest_row["Churn_Count"]) if (_wx_latest_row is not None and "Churn_Count" in _wx_latest_row and pd.notna(_wx_latest_row["Churn_Count"])) else None
if _wx_gross_raw > 0:
    wx_subs_gross_c = _wx_gross_raw
    wx_subs_disc_c  = _wx_churn_cnt if _wx_churn_cnt is not None else 0.0
else:
    wx_subs_disc_c  = wx_subs_open * wx_churn / 100 if (wx_churn and wx_subs_open > 0) else 0.0
    wx_subs_gross_c = max(0.0, wx_subs_close - wx_subs_open + wx_subs_disc_c)
wx_churn_derived = wx_churn if wx_churn else 0.0

# ── 4 KPI boxes ──────────────────────────────────────────────────────────
wx_r_aop_col = rev_var_rag(wx_aop_pct)
wx_r_l1 = (f"{wx_aop_m:+.1f} | {wx_aop_pct:+.1f}% vs AOP"
           if wx_aop_pct is not None else "— vs AOP")
wx_py_pct   = wx_py_m / wx25_rev * 100 if (wx_py_m is not None and wx25_rev) else None
wx_r_l2    = (f"{wx_py_m:+.1f} | {wx_py_pct:+.1f}% vs PY"
              if wx_py_pct is not None else "— vs PY")
wx_r_py_col = rev_var_rag(wx_py_pct) if wx_py_pct is not None else "#7788aa"

wx_a_l1_col = rev_var_rag(wx_arpu_aop_pct)
wx_a_l1 = (f"${wx_arpu_lat - wx_arpu_aop:+.0f} | {wx_arpu_aop_pct:+.1f}% vs AOP"
           if wx_arpu_aop_pct is not None else "— vs AOP")
wx_arpu_py_delta = wx_arpu_lat - wx_arpu_25 if wx_arpu_25 else None
wx_a_l2_col = rev_var_rag(wx_arpu_py_pct) if wx_arpu_py_pct is not None else "#7788aa"
wx_a_l2 = (f"${wx_arpu_py_delta:+.0f} | {wx_arpu_py_pct:+.1f}% vs PY"
           if wx_arpu_py_pct is not None else "— vs PY")

_wx_s_l1_col = rev_var_rag(wx_subs_aop_pct)
_wx_s_l1 = (f"{(wx_subs_close - wx_subs_aop)/1000:+.1f}K | {wx_subs_aop_pct:+.1f}% vs AOP"
            if wx_subs_aop_pct is not None else "— vs AOP")
wx_subs_py_delta = (wx_subs_close - wx_subs_25) / 1000 if wx_subs_25 else None
_wx_s_l2_col = rev_var_rag(wx_subs_py_pct) if wx_subs_py_pct is not None else "#7788aa"
_wx_s_l2 = (f"{wx_subs_py_delta:+.1f}K | {wx_subs_py_pct:+.1f}% vs PY"
            if wx_subs_py_pct is not None else "— vs PY")

_wx_c1     = _pre_kpi("WTTx Revenue", f"{wx26_rev:.1f}",
                       wx_r_l1, wx_r_aop_col, wx_r_l2, wx_r_py_col, "#00d4a0", wx_rev_spark)
_wx_c3     = _pre_kpi("ARPU (TT$)", f"{wx_arpu_lat:.0f}",
                       wx_a_l1, wx_a_l1_col, wx_a_l2, wx_a_l2_col, "#f59e0b", wx_arpu_spark)
_wx_c_subs = _pre_kpi("Subscribers", _fmt_k(wx_subs_close),
                       _wx_s_l1, _wx_s_l1_col, _wx_s_l2, _wx_s_l2_col, "#22c55e", wx_subs_spark)

_wx_churn_lbl  = f"Churn ({wx_churn_derived:.1f}%)"
_wx_mov_rows   = [
    ("Opening",     f"{wx_subs_open/1000:.1f}K",     "#aabbcc"),
    ("Gross Adds",  f"+{wx_subs_gross_c/1000:.1f}K", "#22c55e"),
    (_wx_churn_lbl, f"−{wx_subs_disc_c/1000:.1f}K",  "#ef4444"),
    ("Closing",     f"{wx_subs_close/1000:.1f}K",    "white"),
]
_wx_mov_html = "".join(
    f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
    f'border-bottom:1px solid #1e2a4a;">'
    f'<span style="font-size:29px;color:#7788aa">{lbl}</span>'
    f'<span style="font-size:29px;font-weight:700;color:{col}">{val}</span>'
    f'</div>'
    for lbl, val, col in _wx_mov_rows
)
_wx_c2 = (
    f'<div style="background:#161B22;border-radius:10px;padding:16px 16px;'
    f'border:1px solid #2a2a4a;border-top:3px solid #22c55e;height:100%">'
    f'<div style="font-size:28px;color:#6677aa;font-weight:700;text-transform:uppercase;'
    f'letter-spacing:1.5px;margin-bottom:10px">Subscriber Movements</div>'
    f'{_wx_mov_html}'
    f'</div>'
)

st.markdown(
    f'<div style="display:flex;gap:12px;margin-bottom:16px">'
    f'<div style="flex:1">{_wx_c1}</div>'
    f'<div style="flex:1">{_wx_c3}</div>'
    f'<div style="flex:1">{_wx_c_subs}</div>'
    f'<div style="flex:1">{_wx_c2}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ── Subscriber Net Movement data ──────────────────────────────────────────
wx_sorted = wttx.copy()
wx_sorted["_dt"] = pd.to_datetime(wx_sorted["Month"], format="%b-%y", errors="coerce")
wx_sorted = wx_sorted.sort_values("_dt").reset_index(drop=True)

_wx_mov_rows = []
for _i in range(1, len(wx_sorted)):
    _prev = wx_sorted.iloc[_i - 1]
    _curr = wx_sorted.iloc[_i]
    _open = float(_prev["Subscribers"])
    _clos = float(_curr["Subscribers"])
    _chv  = _curr["Churn_Pct"]
    _chrt = (float(_chv) if pd.notna(_chv) and float(_chv) > 0 else 1.5)
    _disc = _open * _chrt / 100
    _gros = max(0.0, (_clos - _open) + _disc)
    _wx_mov_rows.append({
        "Month":   _curr["Month"],
        "Opening": _open,
        "Gross":   _gros,
        "Disc":    _disc,
        "Closing": _clos,
        "Net":     _clos - _open,
    })
wx_mov_df   = pd.DataFrame(_wx_mov_rows)
wx_mov_mons = wx_mov_df["Month"].tolist()
_wx_op_v    = wx_mov_df["Opening"].tolist()
_wx_gr_v    = wx_mov_df["Gross"].tolist()
_wx_dc_v    = wx_mov_df["Disc"].tolist()
_wx_cl_v    = wx_mov_df["Closing"].tolist()

# AOP implied subscriber base: Revenue_AOP × 1M ÷ ARPU ()
wx_aop_subs = (wx_aop_v * 1_000_000 / wx_arpu_lat
               if wx_aop_v is not None and wx_arpu_lat > 0 else None)

# Y range zoomed to subscriber range
_wx_all_y = _wx_op_v + _wx_cl_v + [o + g for o, g in zip(_wx_op_v, _wx_gr_v)] + [o - d for o, d in zip(_wx_op_v, _wx_dc_v)]
if wx_aop_subs:
    _wx_all_y.append(wx_aop_subs)
_wx_mov_ymin = min(_wx_all_y) * 0.996
_wx_mov_ymax = max(_wx_all_y) * 1.014

# ── Plan type — WTTX by Category sheet ───────────────────────────────────
_wx_cats_df = load_wttx_categories()
if not _wx_cats_df.empty:
    _wx_summary  = (_wx_cats_df.groupby("Category")["Subscribers"]
                    .sum().sort_values(ascending=False))
    wx_plan_names = _wx_summary.index.tolist()
    wx_plan_vals  = _wx_summary.values.tolist()
    _wx_dummy = False
else:
    wx_plan_names = ["Voice Only", "Bundle", "Data"]
    wx_plan_vals  = [8_000, 35_000, 62_000]
    _wx_dummy = True

# ── Charts: Plan Type | Revenue by Service Type ──────────────────────────
ml, mr = st.columns([55, 45])

with ml:
    _CAT_COLORS = {"Data": "#00d4a0", "Bundle": "#4a9eff", "Voice Only": "#a78bfa"}
    _wx_clrs    = [_CAT_COLORS.get(n, "#6b7280") for n in wx_plan_names]
    _wx_total   = sum(wx_plan_vals)
    _wx_pcts    = [v / _wx_total * 100 if _wx_total else 0 for v in wx_plan_vals]
    _wx_lbls    = [f"{n}  {p:.1f}%" for n, p in zip(wx_plan_names, _wx_pcts)]
    _wx_dw      = 0.48
    fig = go.Figure(go.Pie(
        labels=_wx_lbls, values=wx_plan_vals, hole=0.48, sort=False,
        domain=dict(x=[0, _wx_dw]),
        marker=dict(colors=_wx_clrs, line=dict(color="rgba(255,255,255,0.3)", width=2)),
        textinfo="none",
        customdata=wx_plan_names,
        hovertemplate="<b>%{customdata}</b><br>%{value:,.0f} subs (%{percent})<extra></extra>",
        title=dict(
            text=f"<b>{_wx_total/1_000:.1f}K</b>",
            font=dict(size=28, color="white"),
            position="middle center",
        ),
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=427,
        title=dict(
            text="<b>Subscribers by Plan Type</b>"
                 + (" <span style='color:#f87171'> ⚠ no data</span>" if _wx_dummy else ""),
            font=dict(size=28, color="white"), x=0,
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=22, color="white"),
                    x=_wx_dw + 0.04, y=0.5, xanchor="left", yanchor="middle"),
        margin=dict(l=10, r=10, t=44, b=6),
    )
    st.plotly_chart(fig, use_container_width=True)

with mr:
    pass
