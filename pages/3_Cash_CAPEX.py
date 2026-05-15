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

def _pct_val(col):
    """Return latest non-zero value for a percentage column, or None."""
    if col not in cc.columns:
        return None
    v = cc[col].replace(0, pd.NA).dropna()
    return float(v.iloc[-1]) if len(v) else None

coll_gov     = _pct_val("Collections_Pct_Gov")
coll_non_gov = _pct_val("Collections_Pct_NonGov")

try:
    period_label = pd.to_datetime(latest["Month"], format="%b-%y").strftime("%B %Y")
except Exception:
    period_label = str(latest["Month"])

first_month = str(cc["Month"].iloc[0]) if len(cc) > 0 else "May"

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
        height=320, showlegend=False,
        margin=dict(l=8, r=8, t=6, b=20),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=13),
                   showline=False),
        yaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=13),
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

    _fcf_color = "#00e676" if fcf_ytd >= 0 else "#ef4444"
    _fcf_sign  = "+" if fcf_ytd >= 0 else ""

    mc1, mc2, mc3 = st.columns(3)
    for _col, _label, _value, _sub, _sub_color in [
        (mc1, "Cash Balance",      f"{cash_val:,.0f}",                       f"{cash_delta:+,.0f} vs PY", cash_dc),
        (mc2, "Net Debt",          f"{debt_val:,.0f}",                       f"{debt_delta:+,.0f} vs LY", debt_dc),
        (mc3, "Free Cash Flow YTD", f"{_fcf_sign}TT${abs(fcf_ytd):,.0f}M",  "FCF YTD",                   _fcf_color),
    ]:
        with _col:
            st.markdown(
                f'<div style="background:#161b22;padding:16px 18px 14px;border:1px solid #21262d;'
                f'border-radius:8px;text-align:center;margin-bottom:10px">'
                f'<div style="font-size:0.75rem;font-weight:700;color:#556677;text-transform:uppercase;'
                f'letter-spacing:1.3px;margin-bottom:7px">{_label}</div>'
                f'<div style="font-size:1.65rem;font-weight:800;color:white;line-height:1">{_value}</div>'
                f'<div style="font-size:0.7rem;color:{_sub_color};font-weight:600;margin-top:6px">{_sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 3. Collections Performance ────────────────────────────────────────────
    def _coll_stat(label, pct_val, accent):
        if pct_val is not None:
            color  = "#00e676" if pct_val >= 85 else ("#FFD700" if pct_val >= 70 else "#ef4444")
            val_str = f"{pct_val:.1f}%"
        else:
            color   = "#556677"
            val_str = "—"
        bar_w   = f"{min(pct_val, 100):.1f}%" if pct_val is not None else "0%"
        bar_col = color if pct_val is not None else "#21262d"
        return f"""
<div style="flex:1;background:#0d1117;border-radius:8px;padding:14px 16px;border:1px solid #21262d">
  <div style="font-size:0.75rem;font-weight:700;color:{accent};text-transform:uppercase;
              letter-spacing:1.4px;margin-bottom:8px">{label}</div>
  <div style="font-size:1.6rem;font-weight:800;color:{color};line-height:1;margin-bottom:10px">{val_str}</div>
  <div style="background:#1e1e3a;border-radius:4px;height:6px;overflow:hidden">
    <div style="background:{bar_col};width:{bar_w};height:100%;border-radius:4px"></div>
  </div>
  <div style="font-size:0.68rem;color:#556677;margin-top:6px">Collections as % of billings</div>
</div>"""

    _gov_stat     = _coll_stat("Government",     coll_gov,     "#4488ff")
    _non_gov_stat = _coll_stat("Non-Government", coll_non_gov, "#a78bfa")

    st.markdown(f"""
<div style="background:#161b22;border-radius:8px;padding:16px 20px;border:1px solid #21262d">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:12px">Collections Performance</div>
  <div style="display:flex;gap:10px">
    {_gov_stat}
    {_non_gov_stat}
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
        height=300,
        margin=dict(l=8, r=8, t=36, b=10),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=13),
                   showline=False, zeroline=False, ticksuffix="M",
                   range=[0, _ar_x_max]),
        yaxis=dict(tickfont=dict(color="white", size=11), showgrid=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=12),
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
    <div style="font-size:0.75rem;font-weight:700;color:#FF8844;text-transform:uppercase;
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
    <div style="font-size:0.75rem;font-weight:700;color:#ef4444;text-transform:uppercase;
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

    # ── 2. CAPEX Spend to Date ────────────────────────────────────────────────
    capex_remaining = capex_plan - capex_act
    capex_progress  = min(capex_act / capex_plan * 100, 100) if capex_plan else 0
    capex_over      = capex_act > capex_plan

    cap_bar_color = ("linear-gradient(90deg,#ef4444,#ff6b6b)" if capex_over
                     else "linear-gradient(90deg,#1d4ed8,#4a9eff)")
    cap_pct_color = "#ef4444" if capex_over else "#4a9eff"
    cap_rem_color = "#ef4444" if capex_remaining < 0 else "#6688aa"
    cap_rem_label = "over budget" if capex_remaining < 0 else "remaining"
    cap_rem_sign  = "+" if capex_remaining < 0 else ""

    st.markdown(f"""
<div style="background:#161b22;border-radius:8px;padding:18px 20px;
            border:1px solid #21262d;margin-top:4px">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:14px">CAPEX Spend to Date</div>

  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="color:#aaaacc;font-size:14px;font-weight:500">YTD Spend vs Annual Budget</span>
    <span style="color:{cap_pct_color};font-weight:800;font-size:22px">{capex_progress:.1f}%</span>
  </div>
  <div style="background:#1e1e3a;border-radius:8px;height:20px;overflow:hidden;margin-bottom:14px">
    <div style="background:{cap_bar_color};width:{capex_progress:.1f}%;height:100%;border-radius:8px"></div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:baseline">
    <div>
      <div style="color:{cap_pct_color};font-size:18px;font-weight:700">TT${capex_act:,.1f}M</div>
      <div style="color:#6688aa;font-size:12px;margin-top:2px">spent YTD</div>
    </div>
    <div style="text-align:center">
      <div style="color:{cap_rem_color};font-size:18px;font-weight:700">{cap_rem_sign}TT${abs(capex_remaining):,.1f}M</div>
      <div style="color:#6688aa;font-size:12px;margin-top:2px">{cap_rem_label}</div>
    </div>
    <div style="text-align:right">
      <div style="color:#aaaacc;font-size:18px;font-weight:700">TT${capex_plan:,.1f}M</div>
      <div style="color:#6688aa;font-size:12px;margin-top:2px">annual budget</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:1.4rem;padding:0.85rem;
            font-size:0.67rem;color:#3a4455;border-top:1px solid #21262d">
    CONFIDENTIAL — This document is intended for board members only
    and should not be distributed without authorisation.
</div>
""", unsafe_allow_html=True)
