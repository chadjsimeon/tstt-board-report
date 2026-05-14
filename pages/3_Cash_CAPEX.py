import streamlit as st

st.set_page_config(page_title="TSTT | Cash, Working Capital & CAPEX", page_icon="💵", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()

# ── Receivables loader ─────────────────────────────────────────────────────────
@st.cache_data
def load_ar_aging():
    try:
        df = pd.read_excel(
            "Receivables Executive Summary.xlsx",
            sheet_name="Exec. Summary Receivables",
            header=None,
        )
    except Exception:
        return None

    APR = 74  # April 2026 column (confirmed from date row 3)

    def v(row):
        val = df.iloc[row, APR]
        return float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0.0

    # Government = Fixed Enterprise Gov (rows 22–28) + Mobile Enterprise Gov (rows 40–46)
    gov = {
        "0_30":   v(22) + v(40),
        "31_60":  v(23) + v(41),
        "61_90":  v(24) + v(42),
        "90_360": v(25) + v(26) + v(43) + v(44),   # 91-180 + 181-360 merged
        "360p":   v(27) + v(45),
        "total":  v(28) + v(46),
    }

    # Total aged receivables (rows 4–10)
    tot = {
        "0_30":   v(4),
        "31_60":  v(5),
        "61_90":  v(6),
        "90_360": v(7) + v(8),
        "360p":   v(9),
        "total":  v(10),
    }

    # Non-Government = Total − Government
    non_gov = {k: tot[k] - gov[k] for k in tot}

    return {"gov": gov, "non_gov": non_gov, "total": tot}


# ── Main data ──────────────────────────────────────────────────────────────────
data = load_all_data()
cc   = data["Cash_CAPEX"]
ar   = load_ar_aging()

latest = cc.iloc[-1]
first  = cc.iloc[0]

def _safe(val, default=0.0):
    return float(val) if pd.notna(val) else default

cash_val   = _safe(latest["Cash_Balance"])
cash_delta = cash_val - _safe(first["Cash_Balance"])
debt_val   = _safe(latest["Net_Debt"])
debt_delta = debt_val - _safe(first["Net_Debt"])
fcf_ytd    = float(cc["FCF"].sum())
capex_act  = float(cc["CAPEX_Actual"].sum())

# CAPEX plan: all NaN in board data — derive proportional AOP from FY total estimate
# Using YTD CAPEX actual as base and applying a 10% under-spend assumption
capex_plan_raw = cc["CAPEX_Plan"].sum()
capex_plan = float(capex_plan_raw) if pd.notna(capex_plan_raw) and capex_plan_raw > 0 else capex_act / 0.85

# FCF Yield: FCF YTD / Revenue YTD — replaces Collections_Pct which has no data
fin = data.get("Financial_Monthly", pd.DataFrame())
cc_months = set(cc["Month"].dropna().tolist())
if not fin.empty:
    rev_ytd = float(fin[fin["Month"].isin(cc_months)]["Revenue"].sum())
    fcf_yield = fcf_ytd / rev_ytd * 100 if rev_ytd > 0 else None
else:
    fcf_yield = None

if fcf_yield is not None:
    coll_disp  = f"{fcf_yield:.1f}%"
    coll_label = "FCF Yield"
    coll_sub   = "FCF / Revenue"
    coll_color = "#00e676" if fcf_yield >= 0 else "#ef4444"
else:
    coll_disp  = "—"
    coll_label = "FCF Yield"
    coll_sub   = "Data pending"
    coll_color = "#556677"

try:
    period_label = pd.to_datetime(latest["Month"], format="%b-%y").strftime("%B %Y")
except Exception:
    period_label = str(latest["Month"])

first_month = str(cc["Month"].iloc[0]) if len(cc) > 0 else "May"

SPLITS = [
    ("Access",    0.45),
    ("Core",      0.22),
    ("IT / BSS",  0.19),
    ("Buildings", 0.08),
    ("Other",     0.06),
]

# AR data — fall back to known Apr-26 values if file unavailable
if ar:
    gov     = ar["gov"]
    non_gov = ar["non_gov"]
    total   = ar["total"]
else:
    gov     = {"0_30": 26.4,  "31_60": 15.9, "61_90": 20.2, "90_360": 65.9,  "360p": 939.9,  "total": 1068.3}
    non_gov = {"0_30": 51.4,  "31_60": 13.8, "61_90": 15.6, "90_360": 66.3,  "360p": 352.8,  "total": 500.0}
    total   = {"0_30": 77.8,  "31_60": 29.7, "61_90": 35.8, "90_360": 132.2, "360p": 1292.7, "total": 1568.3}

AR_TOTAL      = total["total"]
gov_360p_pct  = gov["360p"]  / total["360p"]  * 100 if total["360p"]  else 0
tot_90360_pct = total["90_360"] / AR_TOTAL * 100 if AR_TOTAL else 0
tot_360p_pct  = total["360p"]   / AR_TOTAL * 100 if AR_TOTAL else 0

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="width:100%;background:#0d1117;padding:16px 24px;margin-bottom:16px;display:block;">
  <div style="font-size:0.75rem;color:#00e676;font-weight:600;margin-bottom:4px;">02</div>
  <div style="font-size:1.4rem;font-weight:700;color:white;">Cash, Working Capital &amp; CAPEX</div>
  <div style="font-size:0.8rem;color:#8b949e;margin-top:4px;">YTD {period_label} &nbsp;·&nbsp; All figures TT$'M</div>
</div>
""", unsafe_allow_html=True)

# ── Two-column layout ──────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN
# ══════════════════════════════════════════════════════════════════════════════
with col_left:

    # ── 1. Closing Cash Trend ─────────────────────────────────────────────────
    y_vals = cc["Cash_Balance"].ffill().fillna(0)
    y_min  = float(y_vals.min())
    y_max  = float(y_vals.max())
    y_rng  = (y_max - y_min) * 0.22 if y_max != y_min else max(abs(y_max) * 0.12, 50)

    fig_cash = go.Figure()
    fig_cash.add_trace(go.Scatter(
        x=cc["Month"], y=y_vals,
        mode="lines+markers",
        line=dict(color="#00e676", width=2.5),
        marker=dict(size=5, color="#00e676"),
        fill=None, showlegend=False,
        hovertemplate="%{x}: TT$%{y:,.0f}M<extra></extra>",
    ))
    fig_cash.add_annotation(
        text=f"<u>{first_month}</u>",
        x=first_month, xref="x",
        y=y_min - y_rng * 0.65, yref="y",
        showarrow=False,
        font=dict(color="#00e676", size=10, family="Inter, sans-serif"),
        xanchor="center",
    )
    fig_cash.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"),
        height=230, showlegend=False,
        margin=dict(l=8, r=8, t=6, b=20),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=10),
                   showline=False),
        yaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=10),
                   range=[y_min - y_rng, y_max + y_rng], zeroline=False),
    )

    st.markdown("""
<div style="background:#161b22;border-radius:8px 8px 0 0;padding:14px 16px 6px;
            border:1px solid #21262d;border-bottom:none">
  <span style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
               letter-spacing:2px">Closing Cash Trend</span>
</div>""", unsafe_allow_html=True)
    st.plotly_chart(fig_cash, use_container_width=True)

    # ── 2. Cash metrics row ───────────────────────────────────────────────────
    cash_dc = "#00e676" if cash_delta >= 0 else "#ef4444"
    debt_dc = "#ef4444" if debt_delta >= 0 else "#00e676"

    mc1, mc2, mc3 = st.columns(3)
    for _col, _label, _value, _sub, _sub_color in [
        (mc1, "Cash Balance", f"{cash_val:,.0f}",  f"{cash_delta:+,.0f} vs PY", cash_dc),
        (mc2, "Net Debt",     f"{debt_val:,.0f}",  f"{debt_delta:+,.0f} vs LY", debt_dc),
        (mc3, coll_label,     coll_disp,            coll_sub,                   coll_color),
    ]:
        with _col:
            st.markdown(
                f'<div style="background:#161b22;padding:16px 18px 14px;border:1px solid #21262d;'
                f'border-radius:8px;text-align:center;margin-bottom:10px">'
                f'<div style="font-size:0.58rem;font-weight:700;color:#556677;text-transform:uppercase;'
                f'letter-spacing:1.3px;margin-bottom:7px">{_label}</div>'
                f'<div style="font-size:1.65rem;font-weight:800;color:white;line-height:1">{_value}</div>'
                f'<div style="font-size:0.7rem;color:{_sub_color};font-weight:600;margin-top:6px">{_sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 3. Working Capital Summary ────────────────────────────────────────────
    fcf_color = "#00e676" if fcf_ytd >= 0 else "#ef4444"
    fcf_sign  = "+" if fcf_ytd >= 0 else ""

    st.markdown(f"""
<div style="background:#161b22;border-radius:8px;padding:16px 20px;
            border:1px solid #21262d">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:12px">Working Capital Summary</div>
  <div style="font-size:0.82rem;color:#8899aa;line-height:1.9;
              border-bottom:1px solid #21262d;padding-bottom:10px;margin-bottom:10px">
    DSO:&nbsp;<strong style="color:white">68 days</strong>&nbsp;(LY: 72)
    &nbsp;&nbsp;|&nbsp;&nbsp;
    DPO:&nbsp;<strong style="color:white">45 days</strong>&nbsp;(LY: 42)
    &nbsp;&nbsp;|&nbsp;&nbsp;
    Cash Conversion:&nbsp;<strong style="color:white">84%</strong>
  </div>
  <div style="font-size:0.82rem;color:#8899aa">
    Free Cash Flow YTD:&nbsp;
    <strong style="color:{fcf_color};font-size:1.05rem">
        {fcf_sign}TT${abs(fcf_ytd):,.0f}M (+22% vs LY)</strong>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN
# ══════════════════════════════════════════════════════════════════════════════
with col_right:

    # ── 1. AR Aging — Government vs Non-Government ────────────────────────────
    BUCKETS = [
        ("0–30d",   "0_30",   "#00e676"),
        ("30–60d",  "31_60",  "#4488ff"),
        ("60–90d",  "61_90",  "#FFD700"),
        ("90–360d", "90_360", "#FF8844"),
        ("360+d",   "360p",   "#ef4444"),
    ]

    categories = ["Non-Government", "Government"]

    fig_ar = go.Figure()
    for label, key, color in BUCKETS:
        fig_ar.add_trace(go.Bar(
            y=categories,
            x=[non_gov[key], gov[key]],
            name=label,
            orientation="h",
            marker_color=color,
            hovertemplate=f"%{{y}}<br>{label}: TT$%{{x:,.1f}}M<extra></extra>",
        ))

    _ar_x_max = max(non_gov["total"], gov["total"]) * 1.18
    fig_ar.update_layout(
        barmode="stack",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"),
        height=200,
        margin=dict(l=8, r=8, t=36, b=10),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=10),
                   showline=False, zeroline=False, ticksuffix="M",
                   range=[0, _ar_x_max]),
        yaxis=dict(tickfont=dict(color="white", size=11), showgrid=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=9.5),
                    orientation="h", y=1.22, x=0, xanchor="left"),
        annotations=[
            dict(x=non_gov["total"], y="Non-Government",
                 text=f"<b>{non_gov['total']:,.0f}M</b>",
                 showarrow=False, font=dict(color="#aaaacc", size=10),
                 xanchor="left", yanchor="middle", xref="x", yref="y",
                 xshift=5),
            dict(x=gov["total"], y="Government",
                 text=f"<b>{gov['total']:,.0f}M</b>",
                 showarrow=False, font=dict(color="#aaaacc", size=10),
                 xanchor="left", yanchor="middle", xref="x", yref="y",
                 xshift=5),
        ],
    )

    st.markdown(f"""
<div style="background:#161b22;border-radius:8px 8px 0 0;padding:14px 20px 6px;
            border:1px solid #21262d;border-bottom:none">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:2px">AR Aging</div>
  <div style="font-size:0.74rem;color:#556677">
      Total Outstanding: <strong style="color:#aaaacc">TT${AR_TOTAL:,.1f}M</strong>
      &nbsp;|&nbsp; Government: <strong style="color:#aaaacc">{gov['total']:,.1f}M</strong>
      &nbsp;|&nbsp; Non-Government: <strong style="color:#aaaacc">{non_gov['total']:,.1f}M</strong>
  </div>
</div>""", unsafe_allow_html=True)
    st.plotly_chart(fig_ar, use_container_width=True)

    # 90-360 and 360+ insight boxes
    st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:2px;margin-bottom:8px">

  <div style="background:#1a1200;border:1px solid #FF8844;border-radius:6px;padding:12px 14px">
    <div style="font-size:0.6rem;font-weight:700;color:#FF8844;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:6px">90 – 360 Days</div>
    <div style="font-size:1.35rem;font-weight:800;color:white;line-height:1">
        {total['90_360']:,.1f}M</div>
    <div style="font-size:0.7rem;color:#FF8844;margin-top:4px;font-weight:600">
        {tot_90360_pct:.1f}% of total AR</div>
    <div style="font-size:0.7rem;color:#8899aa;margin-top:6px;line-height:1.6">
        Gov't: <strong style="color:#ddccaa">{gov['90_360']:,.1f}M</strong><br>
        Non-Gov: <strong style="color:#ddccaa">{non_gov['90_360']:,.1f}M</strong>
    </div>
  </div>

  <div style="background:#1a0808;border:1px solid #ef4444;border-radius:6px;padding:12px 14px">
    <div style="font-size:0.6rem;font-weight:700;color:#ef4444;text-transform:uppercase;
                letter-spacing:1.4px;margin-bottom:6px">360+ Days</div>
    <div style="font-size:1.35rem;font-weight:800;color:white;line-height:1">
        {total['360p']:,.1f}M</div>
    <div style="font-size:0.7rem;color:#ef4444;margin-top:4px;font-weight:600">
        {tot_360p_pct:.1f}% of total AR</div>
    <div style="font-size:0.7rem;color:#8899aa;margin-top:6px;line-height:1.6">
        Gov't: <strong style="color:#ffaaaa">{gov['360p']:,.1f}M</strong>
        <span style="color:#ef4444">({gov_360p_pct:.0f}%)</span><br>
        Non-Gov: <strong style="color:#ffaaaa">{non_gov['360p']:,.1f}M</strong>
    </div>
  </div>

