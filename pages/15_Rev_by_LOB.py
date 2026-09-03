import streamlit as st

st.set_page_config(page_title="TSTT | Rev by LOB", page_icon="🎯", layout="wide")

import math

import pandas as pd
import plotly.graph_objects as go

from utils.data_loader import load_all_data
from utils.month_selector import focus_month_selector, filter_data_to_month
from utils.charts import inject_css
from utils.rag import rev_var_rag, GREEN, AMBER, RED, GREY

inject_css()
focus_month_selector()

# ── Config ───────────────────────────────────────────────────────────────────
FY_START_MONTH = 4      # 4 = fiscal year starts April (Apr–Mar). Set 1 for calendar YTD.

INK, MUTED, FAINT, GRID = "#1F2328", "#5B6675", "#7A8494", "#E6EAF0"
PY_DOT   = "#8A8F98"
DOT_SIZE = 24

# X domain is derived from the data, never fixed: round the peak up to the next
# $50 then add headroom, so the largest dot can't touch the right edge and a
# growing YTD can't silently push a dot off the chart.
X_STEP     = 100        # tick interval
X_ROUND    = 50         # round the domain up to a multiple of this
X_HEADROOM = 0.08       # extra space past the rounded peak
X_PAD_L    = 0.015      # left pad as a fraction of the domain, so near-zero
                        # dots (DPDI) are not half-clipped by the axis

LABEL_GUTTER = 150      # px reserved left of the plot for the LOB labels

# Plot area is sized as a FRACTION of the figure via xaxis.domain rather than by
# pixel margins. Pixel margins make the plot's share of the card drift with the
# viewport — it measured 44% at 1400px and 64% at the 1920px export width. The
# domain holds it at ~57% everywhere, with the value column just to its right.
X_DOMAIN = [0.14, 0.715]

# Brighter on-card RAG than the utils/rag defaults. Page-local by design: editing
# utils/rag.py would recolour every other page's variance text.
BRIGHT = {GREEN: "#16A34A", AMBER: "#F59E0B", RED: "#DC2626", GREY: MUTED}

LOBS = [
    ("Consumer", "CONSUMER SALES"),
    ("Business", "BUSINESS SALES"),
    ("AMPLIA",   "AMPLIA"),
    ("DPDI",     "DPDI"),
]

# ── Data ─────────────────────────────────────────────────────────────────────
data = load_all_data()
pnl  = filter_data_to_month(data["PnL_Breakdown"].copy())
pnl["_dt"] = pd.to_datetime(pnl["Month"], format="%b-%y", errors="coerce")
pnl = pnl.dropna(subset=["_dt"]).sort_values("_dt")

_rev_cols = [f"{col}_Rev" for _, col in LOBS]
_actual   = pnl[pnl[_rev_cols].fillna(0).abs().sum(axis=1) > 0]
if _actual.empty:
    st.warning("No segment revenue available on or before the selected focus month.")
    st.stop()

# The focus month defaults to the last month in Financial_Monthly, which runs to
# Mar-27 on budget rows. Clamp to the last month carrying actual segment revenue —
# otherwise a few real CY months get compared against a full 12-month PY.
end_dt   = _actual["_dt"].max()
fy_start = pd.Timestamp(end_dt.year - (1 if end_dt.month < FY_START_MONTH else 0),
                        FY_START_MONTH, 1)

cy_win = pnl[pnl["_dt"].between(fy_start, end_dt)]
py_win = pnl[pnl["_dt"].between(fy_start - pd.DateOffset(months=12),
                                end_dt   - pd.DateOffset(months=12))]


def _sum(win, col):
    return float(win[col].fillna(0).sum()) if col in win.columns else 0.0


# PY is the 12-month lag of <segment>_Rev, NOT the <segment>_Rev_PY columns. Those
# are only populated Apr-25..Apr-26 and are NaN across the whole current window,
# which understates PY roughly fourfold. Do not "simplify" this back to _Rev_PY.
rows = [(label, _sum(cy_win, f"{col}_Rev"), _sum(py_win, f"{col}_Rev"))
        for label, col in LOBS]
rows.sort(key=lambda r: r[1], reverse=True)

labels   = [r[0] for r in rows]
cy_vals  = [r[1] for r in rows]
py_vals  = [r[2] for r in rows]
variance = [c - p for c, p in zip(cy_vals, py_vals)]
# rev_var_rag owns the threshold rule (>=0 green / >=-10 amber / <-10 red); the
# BRIGHT map only restyles its result.
rags = [BRIGHT[rev_var_rag((c - p) / abs(p) * 100) if p else GREY]
        for c, p in zip(cy_vals, py_vals)]

other_cy = _sum(cy_win, "OTHER_Rev")
other_py = _sum(py_win, "OTHER_Rev")


# ── Formatting ───────────────────────────────────────────────────────────────
def _n(v):
    """Values: one decimal below 10, whole numbers otherwise."""
    return f"{v:,.1f}" if abs(v) < 10 else f"{v:,.0f}"


def _sn(v):
    """Variance: whole numbers unless the absolute value is below 1."""
    return f"{v:+,.1f}" if abs(v) < 1 else f"{v:+,.0f}"


def _m(v):
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.0f}M"


