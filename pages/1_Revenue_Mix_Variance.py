import streamlit as st

st.set_page_config(page_title="TSTT | Revenue Mix & Variance", page_icon="🍩", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.month_selector import focus_month_selector, filter_data_to_month
from utils.charts import inject_css

inject_css()
focus_month_selector()

# ── Data ─────────────────────────────────────────────────────────────────────
data = load_all_data()
fin  = data["Financial_Monthly"].copy()
fin = filter_data_to_month(fin)

# ── Colors ────────────────────────────────────────────────────────────────────
EBI_COLOR = "#4a9eff"
CARD_BG   = "#1a2234"
MUTED     = "#8888aa"
GRID      = "#1e2a3a"

SEG_COLORS = {
    "Consumer": "#22C55E",
    "Business": "#60A5FA",
    "AMPLIA":   "#A78BFA",
    "DPDI":     "#FB923C",
    "Other":    "#6B7280",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _dt_parse(df, col="Month"):
    d = df.copy()
    d["_dt"] = pd.to_datetime(d[col], format="%b-%y", errors="coerce")
    return d


def _psum(df, val_col, s, e):
    if df is None or val_col not in df.columns:
        return 0.0
    mask = df["_dt"].between(s, e, inclusive="both")
    return float(df.loc[mask, val_col].sum())


# ── Segment DataFrames ────────────────────────────────────────────────────────
con_d  = _dt_parse(data["Consumer_Sales"])
biz_d  = _dt_parse(data["Business_Sales"])
fin_d  = _dt_parse(fin)
dpdi_d = _dt_parse(data["DPDI"])             if "DPDI"             in data else None
amp_d  = _dt_parse(data["AMPLIA_Financial"]) if "AMPLIA_Financial" in data else None

# ── Auto-detect latest month ──────────────────────────────────────────────────
latest_dt  = fin_d["_dt"].dropna().max()

# Period boundaries — all derived from latest_dt
_CUR_S = pd.Timestamp(latest_dt.year, latest_dt.month, 1)
_CUR_E = _CUR_S + pd.offsets.MonthEnd(0)          # e.g., 2026-04-30

_YTD_S = pd.Timestamp(latest_dt.year, 1, 1)       # Jan 1 of current year
_YTD_E = _CUR_E                                    # through latest month

_FY_S  = pd.Timestamp(latest_dt.year - 1, 1, 1)   # previous full calendar year
_FY_E  = pd.Timestamp(latest_dt.year - 1, 12, 31)

# Last complete quarter before the current one
_cur_q_0 = (latest_dt.month - 1) // 3             # 0-indexed quarter of latest month
if _cur_q_0 == 0:
    _prev_q_0, _prev_q_yr = 3, latest_dt.year - 1
else:
    _prev_q_0, _prev_q_yr = _cur_q_0 - 1, latest_dt.year
_LCQ_S = pd.Timestamp(_prev_q_yr, _prev_q_0 * 3 + 1, 1)
_LCQ_E = _LCQ_S + pd.offsets.MonthEnd(3)

# Same month, prior year (for YoY bridge)
_LY_S  = pd.Timestamp(latest_dt.year - 1, latest_dt.month, 1)
_LY_E  = _LY_S + pd.offsets.MonthEnd(0)           # e.g., 2025-04-30

# Human-readable labels
_fy_lbl  = f"FY{str(latest_dt.year - 1)[-2:]}"
_lcq_lbl = f"Q{_prev_q_0 + 1} '{str(_prev_q_yr)[-2:]}"
_mon_lbl = latest_dt.strftime("%b '%y")
_ytd_lbl = f"YTD '{str(latest_dt.year)[-2:]}"
_ly_lbl  = _LY_S.strftime("%b '%y")

_periods = [
    (_fy_lbl,  _FY_S,  _FY_E),
    (_lcq_lbl, _LCQ_S, _LCQ_E),
    (_mon_lbl, _CUR_S, _CUR_E),
    (_ytd_lbl, _YTD_S, _YTD_E),
]
p_labels = [p[0] for p in _periods]

# ── Revenue by segment across all periods ─────────────────────────────────────
def _seg_series(df, col):
    return [_psum(df, col, s, e) for _, s, e in _periods]


con_v   = _seg_series(con_d,  "Revenue")
biz_v   = _seg_series(biz_d,  "Revenue")
amp_v   = _seg_series(amp_d,  "Revenue")
dpdi_v  = _seg_series(dpdi_d, "Revenue")
tot_v   = _seg_series(fin_d,  "Revenue")
other_v = [max(0.0, tot_v[i] - con_v[i] - biz_v[i] - amp_v[i] - dpdi_v[i])
           for i in range(len(_periods))]

SEGS = [
    ("Consumer", con_v,   SEG_COLORS["Consumer"]),
    ("Business", biz_v,   SEG_COLORS["Business"]),
    ("AMPLIA",   amp_v,   SEG_COLORS["AMPLIA"]),
    ("DPDI",     dpdi_v,  SEG_COLORS["DPDI"]),
    ("Other",    other_v, SEG_COLORS["Other"]),
]

# Indices: 2 = latest single month, 3 = YTD
_MON_I = 2
_YTD_I = 3

# YTD values → donut chart
ytd_seg = {name: v[_YTD_I] for name, v, _ in SEGS}
ytd_tot = tot_v[_YTD_I]

# Current single month & same month LY → YoY bridge
cur_seg = {name: v[_MON_I] for name, v, _ in SEGS}
cur_tot = tot_v[_MON_I]

ly_seg = {
    "Consumer": _psum(con_d,  "Revenue", _LY_S, _LY_E),
    "Business": _psum(biz_d,  "Revenue", _LY_S, _LY_E),
    "AMPLIA":   _psum(amp_d,  "Revenue", _LY_S, _LY_E),
    "DPDI":     _psum(dpdi_d, "Revenue", _LY_S, _LY_E),
}
ly_tot = _psum(fin_d, "Revenue", _LY_S, _LY_E)
ly_seg["Other"] = max(0.0, ly_tot - sum(ly_seg.values()))

bridge_delta = {name: cur_seg[name] - ly_seg.get(name, 0.0) for name in cur_seg}

# ── Row 1: Full-width stacked bar ─────────────────────────────────────────────
fig_bar = go.Figure()
for name, vals, color in SEGS:
    if any(v > 0 for v in vals):
        fig_bar.add_trace(go.Bar(
            name=name, x=p_labels, y=vals,
            marker_color=color,
            hovertemplate=f"<b>{name}</b>: %{{y:,.1f}}<extra></extra>",
        ))
fig_bar.update_layout(
    barmode="stack",
    height=420,
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="white"),
    title=dict(text="<b>Revenue by Segment</b>",
               font=dict(size=16, color="white"), x=0),
    xaxis=dict(gridcolor=GRID, tickfont=dict(color="white", size=16)),
    yaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED, size=15),
               tickprefix="$", zeroline=False),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white", size=15),
                orientation="h", x=0, y=-0.14),
    margin=dict(l=10, r=10, t=44, b=80),
)
st.plotly_chart(fig_bar, use_container_width=True)

