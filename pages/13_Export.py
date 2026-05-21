import streamlit as st

st.set_page_config(page_title="TSTT | Export to PowerPoint",
                   page_icon="📥", layout="wide")

import subprocess
import sys
from pathlib import Path

import pandas as pd
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()

ROOT   = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "pptx_screenshot_export.py"
OUT    = ROOT / "exports" / "TSTT_Board_Report.pptx"

data = load_all_data()

# ── Period label ────────────────────────────────────────────────────────────────
try:
    fin = data.get("Financial_Monthly", pd.DataFrame())
    period_label = pd.to_datetime(
        fin["Month"].iloc[-1], format="%b-%y"
    ).strftime("%B %Y") if not fin.empty else ""
except Exception:
    period_label = ""

# ── About ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#161b22;border-radius:8px;padding:18px 22px;
            border:1px solid #21262d;margin-bottom:20px;
            font-size:0.85rem;color:#ccccdd;line-height:1.8">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:10px">Board Pack — All Pages</div>
  Every page of the dashboard is screenshotted in a headless browser and placed
  full-bleed on a 16:9 slide, so the deck matches the live dashboard pixel-for-pixel.
  The deck opens with the Executive Summary, then each sidebar page in order —
  Financial Performance, Revenue Mix &amp; Variance, Enterprise Scorecard,
  OPEX Cost, Cash &amp; CAPEX, Consumer Sales, Prepaid / Postpaid / WTTx
  Revenue, Business Sales, DPDI, Amplia Financial and Amplia Commercial.
  Pages taller than a slide are split automatically.
</div>
""", unsafe_allow_html=True)

# ── Notes ────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:#0d1117;border-radius:8px;padding:14px 20px;
            border:1px solid #21262d;margin-bottom:20px;
            font-size:0.8rem;color:#556677;line-height:1.7">
  <strong style="color:#8899aa">Notes:</strong>
  Generation takes roughly 2–3 minutes while every page is rendered and captured.
  The resulting file is a standard .pptx — open in PowerPoint, Keynote, or LibreOffice.
</div>
""", unsafe_allow_html=True)

# ── Build button ─────────────────────────────────────────────────────────────────
col_btn, _ = st.columns([1, 3])
with col_btn:
    generate = st.button("Build PowerPoint", type="primary", use_container_width=True)

if generate:
    port = st.get_option("server.port") or 8501
    result = None
    with st.spinner("Capturing every page in a headless browser — this takes 2–3 minutes…"):
        try:
            result = subprocess.run(
                [sys.executable, str(SCRIPT),
                 "--url", f"http://localhost:{port}",
                 "--out", str(OUT)],
                cwd=str(ROOT),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=900,
            )
        except subprocess.TimeoutExpired:
            st.error("Export timed out after 15 minutes.")

    if result is not None:
        if result.returncode == 0 and OUT.exists():
            fname = (f"TSTT_Board_Report_{period_label.replace(' ', '_')}.pptx"
                     if period_label else "TSTT_Board_Report.pptx")
            st.download_button(
                label=f"Download {fname}",
                data=OUT.read_bytes(),
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
            )
            st.success("Board pack ready — click the button above to download.")
        else:
            st.error("Export failed — see the log below.")
            st.code((result.stderr or result.stdout or "no output").strip()[-3000:])
