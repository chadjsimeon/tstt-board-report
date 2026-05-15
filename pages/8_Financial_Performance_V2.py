import streamlit as st

st.set_page_config(page_title="TSTT | Financial Performance v2", page_icon="📊", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()

# ── Data ─────────────────────────────────────────────────────────────────────
data = load_all_data()
fin  = data["Financial_Monthly"].copy()
fin["EBITDA_Margin_AOP"] = (fin["EBITDA_AOP"] / fin["Revenue_AOP"] * 100)

# Gross Profit from PnL_Breakdown (Revenue - COS)
pnl = data["PnL_Breakdown"].copy()
pnl["Gross_Profit"]     = pnl["Total_Rev"]     - pnl["Total_COS"]
pnl["Gross_Profit_AOP"] = pnl["Total_Rev_AOP"] - pnl["Total_COS_AOP"]
pnl["_dt"] = pd.to_datetime(pnl["Month"], format="%b-%y", errors="coerce")
gp_lk = pnl.dropna(subset=["_dt"]).set_index("_dt")["Gross_Profit"]
pnl["Gross_Profit_PY"] = pnl["_dt"].apply(
    lambda dt, lk=gp_lk: lk.get(dt - pd.DateOffset(months=12))
)
pnl.drop(columns=["_dt"], inplace=True)
fin = fin.merge(pnl[["Month", "Gross_Profit", "Gross_Profit_AOP", "Gross_Profit_PY"]],
                on="Month", how="left")

last12  = fin.tail(13).reset_index(drop=True)
latest  = fin.iloc[-1]

# ── Colors ────────────────────────────────────────────────────────────────────
REV_COLOR = "#00d4a0"
GP_COLOR  = "#FF8844"
EBI_COLOR = "#4a9eff"
PAT_COLOR = "#aa44ff"
CARD_BG   = "#1a2234"
MUTED     = "#8888aa"
GRID      = "#1e2a3a"


# ── Helpers ───────────────────────────────────────────────────────────────────
def make_svg_sparkline(series, color, width=220, height=56):
    vals = [float(v) if pd.notna(v) else 0.0 for v in series]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * width / max(len(vals) - 1, 1)
        y = height - (v - mn) / rng * height * 0.75 - height * 0.12
        pts.append(f"{x:.1f},{y:.1f}")
    line_pts = " ".join(pts)
    fill_pts = f"0,{height} {line_pts} {width},{height}"
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none" style="display:block;margin-top:8px;">'
        f'<polygon points="{fill_pts}" fill="rgba({r},{g},{b},0.15)"/>'
        f'<polyline points="{line_pts}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
    )


def _badge(label, delta, pos_color, neg_color):
    color = pos_color if delta >= 0 else neg_color
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<span style="font-size:14px;font-weight:600;padding:2px 8px;border-radius:3px;'
        f'background:rgba({r},{g},{b},0.15);color:{color};">{label}</span>'
    )


def kpi_card(label, col, aop_col, ly_col, color, is_margin=False):
    actual = latest[col]
    if pd.isna(actual):
        return f'<div style="background:{CARD_BG};border-radius:12px;padding:20px 16px;min-height:230px;">—</div>'

    val_str = f"{actual:.1f}%" if is_margin else f"TT${actual:,.0f}M"
    unit    = "pp" if is_margin else "%"

    badges = []
    aop = latest.get(aop_col)
    if aop is not None and pd.notna(aop) and aop != 0:
        d = (actual - aop) if is_margin else (actual - aop) / abs(aop) * 100
        lbl = f"vs AOP {'+' if d >= 0 else ''}{d:.1f}{unit}"
        badges.append(_badge(lbl, d, "#00d4a0", "#FF4444"))

    ly = latest.get(ly_col)
    if ly is not None and pd.notna(ly) and ly != 0:
        d = (actual - ly) if is_margin else (actual - ly) / abs(ly) * 100
        lbl = f"vs PY {'+' if d >= 0 else ''}{d:.1f}{unit}"
        badges.append(_badge(lbl, d, "#4a9eff", "#FFD700"))

    sparkline = make_svg_sparkline(last12[col].fillna(0).tolist(), color)
    badges_html = "&nbsp;".join(badges) if badges else "&nbsp;"

    return f"""
<div style="background:{CARD_BG};border-radius:12px;padding:20px 16px;
            border:1px solid rgba(74,158,255,0.08);border-top:3px solid {color};height:100%;min-height:230px;">
    <div style="color:{MUTED};font-size:14px;font-weight:500;margin-bottom:4px;">{label}</div>
    <div style="color:white;font-size:64px;font-weight:800;line-height:1;margin:4px 0 10px 0;">{val_str}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px;">{badges_html}</div>
    {sparkline}
</div>"""


