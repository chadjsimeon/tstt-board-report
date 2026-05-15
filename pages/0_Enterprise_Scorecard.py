import streamlit as st

st.set_page_config(page_title="TSTT | Enterprise Scorecard", page_icon="🎯", layout="wide")

import pandas as pd
from datetime import datetime
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()

st.markdown("""
<style>
.main .block-container { padding-bottom: 0.5rem !important; }
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
    return f"{v:.0f}"


def arrow(kpi_name, actual, aop):
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
            f'border:1px solid #2a2a4a;border-left:4px solid {accent};'
            f'display:flex;flex-direction:column;overflow:hidden">'
            f'<div style="font-size:10px;font-weight:700;color:{accent};'
            f'text-transform:uppercase;letter-spacing:2.5px;margin-bottom:14px;flex-shrink:0">'
            f'{section_display}</div>'
            f'<p style="color:#5566aa;font-size:13px">No data available</p></div>'
        )

    # Column header row (fixed, doesn't grow)
    header = (
        f'<div style="display:flex;padding:7px 8px;border-bottom:1px solid #2a2a4a;flex-shrink:0">'
        f'<div style="flex:3;font-size:12px;color:#5566aa;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:1px">KPI</div>'
        f'<div style="flex:1.2;text-align:right;font-size:12px;color:#5566aa;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:1px">Actual</div>'
        f'<div style="flex:1.2;text-align:right;font-size:12px;color:#5566aa;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:1px">AOP</div>'
        f'<div style="flex:0.8;text-align:center;font-size:12px;color:#5566aa;'
        f'font-weight:600;text-transform:uppercase;letter-spacing:1px">Status</div>'
        f'</div>'
    )

    rows = ""
    for _, r in df.iterrows():
        sym, col = arrow(r["KPI_Name"], r["Actual"], r["AOP"])
        dot      = rag_dot(r["Status"])
        actual_s = fmt(r["Actual"], r["Unit"])
        aop_s    = fmt(r["AOP"],    r["Unit"])

        rows += (
            f'<div style="display:flex;align-items:center;flex:1;'
            f'border-bottom:1px solid #16163a;padding:0 8px;min-height:0">'
            f'<div style="flex:3;color:#c8d8ee;font-size:13px;line-height:1.3">'
            f'{r["KPI_Name"]}</div>'
            f'<div style="flex:1.2;text-align:right;font-weight:700;'
            f'font-size:14px;color:white">{actual_s}</div>'
            f'<div style="flex:1.2;text-align:right;font-size:13px;'
            f'color:#6688aa">{aop_s}</div>'
            f'<div style="flex:0.8;display:flex;align-items:center;'
            f'justify-content:center;gap:6px">'
            f'{dot}'
            f'<span style="color:{col};font-size:15px;font-weight:700;'
            f'line-height:1">{sym}</span>'
            f'</div>'
            f'</div>'
        )

    return (
        f'<div style="background:#1a1a2e;border-radius:12px;padding:18px 20px;'
        f'border:1px solid #2a2a4a;border-left:4px solid {accent};'
        f'display:flex;flex-direction:column;overflow:hidden;min-height:0">'
        f'<div style="font-size:12px;font-weight:700;color:{accent};'
        f'text-transform:uppercase;letter-spacing:2.5px;margin-bottom:12px;flex-shrink:0">'
        f'{section_display}</div>'
        f'{header}'
        f'<div style="display:flex;flex-direction:column;flex:1;min-height:0">'
        f'{rows}'
        f'</div>'
        f'</div>'
    )


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:1.1rem 1.6rem;
            background:linear-gradient(135deg,#1a1a2e 0%,#0f1e3c 60%,#0d2040 100%);
            border-radius:12px;border:1px solid #2a3a5a;margin-bottom:1rem">
    <div style="font-size:1.4rem;font-weight:700;color:white;
                letter-spacing:0.5px">Enterprise Scorecard</div>
    <div style="font-size:0.88rem;font-weight:600;color:#00d4a0;
                letter-spacing:0.5px">{period_label} | Balanced View</div>
</div>
""", unsafe_allow_html=True)

# ── 2×2 CSS Grid — all four cards perfectly equal ─────────────────────────────
q_financial = quadrant_html("Financial",  "Financial",            "#00d4a0")
q_customer  = quadrant_html("Customer",   "Customer",             "#4a9eff")
q_network   = quadrant_html("Network",    "Network & Operations", "#a78bfa")
q_people    = quadrant_html("People",     "People & Culture",     "#f59e0b")

st.markdown(f"""
<div style="
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    height: calc(100vh - 180px);
    gap: 14px;
">
    {q_financial}
    {q_customer}
    {q_network}
    {q_people}
</div>
""", unsafe_allow_html=True)

# ── Confidential footer ───────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:12px;padding:8px;
            color:#3a4466;font-size:11px;font-weight:700;
            letter-spacing:2.5px;text-transform:uppercase;
            border-top:1px solid #1e1e3a">
    &#9632; CONFIDENTIAL &mdash; TSTT Board Use Only &mdash; Not for Distribution &#9632;
</div>
""", unsafe_allow_html=True)
