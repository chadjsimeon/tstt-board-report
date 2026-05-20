import streamlit as st

st.set_page_config(page_title="TSTT | Consumer", page_icon="📱", layout="wide")

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

inject_css()
data     = load_all_data()
consumer = data["Consumer_Sales"]

page_header("Consumer", "Prepaid · Postpaid · WTTx — Revenue, Subscribers, Churn, ARPU")

# ── Sidebar ───────────────────────────────────────────────────────────────────
months    = get_month_order(consumer)
segments  = consumer["Segment"].unique().tolist()
sel_month = st.sidebar.selectbox("Focus Month", months, index=len(months) - 1)

# ── Snapshot metrics strip ────────────────────────────────────────────────────
latest_snap = consumer[consumer["Month"] == sel_month]
total_rev   = latest_snap["Revenue"].sum()
total_subs  = latest_snap["Subscribers"].sum()
avg_churn   = latest_snap["Churn_Pct"].mean()
avg_arpu    = ((latest_snap["ARPU"] * latest_snap["Subscribers"]).sum()
               / total_subs if total_subs else 0)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Revenue",     f"{total_rev:,.0f}")
m2.metric("Total Subscribers", f"{total_subs:,.0f}")
m3.metric("Avg Churn",         f"{avg_churn:.1f}%")
m4.metric("Blended ARPU",      f"{avg_arpu:,.0f}")

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════════
# PAGE-LEVEL HELPERS  (shared by all tabs)
# ═════════════════════════════════════════════════════════════════════════════
FY_MONTHS = [m for m in months if m != "Apr-26"]   # Apr-25 → Mar-26

prepaid  = consumer[consumer["Segment"] == "Prepaid"].copy()
postpaid = consumer[consumer["Segment"] == "Postpaid"].copy()
wttx     = consumer[consumer["Segment"] == "WTTx"].copy()


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
    fill_pts  = f"0,{height} {line_pts} {w},{height}"
    r, g, b   = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {w} {height}" '
        f'preserveAspectRatio="none" style="display:block;margin-top:8px">'
        f'<polygon points="{fill_pts}" fill="rgba({r},{g},{b},0.15)"/>'
        f'<polyline points="{line_pts}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
    )


def _card(title, value_str, sub_str, sub_color, extra_str="", accent="#00ff88",
          spark_series=None):
    extra = (""
             if not extra_str
             else f'<div style="font-size:13px;color:#8899bb;margin-top:4px">{extra_str}</div>')
    spark = _sparkline(spark_series, accent) if spark_series is not None else ""
    return (
        f'<div style="background:#161B22;border-radius:10px;padding:14px 16px;'
        f'border:1px solid #2a2a4a;border-top:3px solid {accent};height:100%">'
        f'<div style="font-size:13px;color:#7788aa;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:8px">{title}</div>'
        f'<div style="font-size:28px;font-weight:700;color:white;margin-bottom:6px">{value_str}</div>'
        f'<div style="font-size:15px;color:{sub_color};font-weight:600">{sub_str}</div>'
        f'{extra}{spark}</div>'
    )


def _get_gross_adds(row):
    """Return Gross_Adds from a DataFrame row/Series if populated, else None."""
    try:
        v = float(row["Gross_Adds"])
        return v if v > 0 else None
    except (KeyError, TypeError, ValueError):
        return None


def _commentary(text):
    return (
        '<div style="background:#0f1e10;border-radius:10px;padding:18px 20px;'
        'border:1px solid #1a3a1a;border-left:4px solid #22c55e;height:100%">'
        '<div style="font-size:13px;color:#f59e0b;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:12px">Commentary</div>'
        f'<div style="font-size:15px;color:#aaccaa;line-height:1.7">{text}</div>'
        '</div>'
    )


def _tab_hdr(title, period="YTD April 2026 | TTM"):
    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'margin-bottom:16px">'
        f'<div style="font-size:1.4rem;font-weight:700;color:white">{title}</div>'
        f'<div style="font-size:1.1rem;color:#7788aa">{period}</div>'
        '</div>'
    )


