import streamlit as st

st.set_page_config(page_title="TSTT | Prepaid Revenue", page_icon="📱", layout="wide")

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
from utils.consumer_common import _pre_kpi, _base_layout, _fmt_k

inject_css()
data     = load_all_data()
consumer = data["Consumer_Sales"]

months   = get_month_order(consumer)
prepaid  = consumer[consumer["Segment"] == "Prepaid"].copy()
postpaid = consumer[consumer["Segment"] == "Postpaid"].copy()
wttx     = consumer[consumer["Segment"] == "WTTx"].copy()


# ── Data prep ────────────────────────────────────────────────────────────
pre_mons    = months[-13:]
# Latest prepaid month with booked revenue (was hardcoded to Apr-26)
_pre_rev_by_mon  = prepaid.groupby("Month")["Revenue"].sum()
pre_latest_month = next(
    (m for m in reversed(pre_mons)
     if pd.notna(_pre_rev_by_mon.get(m)) and _pre_rev_by_mon.get(m, 0) > 0),
    pre_mons[-1],
)
pre_py_month = (pd.to_datetime(pre_latest_month, format="%b-%y")
                - pd.DateOffset(months=12)).strftime("%b-%y")
pre_latest  = prepaid[prepaid["Month"] == pre_latest_month]
pre_apr25   = prepaid[prepaid["Month"] == pre_py_month]

# ── Prepaid subscriber totals — source of truth from ARPU buckets file ──
_arpu_df = load_prepaid_arpu()
if not _arpu_df.empty:
    # Sum all 5 buckets per month to get total subscribers
    _arpu_totals = (
        _arpu_df.groupby("Month")["Subscribers"].sum()
    )
    # Latest valid month (skip months with obviously incomplete subs, <300K)
    _arpu_dt_idx = pd.to_datetime(_arpu_totals.index, format="%b-%y", errors="coerce")
    _valid_mask  = (_arpu_totals.values > 300_000) & pd.notnull(_arpu_dt_idx)
    _arpu_latest_month = (
        _arpu_dt_idx[_valid_mask].max().strftime("%b-%y")
        if _valid_mask.any() else _arpu_totals.index[-1]
    )
    _arpu_py_month = (
        pd.to_datetime(_arpu_latest_month, format="%b-%y") - pd.DateOffset(months=12)
    ).strftime("%b-%y")
else:
    _arpu_totals       = pd.Series(dtype=float)
    _arpu_latest_month = "Apr-26"
    _arpu_py_month     = "Apr-25"

# Revenue
apr26_rev   = float(pre_latest["Revenue"].sum())  if not pre_latest.empty else 0.0
# Prefer Revenue_PY column; fall back to Apr-25 row lookup
_pre_py_col = None
if not pre_latest.empty and "Revenue_PY" in pre_latest.columns:
    _v = pre_latest["Revenue_PY"].values[0]
    if pd.notna(_v) and float(_v) != 0:
        _pre_py_col = float(_v)
apr25_rev = _pre_py_col if _pre_py_col is not None else (
    float(pre_apr25["Revenue"].sum()) if not pre_apr25.empty else 0.0)
_r_aop_raw  = pre_latest["Revenue_AOP"].values[0] if not pre_latest.empty else None
apr26_aop_v = (float(_r_aop_raw)
               if _r_aop_raw is not None and pd.notna(_r_aop_raw) else None)
rev_aop_pct = (apr26_rev - apr26_aop_v) / apr26_aop_v * 100 if apr26_aop_v else None
rev_aop_m   = apr26_rev - apr26_aop_v if apr26_aop_v else None
rev_py_m    = apr26_rev - apr25_rev if apr25_rev else None

# Subscribers — from ARPU buckets file (source of truth)
subs_lat   = float(_arpu_totals.get(_arpu_latest_month, 0.0))
subs_25    = float(_arpu_totals.get(_arpu_py_month, 0.0))
_churn_raw = pre_latest["Churn_Pct"].values[0] if not pre_latest.empty else None
churn_pre  = (float(_churn_raw)
              if _churn_raw is not None and pd.notna(_churn_raw) else None)
