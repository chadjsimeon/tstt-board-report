import streamlit as st

st.set_page_config(page_title="TSTT | Enterprise Scorecard", page_icon="🎯", layout="wide")

import pandas as pd
from datetime import datetime
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()

# ── Viewport-fill CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
.main .block-container { padding-bottom: 0.5rem !important; }
[data-testid="column"] { min-height: calc(100vh - 200px); }
</style>
""", unsafe_allow_html=True)

data    = load_all_data()
kpi_all = data["KPI_Summary"]

# ── Derive period label from data ─────────────────────────────────────────────
try:
    period_raw   = kpi_all["Month"].dropna().iloc[-1]
    period_label = datetime.strptime(period_raw, "%b-%y").strftime("%B %Y")
except Exception:
    period_label = period_raw

# ── KPI direction sets ────────────────────────────────────────────────────────
HIGHER_BETTER = {
    "Revenue", "EBITDA", "PAT", "EBITDA Margin", "Free Cash Flow",
    "NPS", "Fibre Net-Adds", "Network Availability",
    "Engagement Score", "Women in Leadership", "Critical Vacancy Fill",
}
LOWER_BETTER = {
    "CAPEX/Revenue", "Postpaid Churn", "Complaints",
    "MTTR", "Install Lead Time", "Voluntary Attrition",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(val, unit):
    if pd.isna(val):
        return "—"
    v = float(val)
    if unit == "TT$M":   return f"TT${v:,.0f}M"
    if unit == "%":      return f"{v:.1f}%"
    if unit == "pts":    return f"{v:.0f} pts"
    if unit == "subs":   return f"{v:,.0f}"
    if unit == "hrs":    return f"{v:.1f} hrs"
    if unit == "days":   return f"{v:.0f} days"
    return f"{v:.0f}"          # score and anything else


def arrow(kpi_name, actual, aop):
    """Returns (symbol, hex_colour) for the direction indicator."""
    if pd.isna(actual) or pd.isna(aop) or aop == 0:
        return "", "#666666"
    pct = abs(float(actual) - float(aop)) / abs(float(aop))
    if pct < 0.02:
        return "→", "#f59e0b"
    if kpi_name in HIGHER_BETTER:
        return ("↑", "#22c55e") if float(actual) > float(aop) else ("↓", "#ef4444")
    if kpi_name in LOWER_BETTER:
        return ("↓", "#22c55e") if float(actual) < float(aop) else ("↑", "#ef4444")
    return "", "#666666"


def rag_dot(status_val):
    """Map Status emoji/string to a styled HTML circle."""
    s = str(status_val).strip()
    if "🟢" in s or s.upper() == "G":
        color = "#22c55e"
    elif "🟡" in s or s.upper() == "A":
        color = "#f59e0b"
    elif "🔴" in s or s.upper() == "R":
        color = "#ef4444"
    else:
        color = "#555577"
    return (
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'border-radius:50%;background:{color};flex-shrink:0"></span>'
    )


def quadrant_html(section_key, section_display, accent):
    df = kpi_all[kpi_all["Section"] == section_key].copy()

    if df.empty:
        return (
            f'<div style="background:#1a1a2e;border-radius:12px;padding:20px;'
            f'border:1px solid #2a2a4a;border-left:4px solid {accent};height:100%">'
            f'<div style="font-size:10px;font-weight:700;color:{accent};'
            f'text-transform:uppercase;letter-spacing:2.5px;margin-bottom:14px">'
            f'{section_display}</div>'
            f'<p style="color:#5566aa;font-size:13px">No data available</p></div>'
        )

    # Header row
    th = (
        'padding:7px 8px;text-align:{align};font-size:10px;color:#5566aa;'
        'font-weight:600;text-transform:uppercase;letter-spacing:1px;'
        'border-bottom:1px solid #2a2a4a'
    )
    header = (
        f'<tr>'
        f'<th style="{th.format(align="left")}">KPI</th>'
        f'<th style="{th.format(align="right")}">Actual</th>'
        f'<th style="{th.format(align="right")}">AOP</th>'
        f'<th style="{th.format(align="center")}">Status</th>'
        f'</tr>'
    )

    rows = ""
    for _, r in df.iterrows():
        sym, col = arrow(r["KPI_Name"], r["Actual"], r["AOP"])
        dot = rag_dot(r["Status"])
        actual_s = fmt(r["Actual"], r["Unit"])
        aop_s    = fmt(r["AOP"],    r["Unit"])

        rows += (
            f'<tr style="border-bottom:1px solid #16163a">'
            f'<td style="padding:9px 8px;color:#c8d8ee;font-size:13px">{r["KPI_Name"]}</td>'
            f'<td style="padding:9px 8px;text-align:right;font-weight:700;'
            f'font-size:14px;color:white">{actual_s}</td>'
            f'<td style="padding:9px 8px;text-align:right;font-size:12px;'
            f'color:#6688aa">{aop_s}</td>'
            f'<td style="padding:9px 10px">'
            f'<div style="display:flex;align-items:center;justify-content:center;gap:6px">'
            f'{dot}'
            f'<span style="color:{col};font-size:15px;font-weight:700;'
            f'line-height:1">{sym}</span>'
            f'</div></td>'
            f'</tr>'
        )

    return (
        f'<div style="background:#1a1a2e;border-radius:12px;padding:18px 20px;'
        f'border:1px solid #2a2a4a;border-left:4px solid {accent}">'
        f'<div style="font-size:10px;font-weight:700;color:{accent};'
        f'text-transform:uppercase;letter-spacing:2.5px;margin-bottom:14px">'
        f'{section_display}</div>'
        f'<table style="width:100%;border-collapse:collapse">'
        f'<thead>{header}</thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
        f'</div>'
    )


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:1.1rem 1.6rem;
            background:linear-gradient(135deg,#1a1a2e 0%,#0f1e3c 60%,#0d2040 100%);
            border-radius:12px;border:1px solid #2a3a5a;margin-bottom:1.4rem">
    <div style="font-size:1.4rem;font-weight:700;color:white;
                letter-spacing:0.5px">Enterprise Scorecard</div>
    <div style="font-size:0.88rem;font-weight:600;color:#00d4a0;
                letter-spacing:0.5px">{period_label} | Balanced View</div>
</div>
""", unsafe_allow_html=True)

# ── 2×2 Quadrant grid ─────────────────────────────────────────────────────────
r1c1, r1c2 = st.columns(2, gap="medium")
r2c1, r2c2 = st.columns(2, gap="medium")

with r1c1:
    st.markdown(
        quadrant_html("Financial",  "Financial",           "#00d4a0"),
        unsafe_allow_html=True,
    )

with r1c2:
    st.markdown(
        quadrant_html("Customer",   "Customer",            "#4a9eff"),
        unsafe_allow_html=True,
    )

with r2c1:
    st.markdown(
        quadrant_html("Network",    "Network & Operations","#a78bfa"),
        unsafe_allow_html=True,
    )

with r2c2:
    st.markdown(
        quadrant_html("People",     "People & Culture",    "#f59e0b"),
        unsafe_allow_html=True,
    )

# ── Confidential footer ───────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:28px;padding:10px;
            color:#3a4466;font-size:11px;font-weight:700;
            letter-spacing:2.5px;text-transform:uppercase;
            border-top:1px solid #1e1e3a">
    &#9632; CONFIDENTIAL &mdash; TSTT Board Use Only &mdash; Not for Distribution &#9632;
</div>
""", unsafe_allow_html=True)