def _vc(pct):
    if pct is None: return "#888888"
    return "#22c55e" if pct >= 0 else "#ef4444"


def _vs(pct, suffix="% vs AOP"):
    if pct is None: return "— vs AOP"
    return f"{pct:+.1f}{suffix}"


def _fmt_k(n):
    n = float(n)
    if n >= 1_000_000: return f"{n/1_000_000:.1f}"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(int(n))


def _ttm(df):
    return df[df["Month"].isin(FY_MONTHS)]["Revenue"].sum()


def _annual_aop(df):
    row = df[df["Month"] == "Apr-26"]
    if row.empty: return None
    v = row["Revenue_AOP"].values[0]
    return v * 12 if pd.notna(v) else None


def _latest_row_with(df, col):
    """Return the last row where col > 0."""
    valid = df[df[col] > 0]
    return valid.iloc[-1] if not valid.empty else None


def _base_layout(fig, title, height, y_range=None):
    kw = dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=14))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=height,
        title=dict(text=f"<b>{title}</b>", font=dict(size=16, color="white"), x=0),
        xaxis=kw,
        yaxis=dict(**kw, range=y_range),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                    y=1.08, x=0, font=dict(size=14)),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
tab_v2, tab2, tab3, tab4 = st.tabs([
    "Consumer Sales V2",
    "Prepaid Revenue",
    "Postpaid Revenue",
    "WTTx Revenue",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Prepaid Revenue
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown(_tab_hdr("Prepaid Revenue"), unsafe_allow_html=True)

    # ── Data prep ────────────────────────────────────────────────────────────
    pre_mons    = months[-13:]
    pre_latest  = prepaid[prepaid["Month"] == "Apr-26"]
    pre_apr25   = prepaid[prepaid["Month"] == "Apr-25"]

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
    apr25_rev   = float(pre_apr25["Revenue"].sum())   if not pre_apr25.empty else 0.0
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

    # TTM for product chart
    ttm_pre = _ttm(prepaid)

    # ── KPI card builder ─────────────────────────────────────────────────────
    def _pre_kpi(label, value, line1, l1_col, line2, l2_col, accent, spark, badge=None):
        b_html = (
            f'<span style="display:inline-block;background:rgba(239,68,68,0.12);'
            f'border:1px solid rgba(239,68,68,0.35);border-radius:20px;padding:2px 10px;'
            f'font-size:10px;color:#f87171;font-weight:600;margin-top:6px">{badge}</span>'
        ) if badge else ""
        sp_html = (
            f'<div style="margin-top:10px;opacity:0.9">{_sparkline(spark, accent, 44)}</div>'
        ) if spark else ""
        return (
            f'<div style="background:#161B22;border-radius:10px;padding:14px 12px;'
            f'border:1px solid #252545;border-top:3px solid {accent};'
            f'height:100%;box-sizing:border-box">'
            f'<div style="font-size:22px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:8px">{label}</div>'
            f'<div style="font-size:52px;font-weight:800;color:white;line-height:1.05;'
            f'margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'{value}</div>'
            f'<div style="font-size:23px;color:{l1_col};font-weight:600;margin-bottom:3px">'
            f'{line1}</div>'
            f'<div style="font-size:23px;color:{l2_col};font-weight:600">{line2}</div>'
            f'{b_html}{sp_html}'
            f'</div>'
        )

    # ── Subscriber movement for the latest month ─────────────────────────────
    _prev_subs_month   = (pd.to_datetime(_arpu_latest_month, format="%b-%y")
                          - pd.DateOffset(months=1)).strftime("%b-%y")
    pre_subs_open  = float(_arpu_totals.get(_prev_subs_month, 0.0))
    pre_subs_close = subs_lat
    pre_subs_net   = pre_subs_close - pre_subs_open
    pre_subs_disc  = pre_subs_open * churn_pre / 100 if (churn_pre and pre_subs_open > 0) else 0.0
    pre_subs_gross = max(0.0, pre_subs_close - pre_subs_open + pre_subs_disc)
    churn_derived  = churn_pre if churn_pre else 0.0

    # ── 4 KPI boxes ──────────────────────────────────────────────────────────
    r_aop_col = rev_var_rag(rev_aop_pct)
    r_l1 = (f"{rev_aop_m:+.1f} | {rev_aop_pct:+.1f}% vs AOP"
            if rev_aop_pct is not None else "— vs AOP")
    r_l2    = f"{rev_py_m:+.1f} vs PY" if rev_py_m is not None else "— vs PY"
    r_py_col = ("#22c55e" if (rev_py_m or 0) >= 0 else "#ef4444") if rev_py_m is not None else "#7788aa"

    a_l1_col = rev_var_rag(arpu_aop_pct)
    a_l1 = (f"${arpu_aop_m:+.0f} | {arpu_aop_pct:+.1f}% vs AOP"
            if arpu_aop_pct is not None else "— vs AOP")
    a_l2_col = ("#22c55e" if (arpu_py_pct or 0) >= 0
                else "#ef4444" if arpu_py_pct is not None else "#7788aa")
    a_l2 = (f"vs PY: {arpu_py_pct:+.1f}%"
            if arpu_py_pct is not None else "vs PY: —")

    s_l1_col = rev_var_rag(subs_aop_pct)
    s_l1 = (f"{subs_aop_m/1000:+.1f}K | {subs_aop_pct:+.1f}% vs AOP"
            if subs_aop_pct is not None else "— vs AOP")
    s_l2_col = ("#22c55e" if (subs_py_pct or 0) >= 0
                else "#ef4444" if subs_py_pct is not None else "#7788aa")
    s_l2 = (f"vs PY: {subs_py_pct:+.1f}%"
            if subs_py_pct is not None else "vs PY: —")

    _c1     = _pre_kpi("Prepaid Revenue", f"{apr26_rev:.1f}",
                       r_l1, r_aop_col, r_l2, r_py_col, "#a78bfa", rev_spark)
    _c3     = _pre_kpi("ARPU", f"${arpu_lat:.0f}",
                       a_l1, a_l1_col, a_l2, a_l2_col, "#f59e0b", arpu_spark)
    _c_subs = _pre_kpi(f"Subscribers — {_arpu_latest_month}", _fmt_k(subs_lat),
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
        f'<span style="font-size:19px;color:#7788aa">{lbl}</span>'
        f'<span style="font-size:22px;font-weight:700;color:{col}">{val}</span>'
        f'</div>'
        for lbl, val, col in _mov_rows
    )
    _c2 = (
        f'<div style="background:#161B22;border-radius:10px;padding:16px 16px;'
        f'border:1px solid #2a2a4a;border-top:3px solid #22c55e;height:100%">'
        f'<div style="font-size:18px;color:#7788aa;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:10px">Movements —{_arpu_latest_month}</div>'
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
    if not _arpu_df.empty:
        _snap = (
            _arpu_df[_arpu_df["Month"] == _arpu_latest_month]
            .groupby("Category")["Subscribers"].sum()
        )
        pre_arpu_cats    = _snap.to_dict() if not _snap.empty else {}
        _arpu_data_label = _arpu_latest_month
    else:
        pre_arpu_cats    = {}
        _arpu_data_label = None

    # ── Charts: Avg Daily Revenue  |  Subscribers by ARPU Category ───────────
    ml, mr = st.columns([55, 45])

    with ml:
        dvr     = pre_daily["Daily_Rev"].dropna().values
        dvr_pad = (dvr.max() - dvr.min()) * 0.18 if len(dvr) > 1 else 0.05
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=pre_daily["Month"], y=pre_daily["Daily_Rev"],
            name="Actual", marker_color="#a78bfa",
            hovertemplate="%{x}<br>%{y:.3f} / day<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=pre_daily["Month"], y=pre_daily["Daily_AOP"],
            name="AOP", mode="lines",
            line=dict(color="#555577", width=1.8, dash="dash"),
            hovertemplate="%{x}<br>AOP %{y:.3f} / day<extra></extra>",
        ))
        _base_layout(fig, "Avg Daily Prepaid Revenue", 480,
                     y_range=([0.6, dvr.max() + dvr_pad]
                               if len(dvr) > 0 else None))
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with mr:
        if pre_arpu_cats:
            _cat_names  = list(pre_arpu_cats.keys())
            _cat_vals   = list(pre_arpu_cats.values())
            _palette    = ["#6b7280", "#6366f1", "#a78bfa", "#f59e0b", "#22c55e"]
            _cat_colors = (_palette * ((len(_cat_names) // len(_palette)) + 1))[:len(_cat_names)]
            _cat_total  = sum(_cat_vals)
            _cat_pcts   = [v / _cat_total * 100 if _cat_total else 0 for v in _cat_vals]
            fig = go.Figure(go.Bar(
                y=_cat_names, x=_cat_vals, orientation="h",
                marker_color=_cat_colors,
                text=[f"{v/1_000:.1f}K  ({p:.0f}%)"
                      for v, p in zip(_cat_vals, _cat_pcts)],
                textposition="outside", textfont=dict(color="white", size=14),
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} subs<extra></extra>",
            ))
            _base_layout(
                fig,
                f"<b>Subscribers by ARPU Category</b>"
                + (f" — {_arpu_data_label}" if _arpu_data_label else ""),
                290,
            )
            fig.update_layout(
                showlegend=False,
                xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=14),
                           range=[0, max(_cat_vals) * 1.45] if _cat_vals else None),
                yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="white", size=15),
                           categoryorder="array", categoryarray=_cat_names),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ARPU bucket data available for the selected month.")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Postpaid Revenue
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown(_tab_hdr("Postpaid Revenue"), unsafe_allow_html=True)

    # ── Data prep ────────────────────────────────────────────────────────────
    pp_mons   = months[-13:]
    pp_latest = postpaid[postpaid["Month"] == "Apr-26"]
    pp_apr25  = postpaid[postpaid["Month"] == "Apr-25"]

    # Revenue
    pp26_rev  = float(pp_latest["Revenue"].sum())  if not pp_latest.empty else 0.0
    pp25_rev  = float(pp_apr25["Revenue"].sum())   if not pp_apr25.empty else 0.0
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

    # TTM for product chart
    ttm_pp = _ttm(postpaid)

    # ── Subscriber movement for card (mirrors chart logic exactly) ───────────
    _pp_sub_sorted = postpaid.copy()
    _pp_sub_sorted["_dt"] = pd.to_datetime(_pp_sub_sorted["Month"], format="%b-%y", errors="coerce")
    _pp_sub_sorted = _pp_sub_sorted.sort_values("_dt").reset_index(drop=True)
    _pp_subs_mon   = _pp_sub_sorted.iloc[-1]["Month"] if not _pp_sub_sorted.empty else "Apr-26"
    pp_subs_close  = float(_pp_sub_sorted.iloc[-1]["Subscribers"]) if not _pp_sub_sorted.empty else pp_subs_lat
    pp_subs_open   = float(_pp_sub_sorted.iloc[-2]["Subscribers"]) if len(_pp_sub_sorted) >= 2 else pp_subs_close
    pp_subs_disc_c   = pp_subs_open * pp_churn / 100 if (pp_churn and pp_subs_open > 0) else 0.0
    pp_subs_gross_c  = max(0.0, pp_subs_close - pp_subs_open + pp_subs_disc_c)
    pp_churn_derived = pp_churn if pp_churn else 0.0

    # ── 4 KPI boxes ──────────────────────────────────────────────────────────
    pp_r_aop_col = rev_var_rag(pp_aop_pct)
    pp_r_l1 = (f"{pp_aop_m:+.1f} | {pp_aop_pct:+.1f}% vs AOP"
               if pp_aop_pct is not None else "— vs AOP")
    pp_r_l2    = f"{pp_py_m:+.1f} vs PY" if pp_py_m is not None else "— vs PY"
    pp_r_py_col = ("#22c55e" if (pp_py_m or 0) >= 0 else "#ef4444") if pp_py_m is not None else "#7788aa"

    pp_a_l1_col = rev_var_rag(pp_arpu_aop_pct)
    pp_a_l1 = (f"${pp_arpu_lat - pp_arpu_aop:+.0f} | {pp_arpu_aop_pct:+.1f}% vs AOP"
               if pp_arpu_aop_pct is not None else "— vs AOP")
    pp_a_l2_col = "#f59e0b" if pp_arpu_py_pct is not None else "#7788aa"
    pp_a_l2 = (f"vs PY: {pp_arpu_py_pct:+.1f}%"
               if pp_arpu_py_pct is not None else "vs PY: —")

    _pp_s_l1_col = rev_var_rag(pp_subs_aop_pct)
    _pp_s_l1 = (f"{(pp_subs_close - pp_subs_aop)/1000:+.1f}K | {pp_subs_aop_pct:+.1f}% vs AOP"
                if pp_subs_aop_pct is not None else "— vs AOP")
    _pp_s_l2_col = ("#22c55e" if (pp_subs_py_pct or 0) >= 0
                    else "#ef4444" if pp_subs_py_pct is not None else "#7788aa")
    _pp_s_l2 = (f"vs PY: {pp_subs_py_pct:+.1f}%"
                if pp_subs_py_pct is not None else "vs PY: —")

    _pp_c1     = _pre_kpi("Postpaid Revenue", f"{pp26_rev:.1f}",
                           pp_r_l1, pp_r_aop_col, pp_r_l2, pp_r_py_col, "#4a9eff", pp_rev_spark)
    _pp_c3     = _pre_kpi("ARPU", f"${pp_arpu_lat:.0f}",
                           pp_a_l1, pp_a_l1_col, pp_a_l2, pp_a_l2_col, "#f59e0b", pp_arpu_spark)
    _pp_c_subs = _pre_kpi(f"Subscribers — {_pp_subs_mon}", _fmt_k(pp_subs_close),
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
        f'<span style="font-size:19px;color:#7788aa">{lbl}</span>'
        f'<span style="font-size:22px;font-weight:700;color:{col}">{val}</span>'
        f'</div>'
        for lbl, val, col in _pp_mov_rows
    )
    _pp_c2 = (
        f'<div style="background:#161B22;border-radius:10px;padding:16px 16px;'
        f'border:1px solid #2a2a4a;border-top:3px solid #22c55e;height:100%">'
        f'<div style="font-size:18px;color:#7788aa;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:10px">Movements —{_pp_subs_mon}</div>'
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
            font=dict(color="white"), height=500,
            title=dict(
                text="<b>Subscribers by Active Plan</b>"
                     + (" <span style='color:#f87171'> ⚠ no data</span>" if _pp_dummy else ""),
                font=dict(size=22, color="white"), x=0,
            ),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=20, color="white"),
                        x=_pp_dw + 0.04, y=0.5, xanchor="left", yanchor="middle"),
            margin=dict(l=10, r=10, t=44, b=6),
        )
        st.plotly_chart(fig, use_container_width=True)

    with mr:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — WTTx Revenue
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown(_tab_hdr("WTTx Revenue"), unsafe_allow_html=True)

    # ── Data prep ────────────────────────────────────────────────────────────
    wx_mons   = months[-13:]
    wx_latest = wttx[wttx["Month"] == "Apr-26"]
    wx_apr25  = wttx[wttx["Month"] == "Apr-25"]

    # Revenue
    wx26_rev  = float(wx_latest["Revenue"].sum())  if not wx_latest.empty else 0.0
    wx25_rev  = float(wx_apr25["Revenue"].sum())   if not wx_apr25.empty else 0.0
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

    # TTM for product chart
    ttm_wx = _ttm(wttx)

    # ── Subscriber movement for card (mirrors chart logic exactly) ───────────
    _wx_sub_sorted = wttx.copy()
    _wx_sub_sorted["_dt"] = pd.to_datetime(_wx_sub_sorted["Month"], format="%b-%y", errors="coerce")
    _wx_sub_sorted = _wx_sub_sorted.sort_values("_dt").reset_index(drop=True)
    _wx_subs_mon   = _wx_sub_sorted.iloc[-1]["Month"] if not _wx_sub_sorted.empty else "Apr-26"
    wx_subs_close  = float(_wx_sub_sorted.iloc[-1]["Subscribers"]) if not _wx_sub_sorted.empty else wx_subs_lat
    wx_subs_open   = float(_wx_sub_sorted.iloc[-2]["Subscribers"]) if len(_wx_sub_sorted) >= 2 else wx_subs_close
    wx_subs_disc_c   = wx_subs_open * wx_churn / 100 if (wx_churn and wx_subs_open > 0) else 0.0
    wx_subs_gross_c  = max(0.0, wx_subs_close - wx_subs_open + wx_subs_disc_c)
    wx_churn_derived = wx_churn if wx_churn else 0.0

    # ── 4 KPI boxes ──────────────────────────────────────────────────────────
    wx_r_aop_col = rev_var_rag(wx_aop_pct)
    wx_r_l1 = (f"{wx_aop_m:+.1f} | {wx_aop_pct:+.1f}% vs AOP"
               if wx_aop_pct is not None else "— vs AOP")
    wx_r_l2    = f"{wx_py_m:+.1f} vs PY" if wx_py_m is not None else "— vs PY"
    wx_r_py_col = ("#22c55e" if (wx_py_m or 0) >= 0 else "#ef4444") if wx_py_m is not None else "#7788aa"

    wx_a_l1_col = rev_var_rag(wx_arpu_aop_pct)
    wx_a_l1 = (f"${wx_arpu_lat - wx_arpu_aop:+.0f} | {wx_arpu_aop_pct:+.1f}% vs AOP"
               if wx_arpu_aop_pct is not None else "— vs AOP")
    wx_a_l2_col = ("#22c55e" if (wx_arpu_py_pct or 0) >= 0
                   else "#ef4444" if wx_arpu_py_pct is not None else "#7788aa")
    wx_a_l2 = (f"vs PY: {wx_arpu_py_pct:+.1f}%"
               if wx_arpu_py_pct is not None else "vs PY: —")

    _wx_s_l1_col = rev_var_rag(wx_subs_aop_pct)
    _wx_s_l1 = (f"{(wx_subs_close - wx_subs_aop)/1000:+.1f}K | {wx_subs_aop_pct:+.1f}% vs AOP"
                if wx_subs_aop_pct is not None else "— vs AOP")
    _wx_s_l2_col = "#f59e0b" if wx_subs_py_pct is not None else "#7788aa"
    _wx_s_l2 = (f"vs PY: {wx_subs_py_pct:+.1f}%"
                if wx_subs_py_pct is not None else "vs PY: —")

    _wx_c1     = _pre_kpi("WTTx Revenue", f"{wx26_rev:.1f}",
                           wx_r_l1, wx_r_aop_col, wx_r_l2, wx_r_py_col, "#00d4a0", wx_rev_spark)
    _wx_c3     = _pre_kpi("ARPU", f"${wx_arpu_lat:.0f}",
                           wx_a_l1, wx_a_l1_col, wx_a_l2, wx_a_l2_col, "#f59e0b", wx_arpu_spark)
    _wx_c_subs = _pre_kpi(f"Subscribers — {_wx_subs_mon}", _fmt_k(wx_subs_close),
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
        f'<span style="font-size:19px;color:#7788aa">{lbl}</span>'
        f'<span style="font-size:22px;font-weight:700;color:{col}">{val}</span>'
        f'</div>'
        for lbl, val, col in _wx_mov_rows
    )
    _wx_c2 = (
        f'<div style="background:#161B22;border-radius:10px;padding:16px 16px;'
        f'border:1px solid #2a2a4a;border-top:3px solid #22c55e;height:100%">'
        f'<div style="font-size:18px;color:#7788aa;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:10px">Movements —{_wx_subs_mon}</div>'
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
            font=dict(color="white"), height=500,
            title=dict(
                text="<b>Subscribers by Plan Type</b>"
                     + (" <span style='color:#f87171'> ⚠ no data</span>" if _wx_dummy else ""),
                font=dict(size=22, color="white"), x=0,
            ),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=22, color="white"),
                        x=_wx_dw + 0.04, y=0.5, xanchor="left", yanchor="middle"),
            margin=dict(l=10, r=10, t=44, b=6),
        )
        st.plotly_chart(fig, use_container_width=True)

    with mr:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# TAB V2 — Consumer Sales V2 (summary overview)