def driver_block(label, color, col, aop_col, ly_col, is_margin=False, last_entry=False):
    actual = latest[col]
    if pd.isna(actual):
        return ""
    val_str = f"{actual:.1f}%" if is_margin else f"TT${actual:,.0f}M"
    unit    = "pp" if is_margin else "%"
    month   = latest["Month"]

    line1 = f"<b>{val_str}</b> in {month}"
    aop = latest.get(aop_col)
    if aop is not None and pd.notna(aop) and aop != 0:
        d = (actual - aop) if is_margin else (actual - aop) / abs(aop) * 100
        line1 += f"&nbsp;&nbsp;{'↑' if d >= 0 else '↓'} {abs(d):.1f}{unit} vs AOP"

    line2 = ""
    ly = latest.get(ly_col)
    if ly is not None and pd.notna(ly) and ly != 0:
        d = (actual - ly) if is_margin else (actual - ly) / abs(ly) * 100
        ly_str = f"{ly:.1f}%" if is_margin else f"TT${ly:,.0f}M"
        line2 = f"{'↑' if d >= 0 else '↓'} {abs(d):.1f}{unit} vs prior year ({ly_str})"

    divider = "" if last_entry else "border-bottom:1px solid #1e3050;"
    return f"""
<div style="margin-bottom:18px;padding-bottom:16px;{divider}">
    <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:6px;">{label}</div>
    <div style="color:#c0c8d8;font-size:14px;line-height:1.6;">{line1}</div>
    {"<div style='color:#8888aa;font-size:13px;line-height:1.6;'>" + line2 + "</div>" if line2 else ""}
</div>"""


# ── Page Header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #1e3050;">
    <div style="display:flex;align-items:center;gap:12px;">
        <span style="background:#00d4a0;color:#000;font-size:13px;font-weight:800;
                     padding:4px 10px;border-radius:4px;">02</span>
        <span style="font-size:26px;font-weight:800;color:white;">Financial Performance</span>
    </div>
    <div style="color:{MUTED};font-size:12px;">All figures in TT$M unless otherwise stated</div>
</div>""", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
METRICS = [
    ("Revenue",      "Revenue",      "Revenue_AOP",      "Revenue_PY",      REV_COLOR, False),
    ("Gross Profit", "Gross_Profit", "Gross_Profit_AOP", "Gross_Profit_PY", GP_COLOR,  False),
    ("EBITDA",       "EBITDA",       "EBITDA_AOP",       "EBITDA_PY",       EBI_COLOR, False),
    ("PAT",          "PAT",          "PAT_AOP",          "PAT_PY",          PAT_COLOR, False),
]

c1, c2, c3, c4 = st.columns(4)
for col_obj, (lbl, col, aop_col, ly_col, clr, is_m) in zip([c1, c2, c3, c4], METRICS):
    with col_obj:
        st.markdown(kpi_card(lbl, col, aop_col, ly_col, clr, is_m), unsafe_allow_html=True)

# ── 60/40 Split ───────────────────────────────────────────────────────────────
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
chart_col, driver_col = st.columns([3, 2])

with chart_col:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=last12["Month"], y=last12["Revenue"],
        mode="lines", name="Revenue",
        line=dict(color=REV_COLOR, width=2.5),
        fill="tozeroy", fillcolor="rgba(0,212,160,0.07)",
    ))
    fig.add_trace(go.Scatter(
        x=last12["Month"], y=last12["Gross_Profit"],
        mode="lines", name="Gross Profit",
        line=dict(color=GP_COLOR, width=2),
        fill="tozeroy", fillcolor="rgba(255,136,68,0.07)",
    ))
    fig.add_trace(go.Scatter(
        x=last12["Month"], y=last12["EBITDA"],
        mode="lines", name="EBITDA",
        line=dict(color=EBI_COLOR, width=2.5),
        fill="tozeroy", fillcolor="rgba(74,158,255,0.07)",
    ))
    fig.update_layout(
        height=560,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        title=dict(text="<b>Revenue, Gross Profit & EBITDA — 13-Month Trend (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED, size=13), showline=False, tickangle=-30),
        yaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED, size=13), showline=False, zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
                    orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=44, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)

with driver_col:
    blocks = "".join([
        driver_block("Revenue",      REV_COLOR, "Revenue",      "Revenue_AOP",      "Revenue_PY",      False),
        driver_block("Gross Profit", GP_COLOR,  "Gross_Profit", "Gross_Profit_AOP", "Gross_Profit_PY", False),
        driver_block("EBITDA",       EBI_COLOR, "EBITDA",       "EBITDA_AOP",       "EBITDA_PY",       False),
        driver_block("PAT",          PAT_COLOR, "PAT",          "PAT_AOP",          "PAT_PY",          False, last_entry=True),
    ])
    st.markdown(f"""
<div style="background:{CARD_BG};border-radius:12px;padding:24px;
            border:1px solid rgba(74,158,255,0.08);">
    <div style="color:white;font-size:15px;font-weight:700;margin-bottom:20px;">
        Key Drivers — {latest['Month']}</div>
    {blocks}
</div>""", unsafe_allow_html=True)
