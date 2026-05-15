import streamlit as st

st.set_page_config(page_title="TSTT | DPDI", page_icon="💻", layout="wide")

import plotly.graph_objects as go
from utils.data_loader import load_all_data, get_month_order
from utils.charts import inject_css

inject_css()
data = load_all_data()
dpdi = data["DPDI"]
months = get_month_order(dpdi)

# ── YTD aggregates ────────────────────────────────────────────────────────────
ytd = dpdi.groupby("Product")[
    ["Revenue", "Revenue_AOP", "Gross_Profit", "EBITDA", "Direct_Costs"]
].sum()

total_rev    = ytd["Revenue"].sum()
total_aop    = ytd["Revenue_AOP"].sum()
total_gp     = ytd["Gross_Profit"].sum()
total_dc     = ytd["Direct_Costs"].sum()
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

ebitda_display = f"({abs(total_ebitda):.1f}M)" if total_ebitda < 0 else f"{total_ebitda:.1f}M"
dc_below_aop   = total_dc < total_aop
dc_sub_text    = "Below AOP ↓" if dc_below_aop else f"{(total_dc - total_aop) / abs(total_aop) * 100:+.1f}% vs AOP"
dc_sub_color   = "#00ff88" if dc_below_aop else "#FF4444"

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("""
<div style="padding:1.2rem 0 0.5rem 0">
  <div style="font-size:0.65rem;font-weight:700;color:#445566;text-transform:uppercase;
              letter-spacing:2.5px;margin-bottom:0.5rem">
    TSTT &nbsp;|&nbsp; BOARD OF DIRECTORS REPORT
  </div>
  <div style="font-size:2rem;font-weight:700;color:#ffffff;line-height:1.1;margin-bottom:0.4rem">
    DPDI Financial Overview
  </div>
  <div style="font-size:0.8rem;color:#7788aa">
    YTD March 2026 &nbsp;&nbsp;|&nbsp;&nbsp; All figures in TT$M unless stated
  </div>
</div>
<hr style="border:none;border-top:1px solid #1a1a2a;margin:0.9rem 0 1.2rem 0">
""", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:1.5rem">

  <div style="background:#0d0d0d;padding:15px 14px 12px;border-bottom:2px solid #cc2222">
    <div style="font-size:0.75rem;font-weight:700;color:#445566;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:7px">TOTAL REVENUE</div>
    <div style="font-size:1.4rem;font-weight:700;color:#FF4444;line-height:1.1">
        TT${total_rev:.1f}M</div>
    <div style="font-size:0.7rem;color:#FF4444;margin-top:5px;font-weight:600">
        {rev_var_pct:+.1f}% vs AOP</div>
  </div>

  <div style="background:#0d0d0d;padding:15px 14px 12px;border-bottom:2px solid #cc2222">
    <div style="font-size:0.75rem;font-weight:700;color:#445566;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:7px">EXCL. E-GOVTT REV</div>
    <div style="font-size:1.4rem;font-weight:700;color:#FF4444;line-height:1.1">
        TT${excl_rev:.1f}M</div>
    <div style="font-size:0.7rem;color:#FF4444;margin-top:5px;font-weight:600">
        {excl_var_pct:+.1f}% vs AOP</div>
  </div>

  <div style="background:#0d0d0d;padding:15px 14px 12px;border-bottom:2px solid #444444">
    <div style="font-size:0.75rem;font-weight:700;color:#445566;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:7px">GROSS PROFIT</div>
    <div style="font-size:1.4rem;font-weight:700;color:#ffffff;line-height:1.1">
        TT${total_gp:.1f}M</div>
    <div style="font-size:0.7rem;color:#aaaaaa;margin-top:5px">GP Margin: {gp_margin:.1f}%</div>
  </div>

  <div style="background:#0d0d0d;padding:15px 14px 12px;border-bottom:2px solid #444444">
    <div style="font-size:0.75rem;font-weight:700;color:#445566;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:7px">DIRECT COSTS</div>
    <div style="font-size:1.4rem;font-weight:700;color:#ffffff;line-height:1.1">
        TT${total_dc:.1f}M</div>
    <div style="font-size:0.7rem;color:{dc_sub_color};margin-top:5px;font-weight:600">
        {dc_sub_text}</div>
  </div>

  <div style="background:#0d0d0d;padding:15px 14px 12px;border-bottom:2px solid #cc2222">
    <div style="font-size:0.75rem;font-weight:700;color:#445566;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:7px">EBITDA</div>
    <div style="font-size:1.4rem;font-weight:700;color:#FF4444;line-height:1.1">
        {ebitda_display}</div>
    <div style="font-size:0.7rem;color:#556677;margin-top:5px">OpEx-heavy BU</div>
  </div>

  <div style="background:#0d0d0d;padding:15px 14px 12px;border-bottom:2px solid #00aa55">
    <div style="font-size:0.75rem;font-weight:700;color:#445566;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:7px">E-GOVTT PIPELINE</div>
    <div style="font-size:1.4rem;font-weight:700;color:#00ff88;line-height:1.1">
        TT${egovtt_pipeline:.1f}M</div>
    <div style="font-size:0.7rem;color:#00ff88;margin-top:5px;font-weight:600">
        Key opportunity →</div>
  </div>

</div>
""", unsafe_allow_html=True)

# ── Two-column charts ─────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    products_list = ytd.index.tolist()
    actual_vals   = [ytd.loc[p, "Revenue"]     for p in products_list]
    aop_vals      = [ytd.loc[p, "Revenue_AOP"] for p in products_list]

    safe_max = max(max(actual_vals + [0.001]), max(aop_vals + [0.001]))
    max_x    = safe_max * 1.6

    annotations = [
        dict(
            x=max(av, bv) + safe_max * 0.06,
            y=prod,
            text=f"<b>{av:.1f}M</b> / {bv:.1f}M",
            showarrow=False,
            font=dict(color="#aaaacc", size=10, family="Inter, sans-serif"),
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
        font=dict(color="white", family="Inter, sans-serif", size=11),
        height=380,
        title=dict(text="<b>Revenue by Product — YTD vs AOP (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#111111", tickfont=dict(color="#556677", size=13),
                   range=[0, max_x], showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(color="white", size=11), showgrid=False,
                   autorange="reversed"),
        margin=dict(l=10, r=130, t=44, b=30),
        annotations=annotations,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=12),
                    orientation="h", y=-0.1, x=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    excl = dpdi[dpdi["Product"] != "e-GOVTT"].groupby("Month")[
        ["Revenue", "Revenue_AOP"]
    ].sum().reset_index()
    excl["_ord"] = excl["Month"].apply(lambda m: months.index(m) if m in months else 99)
    excl = excl.sort_values("_ord").drop(columns=["_ord"])

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=excl["Month"], y=excl["Revenue"],
        name="Actual excl. e-GOVTT",
        mode="lines+markers",
        line=dict(color="#00ff88", width=2.5),
        marker=dict(size=6, color="#00ff88"),
    ))
    fig_line.add_trace(go.Scatter(
        x=excl["Month"], y=excl["Revenue_AOP"],
        name="AOP excl. e-GOVTT",
        mode="lines+markers",
        line=dict(color="#FFD700", width=2, dash="dash"),
        marker=dict(size=5, color="#FFD700"),
    ))
    fig_line.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif", size=11),
        height=380,
        title=dict(text="<b>Monthly Revenue — Actual vs AOP excl. e-GOVTT (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#111111", tickfont=dict(color="#556677", size=13)),
        yaxis=dict(gridcolor="#111111", tickfont=dict(color="#556677", size=13),
                   ticksuffix="M"),
        margin=dict(l=10, r=10, t=44, b=30),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=12),
                    orientation="h", y=-0.1, x=0),
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ── Key commentary ────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#030f0f;border:1px solid #0d2a2a;border-radius:6px;
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
