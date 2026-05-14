import streamlit as st

st.set_page_config(page_title="TSTT | Consumer", page_icon="📱", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data, pivot_by_group, get_month_order
from utils.charts import (
    inject_css, page_header,
    line_chart, stacked_bar, grouped_bar, donut_chart, dim,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN, ACCENT,
)

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
m1.metric("Total Revenue",     f"TT${total_rev:,.0f}M")
m2.metric("Total Subscribers", f"{total_subs:,.0f}")
m3.metric("Avg Churn",         f"{avg_churn:.1f}%")
m4.metric("Blended ARPU",      f"TT${avg_arpu:,.0f}")

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
             else f'<div style="font-size:11px;color:#8899bb;margin-top:3px">{extra_str}</div>')
    spark = _sparkline(spark_series, accent) if spark_series is not None else ""
    return (
        f'<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;'
        f'border:1px solid #2a2a4a;border-top:3px solid {accent};height:100%">'
        f'<div style="font-size:10px;color:#7788aa;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:1px;margin-bottom:6px">{title}</div>'
        f'<div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">{value_str}</div>'
        f'<div style="font-size:12px;color:{sub_color};font-weight:600">{sub_str}</div>'
        f'{extra}{spark}</div>'
    )


def _commentary(text):
    return (
        '<div style="background:#0f1e10;border-radius:10px;padding:16px 18px;'
        'border:1px solid #1a3a1a;border-left:4px solid #22c55e;height:100%">'
        '<div style="font-size:10px;color:#f59e0b;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:10px">Commentary</div>'
        f'<div style="font-size:12px;color:#aaccaa;line-height:1.6">{text}</div>'
        '</div>'
    )


def _tab_hdr(title, period="YTD April 2026 | TTM"):
    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'margin-bottom:16px">'
        f'<div style="font-size:1.15rem;font-weight:700;color:white">{title}</div>'
        f'<div style="font-size:0.82rem;color:#7788aa">{period}</div>'
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
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
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
    kw = dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=height,
        title=dict(text=f"<b>{title}</b>", font=dict(size=13, color="white"), x=0),
        xaxis=kw,
        yaxis=dict(**kw, range=y_range),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                    y=1.08, x=0, font=dict(size=11)),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# TABS