# ── Figure ───────────────────────────────────────────────────────────────────
# The stPlotlyChart div is already styled as a card in assets/style.css, so the
# title, legend, labels, value column and footnote all live inside the figure.
# Wrapping this in an HTML card would double the border.
_peak = max(cy_vals + py_vals + [0.0])
x_max = math.ceil(_peak / X_ROUND) * X_ROUND * (1 + X_HEADROOM)

fig = go.Figure()

# PY first, CY second — trace order is z-order, so CY draws on top where they
# overlap. The white outline keeps both readable when values are close.
fig.add_trace(go.Scatter(
    x=py_vals, y=labels, mode="markers", showlegend=False,
    marker=dict(size=DOT_SIZE, color=PY_DOT, line=dict(color="#FFFFFF", width=2)),
    hovertemplate="%{y} PY: %{x:,.1f}<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=cy_vals, y=labels, mode="markers", showlegend=False,
    marker=dict(size=DOT_SIZE, color=rags, line=dict(color="#FFFFFF", width=2)),
    hovertemplate="%{y} CY: %{x:,.1f}<extra></extra>",
))

# Legend drawn by hand rather than with Plotly's own. Plotly hard-caps a legend
# swatch at 16px, so a built-in legend can never match a 20px chart dot; pixel-
# sized shapes anchored to paper coords give exactly DOT_SIZE either way.
LEG_ROW_Y = 26          # px above the plot top, centre of the legend row
_LEG = [("CY", BRIGHT[GREEN], -110, -92), ("PY", PY_DOT, -50, -32)]

legend_shapes = [
    dict(
        type="circle", xref="x domain", yref="y domain",
        xsizemode="pixel", ysizemode="pixel", xanchor=1, yanchor=1,
        x0=dot_x - DOT_SIZE / 2, x1=dot_x + DOT_SIZE / 2,
        y0=LEG_ROW_Y - DOT_SIZE / 2, y1=LEG_ROW_Y + DOT_SIZE / 2,
        fillcolor=colour, line=dict(color="#FFFFFF", width=2), layer="above",
    )
    for _name, colour, dot_x, _text_x in _LEG
]

legend_ann = [
    dict(
        xref="x domain", x=1, xanchor="left", xshift=text_x,
        yref="y domain", y=1, yanchor="middle", yshift=LEG_ROW_Y,
        text=name, showarrow=False,
        font=dict(color=MUTED, size=15, family="Inter, sans-serif"),
    )
    for name, _colour, _dot_x, text_x in _LEG
]

# LOB labels as annotations rather than y ticks: Plotly tick labels are right-
# aligned against the axis and have no alignment property, so left-aligning them
# needs a fixed pixel offset. xshift is container-width independent, unlike a
# negative paper x.
label_ann = [
    dict(
        xref="x domain", x=0, xanchor="left", xshift=-LABEL_GUTTER,
        yref="y", y=label, yanchor="middle",
        text=f"<b>{label}</b>", showarrow=False, align="left",
        font=dict(color=INK, size=17, family="Inter, sans-serif"),
    )
    for label in labels
]

# Value column. Constant paper x plus a pixel shift gives a true left-aligned
# column (data-coord x would leave it ragged); category y locks each line to its
# own row through the sort and the reversed axis.
value_ann = [
    dict(
        xref="x domain", x=1, xanchor="left", xshift=14,
        yref="y", y=label, yanchor="middle",
        text=(f"{_n(c)} → {_n(p)} "
              f'<span style="color:{rc}"><b>({_sn(v)})</b></span>'),
        showarrow=False, align="left",
        font=dict(color=MUTED, size=17, family="Inter, sans-serif"),
    )
    for label, c, p, v, rc in zip(labels, cy_vals, py_vals, variance, rags)
]

footnote_ann = dict(
    xref="x domain", x=0, xanchor="left", xshift=-LABEL_GUTTER,
    yref="y domain", y=0, yanchor="top", yshift=-32,
    text=(f"Other revenue (mainly Consolidated Adjustments) "
          f"({_m(other_cy)} YTD / {_m(other_py)} PY) excluded from chart"),
    showarrow=False,
    font=dict(color=FAINT, size=12, family="Inter, sans-serif"),
)

fig.update_layout(
    height=625,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=INK, family="Inter, sans-serif", size=15),
    title=dict(
        text=("<b>Revenue by LOB</b>  "
              f'<span style="font-size:15px;color:{MUTED}">YTD vs PY · TT$M</span>'),
        font=dict(size=24, color=INK, family="Inter, sans-serif"),
        x=0, xanchor="left", y=1, yanchor="top", pad=dict(t=14, l=10),
    ),
    xaxis=dict(
        domain=X_DOMAIN,
        range=[-x_max * X_PAD_L, x_max], tick0=0, dtick=X_STEP, tickprefix="$",
        showgrid=True, gridcolor=GRID, gridwidth=1,
        showline=False, zeroline=False,
        tickfont=dict(color=FAINT, size=14),
    ),
    yaxis=dict(
        categoryorder="array", categoryarray=labels, autorange="reversed",
        showticklabels=False,                       # replaced by label_ann
        showgrid=False, showline=False, zeroline=False, ticks="",
    ),
    margin=dict(l=10, r=10, t=54, b=54),   # width is governed by X_DOMAIN
    annotations=label_ann + value_ann + legend_ann + [footnote_ann],
    shapes=legend_shapes,
    showlegend=False,
    hoverlabel=dict(bgcolor="#F6F8FA", font_color=INK, bordercolor="#D0D7DE"),
)

st.plotly_chart(fig, use_container_width=True)