# ── Row 2: Donut (left) + Waterfall (right) ───────────────────────────────────
donut_col, wf_col = st.columns(2)

with donut_col:
    d_names  = [n for n, v, _ in SEGS if ytd_seg[n] > 0]
    d_vals   = [ytd_seg[n] for n, v, _ in SEGS if ytd_seg[n] > 0]
    d_colors = [c for n, v, c in SEGS if ytd_seg[n] > 0]

    fig_donut = go.Figure(go.Pie(
        labels=d_names, values=d_vals, hole=0.55,
        marker=dict(colors=d_colors, line=dict(color="#0d1117", width=2)),
        textinfo="label+percent",
        textfont=dict(color="white", size=14),
        hovertemplate="<b>%{label}</b>: %{value:,.1f} (%{percent})<extra></extra>",
        title=dict(
            text=f"<b>Total<br>{ytd_tot:,.0f}</b>",
            font=dict(size=16, color="white"),
            position="middle center",
        ),
    ))
    fig_donut.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        title=dict(text=f"<b>{_ytd_lbl} Revenue Mix</b>",
                   font=dict(size=16, color="white"), x=0),
        showlegend=False,
        margin=dict(l=10, r=10, t=44, b=10),
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with wf_col:
    wf_x = [_ly_lbl] + list(bridge_delta.keys()) + [_mon_lbl]
    wf_m = ["absolute"] + ["relative"] * len(bridge_delta) + ["total"]
    wf_y = [ly_tot] + list(bridge_delta.values()) + [cur_tot]
    wf_text = [
        f"{v:+,.1f}" if m == "relative" else f"{v:,.1f}"
        for v, m in zip(wf_y, wf_m)
    ]

    fig_wf = go.Figure(go.Waterfall(
        x=wf_x, y=wf_y, measure=wf_m,
        text=wf_text,
        textposition="outside",
        textfont=dict(color="white", size=14),
        increasing=dict(marker=dict(color="#00d4a0")),
        decreasing=dict(marker=dict(color="#FF4444")),
        totals=dict(marker=dict(color=EBI_COLOR)),
        connector=dict(line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dot")),
        hovertemplate="<b>%{x}</b>: %{y:,.1f}<extra></extra>",
    ))
    fig_wf.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        title=dict(text=f"<b>YoY Revenue Bridge — {_mon_lbl} vs {_ly_lbl}</b>",
                   font=dict(size=16, color="white"), x=0),
        xaxis=dict(gridcolor=GRID, tickfont=dict(color="white", size=14)),
        yaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED, size=14), zeroline=False),
        showlegend=False,
        margin=dict(l=10, r=10, t=44, b=30),
    )
    st.plotly_chart(fig_wf, use_container_width=True)

# ── Confidential Footer ───────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:24px;padding:12px 16px;border-top:1px solid #1e3050;
            color:#445566;font-size:11px;text-align:center;">
    CONFIDENTIAL — This document is intended for board members only and should not be
    distributed without authorisation.
</div>""", unsafe_allow_html=True)