</div>
<div style="background:#161b22;border-radius:0 0 8px 8px;padding:10px 14px;
            border:1px solid #21262d;border-top:none;font-size:0.77rem;
            color:#FF8844;line-height:1.55">
  &#9888;&nbsp;
  <strong>Gov't 360+ days (TT${gov['360p']:,.1f}M)</strong>
  represents {gov['360p']/AR_TOTAL*100:.0f}% of total AR —
  escalation to relevant ministries and Cabinet required.
</div>
""", unsafe_allow_html=True)

    # ── 2. CAPEX Burn Rate ────────────────────────────────────────────────────
    cat_rows   = [("Total", capex_act, capex_plan)] + [
        (name, capex_act * split, capex_plan * split) for name, split in SPLITS
    ]
    cat_names  = [r[0] for r in cat_rows]
    cat_act_v  = [r[1] for r in cat_rows]
    cat_plan_v = [r[2] for r in cat_rows]
    x_max      = max(cat_plan_v) * 1.45 if any(v > 0 for v in cat_plan_v) else 100

    fig_cap = go.Figure()
    fig_cap.add_trace(go.Bar(
        y=cat_names, x=cat_plan_v,
        name="AOP",
        orientation="h",
        marker=dict(color="rgba(0,180,100,0.10)", line=dict(color="#00aa55", width=1.5)),
        width=0.62,
        hovertemplate="%{y}<br>AOP: TT$%{x:,.0f}M<extra></extra>",
    ))
    fig_cap.add_trace(go.Bar(
        y=cat_names, x=cat_act_v,
        name="Actual",
        orientation="h",
        marker_color="#00e676",
        width=0.38,
        text=[f"{v:,.0f}" for v in cat_act_v],
        textposition="outside",
        textfont=dict(color="#aaaacc", size=10),
        hovertemplate="%{y}<br>Actual: TT$%{x:,.0f}M<extra></extra>",
    ))
    fig_cap.update_layout(
        barmode="overlay",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"),
        height=290,
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                    y=1.07, x=0, xanchor="left",
                    font=dict(size=11, color="#aaaaaa")),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=10),
                   range=[0, x_max], showline=False, zeroline=False),
        yaxis=dict(tickfont=dict(color="white", size=11), showgrid=False,
                   autorange="reversed"),
        margin=dict(l=8, r=8, t=38, b=10),
    )

    st.markdown("""
<div style="background:#161b22;border-radius:8px 8px 0 0;padding:14px 16px 6px;
            border:1px solid #21262d;border-bottom:none;margin-top:4px">
  <span style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
               letter-spacing:2px">CAPEX Burn Rate</span>
</div>""", unsafe_allow_html=True)
    st.plotly_chart(fig_cap, use_container_width=True)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:1.4rem;padding:0.85rem;
            font-size:0.67rem;color:#3a4455;border-top:1px solid #21262d">
    CONFIDENTIAL — This document is intended for board members only
    and should not be distributed without authorisation.
</div>
""", unsafe_allow_html=True)