# ─────────────────────────────────────────────────────────────────────────────
with tab_v2:
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
        r = v2_py_snap[v2_py_snap["Segment"] == seg]["Revenue"]
        return float(r.values[0]) if not r.empty else None

    def _v2vp(rev, aop): return (rev - aop) / abs(aop) * 100 if aop else None
    def _v2vm(rev, aop): return rev - aop if aop is not None else None

    v2_t_rev = float(v2_latest["Revenue"].sum())
    v2_t_aop = float(v2_latest["Revenue_AOP"].sum())
    v2_t_py  = float(v2_py_snap["Revenue"].sum()) if not v2_py_snap.empty else None
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
    dc_aop_str  = f"{dc_aop_pct:+.1f}% vs AOP" if dc_aop_pct is not None else "— vs AOP"
    gp_aop_str  = f"{gp_aop_pct:+.1f}% vs AOP" if gp_aop_pct is not None else "— vs AOP"
    dc_aop_col  = rag(dc_aop_pct, 0, 10, higher=False) if dc_aop_pct is not None else "#7788aa"
    gp_aop_col  = rev_var_rag(gp_aop_pct)

    dc_trend = f"{dc_act - dc_py:+.1f} vs PY" if dc_py is not None else "—"
    dc_col   = "#f59e0b" if dc_py is not None else "#7788aa"
    gp_trend = f"{gp_act - gp_py:+.1f} vs PY" if gp_py is not None else "—"
    gp_col   = "#f59e0b" if gp_py is not None else "#8899bb"

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
    def r1_card(label, val_str, aop_pct, aop_m_str, yoy_str, accent, spark_series=None):
        col = rev_var_rag(aop_pct)
        aop_html = (
            f'<span style="color:{col}">{aop_m_str}&nbsp;|&nbsp;{aop_pct:+.1f}%&nbsp;vs&nbsp;AOP</span>'
            if aop_pct is not None
            else '<span style="color:#445566">— vs AOP</span>'
        )
        yoy_html = (
            f'<span style="color:#f59e0b;font-weight:700">{yoy_str}</span>'
            if yoy_str else '<span style="color:#445566">— vs PY</span>'
        )
        spark_html = (
            f'<div style="margin-top:8px;opacity:0.85">{_sparkline(spark_series, accent)}</div>'
            if spark_series else ""
        )
        return (
            f'<div style="background:#161B22;border-radius:10px;padding:14px 12px;'
            f'border:1px solid #252545;border-top:3px solid {accent};height:100%">'
            f'<div style="font-size:22px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:8px">{label}</div>'
            f'<div style="font-size:52px;font-weight:800;color:white;margin-bottom:8px;'
            f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
            f'<div style="font-size:23px;font-weight:600;margin-bottom:3px">{aop_html}</div>'
            f'<div style="font-size:23px;font-weight:600">{yoy_html}</div>'
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
        l2_h = (f'<div style="font-size:23px;color:{line2_col};font-weight:600;margin-top:2px">'
                f'{line2}</div>') if line2 else ""
        l1_h = (f'<div style="font-size:23px;color:{line1_col};font-weight:600">{line1}</div>'
                ) if line1 else ""
        mh = f"min-height:{min_height};" if min_height else ""
        return (
            f'<div style="background:#161B22;border-radius:10px;padding:12px 14px;'
            f'border:1px solid #252545;border-top:3px solid {accent};height:100%;{mh}">'
            f'<div style="font-size:22px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:8px;display:flex;align-items:center">{label}{dot}</div>'
            f'<div style="font-size:{val_size};font-weight:800;color:white;margin-bottom:8px;'
            f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
            f'{l1_h}{l2_h}{note_h}</div>'
        )

    # ════════════════════════════════════════════════════════════════════
    # ROW 1 — 5 KPI cards
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(r1_card(
        "Total Revenue", f"{v2_t_rev:.1f}",
        v2_tv_pct, f"{v2_tv_m:+.1f}",
        f"{v2_t_rev - v2_t_py:+.1f} vs PY" if v2_t_py is not None else None,
        "#00d4a0", spark_series=v2_total_trend,
    ), unsafe_allow_html=True)

    c2.markdown(r1_card(
        "Prepaid", f"{pr_rev:.1f}",
        _v2vp(pr_rev, pr_aop),
        f"{_v2vm(pr_rev, pr_aop):+.1f}" if _v2vm(pr_rev, pr_aop) is not None else "—",
        f"{pr_rev - pr_py_v:+.1f} vs PY" if pr_py_v is not None else None,
        "#a78bfa", spark_series=v2_pre_trend,
    ), unsafe_allow_html=True)

    c3.markdown(r1_card(
        "Postpaid", f"{pp_rev:.1f}",
        _v2vp(pp_rev, pp_aop),
        f"{_v2vm(pp_rev, pp_aop):+.1f}" if _v2vm(pp_rev, pp_aop) is not None else "—",
        f"{pp_rev - pp_py_v:+.1f} vs PY" if pp_py_v is not None else None,
        "#4a9eff", spark_series=v2_post_trend,
    ), unsafe_allow_html=True)

    c4.markdown(r1_card(
        "WTTx", f"{wx_rev:.1f}",
        _v2vp(wx_rev, wx_aop),
        f"{_v2vm(wx_rev, wx_aop):+.1f}" if _v2vm(wx_rev, wx_aop) is not None else "—",
        f"{wx_rev - wx_py_v:+.1f} vs PY" if wx_py_v is not None else None,
        "#f59e0b", spark_series=v2_wx_trend,
    ), unsafe_allow_html=True)

    c5.markdown(r1_card(
        "Other Revenue", f"{v2_other_rev:.1f}",
        v2_other_var,
        f"{v2_other_rev - v2_other_aop:+.1f}" if v2_other_aop else "—",
        f"{v2_other_rev - v2_other_py:+.1f} vs PY" if v2_other_py is not None else None,
        "#ff6b6b", spark_series=v2_other_trend,
    ), unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # ROW 2 — [1,1,3] columns: costs|prepaid metrics|revenue mix donut
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin:14px 0 8px'></div>", unsafe_allow_html=True)
    col_AB, col_C, _ = st.columns([2, 1.5, 1.5])

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
        _mou_html = r2_card(
            "Prepaid MoU / Sub", pre_mou_str,
            pre_mou_trend, pre_mou_col,
            is_ph=pre_mou_ph, accent="#a78bfa",
        )
        _gb_html  = r2_card(
            "Prepaid GB / Sub", pre_gb_str,
            pre_gb_trend, pre_gb_col,
            is_ph=pre_gb_ph, accent="#a78bfa",
        )
        st.markdown(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:8px;">'
            f'<div style="display:flex;flex-direction:column">{_dc_html}</div>'
            f'<div style="display:flex;flex-direction:column">{_mou_html}</div>'
            f'<div style="display:flex;flex-direction:column">{_gp_html}</div>'
            f'<div style="display:flex;flex-direction:column">{_gb_html}</div>'
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
            textfont=dict(size=14, color="white"),
            insidetextorientation="radial",
            customdata=d_segs,
            hovertemplate="<b>%{customdata}</b><br>%{value:.1f} (%{percent})<extra></extra>",
            title=dict(
                text=f"<b>{d_total:.1f}</b>",
                font=dict(size=26, color="white"),
                position="middle center",
            ),
        ))
        fig_d.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=420,
            title=dict(text=f"<b>{sel_month} Revenue Mix</b>",
                       font=dict(size=22, color="white"), x=0),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=16, color="white"),
                orientation="h",
                x=0.5, y=-0.12,
                xanchor="center",
                yanchor="top",
            ),
            margin=dict(l=10, r=10, t=44, b=60),
        )
        st.plotly_chart(fig_d, use_container_width=True)


