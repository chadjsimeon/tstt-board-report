import streamlit as st

st.set_page_config(page_title="TSTT | Amplia Financial", page_icon="📶", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.month_selector import focus_month_selector, filter_data_to_month
from utils.charts import inject_css
from utils.rag import rev_var_rag
from utils.consumer_common import _sparkline

inject_css()
focus_month_selector()

data    = load_all_data()
amp_raw = data["AMPLIA_Financial"].copy()
amp_raw = filter_data_to_month(amp_raw)

# Gross Profit = Revenue − Direct Costs (COS); EBITDA = Gross Profit − OPEX.
# Override the sourced columns so the cards, PY variance, trend chart and driver
# block all use these definitions. Where OPEX is missing (e.g. latest month not
# yet booked), fall back to the sourced EBITDA so the card still renders.
if "Direct_Costs" in amp_raw.columns:
    amp_raw["Gross_Profit"]     = amp_raw["Revenue"] - amp_raw["Direct_Costs"]
    if "Direct_Costs_AOP" in amp_raw.columns and "Revenue_AOP" in amp_raw.columns:
        amp_raw["Gross_Profit_AOP"] = amp_raw["Revenue_AOP"] - amp_raw["Direct_Costs_AOP"]
if "OPEX" in amp_raw.columns:
    _src_ebitda = amp_raw["EBITDA"]
    amp_raw["EBITDA"] = (amp_raw["Gross_Profit"] - amp_raw["OPEX"]).fillna(_src_ebitda)

# ── Derive PY columns (12 months prior) ───────────────────────────────────────
amp_raw["_dt"] = pd.to_datetime(amp_raw["Month"], format="%b-%y", errors="coerce")
for col in ["Revenue", "Gross_Profit", "EBITDA", "PAT"]:
    if col in amp_raw.columns:
        lk = amp_raw.dropna(subset=["_dt"]).set_index("_dt")[col]
        amp_raw[f"{col}_PY"] = amp_raw["_dt"].apply(
            lambda dt, lk=lk: lk.get(dt - pd.DateOffset(months=12))
        )
amp_raw.drop(columns=["_dt"], inplace=True)

last12  = amp_raw.tail(13).reset_index(drop=True)
latest  = amp_raw.iloc[-1]

# ── Colors ────────────────────────────────────────────────────────────────────
REV_COLOR = "#00d4a0"
GP_COLOR  = "#FF8844"
EBI_COLOR = "#4a9eff"
PAT_COLOR = "#aa44ff"
CARD_BG   = "#161B22"
MUTED     = "#8888aa"
GRID      = "#1e2a3a"


# ── Helpers — KPI card mirrors Consumer Sales r1_card (size/font/sparkline) ────
def kpi_card(label, col, aop_col, ly_col, color, is_margin=False):
    actual = latest[col] if col in latest.index else None
    if actual is None or pd.isna(actual):
        return (f'<div style="background:{CARD_BG};border-radius:10px;padding:7px 12px;'
                f'border:1px solid #252545;border-top:3px solid {color};height:100%">—</div>')

    val_str = f"{actual:.1f}%" if is_margin else f"{actual:,.0f}"

    def _var_line(ref_col, tag):
        if not ref_col or ref_col not in latest.index:
            return f'<div style="font-size:29px;color:#445566;font-weight:600">— vs {tag}</div>'
        ref = latest[ref_col]
        if pd.isna(ref) or ref == 0:
            return f'<div style="font-size:29px;color:#445566;font-weight:600">— vs {tag}</div>'
        d_pct = (actual - ref) if is_margin else (actual - ref) / abs(ref) * 100
        clr   = rev_var_rag(d_pct)
        txt   = (f"{d_pct:+.1f}pp vs {tag}" if is_margin
                 else f"{actual - ref:+,.0f}&nbsp;|&nbsp;{d_pct:+.1f}%&nbsp;vs&nbsp;{tag}")
        return (f'<div style="font-size:29px;color:{clr};font-weight:600;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{txt}</div>')

    aop_line = _var_line(aop_col, "AOP")
    py_line  = _var_line(ly_col, "PY")

    spark_col  = col if col in last12.columns else None
    spark_html = (f'<div style="margin-top:8px;opacity:0.85">'
                  f'{_sparkline(last12[spark_col].fillna(0).tolist(), color)}</div>'
                  if spark_col else "")

    return (
        f'<div style="background:{CARD_BG};border-radius:10px;padding:7px 12px;'
        f'border:1px solid #252545;border-top:3px solid {color};height:100%">'
        f'<div style="font-size:28px;color:#6677aa;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:2px">{label}</div>'
        f'<div style="font-size:62px;font-weight:800;color:white;margin-bottom:2px;'
        f'line-height:1.05;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{val_str}</div>'
        f'{aop_line}{py_line}{spark_html}'
        f'</div>'
    )


def driver_block(label, color, col, aop_col, ly_col, is_margin=False, last_entry=False):
    actual = latest[col] if col in latest.index else None
    if actual is None or pd.isna(actual):
        return ""
    val_str = f"{actual:.1f}%" if is_margin else f"{actual:,.0f}"
    unit    = "pp" if is_margin else "%"
    month   = latest["Month"]

    line1 = f"<b>{val_str}</b> in {month}"
    if aop_col and aop_col in latest.index:
        aop = latest[aop_col]
        if pd.notna(aop) and aop != 0:
            d = (actual - aop) if is_margin else (actual - aop) / abs(aop) * 100
            line1 += f"&nbsp;&nbsp;{'↑' if d >= 0 else '↓'} {abs(d):.1f}{unit} vs AOP"

    line2 = ""
    if ly_col and ly_col in latest.index:
        ly = latest[ly_col]
        if pd.notna(ly) and ly != 0:
            d = (actual - ly) if is_margin else (actual - ly) / abs(ly) * 100
            ly_str = f"{ly:.1f}%" if is_margin else f"{ly:,.0f}"
            line2 = f"{'↑' if d >= 0 else '↓'} {abs(d):.1f}{unit} vs prior year ({ly_str})"

    divider = "" if last_entry else "border-bottom:1px solid #1e3050;"
    return f"""
<div style="margin-bottom:18px;padding-bottom:16px;{divider}">
    <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:6px;">{label}</div>
    <div style="color:#c0c8d8;font-size:14px;line-height:1.6;">{line1}</div>
    {"<div style='color:#8888aa;font-size:13px;line-height:1.6;'>" + line2 + "</div>" if line2 else ""}
</div>"""


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

# ── 60/40 split — trend chart + key drivers ───────────────────────────────────
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
    if "Gross_Profit" in last12.columns:
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
        title=dict(text="<b>Revenue, Gross Profit & EBITDA — 13-Month Trend</b>",
                   font=dict(size=28, color="white"), x=0),
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
    <div style="color:white;font-size:28px;font-weight:700;margin-bottom:20px;">
        Key Drivers — {latest['Month']}</div>
    {blocks}
</div>""", unsafe_allow_html=True)