_saop      = "Subscribers_AOP"
subs_aop_v = (float(pre_latest[_saop].values[0])
              if not pre_latest.empty and _saop in pre_latest.columns
              and pd.notna(pre_latest[_saop].values[0]) else None)
subs_aop_pct = (subs_lat - subs_aop_v) / subs_aop_v * 100 if subs_aop_v else None
subs_aop_m   = (subs_lat - subs_aop_v) if subs_aop_v else None
subs_py_pct  = (subs_lat - subs_25) / subs_25 * 100 if subs_25 else None

# ARPU — derived from revenue / subscribers (subscribers from ARPU buckets file)
arpu_lat   = (apr26_rev * 1_000_000 / subs_lat)  if subs_lat  > 0 else 0.0
arpu_25    = (apr25_rev * 1_000_000 / subs_25)   if subs_25   > 0 else 0.0
_aaop      = "ARPU_AOP"
arpu_aop_v = (float(pre_latest[_aaop].values[0])
              if not pre_latest.empty and _aaop in pre_latest.columns
              and pd.notna(pre_latest[_aaop].values[0]) else None)
arpu_aop_pct = (arpu_lat - arpu_aop_v) / arpu_aop_v * 100 if arpu_aop_v else None
arpu_aop_m   = (arpu_lat - arpu_aop_v) if arpu_aop_v else None
arpu_py_pct  = (arpu_lat - arpu_25) / arpu_25 * 100 if arpu_25 else None

# Sparklines
_pre_rev_s = prepaid.groupby("Month")["Revenue"].sum()
rev_spark  = _pre_rev_s.reindex(pre_mons, fill_value=0).tolist()
subs_spark = _arpu_totals.reindex(pre_mons, fill_value=0).tolist()
arpu_spark = [
    float(_pre_rev_s.get(m, 0) * 1_000_000 / _arpu_totals[m])
    if m in _arpu_totals.index and _arpu_totals[m] > 0 else 0.0
    for m in pre_mons
]


# ── Subscriber movement for the latest month ─────────────────────────────
_prev_subs_month   = (pd.to_datetime(_arpu_latest_month, format="%b-%y")
                      - pd.DateOffset(months=1)).strftime("%b-%y")
pre_subs_open  = float(_arpu_totals.get(_prev_subs_month, 0.0))
pre_subs_close = subs_lat
pre_subs_net   = pre_subs_close - pre_subs_open
# Use Gross_Adds / Churn_Count directly when available (new whole-number format)
_pre_gross_adds_raw = pre_latest["Gross_Adds"].values[0] if not pre_latest.empty else 0.0
_pre_churn_count_raw = pre_latest["Churn_Count"].values[0] if (not pre_latest.empty and "Churn_Count" in pre_latest.columns) else None
if _pre_gross_adds_raw and float(_pre_gross_adds_raw) > 0:
    pre_subs_gross = float(_pre_gross_adds_raw)
    # Churn back-calculated so Opening + Gross Adds − Churn reconciles to Closing
    pre_subs_disc  = max(0.0, pre_subs_open + pre_subs_gross - pre_subs_close)
else:
    pre_subs_disc  = pre_subs_open * churn_pre / 100 if (churn_pre and pre_subs_open > 0) else 0.0
    pre_subs_gross = max(0.0, pre_subs_close - pre_subs_open + pre_subs_disc)
churn_derived  = (pre_subs_disc / pre_subs_open * 100) if pre_subs_open > 0 else 0.0

# ── 4 KPI boxes ──────────────────────────────────────────────────────────
r_aop_col  = rev_var_rag(rev_aop_pct)
r_l1       = (f"{rev_aop_m:+.1f} | {rev_aop_pct:+.1f}% vs AOP"
              if rev_aop_pct is not None else "— vs AOP")
rev_py_pct = (rev_py_m / apr25_rev * 100) if (rev_py_m is not None and apr25_rev) else None
r_l2       = (f"{rev_py_m:+.1f} | {rev_py_pct:+.1f}% vs PY"
              if rev_py_pct is not None else "— vs PY")
