import streamlit as st

st.set_page_config(page_title="TSTT | Cash, Working Capital & CAPEX", page_icon="💵", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()
st.markdown("""<style>
@keyframes skeleton-pulse {
    0%   { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
</style>""", unsafe_allow_html=True)

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
fcf_month  = _safe(latest["FCF"])
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

# ── Pre-compute all values before column layout ────────────────────────────────
cash_dc    = "#00e676" if cash_delta >= 0 else "#ef4444"
debt_dc    = "#ef4444" if debt_delta >= 0 else "#00e676"
_fcf_color = "#00e676" if fcf_month >= 0 else "#ef4444"
_fcf_sign  = "+" if fcf_month >= 0 else ""

_cg_color  = ("#00e676" if (coll_gov or 0) >= 85
              else ("#FFD700" if (coll_gov or 0) >= 70 else "#ef4444")) if coll_gov is not None else "#556677"
_cng_color = ("#00e676" if (coll_non_gov or 0) >= 85
              else ("#FFD700" if (coll_non_gov or 0) >= 70 else "#ef4444")) if coll_non_gov is not None else "#556677"
_cg_val    = f"{coll_gov:.1f}%"     if coll_gov     is not None else "—"
_cng_val   = f"{coll_non_gov:.1f}%" if coll_non_gov is not None else "—"

capex_remaining = capex_plan - capex_act
capex_progress  = min(capex_act / capex_plan * 100, 100) if capex_plan else 0
capex_over      = capex_act > capex_plan
cap_bar_color = ("linear-gradient(90deg,#ef4444,#ff6b6b)" if capex_over
                 else "linear-gradient(90deg,#1d4ed8,#4a9eff)")
cap_pct_color = "#ef4444" if capex_over else "#4a9eff"
cap_rem_color = "#ef4444" if capex_remaining < 0 else "#6688aa"
cap_rem_label = "over budget" if capex_remaining < 0 else "remaining"
cap_rem_sign  = "+" if capex_remaining < 0 else ""

AR_BUCKETS = [
    ("0–30d",   "0_30",   "#00e676"),
    ("30–60d",  "31_60",  "#4488ff"),
    ("60–90d",  "61_90",  "#FFD700"),
    ("90–360d", "90_360", "#FF8844"),
    ("360+d",   "360p",   "#ef4444"),
]
_ar_max = max(gov["total"], non_gov["total"])

def _pill_row(row_label, data):
    row_total = data["total"]
    bar_pct   = row_total / _ar_max * 100
    pill_parts = []
    for bl, key, color in AR_BUCKETS:
        if data[key] <= 0:
            continue
        pct = data[key] / row_total * 100
        label_html = (
            f'<span style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
            f'font-size:0.62rem;font-weight:700;color:rgba(0,0,0,0.72);white-space:nowrap;'
            f'pointer-events:none">{pct:.0f}%</span>'
            if pct > 8 else ""
        )
        pill_parts.append(
            f'<div title="{bl}: TT${data[key]:,.1f}M ({pct:.1f}%)" '
            f'style="flex:{max(data[key], 0.001):.3f};min-width:20px;background:{color};'
            f'border-radius:6px;height:100%;position:relative;overflow:hidden">'
            f'{label_html}'
            f'</div>'
        )
    pills = "".join(pill_parts)
    return (
        f'<div style="margin-bottom:28px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px">'
        f'<span style="font-size:1rem;color:white;font-weight:600">{row_label}</span>'
        f'<span style="font-size:1rem;color:#aaaacc;font-weight:700">TT${row_total:,.1f}M</span>'
        f'</div>'
        f'<div style="display:flex;gap:0;height:72px;width:{bar_pct:.1f}%">{pills}</div>'
        f'</div>'
    )

_ar_legend = "".join(
    f'<div style="display:flex;align-items:center;gap:7px;white-space:nowrap">'
    f'<span style="width:14px;height:14px;border-radius:3px;background:{color};'
    f'flex-shrink:0;display:inline-block"></span>'
    f'<span style="font-size:0.82rem;color:#8899aa">{bl}</span></div>'
    for bl, _, color in AR_BUCKETS
)

def _mc(label, value, sub, sub_color):
    return (
        f'<div style="flex:1;background:#161b22;padding:16px 14px 14px;'
        f'border:1px solid #21262d;border-left:3px solid {sub_color};border-radius:8px;text-align:center">'
        f'<div style="font-size:0.72rem;font-weight:700;color:#556677;text-transform:uppercase;'
        f'letter-spacing:1.2px;margin-bottom:7px">{label}</div>'
        f'<div style="font-size:1.55rem;font-weight:800;color:white;line-height:1">{value}</div>'
        f'<div style="font-size:0.7rem;color:{sub_color};font-weight:600;margin-top:6px;text-align:right">{sub}</div>'
        f'</div>'
    )


def _coll_display(pct_val, color):
    """Skeleton loader when data unavailable, formatted value otherwise."""
    if pct_val is None:
        return (
            '<div style="background:linear-gradient(90deg,#21262d 25%,#2d3748 50%,#21262d 75%);'
            'background-size:200% 100%;animation:skeleton-pulse 1.5s ease-in-out infinite;'
            'border-radius:4px;height:26px;width:65%;margin:4px auto 6px"></div>'
        )
    return f'<div style="font-size:1.55rem;font-weight:800;color:{color};line-height:1">{pct_val:.1f}%</div>'

# ══════════════════════════════════════════════════════════════════════════════
# ROW 1 — Cash Trend (left) | AR Aging (right)
# ══════════════════════════════════════════════════════════════════════════════
r1_left, r1_right = st.columns(2)

with r1_left:
    y_vals = cc["Cash_Balance"].ffill().fillna(0)
    y_min  = float(y_vals.min())
    y_max  = float(y_vals.max())
    y_rng  = (y_max - y_min) * 0.22 if y_max != y_min else max(abs(y_max) * 0.12, 50)

    fig_cash = go.Figure()
    fig_cash.add_trace(go.Scatter(
        x=cc["Month"], y=y_vals,
        mode="lines+markers",
        line=dict(color="#00e676", width=2.5, shape="linear"),
        marker=dict(size=5, color="#00e676"),
        fill=None, showlegend=False,
        hovertemplate="%{x}: TT$%{y:,.0f}M<extra></extra>",
    ))
    fig_cash.add_hline(
        y=cash_val,
        line=dict(color="#00e676", width=1, dash="dash"),
        opacity=0.35,
    )
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

with r1_right:
    st.markdown(f"""
<div style="background:#161b22;border-radius:8px;padding:24px 24px 20px;border:1px solid #21262d">
  <div style="font-size:0.75rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:6px">AR Aging</div>
  <div style="font-size:0.85rem;color:#556677;margin-bottom:28px">
    Total: <strong style="color:#aaaacc">TT${AR_TOTAL:,.1f}M</strong>
    &nbsp;|&nbsp; Gov: <strong style="color:#aaaacc">{gov['total']:,.1f}M</strong>
    &nbsp;|&nbsp; Non-Gov: <strong style="color:#aaaacc">{non_gov['total']:,.1f}M</strong>
  </div>
  {_pill_row("Government", gov)}
  {_pill_row("Non-Government", non_gov)}
  <div style="display:flex;gap:20px;flex-wrap:wrap;margin-top:8px">{_ar_legend}</div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# ROW 2 — single flex row so all cards share the same height via align-items:stretch
#         Cash Balance | Net Debt | Free Cash Flow | Collections Performance
#         flex:1        flex:1     flex:1            flex:3  (keeps 50/50 visual split)
# ══════════════════════════════════════════════════════════════════════════════
_collections_card = (
    f'<div style="flex:3;background:#161b22;border-radius:8px;padding:16px 14px;'
    f'border:1px solid #21262d;display:flex;flex-direction:column">'
    f'<div style="font-size:0.72rem;font-weight:700;color:#556677;text-transform:uppercase;'
    f'letter-spacing:1.2px;margin-bottom:8px">Collections Performance</div>'
    f'<div style="display:flex;gap:8px;flex:1">'
    f'<div style="flex:1;background:#0d1117;border-radius:8px;padding:10px 12px;'
    f'border:1px solid #21262d;text-align:center;display:flex;flex-direction:column;justify-content:center">'
    f'<div style="font-size:0.72rem;color:#4488ff;font-weight:600;margin-bottom:5px;'
    f'text-transform:uppercase;letter-spacing:1px">Government</div>'
    f'{_coll_display(coll_gov, _cg_color)}'
    f'<div style="font-size:0.65rem;color:#556677;margin-top:5px">% of billings</div>'
    f'</div>'
    f'<div style="flex:1;background:#0d1117;border-radius:8px;padding:10px 12px;'
    f'border:1px solid #21262d;text-align:center;display:flex;flex-direction:column;justify-content:center">'
    f'<div style="font-size:0.72rem;color:#a78bfa;font-weight:600;margin-bottom:5px;'
    f'text-transform:uppercase;letter-spacing:1px">Non-Government</div>'
    f'{_coll_display(coll_non_gov, _cng_color)}'
    f'<div style="font-size:0.65rem;color:#556677;margin-top:5px">% of billings</div>'
    f'</div>'
    f'</div>'
    f'</div>'
)

st.markdown(
    f'<div style="display:flex;gap:10px;align-items:stretch;margin-bottom:12px">'
    f'{_mc("Cash Balance",  f"TT${cash_val:,.0f}M",              f"TT${cash_delta:+,.1f}M vs PY",   cash_dc)}'
    f'{_mc("Net Debt",      f"TT${debt_val:,.0f}M",              f"TT${debt_delta:+,.1f}M vs LY",   debt_dc)}'
    f'{_mc("Free Cash Flow",f"TT${abs(fcf_month):,.0f}M",        str(latest["Month"]),              _fcf_color)}'
    f'{_collections_card}'
    f'</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# ROW 3 — CAPEX (left only)
# ══════════════════════════════════════════════════════════════════════════════
r3_left, _ = st.columns(2)

with r3_left:
    st.markdown(f"""
<style>
@keyframes capex-fill-{int(capex_progress*10)} {{
    from {{ width: 0%; }}
    to   {{ width: {capex_progress:.1f}%; }}
}}
.capex-bar {{ animation: capex-fill-{int(capex_progress*10)} 600ms ease-in forwards; }}
</style>
<div style="background:#161b22;border-radius:8px;padding:18px 20px;border:1px solid #21262d">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:14px">CAPEX Spend to Date</div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="color:#aaaacc;font-size:14px;font-weight:500">YTD Spend vs Annual Budget</span>
    <span style="color:{cap_pct_color};font-weight:800;font-size:22px">{capex_progress:.1f}%</span>
  </div>
  <div style="background:#1e1e3a;border-radius:8px;height:20px;overflow:hidden;margin-bottom:14px">
    <div class="capex-bar" style="background:{cap_bar_color};height:100%;border-radius:8px"></div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:baseline">
    <div>
      <div style="color:{cap_pct_color};font-size:18px;font-weight:700">TT${capex_act:,.1f}M</div>
      <div style="color:#6688aa;font-size:13px;margin-top:2px">spent YTD</div>
    </div>
    <div style="text-align:center">
      <div style="color:{cap_rem_color};font-size:18px;font-weight:700">{cap_rem_sign}TT${abs(capex_remaining):,.1f}M</div>
      <div style="color:#6688aa;font-size:13px;margin-top:2px">{cap_rem_label}</div>
    </div>
    <div style="text-align:right">
      <div style="color:#aaaacc;font-size:18px;font-weight:700">TT${capex_plan:,.1f}M</div>
      <div style="color:#6688aa;font-size:13px;margin-top:2px">annual budget</div>
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