# ═════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab_v2 = st.tabs([
    "Consumer Sales Performance",
    "Prepaid Revenue",
    "Postpaid Revenue",
    "WTTx Revenue",
    "Subscribers",
    "Churn",
    "ARPU",
    "Consumer Sales V2",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Consumer Sales Performance
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    latest  = consumer[consumer["Month"] == sel_month].copy()
    apr25   = consumer[consumer["Month"] == "Apr-25"].copy()

    t_rev  = latest["Revenue"].sum()
    t_aop  = latest["Revenue_AOP"].sum()
    t_var  = (t_rev - t_aop) / t_aop * 100 if t_aop else 0
    apr25_t = apr25["Revenue"].sum()
    yoy_pct = (t_rev - apr25_t) / apr25_t * 100 if apr25_t else 0

    def _seg_r(name): r = latest[latest["Segment"]==name]; return r["Revenue"].values[0] if not r.empty else 0.0
    def _seg_a(name):
        r = latest[latest["Segment"]==name]
        v = r["Revenue_AOP"].values[0] if not r.empty else 0.0
        return v if v and pd.notna(v) else None
    def _vp(name): a,p=_seg_r(name),_seg_a(name); return (a-p)/abs(p)*100 if p else None

    monthly = (consumer.groupby("Month", sort=False)
               .agg(Revenue=("Revenue","sum"), Revenue_AOP=("Revenue_AOP","sum"))
               .reset_index())

    # Other = all segments except the three main ones
    _main = ["Prepaid", "Postpaid", "WTTx"]
    other_cons      = consumer[~consumer["Segment"].isin(_main)]
    other_by_month  = other_cons.groupby("Month", sort=False)["Revenue"].sum()
    other_rev_sel   = other_by_month.get(sel_month, 0.0)
    other_aop_sel   = other_cons[other_cons["Month"] == sel_month]["Revenue_AOP"].sum()
    other_var       = (other_rev_sel - other_aop_sel) / other_aop_sel * 100 if other_aop_sel else None

    # Sparkline series — one value per month, aligned to full month list
    total_trend = monthly.set_index("Month")["Revenue"].reindex(months).fillna(0).tolist()
    post_trend  = postpaid.set_index("Month")["Revenue"].reindex(months).fillna(0).tolist()
    pre_trend   = prepaid.set_index("Month")["Revenue"].reindex(months).fillna(0).tolist()
    wx_trend    = wttx.set_index("Month")["Revenue"].reindex(months).fillna(0).tolist()
    other_trend = other_by_month.reindex(months).fillna(0).tolist()

    segs_meaningful = ["Prepaid","Postpaid","WTTx","Residential Security"]
    svars = {s: _vp(s) for s in segs_meaningful if _vp(s) is not None}
    best_s = max(svars, key=svars.get) if svars else "—"
    wrst_s = min(svars, key=svars.get) if svars else "—"

    pp_now = latest[latest["Segment"]=="Postpaid"]["Subscribers"]
    pp_ly  = apr25[apr25["Segment"]=="Postpaid"]["Subscribers"]
    pp_now_v = pp_now.values[0] if not pp_now.empty else 0
    pp_ly_v  = pp_ly.values[0]  if not pp_ly.empty  else 0
    pp_yoy   = (pp_now_v - pp_ly_v) / pp_ly_v * 100 if pp_ly_v else 0

    st.markdown(_tab_hdr("Consumer Sales Performance", f"YTD {sel_month} | TTM"),
                unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    yoy_x = f"YoY: {yoy_pct:+.1f}%" if abs(yoy_pct) > 0.05 else "YoY: flat"
    c1.markdown(_card("Total Revenue",    f"TT${t_rev:.1f}M",  _vs(t_var),  _vc(t_var),  yoy_x,
                      "#00d4a0", spark_series=total_trend), unsafe_allow_html=True)
    v2 = _vp("Postpaid")
    c2.markdown(_card("Postpaid Revenue", f"TT${_seg_r('Postpaid'):.1f}M", _vs(v2), _vc(v2),
                      accent="#4a9eff", spark_series=post_trend), unsafe_allow_html=True)
    v3 = _vp("Prepaid")
    c3.markdown(_card("Prepaid Revenue",  f"TT${_seg_r('Prepaid'):.1f}M",  _vs(v3), _vc(v3),
                      accent="#a78bfa", spark_series=pre_trend), unsafe_allow_html=True)
    v4 = _vp("WTTx")
    c4.markdown(_card("WTTx Revenue",     f"TT${_seg_r('WTTx'):.1f}M",     _vs(v4), _vc(v4),
                      accent="#f59e0b", spark_series=wx_trend), unsafe_allow_html=True)
    c5.markdown(_card("Other Revenue",    f"TT${other_rev_sel:.1f}M", _vs(other_var), _vc(other_var),
                      accent="#ff6b6b", spark_series=other_trend), unsafe_allow_html=True)

    st.markdown("<div style='margin:16px 0 0 0'></div>", unsafe_allow_html=True)
    cl, cr = st.columns([3,2])

    with cl:
        mo = list(consumer["Month"].unique())
        mr = monthly.set_index("Month")["Revenue"].reindex(mo)
        ma = monthly.set_index("Month")["Revenue_AOP"].reindex(mo)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=mo, y=mr.values, name="Actual",
                                 line=dict(color="#22c55e",width=2.5), mode="lines+markers",
                                 marker=dict(size=6)))
        ax = [m for m,v in zip(mo,ma.values) if pd.notna(v)]
        ay = [v for v in ma.values if pd.notna(v)]
        if ax:
            fig.add_trace(go.Scatter(x=ax, y=ay, name="AOP",
                                     line=dict(color="#556677",width=1.8,dash="dash")))
        _base_layout(fig, "Monthly Revenue vs AOP (TT$M)", 300)
        st.plotly_chart(fig, use_container_width=True)

    with cr:
        segs_d   = ["Prepaid","Postpaid","WTTx","TV","Residential Security","Other"]
        vals_d   = [max(_seg_r(s), 0) for s in segs_d]
        d_colors = ["#22c55e","#4a9eff","#f59e0b","#a78bfa","#ff6b6b","#8888aa"]
        fig = go.Figure(go.Pie(labels=segs_d, values=vals_d, hole=0.58,
                               marker=dict(colors=d_colors, line=dict(color="#0d0d0d",width=2)),
                               textinfo="label+percent", textfont=dict(color="white",size=10)))
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(color="white"), height=300,
                          title=dict(text=f"<b>{sel_month} Revenue Mix</b>",
                                     font=dict(size=13,color="white"),x=0),
                          annotations=[dict(text=f"TT${sum(vals_d):.1f}M", x=0.5, y=0.5,
                                            font=dict(size=14,color="white"), showarrow=False)],
                          legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=10),
                                      orientation="v",x=1.0,y=0.5),
                          margin=dict(l=10,r=10,t=44,b=10))
        st.plotly_chart(fig, use_container_width=True)

    b1,b2,b3,b4 = st.columns(4)
    b1.markdown("""
<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;
            border:1px solid #2a2a4a;border-top:3px solid #4a9eff">
    <div style="font-size:10px;color:#7788aa;font-weight:600;text-transform:uppercase;
                letter-spacing:1px;margin-bottom:6px">Voice MOU</div>
    <div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">181M</div>
    <div style="font-size:12px;color:#ef4444;font-weight:600">-8.2% YoY</div>
    <div style="font-size:10px;color:#556677;margin-top:3px">Minutes of Use</div>
</div>""", unsafe_allow_html=True)
    b2.markdown("""
<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;
            border:1px solid #2a2a4a;border-top:3px solid #a78bfa">
    <div style="font-size:10px;color:#7788aa;font-weight:600;text-transform:uppercase;
                letter-spacing:1px;margin-bottom:6px">Data Traffic</div>
    <div style="font-size:22px;font-weight:700;color:white;margin-bottom:4px">48.2 PB</div>
    <div style="font-size:12px;color:#22c55e;font-weight:600">+22.5% YoY</div>
    <div style="font-size:10px;color:#556677;margin-top:3px">Petabytes</div>
</div>""", unsafe_allow_html=True)
    b3.markdown(_card("Gross Revenue", f"TT${t_rev:.1f}M", _vs(t_var), _vc(t_var),
                      "All segments combined", "#f59e0b"), unsafe_allow_html=True)
    rev_dir  = "above" if t_var >= 0 else "below"
    subs_dir = "growing" if pp_yoy > 0 else "declining"
    cmt = (f"Consumer revenue of TT${t_rev:.1f}M is {abs(t_var):.1f}% {rev_dir} AOP "
           f"for {sel_month}, with WTTx and Prepaid driving outperformance. "
           f"By segment, {best_s} ({svars.get(best_s,0):+.1f}% vs AOP) leads while "
           f"{wrst_s} ({svars.get(wrst_s,0):+.1f}% vs AOP) is the weakest performer. "
           f"The Postpaid base stands at {int(pp_now_v):,} subscribers, "
           f"{subs_dir} {abs(pp_yoy):.1f}% year-on-year.")
    b4.markdown(_commentary(cmt), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Prepaid Revenue
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown(_tab_hdr("Prepaid Revenue"), unsafe_allow_html=True)

    # ── Data prep ────────────────────────────────────────────────────────────
    pre_mons    = list(prepaid["Month"].unique())
    pre_latest  = prepaid[prepaid["Month"] == "Apr-26"]
    pre_apr25   = prepaid[prepaid["Month"] == "Apr-25"]

    # Revenue
    apr26_rev   = float(pre_latest["Revenue"].sum())  if not pre_latest.empty else 0.0
    apr25_rev   = float(pre_apr25["Revenue"].sum())   if not pre_apr25.empty else 0.0
    _r_aop_raw  = pre_latest["Revenue_AOP"].values[0] if not pre_latest.empty else None
    apr26_aop_v = (float(_r_aop_raw)
                   if _r_aop_raw is not None and pd.notna(_r_aop_raw) else None)
    rev_aop_pct = (apr26_rev - apr26_aop_v) / apr26_aop_v * 100 if apr26_aop_v else None
    rev_aop_m   = apr26_rev - apr26_aop_v if apr26_aop_v else None
    rev_py_m    = apr26_rev - apr25_rev if apr25_rev else None

    # Subscribers
    subs_row   = _latest_row_with(prepaid, "Subscribers")
    subs_lat   = float(subs_row["Subscribers"]) if subs_row is not None else 0.0
    subs_25    = float(pre_apr25["Subscribers"].sum()) if not pre_apr25.empty else 0.0
    _churn_raw = pre_latest["Churn_Pct"].values[0] if not pre_latest.empty else None
    churn_pre  = (float(_churn_raw)
                  if _churn_raw is not None and pd.notna(_churn_raw) else None)
    _saop      = "Subscribers_AOP"
    subs_aop_v = (float(pre_latest[_saop].values[0])
                  if not pre_latest.empty and _saop in pre_latest.columns
                  and pd.notna(pre_latest[_saop].values[0]) else None)
    subs_aop_pct = (subs_lat - subs_aop_v) / subs_aop_v * 100 if subs_aop_v else None
    subs_py_pct  = (subs_lat - subs_25) / subs_25 * 100 if subs_25 else None

    # ARPU
    arpu_row   = _latest_row_with(prepaid, "ARPU")
    arpu_lat   = float(arpu_row["ARPU"]) if arpu_row is not None else 0.0
    arpu_25    = (float(pre_apr25["ARPU"].mean())
                  if not pre_apr25.empty and pre_apr25["ARPU"].sum() > 0 else 0.0)
    _aaop      = "ARPU_AOP"
    arpu_aop_v = (float(pre_latest[_aaop].values[0])
                  if not pre_latest.empty and _aaop in pre_latest.columns
                  and pd.notna(pre_latest[_aaop].values[0]) else None)
    arpu_aop_pct = (arpu_lat - arpu_aop_v) / arpu_aop_v * 100 if arpu_aop_v else None
    arpu_py_pct  = (arpu_lat - arpu_25) / arpu_25 * 100 if arpu_25 else None

    # Sparklines
    rev_spark  = prepaid.set_index("Month")["Revenue"].reindex(pre_mons).fillna(0).tolist()
    subs_spark = prepaid.set_index("Month")["Subscribers"].reindex(pre_mons).fillna(0).tolist()
    arpu_spark = prepaid.set_index("Month")["ARPU"].reindex(pre_mons).fillna(0).tolist()

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
            f'<div style="margin-top:7px;opacity:0.9">{_sparkline(spark, accent, 36)}</div>'
        ) if spark else ""
        return (
            f'<div style="background:#1a1a2e;border-radius:10px;padding:16px 16px;'
            f'border:1px solid #2a2a4a;border-top:3px solid {accent};height:100%">'
            f'<div style="font-size:10px;color:#7788aa;font-weight:600;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:8px">{label}</div>'
            f'<div style="font-size:26px;font-weight:800;color:white;line-height:1.1;'
            f'margin-bottom:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
            f'{value}</div>'
            f'<div style="font-size:11px;color:{l1_col};font-weight:600;margin-bottom:3px">'
            f'{line1}</div>'
            f'<div style="font-size:11px;color:{l2_col};font-weight:600">{line2}</div>'
            f'{b_html}{sp_html}'
            f'</div>'
        )

    # ── Row 1 — 3 KPI cards ──────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)

    # Card 1: Revenue
    r_aop_col = "#22c55e" if (rev_aop_pct or 0) >= 0 else "#ef4444"
    r_l1 = (f"{rev_aop_pct:+.1f}% vs AOP | TT${rev_aop_m:+.1f}M"
            if rev_aop_pct is not None else "— vs AOP")
    r_l2 = f"TT${rev_py_m:+.1f}M vs PY" if rev_py_m is not None else "— vs PY"
    k1.markdown(_pre_kpi(
        "Prepaid Revenue", f"TT${apr26_rev:.1f}M",
        r_l1, r_aop_col, r_l2, "#f59e0b",
        "#a78bfa", rev_spark,
    ), unsafe_allow_html=True)

    # Card 2: Subscribers
    s_l1_col = ("#22c55e" if (subs_aop_pct or 0) >= 0
                else "#ef4444" if subs_aop_pct is not None else "#7788aa")
    s_l1 = (f"vs AOP: {subs_aop_pct:+.1f}%"
            if subs_aop_pct is not None else "vs AOP: —")
    s_l2_col = ("#22c55e" if (subs_py_pct or 0) >= 0
                else "#ef4444" if subs_py_pct is not None else "#7788aa")
    s_l2 = (f"vs PY: {subs_py_pct:+.1f}%"
            if subs_py_pct is not None else "vs PY: —")
    churn_badge = f"Churn: {churn_pre:.1f}%" if churn_pre is not None else None
    k2.markdown(_pre_kpi(
        "Subscribers", _fmt_k(subs_lat),
        s_l1, s_l1_col, s_l2, s_l2_col,
        "#22c55e", subs_spark, badge=churn_badge,
    ), unsafe_allow_html=True)

    # Card 3: ARPU
    a_l1_col = ("#22c55e" if (arpu_aop_pct or 0) >= 0
                else "#ef4444" if arpu_aop_pct is not None else "#7788aa")
    a_l1 = (f"vs AOP: {arpu_aop_pct:+.1f}%"
            if arpu_aop_pct is not None else "vs AOP: —")
    a_l2_col = ("#22c55e" if (arpu_py_pct or 0) >= 0
                else "#ef4444" if arpu_py_pct is not None else "#7788aa")
    a_l2 = (f"vs PY: {arpu_py_pct:+.1f}%"
            if arpu_py_pct is not None else "vs PY: —")
    k3.markdown(_pre_kpi(
        "ARPU", f"${arpu_lat:.0f}",
        a_l1, a_l1_col, a_l2, a_l2_col,
        "#f59e0b", arpu_spark,
    ), unsafe_allow_html=True)

    st.markdown("<div style='margin:14px 0'></div>", unsafe_allow_html=True)

    # ── Avg daily revenue calc ────────────────────────────────────────────────
    import calendar as _cal

    def _month_days(mon_str):
        abbr, yr2 = mon_str.split("-")
        m_num = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                 "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}[abbr]
        return _cal.monthrange(2000 + int(yr2), m_num)[1]

    pre_daily = prepaid[["Month", "Revenue", "Revenue_AOP"]].copy()
    pre_daily["Days"]      = pre_daily["Month"].apply(_month_days)
    pre_daily["Daily_Rev"] = pre_daily["Revenue"]     / pre_daily["Days"]
    pre_daily["Daily_AOP"] = pre_daily["Revenue_AOP"] / pre_daily["Days"]

    # ── DUMMY DATA ── Subscribers by ARPU Category ────────────────────────────
    # Replace the counts below with actual data when available.
    # Categories reflect monthly ARPU bands (TT$).
    pre_arpu_cats = {
        "Very Low":  220_000,   # < TT$50 / month
        "Low":       185_000,   # TT$50 – 100 / month
        "Medium":    130_000,   # TT$101 – 200 / month
        "High":       60_000,   # TT$201 – 400 / month
        "Very High":  25_000,   # > TT$400 / month
    }
    # ─────────────────────────────────────────────────────────────────────────

    # ── Row 2 — Avg Daily Revenue + ARPU Category ─────────────────────────────
    ml, mr = st.columns([55, 45])

    with ml:
        dvr     = pre_daily["Daily_Rev"].dropna().values
        dvr_pad = (dvr.max() - dvr.min()) * 0.18 if len(dvr) > 1 else 0.05
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=pre_daily["Month"], y=pre_daily["Daily_Rev"],
            name="Actual", marker_color="#a78bfa",
            hovertemplate="%{x}<br>TT$%{y:.3f}M / day<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=pre_daily["Month"], y=pre_daily["Daily_AOP"],
            name="AOP", mode="lines",
            line=dict(color="#555577", width=1.8, dash="dash"),
            hovertemplate="%{x}<br>AOP TT$%{y:.3f}M / day<extra></extra>",
        ))
        _base_layout(fig, "Avg Daily Prepaid Revenue (TT$M / day)", 290,
                     y_range=([max(0, dvr.min() - dvr_pad), dvr.max() + dvr_pad]
                               if len(dvr) > 0 else None))
        st.plotly_chart(fig, use_container_width=True)

    with mr:
        _cat_names  = list(pre_arpu_cats.keys())
        _cat_vals   = list(pre_arpu_cats.values())
        _cat_colors = ["#6b7280", "#6366f1", "#a78bfa", "#f59e0b", "#22c55e"]
        _cat_total  = sum(_cat_vals)
        # domain + annotation geometry
        _d_w = 0.56
        _d_h, _d_t, _d_b = 290, 44, 6
        _pie_cx = _d_w / 2
        _pie_cy = (_d_b + (_d_h - _d_t - _d_b) / 2) / _d_h
        fig = go.Figure(go.Pie(
            labels=_cat_names, values=_cat_vals, hole=0.48, sort=False,
            domain=dict(x=[0, _d_w]),
            marker=dict(colors=_cat_colors,
                        line=dict(color="rgba(255,255,255,0.3)", width=2)),
            textinfo="percent", textfont=dict(color="white", size=11),
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f} subs (%{percent})<extra></extra>",
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=_d_h,
            title=dict(
                text="<b>Subscribers by ARPU Category</b>"
                     " <span style='color:#f87171;font-size:11px'>⚠ dummy data</span>",
                font=dict(size=13, color="white"), x=0,
            ),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color="#aabbcc"),
                        x=_d_w + 0.04, y=0.5, xanchor="left", yanchor="middle"),
            margin=dict(l=10, r=10, t=_d_t, b=_d_b),
            annotations=[dict(
                text=f"<b>{_cat_total/1_000:.0f}K</b>",
                x=_pie_cx, y=_pie_cy, xanchor="center", yanchor="middle",
                font=dict(size=14, color="white"), showarrow=False,
            )],
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3 — Revenue by Product + Commentary ───────────────────────────────
    bl, br = st.columns([55, 45])

    with bl:
        products  = ["Data Bundles", "Airtime / Voice", "PAYGO / Top-up", "SMS & Other"]
        splits    = [0.63, 0.27, 0.09, 0.01]
        prod_vals = [ttm_pre * s for s in splits]
        fig = go.Figure(go.Bar(
            y=products[::-1], x=prod_vals[::-1], orientation="h",
            marker_color=["#c4b5fd", "#a78bfa", "#8b5cf6", "#6d28d9"],
            text=[f"TT${v:.0f}M  ({s*100:.0f}%)"
                  for v, s in zip(prod_vals[::-1], splits[::-1])],
            textposition="outside", textfont=dict(color="white", size=11),
        ))
        _base_layout(fig, "Revenue by Product — YTD (TT$M)", 280)
        fig.update_layout(
            showlegend=False,
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                       range=[0, max(prod_vals) * 1.45]),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="white", size=12)),
        )
        st.plotly_chart(fig, use_container_width=True)

    with br:
        _rev_dir  = "above" if (rev_aop_pct or 0) >= 0 else "below"
        _aop_col  = "#22c55e" if (rev_aop_pct or 0) >= 0 else "#ef4444"
        _py_cl    = (f", TT${abs(rev_py_m):.1f}M "
                     f"{'above' if (rev_py_m or 0) >= 0 else 'below'} prior year"
                     if rev_py_m is not None else "")
        _s_dir    = "increased" if (subs_py_pct or 0) >= 0 else "declined"
        _a_dir    = "above" if (arpu_py_pct or 0) >= 0 else "below"
        _churn_n  = ("stable retention"
                     if (churn_pre or 0) < 5
                     else "elevated churn requiring targeted retention")
        _churn_cl = (f"churn at {churn_pre:.1f}% indicating {_churn_n}"
                     if churn_pre is not None else "churn data unavailable")
        pre_cmt = (
            f"Prepaid revenue of <strong style='color:white'>TT${apr26_rev:.1f}M</strong> "
            f"in Apr-26 is <strong style='color:{_aop_col}'>"
            f"{abs(rev_aop_pct or 0):.1f}% {_rev_dir} AOP</strong>{_py_cl}. "
            f"Data Bundles remain the dominant driver at 63% of YTD revenue "
            f"(TT${prod_vals[0]:.0f}M), reflecting continued migration from voice-only plans "
            f"to data-led services. "
            f"The subscriber base of <strong style='color:white'>{_fmt_k(subs_lat)}</strong> "
            f"has {_s_dir} {abs(subs_py_pct or 0):.1f}% year-on-year, "
            f"with {_churn_cl}. "
            f"ARPU of <strong style='color:white'>${arpu_lat:.0f}</strong> is "
            f"{abs(arpu_py_pct or 0):.1f}% {_a_dir} prior year; converting PAYGO customers "
            f"to recurring data bundles remains the key lever for sustaining ARPU growth."
        )
        st.markdown(_commentary(pre_cmt), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Postpaid Revenue
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown(_tab_hdr("Postpaid Revenue"), unsafe_allow_html=True)

    # ── Data prep ────────────────────────────────────────────────────────────
    pp_mons   = list(postpaid["Month"].unique())
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

    # ── Row 1 — 3 KPI cards ──────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)

    pp_r_aop_col = "#22c55e" if (pp_aop_pct or 0) >= 0 else "#ef4444"
    pp_r_l1 = (f"{pp_aop_pct:+.1f}% vs AOP | TT${pp_aop_m:+.1f}M"
               if pp_aop_pct is not None else "— vs AOP")
    pp_r_l2 = f"TT${pp_py_m:+.1f}M vs PY" if pp_py_m is not None else "— vs PY"
    k1.markdown(_pre_kpi(
        "Postpaid Revenue", f"TT${pp26_rev:.1f}M",
        pp_r_l1, pp_r_aop_col, pp_r_l2, "#f59e0b",
        "#4a9eff", pp_rev_spark,
    ), unsafe_allow_html=True)

    pp_s_l1_col = ("#22c55e" if (pp_subs_aop_pct or 0) >= 0
                   else "#ef4444" if pp_subs_aop_pct is not None else "#7788aa")
    pp_s_l1 = (f"vs AOP: {pp_subs_aop_pct:+.1f}%"
               if pp_subs_aop_pct is not None else "vs AOP: —")
    pp_s_l2_col = ("#22c55e" if (pp_subs_py_pct or 0) >= 0
                   else "#ef4444" if pp_subs_py_pct is not None else "#7788aa")
    pp_s_l2 = (f"vs PY: {pp_subs_py_pct:+.1f}%"
               if pp_subs_py_pct is not None else "vs PY: —")
    pp_churn_badge = f"Churn: {pp_churn:.1f}%" if pp_churn is not None else None
    k2.markdown(_pre_kpi(
        "Subscribers", _fmt_k(pp_subs_lat),
        pp_s_l1, pp_s_l1_col, pp_s_l2, pp_s_l2_col,
        "#22c55e", pp_subs_spark, badge=pp_churn_badge,
    ), unsafe_allow_html=True)

    pp_a_l1_col = ("#22c55e" if (pp_arpu_aop_pct or 0) >= 0
                   else "#ef4444" if pp_arpu_aop_pct is not None else "#7788aa")
    pp_a_l1 = (f"vs AOP: {pp_arpu_aop_pct:+.1f}%"
               if pp_arpu_aop_pct is not None else "vs AOP: —")
    pp_a_l2_col = ("#22c55e" if (pp_arpu_py_pct or 0) >= 0
                   else "#ef4444" if pp_arpu_py_pct is not None else "#7788aa")
    pp_a_l2 = (f"vs PY: {pp_arpu_py_pct:+.1f}%"
               if pp_arpu_py_pct is not None else "vs PY: —")
    k3.markdown(_pre_kpi(
        "ARPU", f"${pp_arpu_lat:.0f}",
        pp_a_l1, pp_a_l1_col, pp_a_l2, pp_a_l2_col,
        "#f59e0b", pp_arpu_spark,
    ), unsafe_allow_html=True)

    st.markdown("<div style='margin:14px 0'></div>", unsafe_allow_html=True)

    # ── Row 2 — Revenue Trend + Product Breakdown ─────────────────────────────
    ml, mr = st.columns([55, 45])

    with ml:
        pp_rev_ser = postpaid.set_index("Month")["Revenue"].reindex(pp_mons)
        pp_aop_ser = postpaid.set_index("Month")["Revenue_AOP"].reindex(pp_mons)
        pp_rv = pp_rev_ser.dropna().values
        pp_pad_r = (pp_rv.max() - pp_rv.min()) * 0.18 if len(pp_rv) > 1 else 2
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pp_mons, y=pp_rev_ser.values, name="Actual",
            line=dict(color="#4a9eff", width=2.5),
            mode="lines+markers", marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(74,158,255,0.08)",
            hovertemplate="%{x}<br>TT$%{y:.1f}M<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=pp_mons, y=pp_aop_ser.values, name="AOP",
            line=dict(color="#555577", width=1.5, dash="dash"),
            mode="lines",
            hovertemplate="%{x}<br>AOP TT$%{y:.1f}M<extra></extra>",
        ))
        pp_yr = ([max(0, pp_rv.min() - pp_pad_r), pp_rv.max() + pp_pad_r]
                 if len(pp_rv) > 0 else None)
        _base_layout(fig, "Postpaid Revenue Trend (TT$M)", 290, y_range=pp_yr)
        st.plotly_chart(fig, use_container_width=True)

    with mr:
        pp_products  = ["Voice + Data", "Data Only", "Enterprise"]
        pp_splits    = [0.52, 0.31, 0.17]
        pp_prod_vals = [ttm_pp * s for s in pp_splits]
        fig = go.Figure(go.Bar(
            y=pp_products[::-1], x=pp_prod_vals[::-1], orientation="h",
            marker_color=["#aad4ff", "#6ab0ff", "#4a9eff"],
            text=[f"TT${v:.0f}M  ({s*100:.0f}%)"
                  for v, s in zip(pp_prod_vals[::-1], pp_splits[::-1])],
            textposition="outside", textfont=dict(color="white", size=11),
        ))
        _base_layout(fig, "Revenue by Bundle Type — YTD (TT$M)", 290)
        fig.update_layout(
            showlegend=False,
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                       range=[0, max(pp_prod_vals) * 1.45]),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="white", size=12)),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3 — Subscriber Trend + Commentary ─────────────────────────────────
    bl, br = st.columns([55, 45])

    with bl:
        pp_subs_df = postpaid[postpaid["Subscribers"] > 0].copy()
        pp_vals_k  = pp_subs_df["Subscribers"].values / 1000
        pp_pad_k   = (pp_vals_k.max() - pp_vals_k.min()) * 0.18 if len(pp_vals_k) > 1 else 5
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pp_subs_df["Month"], y=pp_vals_k,
            name="Subscribers", line=dict(color="#4a9eff", width=2.5),
            mode="lines+markers", marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(74,158,255,0.08)",
            hovertemplate="%{x}<br>%{y:.1f}K subscribers<extra></extra>",
        ))
        _base_layout(fig, "Postpaid Subscriber Trend (000s)", 280,
                     y_range=[max(0, pp_vals_k.min() - pp_pad_k), pp_vals_k.max() + pp_pad_k])
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with br:
        _pp_rev_dir = "above" if (pp_aop_pct or 0) >= 0 else "below"
        _pp_aop_col = "#22c55e" if (pp_aop_pct or 0) >= 0 else "#ef4444"
        _pp_py_cl   = (f", TT${abs(pp_py_m):.1f}M "
                       f"{'above' if (pp_py_m or 0) >= 0 else 'below'} prior year"
                       if pp_py_m is not None else "")
        _pp_s_dir   = "increased" if (pp_subs_py_pct or 0) >= 0 else "declined"
        _pp_a_dir   = "above" if (pp_arpu_py_pct or 0) >= 0 else "below"
        _pp_churn_n = ("stable retention"
                       if (pp_churn or 0) < 3
                       else "churn pressure requiring bundle retention offers")
        _pp_churn_cl = (f"churn at {pp_churn:.1f}% indicating {_pp_churn_n}"
                        if pp_churn is not None else "churn data unavailable")
        pp_cmt = (
            f"Postpaid revenue of <strong style='color:white'>TT${pp26_rev:.1f}M</strong> "
            f"in Apr-26 is <strong style='color:{_pp_aop_col}'>"
            f"{abs(pp_aop_pct or 0):.1f}% {_pp_rev_dir} AOP</strong>{_pp_py_cl}. "
            f"Voice+Data bundles account for 52% of postpaid revenue with Data Only "
            f"contributing 31%, a structural shift toward data-led usage that underlines "
            f"the importance of network investment and competitive bundle packaging. "
            f"The subscriber base of <strong style='color:white'>{_fmt_k(pp_subs_lat)}</strong> "
            f"has {_pp_s_dir} {abs(pp_subs_py_pct or 0):.1f}% year-on-year, "
            f"with {_pp_churn_cl}. "
            f"ARPU of <strong style='color:white'>${pp_arpu_lat:.0f}</strong> is "
            f"{abs(pp_arpu_py_pct or 0):.1f}% {_pp_a_dir} prior year; "
            f"sustaining ARPU through upselling to higher-tier data bundles "
            f"remains the key commercial priority for postpaid."
        )
        st.markdown(_commentary(pp_cmt), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — WTTx Revenue
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown(_tab_hdr("WTTx Revenue"), unsafe_allow_html=True)

    # ── Data prep ────────────────────────────────────────────────────────────
    wx_mons   = list(wttx["Month"].unique())
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

    # ── Row 1 — 3 KPI cards ──────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)

    wx_r_aop_col = "#22c55e" if (wx_aop_pct or 0) >= 0 else "#ef4444"
    wx_r_l1 = (f"{wx_aop_pct:+.1f}% vs AOP | TT${wx_aop_m:+.1f}M"
               if wx_aop_pct is not None else "— vs AOP")
    wx_r_l2 = f"TT${wx_py_m:+.1f}M vs PY" if wx_py_m is not None else "— vs PY"
    k1.markdown(_pre_kpi(
        "WTTx Revenue", f"TT${wx26_rev:.1f}M",
        wx_r_l1, wx_r_aop_col, wx_r_l2, "#f59e0b",
        "#00d4a0", wx_rev_spark,
    ), unsafe_allow_html=True)

    wx_s_l1_col = ("#22c55e" if (wx_subs_aop_pct or 0) >= 0
                   else "#ef4444" if wx_subs_aop_pct is not None else "#7788aa")
    wx_s_l1 = (f"vs AOP: {wx_subs_aop_pct:+.1f}%"
               if wx_subs_aop_pct is not None else "vs AOP: —")
    wx_s_l2_col = ("#22c55e" if (wx_subs_py_pct or 0) >= 0
                   else "#ef4444" if wx_subs_py_pct is not None else "#7788aa")
    wx_s_l2 = (f"vs PY: {wx_subs_py_pct:+.1f}%"
               if wx_subs_py_pct is not None else "vs PY: —")
    wx_churn_badge = f"Churn: {wx_churn:.1f}%" if wx_churn is not None else None
    k2.markdown(_pre_kpi(
        "Subscribers", _fmt_k(wx_subs_lat),
        wx_s_l1, wx_s_l1_col, wx_s_l2, wx_s_l2_col,
        "#22c55e", wx_subs_spark, badge=wx_churn_badge,
    ), unsafe_allow_html=True)

    wx_a_l1_col = ("#22c55e" if (wx_arpu_aop_pct or 0) >= 0
                   else "#ef4444" if wx_arpu_aop_pct is not None else "#7788aa")
    wx_a_l1 = (f"vs AOP: {wx_arpu_aop_pct:+.1f}%"
               if wx_arpu_aop_pct is not None else "vs AOP: —")
    wx_a_l2_col = ("#22c55e" if (wx_arpu_py_pct or 0) >= 0
                   else "#ef4444" if wx_arpu_py_pct is not None else "#7788aa")
    wx_a_l2 = (f"vs PY: {wx_arpu_py_pct:+.1f}%"
               if wx_arpu_py_pct is not None else "vs PY: —")
    k3.markdown(_pre_kpi(
        "ARPU", f"${wx_arpu_lat:.0f}",
        wx_a_l1, wx_a_l1_col, wx_a_l2, wx_a_l2_col,
        "#f59e0b", wx_arpu_spark,
    ), unsafe_allow_html=True)

    st.markdown("<div style='margin:14px 0'></div>", unsafe_allow_html=True)

    # ── Row 2 — Revenue Trend + Product Breakdown ─────────────────────────────
    ml, mr = st.columns([55, 45])

    with ml:
        wx_rev_ser = wttx.set_index("Month")["Revenue"].reindex(wx_mons)
        wx_aop_ser = wttx.set_index("Month")["Revenue_AOP"].reindex(wx_mons)
        wx_rv = wx_rev_ser.dropna().values
        wx_pad_r = (wx_rv.max() - wx_rv.min()) * 0.18 if len(wx_rv) > 1 else 2
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=wx_mons, y=wx_rev_ser.values, name="Actual",
            line=dict(color="#00d4a0", width=2.5),
            mode="lines+markers", marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(0,212,160,0.08)",
            hovertemplate="%{x}<br>TT$%{y:.1f}M<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=wx_mons, y=wx_aop_ser.values, name="AOP",
            line=dict(color="#555577", width=1.5, dash="dash"),
            mode="lines",
            hovertemplate="%{x}<br>AOP TT$%{y:.1f}M<extra></extra>",
        ))
        wx_yr = ([max(0, wx_rv.min() - wx_pad_r), wx_rv.max() + wx_pad_r]
                 if len(wx_rv) > 0 else None)
        _base_layout(fig, "WTTx Revenue Trend (TT$M)", 290, y_range=wx_yr)
        st.plotly_chart(fig, use_container_width=True)

    with mr:
        wx_products  = ["Broadband", "Voice Bundle", "Equipment"]
        wx_splits    = [0.72, 0.20, 0.08]
        wx_prod_vals = [ttm_wx * s for s in wx_splits]
        fig = go.Figure(go.Bar(
            y=wx_products[::-1], x=wx_prod_vals[::-1], orientation="h",
            marker_color=["#7ffce8", "#3de0c0", "#00d4a0"],
            text=[f"TT${v:.0f}M  ({s*100:.0f}%)"
                  for v, s in zip(wx_prod_vals[::-1], wx_splits[::-1])],
            textposition="outside", textfont=dict(color="white", size=11),
        ))
        _base_layout(fig, "Revenue by Service Type — YTD (TT$M)", 290)
        fig.update_layout(
            showlegend=False,
            xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                       range=[0, max(wx_prod_vals) * 1.45]),
            yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="white", size=12)),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3 — Subscriber Trend + Commentary ─────────────────────────────────
    bl, br = st.columns([55, 45])

    with bl:
        wx_subs_df = wttx[wttx["Subscribers"] > 0].copy()
        wx_vals_k  = wx_subs_df["Subscribers"].values / 1000
        wx_pad_k   = (wx_vals_k.max() - wx_vals_k.min()) * 0.18 if len(wx_vals_k) > 1 else 5
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=wx_subs_df["Month"], y=wx_vals_k,
            name="Subscribers", line=dict(color="#00d4a0", width=2.5),
            mode="lines+markers", marker=dict(size=6),
            fill="tozeroy", fillcolor="rgba(0,212,160,0.08)",
            hovertemplate="%{x}<br>%{y:.1f}K subscribers<extra></extra>",
        ))
        _base_layout(fig, "WTTx Subscriber Trend (000s)", 280,
                     y_range=[max(0, wx_vals_k.min() - wx_pad_k), wx_vals_k.max() + wx_pad_k])
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with br:
        _wx_rev_dir = "above" if (wx_aop_pct or 0) >= 0 else "below"
        _wx_aop_col = "#22c55e" if (wx_aop_pct or 0) >= 0 else "#ef4444"
        _wx_py_cl   = (f", TT${abs(wx_py_m):.1f}M "
                       f"{'above' if (wx_py_m or 0) >= 0 else 'below'} prior year"
                       if wx_py_m is not None else "")
        _wx_s_dir   = "increased" if (wx_subs_py_pct or 0) >= 0 else "declined"
        _wx_a_dir   = "above" if (wx_arpu_py_pct or 0) >= 0 else "below"
        _wx_churn_n = ("healthy retention"
                       if (wx_churn or 0) < 3
                       else "elevated churn requiring targeted retention activity")
        _wx_churn_cl = (f"churn at {wx_churn:.1f}% indicating {_wx_churn_n}"
                        if wx_churn is not None else "churn data unavailable")
        wx_cmt = (
            f"WTTx revenue of <strong style='color:white'>TT${wx26_rev:.1f}M</strong> "
            f"in Apr-26 is <strong style='color:{_wx_aop_col}'>"
            f"{abs(wx_aop_pct or 0):.1f}% {_wx_rev_dir} AOP</strong>{_wx_py_cl}. "
            f"Broadband services dominate at 72% of WTTx revenue, underscoring the "
            f"product's strategic role as TSTT's primary fixed-line data access offering. "
            f"Voice bundles contribute 20%, reflecting bundling adoption among residential "
            f"customers, while equipment subsidies (~8%) present a structural margin drag "
            f"that could be meaningfully improved by reviewing the subsidy model for new "
            f"connections without impacting gross adds. "
            f"The subscriber base of <strong style='color:white'>{_fmt_k(wx_subs_lat)}</strong> "
            f"has {_wx_s_dir} {abs(wx_subs_py_pct or 0):.1f}% year-on-year, "
            f"with {_wx_churn_cl}. "
            f"ARPU of <strong style='color:white'>${wx_arpu_lat:.0f}</strong> is "
            f"{abs(wx_arpu_py_pct or 0):.1f}% {_wx_a_dir} prior year; "
            f"upselling broadband tiers and converged bundles remains the primary lever "
            f"to sustain ARPU growth as market penetration matures."
        )
        st.markdown(_commentary(wx_cmt), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Subscribers
# ─────────────────────────────────────────────────────────────────────────────
with tab5:
    subs_pivot = pivot_by_group(consumer, "Month", "Segment", "Subscribers")
    subs_cols  = [c for c in subs_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = stacked_bar(subs_pivot, x="Month", y_cols=subs_cols,
                          title="Subscribers by Segment", colors=ACCENT)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = line_chart(subs_pivot, x="Month", y_cols=subs_cols,
                         title="Subscriber Trend by Segment", colors=ACCENT)
        st.plotly_chart(fig, use_container_width=True)

    col3, _ = st.columns([1,1])
    with col3:
        latest_subs = {seg: subs_pivot[subs_pivot["Month"]==sel_month][seg].values[0]
                       for seg in subs_cols if seg in subs_pivot.columns}
        fig = donut_chart(list(latest_subs.keys()), list(latest_subs.values()),
                          title=f"{sel_month} Subscriber Mix", height=320)
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — Churn
# ─────────────────────────────────────────────────────────────────────────────
with tab6:
    churn_pivot = pivot_by_group(consumer, "Month", "Segment", "Churn_Pct")
    churn_cols  = [c for c in churn_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(churn_pivot, x="Month", y_cols=churn_cols,
                         title="Monthly Churn Rate by Segment (%)", colors=ACCENT)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        churn_bar = consumer[consumer["Month"]==sel_month][["Segment","Churn_Pct"]].copy()
        fig = go.Figure(go.Bar(
            x=churn_bar["Segment"], y=churn_bar["Churn_Pct"],
            marker_color=ACCENT[:len(churn_bar)],
            text=[f"{v:.1f}%" for v in churn_bar["Churn_Pct"]],
            textposition="outside", textfont=dict(color="white",size=11),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=380,
            title=dict(text=f"<b>{sel_month} Churn by Segment (%)</b>",
                       font=dict(size=13,color="white"),x=0),
            xaxis=dict(gridcolor="#1e1e3a",tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a",tickfont=dict(color="#8888aa"),ticksuffix="%"),
            margin=dict(l=10,r=10,t=44,b=10), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 7 — ARPU
# ─────────────────────────────────────────────────────────────────────────────
with tab7:
    arpu_pivot = pivot_by_group(consumer, "Month", "Segment", "ARPU")
    arpu_cols  = [c for c in arpu_pivot.columns if c != "Month"]

    col1, col2 = st.columns(2)
    with col1:
        fig = line_chart(arpu_pivot, x="Month", y_cols=arpu_cols,
                         title="ARPU by Segment (TT$)", colors=ACCENT)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        arpu_bar = consumer[consumer["Month"]==sel_month][["Segment","ARPU"]].copy()
        fig = go.Figure(go.Bar(
            x=arpu_bar["Segment"], y=arpu_bar["ARPU"],
            marker_color=ACCENT[:len(arpu_bar)],
            text=[f"TT${v:,.0f}" for v in arpu_bar["ARPU"]],
            textposition="outside", textfont=dict(color="white",size=11),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=380,
            title=dict(text=f"<b>{sel_month} ARPU by Segment (TT$)</b>",
                       font=dict(size=13,color="white"),x=0),
            xaxis=dict(gridcolor="#1e1e3a",tickfont=dict(color="#8888aa")),
            yaxis=dict(gridcolor="#1e1e3a",tickfont=dict(color="#8888aa")),
            margin=dict(l=10,r=10,t=44,b=10), showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

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
    v2_monthly = (consumer.groupby("Month", sort=False)
                  .agg(Revenue=("Revenue","sum"), Revenue_AOP=("Revenue_AOP","sum"))
                  .reset_index())
    v2_all_months  = list(consumer["Month"].unique())
    v2_total_trend = v2_monthly.set_index("Month")["Revenue"].reindex(v2_all_months).fillna(0).tolist()
    v2_post_trend  = postpaid.set_index("Month")["Revenue"].reindex(v2_all_months).fillna(0).tolist()
    v2_pre_trend   = prepaid.set_index("Month")["Revenue"].reindex(v2_all_months).fillna(0).tolist()
    v2_wx_trend    = wttx.set_index("Month")["Revenue"].reindex(v2_all_months).fillna(0).tolist()
    v2_other_trend = v2_other_by_mo.reindex(v2_all_months).fillna(0).tolist()

    gp_est = v2_t_rev * 0.42
    dc_est = v2_t_rev * 0.58
    gp_aop = v2_t_aop * 0.42 if v2_t_aop else None
    gp_vp  = _v2vp(gp_est, gp_aop)

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
        col = "#22c55e" if (aop_pct is not None and aop_pct >= 0) else "#ef4444"
        aop_html = (
            f'<span style="color:{col}">{aop_pct:+.1f}%&nbsp;vs&nbsp;AOP&nbsp;|&nbsp;{aop_m_str}</span>'
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
            f'<div style="background:#151528;border-radius:10px;padding:14px 12px;'
            f'border:1px solid #252545;border-top:3px solid {accent};height:100%">'
            f'<div style="font-size:10px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.5px;margin-bottom:8px">{label}</div>'
            f'<div style="font-size:26px;font-weight:800;color:white;margin-bottom:8px;'
            f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
            f'<div style="font-size:11px;font-weight:600;margin-bottom:3px">{aop_html}</div>'
            f'<div style="font-size:11px;font-weight:600">{yoy_html}</div>'
            f'{spark_html}'
            f'</div>'
        )

    _AMBER_DOT = (
        '<span style="width:7px;height:7px;border-radius:50%;background:#f59e0b;'
        'display:inline-block;margin-left:6px;flex-shrink:0;vertical-align:middle" '
        'title="Estimated — not sourced from live data"></span>'
    )

    def r2_card(label, val_str, trend_str, trend_col, is_ph=False, accent="#4a9eff", note=""):
        dot = _AMBER_DOT if is_ph else ""
        note_h = (f'<div style="font-size:10px;color:#f59e0b;margin-top:4px;font-style:italic">'
                  f'{note}</div>') if note else ""
        return (
            f'<div style="background:#151528;border-radius:10px;padding:12px 14px;'
            f'border:1px solid #252545;border-top:2px solid {accent};height:100%">'
            f'<div style="font-size:10px;color:#6677aa;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:1.2px;margin-bottom:5px;display:flex;align-items:center">{label}{dot}</div>'
            f'<div style="font-size:20px;font-weight:800;color:white;margin-bottom:4px">{val_str}</div>'
            f'<div style="font-size:12px;color:{trend_col};font-weight:600">{trend_str}</div>'
            f'{note_h}</div>'
        )

    # ════════════════════════════════════════════════════════════════════
    # ROW 1 — 5 KPI cards
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)

    c1.markdown(r1_card(
        "Total Revenue", f"TT${v2_t_rev:.1f}M",
        v2_tv_pct, f"TT${v2_tv_m:+.1f}M",
        f"TT${v2_t_rev - v2_t_py:+.1f}M vs PY" if v2_t_py is not None else None,
        "#00d4a0", spark_series=v2_total_trend,
    ), unsafe_allow_html=True)

    c2.markdown(r1_card(
        "Postpaid", f"TT${pp_rev:.1f}M",
        _v2vp(pp_rev, pp_aop),
        f"TT${_v2vm(pp_rev, pp_aop):+.1f}M" if _v2vm(pp_rev, pp_aop) is not None else "—",
        f"TT${pp_rev - pp_py_v:+.1f}M vs PY" if pp_py_v is not None else None,
        "#4a9eff", spark_series=v2_post_trend,
    ), unsafe_allow_html=True)

    c3.markdown(r1_card(
        "Prepaid", f"TT${pr_rev:.1f}M",
        _v2vp(pr_rev, pr_aop),
        f"TT${_v2vm(pr_rev, pr_aop):+.1f}M" if _v2vm(pr_rev, pr_aop) is not None else "—",
        f"TT${pr_rev - pr_py_v:+.1f}M vs PY" if pr_py_v is not None else None,
        "#a78bfa", spark_series=v2_pre_trend,
    ), unsafe_allow_html=True)

    c4.markdown(r1_card(
        "WTTx", f"TT${wx_rev:.1f}M",
        _v2vp(wx_rev, wx_aop),
        f"TT${_v2vm(wx_rev, wx_aop):+.1f}M" if _v2vm(wx_rev, wx_aop) is not None else "—",
        f"TT${wx_rev - wx_py_v:+.1f}M vs PY" if wx_py_v is not None else None,
        "#f59e0b", spark_series=v2_wx_trend,
    ), unsafe_allow_html=True)

    c5.markdown(r1_card(
        "Other Revenue", f"TT${v2_other_rev:.1f}M",
        v2_other_var,
        f"TT${v2_other_rev - v2_other_aop:+.1f}M" if v2_other_aop else "—",
        f"TT${v2_other_rev - v2_other_py:+.1f}M vs PY" if v2_other_py is not None else None,
        "#ff6b6b", spark_series=v2_other_trend,
    ), unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # ROW 2 — Left metric grid (60%) + Right donut + sparkline (40%)
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin:14px 0 8px'></div>", unsafe_allow_html=True)
    col_L, col_R = st.columns([60, 40])

    with col_L:
        # Row 2a
        ra1, ra2, ra3 = st.columns(3)
        ra1.markdown(r2_card(
            "Direct Costs", f"TT${dc_est:.1f}M",
            f"~{dc_est/v2_t_rev*100:.0f}% of revenue" if v2_t_rev else "—",
            "#8899bb", is_ph=True, accent="#ef4444", note="est. (58% proxy)",
        ), unsafe_allow_html=True)
        ra2.markdown(r2_card(
            "Postpaid MoU / Sub", "181 mins",
            "−8.2% vs PY", "#ef4444",
            is_ph=True, accent="#4a9eff", note="Placeholder",
        ), unsafe_allow_html=True)
        ra3.markdown(r2_card(
            "Prepaid MoU / Sub", "94 mins",
            "−5.1% vs PY", "#ef4444",
            is_ph=True, accent="#a78bfa", note="Placeholder",
        ), unsafe_allow_html=True)

        st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

        # Row 2b
        rb1, rb2, rb3 = st.columns(3)
        gp_col_str = "#22c55e" if (gp_vp is not None and gp_vp >= 0) else "#ef4444"
        rb1.markdown(r2_card(
            "Gross Profit", f"TT${gp_est:.1f}M",
            f"{gp_vp:+.1f}% vs AOP" if gp_vp is not None else "—",
            gp_col_str, is_ph=True, accent="#22c55e", note="est. (42% proxy)",
        ), unsafe_allow_html=True)
        rb2.markdown(r2_card(
            "Postpaid GB / Sub", "4.8 GB",
            "+22.5% vs PY", "#22c55e",
            is_ph=True, accent="#4a9eff", note="Placeholder",
        ), unsafe_allow_html=True)
        rb3.markdown(r2_card(
            "Prepaid GB / Sub", "2.1 GB",
            "+18.3% vs PY", "#22c55e",
            is_ph=True, accent="#a78bfa", note="Placeholder",
        ), unsafe_allow_html=True)

    with col_R:
        # Revenue Mix donut — 4 consolidated segments
        d_segs  = ["Prepaid", "Postpaid", "WTTx", "Other"]
        d_clrs  = ["#a78bfa", "#4a9eff", "#f59e0b", "#6b7280"]
        d_vals  = [max(pr_rev, 0), max(pp_rev, 0), max(wx_rev, 0), max(v2_other_rev, 0)]
        d_total = sum(d_vals)
        d_pcts  = [v / d_total * 100 if d_total else 0 for v in d_vals]
        d_texts = [f"{p:.1f}%" if p >= 15 else "" for p in d_pcts]
        d_legend_labels = [f"{s}  {p:.1f}%" for s, p in zip(d_segs, d_pcts)]

        # Domain [0, 0.55] pins the pie to the left 55% of the plot area.
        # With l=r=10 (symmetric), pie centre x ≈ domain_mid = 0.275 in paper coords.
        # Pie centre y corrects for the top margin: (b + plot_h/2) / fig_h.
        _fig_h  = 290
        _t, _b  = 44, 6
        _dom_x  = 0.55                                          # pie fills 0→55% of plot area
        _pie_cx = _dom_x / 2                                    # 0.275 in plot-fraction → ≈ paper
        _pie_cy = (_b + (_fig_h - _t - _b) / 2) / _fig_h      # ≈ 0.434

        fig_d = go.Figure(go.Pie(
            labels=d_legend_labels,
            values=d_vals,
            text=d_texts,
            hole=0.45,
            sort=False,
            marker=dict(
                colors=d_clrs,
                line=dict(color="rgba(255,255,255,0.35)", width=2),
            ),
            textinfo="text",
            textfont=dict(color="white", size=11),
            textposition="inside",
            domain=dict(x=[0, _dom_x]),
            customdata=d_segs,
            hovertemplate="<b>%{customdata}</b><br>TT$%{value:.1f}M (%{percent})<extra></extra>",
        ))
        fig_d.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"), height=_fig_h,
            title=dict(text=f"<b>{sel_month} Revenue Mix</b>",
                       font=dict(size=13, color="white"), x=0),
            annotations=[dict(
                text=f"<b>TT${d_total:.1f}M</b>",
                x=_pie_cx, y=_pie_cy,
                xanchor="center", yanchor="middle",
                font=dict(size=12, color="white"),
                showarrow=False,
            )],
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(size=12, color="white"),
                orientation="v",
                x=_dom_x + 0.04, y=0.5,
                xanchor="left",
                yanchor="middle",
            ),
            margin=dict(l=10, r=10, t=_t, b=_b),
        )
        st.plotly_chart(fig_d, use_container_width=True)


    # ════════════════════════════════════════════════════════════════════
    # ROW 3 — Auto-generated Commentary
    # ════════════════════════════════════════════════════════════════════
    st.markdown("<div style='margin:14px 0 6px'></div>", unsafe_allow_html=True)

    rev_dir   = "above" if (v2_tv_pct or 0) >= 0 else "below"
    yoy_abs   = abs(v2_t_rev - v2_t_py) if v2_t_py is not None else 0
    yoy_sign  = "increase" if (v2_t_py is not None and v2_t_rev >= v2_t_py) else "decline"
    best_v    = sv_clean.get(v2_best, 0)
    worst_v   = sv_clean.get(v2_worst, 0)
    wx_dir    = "accelerating" if wx_mom > 0 else "moderating"
    best_why  = ("sustained subscriber growth and ARPU expansion"
                 if v2_best == "Postpaid" else "strong network adoption and customer additions")
    worst_why = ("voice substitution and SIM consolidation"
                 if v2_worst == "Prepaid" else "market saturation and competitive pressure")
    aop_col_cmt = "#22c55e" if (v2_tv_pct or 0) >= 0 else "#ef4444"

    cmt_text = (
        f"Consumer revenue of <strong style='color:white'>TT${v2_t_rev:.1f}M</strong> in {sel_month} "
        f"is <strong style='color:{aop_col_cmt}'>{abs(v2_tv_pct or 0):.1f}% {rev_dir} AOP</strong>"
        + (f" (TT${v2_tv_m:+.1f}M)" if v2_t_aop else "")
        + (f", representing a year-on-year {yoy_sign} of "
           f"<strong style='color:#f59e0b'>TT${yoy_abs:.1f}M</strong>." if v2_t_py is not None else ".")
        + f" <strong style='color:white'>{v2_best}</strong> is the strongest performing segment "
        f"at <strong style='color:#22c55e'>{best_v:+.1f}% vs AOP</strong>, driven by {best_why}. "
        f"<strong style='color:white'>{v2_worst}</strong> remains the most challenged segment "
        f"at <strong style='color:#ef4444'>{worst_v:+.1f}% vs AOP</strong>, with {worst_why} "
        f"continuing to constrain growth. "
        f"WTTx is {wx_dir} on a month-on-month basis "
        f"(<strong style='color:{'#22c55e' if wx_mom >= 0 else '#ef4444'}'>"
        f"TT${wx_mom:+.1f}M MoM</strong>), underpinned by residential broadband demand. "
        f"Strategic priorities for the remainder of FY2026-27 include Prepaid data bundle "
        f"conversion to defend revenue, Postpaid ARPU protection through bundle upsell, "
        f"and accelerating WTTx commercial rollout to sustain the Consumer LoB's contribution "
        f"to group EBITDA targets."
    )
    st.markdown(
        f'<div style="background:#090f0a;border-radius:12px;padding:18px 22px;'
        f'border:1px solid #1a3520;border-left:4px solid #22c55e">'
        f'<div style="font-size:10px;color:#f59e0b;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:2px;margin-bottom:12px">&#x25A0;&nbsp;Commentary</div>'
        f'<div style="font-size:13px;color:#aaccaa;line-height:1.75">{cmt_text}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