r_py_col   = rev_var_rag(rev_py_pct) if rev_py_pct is not None else "#7788aa"

a_l1_col     = rev_var_rag(arpu_aop_pct)
a_l1         = (f"${arpu_aop_m:+.0f} | {arpu_aop_pct:+.1f}% vs AOP"
                if arpu_aop_pct is not None else "— vs AOP")
a_l2_col     = rev_var_rag(arpu_py_pct) if arpu_py_pct is not None else "#7788aa"
arpu_py_delta = arpu_lat - arpu_25 if arpu_25 else None
a_l2         = (f"${arpu_py_delta:+.0f} | {arpu_py_pct:+.1f}% vs PY"
                if arpu_py_pct is not None else "— vs PY")

s_l1_col     = rev_var_rag(subs_aop_pct)
s_l1         = (f"{subs_aop_m/1000:+.1f}K | {subs_aop_pct:+.1f}% vs AOP"
                if subs_aop_pct is not None else "— vs AOP")
s_l2_col     = rev_var_rag(subs_py_pct) if subs_py_pct is not None else "#7788aa"
subs_py_delta = (subs_lat - subs_25) / 1000 if subs_25 else None
s_l2         = (f"{subs_py_delta:+.1f}K | {subs_py_pct:+.1f}% vs PY"
                if subs_py_pct is not None else "— vs PY")

_c1     = _pre_kpi("Prepaid Revenue", f"{apr26_rev:.1f}",
                   r_l1, r_aop_col, r_l2, r_py_col, "#a78bfa", rev_spark)
_c3     = _pre_kpi("ARPU (TT$ -/sub)", f"{arpu_lat:.0f}",
                   a_l1, a_l1_col, a_l2, a_l2_col, "#f59e0b", arpu_spark)
_c_subs = _pre_kpi("Subscribers", _fmt_k(subs_lat),
                   s_l1, s_l1_col, s_l2, s_l2_col, "#22c55e", subs_spark)

# Subscriber movements card
_churn_lbl = f"Churn ({churn_derived:.1f}%)"
_mov_rows  = [
    ("Opening",    f"{pre_subs_open/1000:.1f}K",   "#aabbcc"),
    ("Gross Adds", f"+{pre_subs_gross/1000:.1f}K", "#22c55e"),
    (_churn_lbl,   f"−{pre_subs_disc/1000:.1f}K",  "#ef4444"),
    ("Closing",    f"{pre_subs_close/1000:.1f}K",  "white"),
]
_mov_html = "".join(
    f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
    f'border-bottom:1px solid #1e2a4a;">'
    f'<span style="font-size:29px;color:#7788aa">{lbl}</span>'
    f'<span style="font-size:29px;font-weight:700;color:{col}">{val}</span>'
    f'</div>'
    for lbl, val, col in _mov_rows
)
_c2 = (
    f'<div style="background:#161B22;border-radius:10px;padding:16px 16px;'
    f'border:1px solid #2a2a4a;border-top:3px solid #22c55e;height:100%">'
    f'<div style="font-size:28px;color:#6677aa;font-weight:700;text-transform:uppercase;'
    f'letter-spacing:1.5px;margin-bottom:10px">Subscriber Movements</div>'
    f'{_mov_html}'
    f'</div>'
)

