import streamlit as st

st.set_page_config(page_title="TSTT | Cash, Working Capital & CAPEX", page_icon="💵", layout="wide")

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()

st.markdown("""
<style>
.main .block-container { padding-bottom: 0.5rem !important; }
</style>
""", unsafe_allow_html=True)

data = load_all_data()
cc   = data["Cash_CAPEX"]

# ── Data prep ──────────────────────────────────────────────────────────────────
latest = cc.iloc[-1]
first  = cc.iloc[0]

def _safe(val, default=0.0):
    return float(val) if pd.notna(val) else default

cash_val   = _safe(latest["Cash_Balance"])
cash_delta = cash_val - _safe(first["Cash_Balance"])

debt_val   = _safe(latest["Net_Debt"])
debt_delta = debt_val - _safe(first["Net_Debt"])

coll_val   = _safe(latest["Collections_Pct"])

# FCF YTD — sum all available months (series covers most recent complete FY)
fcf_ytd = float(cc["FCF"].sum())

# CAPEX totals across all months
capex_act  = float(cc["CAPEX_Actual"].sum())
capex_plan = float(cc["CAPEX_Plan"].sum())

# CAPEX sub-category splits (fixed percentages)
SPLITS = [
    ("Access",    0.45),
    ("Core",      0.22),
    ("IT / BSS",  0.19),
    ("Buildings", 0.08),
    ("Other",     0.06),
]

# Period label from latest row
try:
    period_label = pd.to_datetime(latest["Month"], format="%b-%y").strftime("%B %Y")
except Exception:
    period_label = str(latest["Month"])

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:1.0rem 1.6rem;
            background:linear-gradient(135deg,#1a1a2e 0%,#0f1e3c 60%,#0d2040 100%);
            border-radius:12px;border:1px solid #2a3a5a;margin-bottom:1rem">
    <div style="display:flex;align-items:center;gap:16px">
        <div style="background:#00c46a;color:#001a0d;font-size:14px;font-weight:900;
                    width:36px;height:36px;border-radius:6px;
                    display:flex;align-items:center;justify-content:center;flex-shrink:0">02</div>
        <div>
            <div style="font-size:1.3rem;font-weight:700;color:white;letter-spacing:0.3px">
                Cash, Working Capital &amp; CAPEX</div>
            <div style="font-size:0.82rem;color:#7eb8f7;margin-top:2px">YTD {period_label}</div>
        </div>
    </div>
    <div style="font-size:0.78rem;color:#5566aa;font-style:italic;text-align:right">
        All figures in TT$M unless otherwise stated</div>
</div>
""", unsafe_allow_html=True)

# ── Two-column layout ──────────────────────────────────────────────────────────
col_left, col_right = st.columns([55, 45])

# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN
# ══════════════════════════════════════════════════════════════════════════════
with col_left:

    # ── 1. Cash & Liquidity chart ─────────────────────────────────────────────
    st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
    <div style="width:4px;height:20px;background:#00ff88;border-radius:2px;flex-shrink:0"></div>
    <span style="font-size:11px;font-weight:700;color:#00ff88;text-transform:uppercase;
                 letter-spacing:2.5px">Cash &amp; Liquidity</span>
</div>
""", unsafe_allow_html=True)

    y_vals = cc["Cash_Balance"].ffill().fillna(0)
    y_min  = float(y_vals.min())
    y_max  = float(y_vals.max())
    y_rng  = (y_max - y_min) * 0.18 if y_max != y_min else max(y_max * 0.1, 50)

    fig_cash = go.Figure()
    fig_cash.add_trace(go.Scatter(
        x=cc["Month"],
        y=y_vals,
        mode="lines+markers",
        line=dict(color="#00ff88", width=2.5),
        marker=dict(size=5, color="#00ff88", line=dict(color="#00ff88", width=1)),
        fill=None,
        showlegend=False,
        hovertemplate="%{x}: TT$%{y:,.0f}M<extra></extra>",
    ))
    fig_cash.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=220, showlegend=False,
        margin=dict(l=10, r=10, t=6, b=8),
        xaxis=dict(
            gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=10),
            showline=False,
        ),
        yaxis=dict(
            gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=10),
            title=dict(text="TT$M", font=dict(color="#8888aa", size=10)),
            range=[y_min - y_rng, y_max + y_rng],
            zeroline=False,
        ),
    )
    st.plotly_chart(fig_cash, use_container_width=True)

    # ── 2. Three metric cards ─────────────────────────────────────────────────
    cash_dc   = "#00ff88" if cash_delta >= 0 else "#ef4444"
    debt_dc   = "#ef4444" if debt_delta >= 0 else "#00ff88"   # higher debt = worse
    coll_disp = f"{coll_val:.1f}%" if (pd.notna(coll_val) and coll_val != 0) else "N/A"
    coll_sub  = "vs Billing"

    st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:12px">

  <div style="background:#151528;border-radius:10px;padding:14px 16px;
              border:1px solid #252545;border-top:3px solid #00d4a0">
    <div style="font-size:10px;color:#556688;font-weight:600;text-transform:uppercase;
                letter-spacing:1.5px;margin-bottom:8px">Cash Balance</div>
    <div style="font-size:20px;font-weight:800;color:white;margin-bottom:5px;
                white-space:nowrap">TT${cash_val:,.0f}M</div>
    <div style="font-size:12px;color:{cash_dc};font-weight:600">
        {cash_delta:+,.0f} vs PY</div>
  </div>

  <div style="background:#151528;border-radius:10px;padding:14px 16px;
              border:1px solid #252545;border-top:3px solid #FF8844">
    <div style="font-size:10px;color:#556688;font-weight:600;text-transform:uppercase;
                letter-spacing:1.5px;margin-bottom:8px">Net Debt</div>
    <div style="font-size:20px;font-weight:800;color:white;margin-bottom:5px;
                white-space:nowrap">TT${debt_val:,.0f}M</div>
    <div style="font-size:12px;color:{debt_dc};font-weight:600">
        {debt_delta:+,.0f} vs PY</div>
  </div>

  <div style="background:#151528;border-radius:10px;padding:14px 16px;
              border:1px solid #252545;border-top:3px solid #aa44ff">
    <div style="font-size:10px;color:#556688;font-weight:600;text-transform:uppercase;
                letter-spacing:1.5px;margin-bottom:8px">Collections</div>
    <div style="font-size:20px;font-weight:800;color:white;margin-bottom:5px">
        {coll_disp}</div>
    <div style="font-size:12px;color:#5566aa">{coll_sub}</div>
  </div>

