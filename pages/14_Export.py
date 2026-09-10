import streamlit as st

st.set_page_config(page_title="TSTT | Export to PowerPoint",
                   page_icon="📥", layout="wide")

import subprocess
import sys
from pathlib import Path

import pandas as pd
from utils.data_loader import load_all_data
from utils.month_selector import focus_month_selector
from utils import theme
from utils.charts import inject_css
from tools.pptx_screenshot_export import discover_pages

inject_css()
focus_month_selector()

ROOT = Path(__file__).resolve().parent.parent

FORMATS = {
    "PowerPoint (.pptx)": {
        "script": ROOT / "tools" / "pptx_screenshot_export.py",
        "out":    ROOT / "exports" / "TSTT_Board_Report.pptx",
        "ext":    "pptx",
        "mime":   "application/vnd.openxmlformats-officedocument."
                  "presentationml.presentation",
        "app":    "PowerPoint",
    },
    "Word (.docx)": {
        "script": ROOT / "tools" / "docx_screenshot_export.py",
        "out":    ROOT / "exports" / "TSTT_Board_Report.docx",
        "ext":    "docx",
        "mime":   "application/vnd.openxmlformats-officedocument."
                  "wordprocessingml.document",
        "app":    "Word",
    },
}

# Page labels available to export (excludes the Export page itself)
ALL_LABELS = [label for label, _ in discover_pages()]

data = load_all_data()

# ── Period label ────────────────────────────────────────────────────────────────
focus_month = st.session_state.get("focus_month")
try:
    period_label = pd.to_datetime(
        focus_month, format="%b-%y"
    ).strftime("%B %Y") if focus_month else ""
except Exception:
    period_label = ""

# ── Format ───────────────────────────────────────────────────────────────────────
fmt_name = st.radio(
    "Export format",
    options=list(FORMATS),
    horizontal=True,
    help="PowerPoint is the board-pack format. Word is kept as an alternative.",
)
FMT    = FORMATS[fmt_name]
SCRIPT = FMT["script"]
OUT    = FMT["out"]

_is_word = FMT["ext"] == "docx"
_target  = ("one landscape Word page per dashboard page, under a heading"
            if _is_word else "full-bleed on a 16:9 slide")
_unit    = "page" if _is_word else "slide"
_style   = theme.LABELS[theme.active()]

# ── About ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:#161b22;border-radius:8px;padding:18px 22px;
            border:1px solid #21262d;margin-bottom:20px;
            font-size:0.85rem;color:#ccccdd;line-height:1.8">
  <div style="font-size:0.7rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:10px">Board Pack — {FMT['app']} Export</div>
  Each selected page is screenshotted in a headless browser and placed
  {_target}, so the document matches the live dashboard pixel-for-pixel.
  By default every page is exported, in sidebar order, starting with the Executive
  Summary. Use the selector below to export a single page or any subset.
  Pages taller than one {_unit} are split automatically.
  <div style="margin-top:10px">Captured in the report style selected in the
  sidebar — currently <strong>{_style}</strong>.</div>
</div>
""", unsafe_allow_html=True)

# ── Page selection ────────────────────────────────────────────────────────────────
selected_pages = st.multiselect(
    "Pages to export",
    options=ALL_LABELS,
    default=ALL_LABELS,
    help="Defaults to all pages. Remove pages, or pick just one, to export a subset.",
)

# ── Notes ────────────────────────────────────────────────────────────────────────
_opens = ("Word, Google Docs, or LibreOffice"
          if _is_word else "PowerPoint, Keynote, or LibreOffice")
st.markdown(f"""
<div style="background:#0d1117;border-radius:8px;padding:14px 20px;
            border:1px solid #21262d;margin-bottom:20px;
            font-size:0.8rem;color:#556677;line-height:1.7">
  <strong style="color:#8899aa">Notes:</strong>
  Generation takes roughly 2–3 minutes while every page is rendered and captured.
  The resulting file is a standard .{FMT['ext']} — open in {_opens}.
</div>
""", unsafe_allow_html=True)

# ── Build button ─────────────────────────────────────────────────────────────────
n_sel = len(selected_pages)
col_btn, _ = st.columns([1, 3])
with col_btn:
    generate = st.button(f"Build {FMT['app']}", type="primary",
                         use_container_width=True, disabled=(n_sel == 0))
if n_sel == 0:
    st.warning("Select at least one page to export.")

if generate and n_sel:
    port = st.get_option("server.port") or 8501
    cmd = [sys.executable, str(SCRIPT),
           "--url", f"http://localhost:{port}",
           "--out", str(OUT),
           "--theme", theme.active()]
    if focus_month:
        cmd += ["--focus-month", focus_month]
    # The Word cover page shows a spelled-out period ("June 2026")
    if _is_word and period_label:
        cmd += ["--period-label", period_label]
    # Pass an explicit subset unless every page is selected
    if n_sel < len(ALL_LABELS):
        cmd += ["--pages", ",".join(selected_pages)]

    _what = ("every page" if n_sel == len(ALL_LABELS)
             else (f"“{selected_pages[0]}”" if n_sel == 1 else f"{n_sel} pages"))
    _est  = "2–3 minutes" if n_sel > 3 else "under a minute"
    result = None
    with st.spinner(f"Capturing {_what} in a headless browser — this takes {_est}…"):
        try:
            result = subprocess.run(
                cmd, cwd=str(ROOT),
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=900,
            )
        except subprocess.TimeoutExpired:
            st.error("Export timed out after 15 minutes.")

    if result is not None:
        if result.returncode == 0 and OUT.exists():
            _base = (f"TSTT_{selected_pages[0].replace(' ', '_')}" if n_sel == 1
                     else "TSTT_Board_Report")
            _ext  = FMT["ext"]
            fname = (f"{_base}_{period_label.replace(' ', '_')}.{_ext}"
                     if period_label else f"{_base}.{_ext}")
            st.download_button(
                label=f"Download {fname}",
                data=OUT.read_bytes(),
                file_name=fname,
                mime=FMT["mime"],
                use_container_width=True,
            )
            st.success("Export ready — click the button above to download.")
        else:
            st.error("Export failed — see the log below.")
            st.code((result.stderr or result.stdout or "no output").strip()[-3000:])