st.markdown(
    f'<div style="display:flex;gap:12px;margin-bottom:16px">'
    f'<div style="flex:1">{_c1}</div>'
    f'<div style="flex:1">{_c3}</div>'
    f'<div style="flex:1">{_c_subs}</div>'
    f'<div style="flex:1">{_c2}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Avg daily revenue calc ────────────────────────────────────────────────
import calendar as _cal

def _month_days(mon_str):
    abbr, yr2 = mon_str.split("-")
    m_num = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
             "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}[abbr]
    return _cal.monthrange(2000 + int(yr2), m_num)[1]

pre_daily = prepaid[prepaid["Month"].isin(set(pre_mons))][["Month", "Revenue", "Revenue_AOP"]].copy()
pre_daily["Days"]      = pre_daily["Month"].apply(_month_days)
pre_daily["Daily_Rev"] = pre_daily["Revenue"]     / pre_daily["Days"]
pre_daily["Daily_AOP"] = pre_daily["Revenue_AOP"] / pre_daily["Days"]

# ── ARPU Category ─────────────────────────────────────────────────────────
# Display order: VHV at the top of the chart down to VLV at the bottom.
# (Plotly draws horizontal-bar categories bottom→top, so the array is reversed.)
_ARPU_ORDER_BOTTOM_UP = ["VLV <$5", "LV $5-$30", "MV $30-$120",
                         "HV $120-$300", "VHV $300+"]
_ARPU_COLORS = {
    "VHV $300+":    "#22c55e",
    "HV $120-$300": "#a78bfa",
    "MV $30-$120":  "#6366f1",
    "LV $5-$30":    "#f59e0b",
    "VLV <$5":      "#6b7280",
}

def _arpu_cat_snapshot(month):
    if _arpu_df.empty or not month:
        return {}
    _snap = (
        _arpu_df[_arpu_df["Month"] == month]
        .groupby("Category")["Subscribers"].sum()
    )
    return _snap.to_dict() if not _snap.empty else {}

pre_arpu_cats    = _arpu_cat_snapshot(_arpu_latest_month)
_arpu_data_label = _arpu_latest_month if pre_arpu_cats else None
_arpu_prev_month = (pd.to_datetime(_arpu_latest_month, format="%b-%y")
                    - pd.DateOffset(months=1)).strftime("%b-%y")
pre_arpu_cats_prev = _arpu_cat_snapshot(_arpu_prev_month)

def _arpu_cat_chart(cats, month_label):
    _cat_names  = ([c for c in cats if c not in _ARPU_ORDER_BOTTOM_UP]
                   + [c for c in _ARPU_ORDER_BOTTOM_UP if c in cats])
    _cat_vals   = [cats[c] for c in _cat_names]
    _cat_colors = [_ARPU_COLORS.get(c, "#6b7280") for c in _cat_names]
    _cat_total  = sum(_cat_vals)
    _cat_pcts   = [v / _cat_total * 100 if _cat_total else 0 for v in _cat_vals]
    fig = go.Figure(go.Bar(
        y=_cat_names, x=_cat_vals, orientation="h",
        marker_color=_cat_colors,
        text=[f"{p:.0f}%" for p in _cat_pcts],
        textposition="outside", textfont=dict(color="white", size=22),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} subs<extra></extra>",
    ))
    _base_layout(fig, f"<b>Subs by ARPU — {month_label}</b>", 320)
    fig.update_layout(
        showlegend=False,
        xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=20),
                   range=[0, max(_cat_vals) * 1.45] if _cat_vals else None),
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="white", size=20),
                   categoryorder="array", categoryarray=_cat_names),
    )
    return fig

# ── Charts: Avg Daily Revenue  |  Subscribers by ARPU Category ───────────
ml, mc, mr = st.columns([40, 30, 30])

with ml:
    dvr     = pre_daily["Daily_Rev"].dropna().values
    dvr_pad = (dvr.max() - dvr.min()) * 0.18 if len(dvr) > 1 else 0.05
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pre_daily["Month"], y=pre_daily["Daily_Rev"],
        name="Actual", marker_color="#a78bfa",
        hovertemplate="%{x}<br>%{y:.3f} / day<extra></extra>",
    ))
    _base_layout(fig, "Avg Daily Prepaid Revenue", 320,
                 y_range=([0.6, dvr.max() + dvr_pad]
                           if len(dvr) > 0 else None))
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with mc:
    if pre_arpu_cats_prev:
        st.plotly_chart(_arpu_cat_chart(pre_arpu_cats_prev, _arpu_prev_month),
                        use_container_width=True)
    else:
        st.info(f"No ARPU bucket data for {_arpu_prev_month}.")

with mr:
    if pre_arpu_cats:
        st.plotly_chart(_arpu_cat_chart(pre_arpu_cats, _arpu_latest_month),
                        use_container_width=True)
    else:
        st.info("No ARPU bucket data available for the selected month.")