</div>
""", unsafe_allow_html=True)

    # ── 3. Working Capital Summary ────────────────────────────────────────────
    fcf_color = "#00ff88" if fcf_ytd >= 0 else "#ef4444"

    st.markdown(f"""
<div style="background:#151528;border-radius:12px;padding:18px 20px;
            border:1px solid #252545;border-left:4px solid #00ff88">
    <div style="font-size:10px;font-weight:700;color:#00ff88;text-transform:uppercase;
                letter-spacing:2.5px;margin-bottom:14px">Working Capital Summary</div>
    <div style="font-size:13px;color:#c8d8ee;line-height:2;
                border-bottom:1px solid #1e1e3a;padding-bottom:12px;margin-bottom:12px">
        DSO:&nbsp;<strong style="color:white">68 days</strong>&nbsp;(PY: 72)
        &nbsp;&nbsp;|&nbsp;&nbsp;
        DPO:&nbsp;<strong style="color:white">45 days</strong>&nbsp;(PY: 42)
        &nbsp;&nbsp;|&nbsp;&nbsp;
        Cash Conversion:&nbsp;<strong style="color:white">84%</strong>
    </div>
    <div style="font-size:13px;color:#c8d8ee">
        Free Cash Flow YTD:&nbsp;
        <strong style="color:{fcf_color};font-size:17px">{"+" if fcf_ytd >= 0 else ""}TT${abs(fcf_ytd):,.0f}M</strong>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN
