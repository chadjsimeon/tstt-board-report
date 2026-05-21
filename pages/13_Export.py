import streamlit as st

st.set_page_config(page_title="TSTT | Export to PowerPoint",
                   page_icon="📥", layout="wide")

import pandas as pd
from utils.data_loader import load_all_data
from utils.charts import inject_css
from utils.ar_loader import load_ar_aging
from utils.pptx_export import build_pptx

inject_css()

data = load_all_data()
ar   = load_ar_aging()

# ── Period label ───────────────────────────────────────────────────────────────
try:
    fin = data.get("Financial_Monthly", pd.DataFrame())
    period_label = pd.to_datetime(
        fin["Month"].iloc[-1], format="%b-%y"
    ).strftime("%B %Y") if not fin.empty else ""
except Exception:
    period_label = ""

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="width:100%;background:#0d1117;padding:16px 24px;margin-bottom:20px;display:block;">
  <div style="font-size:0.75rem;color:#00e676;font-weight:600;margin-bottom:4px;">EXPORT</div>
  <div style="font-size:1.4rem;font-weight:700;color:white;">Download Board Report</div>
  <div style="font-size:0.8rem;color:#8b949e;margin-top:4px;">
      Generates a branded dark-theme PowerPoint deck &nbsp;·&nbsp; YTD {period_label}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Board Pack Contents ────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#161b22;border-radius:8px;padding:18px 22px;
            border:1px solid #21262d;margin-bottom:20px">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:14px">Board Pack Contents — 10 Slides</div>
  <table style="width:100%;border-collapse:collapse;font-size:0.82rem;color:#ccccdd">
    <tr style="border-bottom:1px solid #21262d">
      <td style="padding:6px 10px;color:#556677;font-weight:700;width:40px">#</td>
      <td style="padding:6px 10px;font-weight:700">Section</td>
      <td style="padding:6px 10px;color:#556677">Content</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22">
      <td style="padding:6px 10px;color:#556677">01</td>
      <td style="padding:6px 10px">Title</td>
      <td style="padding:6px 10px;color:#556677">TSTT logo, report period, CONFIDENTIAL</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22;background:rgba(255,255,255,0.02)">
      <td style="padding:6px 10px;color:#556677">02</td>
      <td style="padding:6px 10px">Enterprise Scorecard</td>
      <td style="padding:6px 10px;color:#556677">KPI table — Financial, Customer, Network, People</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22">
      <td style="padding:6px 10px;color:#556677">03</td>
      <td style="padding:6px 10px">Financial Performance</td>
      <td style="padding:6px 10px;color:#556677">Revenue & EBITDA trends vs AOP vs PY + KPI row</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22;background:rgba(255,255,255,0.02)">
      <td style="padding:6px 10px;color:#556677">04</td>
      <td style="padding:6px 10px">EBITDA Bridge</td>
      <td style="padding:6px 10px;color:#556677">Waterfall: AOP → Actual with variance components</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22">
      <td style="padding:6px 10px;color:#556677">05</td>
      <td style="padding:6px 10px">OPEX & Cost Management</td>
      <td style="padding:6px 10px;color:#556677">Category bullet chart: Actual vs Plan</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22;background:rgba(255,255,255,0.02)">
      <td style="padding:6px 10px;color:#556677">06</td>
      <td style="padding:6px 10px">Cash, Working Capital & CAPEX</td>
      <td style="padding:6px 10px;color:#556677">Cash trend, AR Aging chart, KPI row</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22">
      <td style="padding:6px 10px;color:#556677">07</td>
      <td style="padding:6px 10px">Consumer</td>
      <td style="padding:6px 10px;color:#556677">Revenue by segment, Subscriber trends</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22;background:rgba(255,255,255,0.02)">
      <td style="padding:6px 10px;color:#556677">08</td>
      <td style="padding:6px 10px">Business Sales</td>
      <td style="padding:6px 10px;color:#556677">Revenue by segment, Revenue & Gross Profit combo</td>
    </tr>
    <tr style="border-bottom:1px solid #161b22">
      <td style="padding:6px 10px;color:#556677">09</td>
      <td style="padding:6px 10px">DPDI</td>
      <td style="padding:6px 10px;color:#556677">Revenue by product, monthly trend excl. e-GOVTT</td>
    </tr>
    <tr>
      <td style="padding:6px 10px;color:#556677">10</td>
      <td style="padding:6px 10px">Amplia</td>
      <td style="padding:6px 10px;color:#556677">Revenue, EBITDA and PAT trend charts</td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)

# ── Notes ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#0d1117;border-radius:8px;padding:14px 20px;
            border:1px solid #21262d;margin-bottom:20px;
            font-size:0.8rem;color:#556677;line-height:1.7">
  <strong style="color:#8899aa">Notes:</strong>
  Generation takes approximately 30–60 seconds on first run while charts are rendered.
  The resulting file is a standard .pptx — open in PowerPoint, Keynote, or LibreOffice.
  Dark theme matches the dashboard with TSTT branding and green accents.
</div>
""", unsafe_allow_html=True)

# ── Build button ───────────────────────────────────────────────────────────────
col_btn, col_spacer = st.columns([1, 3])
with col_btn:
    generate = st.button("Build PowerPoint", type="primary", use_container_width=True)

if generate:
    with st.spinner("Generating slides — rendering charts via kaleido..."):
        try:
            buf = build_pptx(data, ar_data=ar)
            fname = f"TSTT_Board_Report_{period_label.replace(' ', '_')}.pptx" \
                    if period_label else "TSTT_Board_Report.pptx"
            st.download_button(
                label="Download TSTT_Board_Report.pptx",
                data=buf,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
            st.success("Board pack ready — click the button above to download.")
        except Exception as exc:
            st.error(f"Export failed: {exc}")
            st.info(
                "Ensure `kaleido==0.2.1` and `python-pptx>=1.0.2` are installed: "
                "`pip install 'kaleido>=1.0.0' python-pptx`"
            )
