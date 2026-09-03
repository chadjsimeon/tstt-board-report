import streamlit as st

st.set_page_config(
    page_title="TSTT Board Report",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
from utils.data_loader import load_all_data
from utils.month_selector import focus_month_selector
from utils.charts import (
    inject_css, page_header, kpi_card,
    line_chart, grouped_bar,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE,
    BLUE_DIM, GREEN_DIM, PURPLE_DIM, WHITE_DIM, WHITE_FAINT,
)

inject_css()
focus_month_selector()

data = load_all_data()
kpi = data["KPI_Summary"]
fin = data["Financial_Monthly"]

# ── Header ───────────────────────────────────────────────────────────────────
period = kpi["Month"].iloc[0] if not kpi.empty else "Apr-26"
page_header(
    "Executive Summary",
    "Telecommunications Services of Trinidad and Tobago",
    period,
)

# ── KPI Scorecards ────────────────────────────────────────────────────────────
st.markdown("### Key Performance Indicators")

# Unique accent palette for KPI cards — visually distinct per metric,
# independent of RAG status (green/red text still signals good/bad variance)
KPI_ACCENTS = ["#00786C", "#0B6BCB", "#7C2BD9", "#C2410C", "#0E7490", "#A16207", "#C53030"]

sections = [s for s in dict.fromkeys(kpi["Section"].dropna().tolist()) if str(s).strip()]
for section in sections:
    section_df = kpi[kpi["Section"] == section].reset_index(drop=True)
    if len(section_df) == 0:
        continue
    st.markdown(f"<p class='section-label'>{section}</p>", unsafe_allow_html=True)
    cols = st.columns(len(section_df))
    for local_i, (_, row) in enumerate(section_df.iterrows()):
        aop = float(row["AOP"]) if pd.notna(row["AOP"]) and row["AOP"] != 0 else 1.0
        py  = float(row["PY"])  if pd.notna(row["PY"])  and row["PY"]  != 0 else 1.0
        vs_aop = (float(row["Actual"]) - aop) / abs(aop) * 100
        vs_py  = (float(row["Actual"]) - py)  / abs(py)  * 100
        unit = str(row["Unit"]) if pd.notna(row["Unit"]) else ""
        with cols[local_i]:
            kpi_card(
                name=row["KPI_Name"],
                actual=row["Actual"],
                unit=unit,
                vs_aop_pct=vs_aop,
                vs_py_pct=vs_py,
                status_emoji=str(row["Status"]),
                accent_color=KPI_ACCENTS[local_i % len(KPI_ACCENTS)],
            )

st.markdown("---")

# ── Financial Overview ────────────────────────────────────────────────────────
st.markdown("### Financial Overview")

col1, col2 = st.columns(2)
with col1:
    fig = line_chart(
        fin, x="Month",
        y_cols=["Revenue", "Revenue_AOP", "Revenue_PY"],
        title="Revenue",
        colors=[BLUE, BLUE_DIM, WHITE_DIM],
        dash_cols=["Revenue_AOP", "Revenue_PY"],
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = line_chart(
        fin, x="Month",
        y_cols=["EBITDA", "EBITDA_AOP", "EBITDA_PY"],
        title="EBITDA",
        colors=[GREEN, GREEN_DIM, WHITE_DIM],
        dash_cols=["EBITDA_AOP", "EBITDA_PY"],
    )
    st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    fig = line_chart(
        fin, x="Month",
        y_cols=["PAT", "PAT_AOP", "PAT_PY"],
        title="Profit After Tax",
        colors=[PURPLE, PURPLE_DIM, WHITE_DIM],
        dash_cols=["PAT_AOP", "PAT_PY"],
    )
    st.plotly_chart(fig, use_container_width=True)

with col4:
    import plotly.graph_objects as go
    fig = line_chart(
        fin, x="Month",
        y_cols=["EBITDA_Margin"],
        title="EBITDA Margin (%)",
        colors=[YELLOW],
    )
    fig.add_hline(
        y=30, line_dash="dot", line_color=WHITE_FAINT,
        annotation_text="30% AOP", annotation_font_color="#5B6675",
        annotation_position="bottom right",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── YTD Snapshot ─────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### YTD Snapshot — Apr 2026")

latest = fin.iloc[-1]
m1, m2, m3, m4 = st.columns(4)

def delta_str(actual, ref):
    if ref and ref != 0:
        pct = (actual - ref) / abs(ref) * 100
        return f"{pct:+.1f}%"
    return "N/A"

m1.metric("Revenue",      f"{latest['Revenue']:,.0f}",
          delta_str(latest["Revenue"], latest["Revenue_AOP"]))
m2.metric("EBITDA",       f"{latest['EBITDA']:,.0f}",
          delta_str(latest["EBITDA"], latest["EBITDA_AOP"]))
m3.metric("PAT",          f"{latest['PAT']:,.0f}",
          delta_str(latest["PAT"], latest["PAT_AOP"]))
m4.metric("EBITDA Margin", f"{latest['EBITDA_Margin']:.1f}%",
          delta_str(latest["EBITDA_Margin"], 30.2))