# ══════════════════════════════════════════════════════════════════════════════
with col_right:

    # ── 1. AR Aging (hardcoded placeholder) ───────────────────────────────────
    AR_TOTAL   = 840
    AR_BUCKETS = [
        ("Current", 420, "#00c46a", "#001a0d"),
        ("30–60d",  185, "#4488ff", "#ffffff"),
        ("60–90d",   95, "#f59e0b", "#001a0d"),
        ("90+ d",   140, "#ef4444", "#ffffff"),
    ]

    segs = ""
    for lbl, val, bg, tc in AR_BUCKETS:
        pct = val / AR_TOTAL * 100
        segs += (
            f'<div style="flex:{pct:.1f};background:{bg};height:50px;'
            f'display:flex;flex-direction:column;align-items:center;'
            f'justify-content:center;gap:1px">'
            f'<span style="font-size:10px;font-weight:700;color:{tc}">{lbl}</span>'
            f'<span style="font-size:12px;font-weight:800;color:{tc}">{val}M</span>'
            f'</div>'
        )

    legend = ""
    for lbl, val, bg, _ in AR_BUCKETS:
        legend += (
            f'<span style="display:inline-flex;align-items:center;gap:5px;'
            f'font-size:11px;color:#aaaacc">'
            f'<span style="width:8px;height:8px;border-radius:2px;background:{bg};'
            f'display:inline-block"></span>{lbl} TT${val}M</span>'
        )

    st.markdown(f"""
<div style="background:#151528;border-radius:12px;padding:18px 20px;
            border:1px solid #252545;border-left:4px solid #4488ff;margin-bottom:12px">
    <div style="font-size:10px;font-weight:700;color:#4488ff;text-transform:uppercase;
                letter-spacing:2.5px;margin-bottom:10px">AR Aging</div>
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:8px">
        <span style="font-size:12px;color:#6688aa">Total AR Outstanding</span>
        <span style="font-size:21px;font-weight:800;color:white">TT${AR_TOTAL}M</span>
    </div>
    <div style="display:flex;border-radius:8px;overflow:hidden;margin-bottom:10px">
        {segs}
    </div>
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px">{legend}</div>
    <div style="background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.28);
                border-radius:8px;padding:10px 14px;font-size:12px;
                color:#f87171;line-height:1.5">
        &#9888;&nbsp;<strong>90+ days: TT$140M (16.7% of total)</strong>
        &nbsp;— focus collection actions on top 10 enterprise accounts.
    </div>
</div>
""", unsafe_allow_html=True)

    # ── 2. CAPEX Burn Rate ────────────────────────────────────────────────────
    cat_names = [s[0] for s in SPLITS]
    cat_act   = [capex_act  * s[1] for s in SPLITS]
    cat_plan  = [capex_plan * s[1] for s in SPLITS]

    st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
    <div style="width:4px;height:20px;background:#00ff88;border-radius:2px;flex-shrink:0"></div>
    <span style="font-size:11px;font-weight:700;color:#00ff88;text-transform:uppercase;
                 letter-spacing:2.5px">CAPEX Burn Rate</span>
</div>
""", unsafe_allow_html=True)

    fig_cap = go.Figure()

    # AOP reference — wide, translucent grey
    fig_cap.add_trace(go.Bar(
        y=cat_names, x=cat_plan, orientation="h",
        name="AOP",
        marker_color="rgba(90,90,130,0.32)",
        marker_line=dict(color="rgba(140,140,180,0.55)", width=1),
        width=0.65,
        hovertemplate="%{y}<br>AOP: TT$%{x:,.0f}M<extra></extra>",
    ))

    # Actual — narrower, green, value outside
    fig_cap.add_trace(go.Bar(
        y=cat_names, x=cat_act, orientation="h",
        name="Actual",
        marker_color="#00ff88",
        width=0.38,
        text=[f"TT${v:,.0f}M" for v in cat_act],
        textposition="outside",
        textfont=dict(color="white", size=11),
        hovertemplate="%{y}<br>Actual: TT$%{x:,.0f}M<extra></extra>",
    ))

    x_max = max(cat_plan) * 1.42 if any(v > 0 for v in cat_plan) else 100

    fig_cap.update_layout(
        barmode="overlay",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        height=290,
        legend=dict(
            bgcolor="rgba(0,0,0,0)", orientation="h",
            y=1.06, x=0, xanchor="left",
            font=dict(size=12, color="white"),
        ),
        xaxis=dict(
            gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=10),
            title=dict(text="TT$M", font=dict(color="#8888aa", size=10)),
            range=[0, x_max],
        ),
        yaxis=dict(tickfont=dict(color="white", size=12)),
        margin=dict(l=10, r=95, t=38, b=10),
    )
    st.plotly_chart(fig_cap, use_container_width=True)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:8px;padding:6px;
            color:#3a4466;font-size:11px;font-weight:700;
            letter-spacing:2.5px;text-transform:uppercase;
            border-top:1px solid #1e1e3a">
    &#9632; CONFIDENTIAL &mdash; TSTT Board Use Only &mdash; Not for Distribution &#9632;
</div>
""", unsafe_allow_html=True)
