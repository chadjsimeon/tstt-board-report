import streamlit as st

st.set_page_config(page_title="TSTT | DPDI", page_icon="💻", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data, get_month_order
from utils.charts import inject_css

inject_css()
data = load_all_data()
dpdi = data["DPDI"]
months = get_month_order(dpdi)

sel_month = st.sidebar.selectbox("Month", months, index=len(months) - 1)

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
dc_sub_text    = "Below AOP ↓" if dc_below_aop else f"{(total_dc - _dc_aop_ref) / abs(_dc_aop_ref) * 100:+.1f}% vs AOP"
dc_sub_color   = "#00ff88" if dc_below_aop else "#FF4444"

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:1.2rem 0 0.5rem 0">
  <div style="font-size:0.65rem;font-weight:700;color:#445566;text-transform:uppercase;
              letter-spacing:2.5px;margin-bottom:0.5rem">
    TSTT &nbsp;|&nbsp; BOARD OF DIRECTORS REPORT
  </div>
  <div style="font-size:2rem;font-weight:700;color:#ffffff;line-height:1.1;margin-bottom:0.4rem">
    DPDI Financial Overview
  </div>
  <div style="font-size:0.8rem;color:#7788aa">
    {sel_month} &nbsp;&nbsp;|&nbsp;&nbsp; All figures in TTD'000 unless stated
  </div>
</div>
<hr style="border:none;border-top:1px solid #1a1a2a;margin:0.9rem 0 1.2rem 0">
""", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
def _dpdi_card(label, value_str, sub_str, sub_color, accent, note=""):
    return (
        f'<div style="background:#161B22;border-radius:10px;padding:14px 16px;'
        f'border:1px solid #252545;border-top:2px solid {accent};height:100%;min-height:165px">'
        f'<div style="font-size:19px;color:#6677aa;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.2px;margin-bottom:5px">{label}</div>'
        f'<div style="font-size:42px;font-weight:800;color:white;margin-bottom:6px">{value_str}</div>'
        f'<div style="font-size:21px;color:{sub_color};font-weight:600;margin-bottom:3px">{sub_str or "&nbsp;"}</div>'
        f'<div style="font-size:15px;color:#556677;font-weight:600">{note or "&nbsp;"}</div>'
        f'</div>'
    )

K = 1000
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(_dpdi_card("Total Revenue",    f"{total_rev*K:,.0f}",       f"{rev_var_pct:+.1f}% vs AOP",    "#ef4444", "#ef4444"), unsafe_allow_html=True)
c2.markdown(_dpdi_card("Excl. e-GOVTT",   f"{excl_rev*K:,.0f}",        f"{excl_var_pct:+.1f}% vs AOP",   "#ef4444", "#ef4444"), unsafe_allow_html=True)
c3.markdown(_dpdi_card("Direct Costs",     f"{total_dc*K:,.0f}",        dc_sub_text,                       dc_sub_color, "#ff6b6b"), unsafe_allow_html=True)
c4.markdown(_dpdi_card("Gross Profit",     f"{total_gp*K:,.0f}",        f"GP Margin: {gp_margin:.1f}%",   "#8899bb", "#22c55e"), unsafe_allow_html=True)
c5.markdown(_dpdi_card("e-GOVTT Pipeline", f"{egovtt_pipeline*K:,.0f}", "Key opportunity →",              "#00ff88", "#00aa55"), unsafe_allow_html=True)
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
            font=dict(color="#aaaacc", size=16, family="Inter, sans-serif"),
            xanchor="left",
            yanchor="middle",
        )
        for prod, av, bv in zip(products_list, actual_vals, aop_vals)
    ]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=products_list, x=aop_vals, name="AOP Target",
        orientation="h",
        marker=dict(color="rgba(100,220,100,0.10)", line=dict(color="#55aa66", width=1.5)),
    ))
    fig_bar.add_trace(go.Bar(
        y=products_list, x=actual_vals, name="YTD Actual",
        orientation="h",
        marker_color="#00cc55",
    ))
    fig_bar.update_layout(
        barmode="overlay",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif", size=16),
        height=380,
        title=dict(text="<b>Revenue by Product — YTD vs AOP</b>",
                   font=dict(size=20, color="white"), x=0),
        xaxis=dict(gridcolor="#111111", tickfont=dict(color="#556677", size=15),
                   range=[0, max_x], showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(color="white", size=15), showgrid=False,
                   autorange="reversed"),
        margin=dict(l=10, r=160, t=70, b=30),
        annotations=annotations,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=15),
                    orientation="h", y=1.12, x=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    sel_idx   = months.index(sel_month)
    trend_months = months[max(0, sel_idx - 12): sel_idx + 1]
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
        line=dict(color="#55aa66", width=2, dash="dot"),
    ))
    fig_trend.add_trace(go.Scatter(
        x=trend_months, y=t_rev, name="Actual Revenue",
        mode="lines+markers",
        line=dict(color="#00cc55", width=2.5),
        marker=dict(size=6, color="#00cc55"),
    ))
    fig_trend.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif", size=16),
        height=380,
        title=dict(text="<b>Revenue Trend — 13 Months vs AOP</b>",
                   font=dict(size=20, color="white"), x=0),
        xaxis=dict(gridcolor="#111111", tickfont=dict(color="#556677", size=15),
                   showline=False, zeroline=False),
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=15),
                   zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=15),
                    orientation="h", y=1.12, x=0),
        margin=dict(l=10, r=10, t=70, b=30),
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Key commentary ────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#161B22;border:1px solid #0d2a2a;border-radius:6px;
            padding:1.2rem 1.6rem;margin-top:0.4rem">
  <div style="font-size:0.62rem;font-weight:700;color:#00aaaa;text-transform:uppercase;
              letter-spacing:2.2px;margin-bottom:0.85rem;border-left:3px solid #00aaaa;
              padding-left:8px">KEY COMMENTARY</div>
  <ul style="list-style:none;padding:0;margin:0;font-size:0.83rem;line-height:2">
    <li><span style="color:#00ff88;margin-right:10px">●</span>
      <b style="color:white">e-GOVTT</b>
      <span style="color:#cccccc"> — Primary revenue opportunity; AOP pipeline value represents
      key FY2026 activation target pending government contract finalization.</span></li>
    <li><span style="color:#FF8844;margin-right:10px">●</span>
      <b style="color:white">e-Tender</b>
      <span style="color:#cccccc"> — Most mature product, generating the largest share of YTD
      revenue with active deployment at Ministry of Finance.</span></li>
    <li><span style="color:#FF4444;margin-right:10px">●</span>
      <b style="color:white">EBITDA</b>
      <span style="color:#cccccc"> — Portfolio-wide EBITDA remains negative due to investment
      and go-to-market costs; positive run-rate expected from FY2027.</span></li>
    <li><span style="color:#4488ff;margin-right:10px">●</span>
      <b style="color:white">e-Health · e-Pay · e-Kiosk</b>
      <span style="color:#cccccc"> — In pilot or pre-revenue stage. Commercial launches
      targeted Q3–Q4 FY2026 to drive subscriber and revenue growth.</span></li>
  </ul>
</div>
""", unsafe_allow_html=True)

# ── Confidential footer ───────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:0.62rem;color:#333344;margin-top:2rem;
            padding-top:0.9rem;border-top:1px solid #111122;letter-spacing:2px">
  CONFIDENTIAL — FOR BOARD OF DIRECTORS USE ONLY
</div>
""", unsafe_allow_html=True)
