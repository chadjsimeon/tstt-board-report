import streamlit as st

st.set_page_config(page_title="TSTT | Number Porting", page_icon="🔁", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_porting_trend
from utils.charts import inject_css
from utils.rag import rev_var_rag
from utils.consumer_common import _pre_kpi, _base_layout
from utils.month_selector import focus_month_selector, filter_data_to_month

inject_css()
focus_month_selector()

pt = load_porting_trend()
pt = filter_data_to_month(pt)

if pt is None or pt.empty:
    st.warning("No data found on the 'Porting Trend' sheet of the master template.")
    st.stop()

# ── Order chronologically ────────────────────────────────────────────────────
pt = pt.copy()
pt["_dt"] = pd.to_datetime(pt["Month"], format="%b-%y", errors="coerce")
pt = pt.sort_values("_dt").reset_index(drop=True)

latest = pt.iloc[-1]
prev   = pt.iloc[-2] if len(pt) >= 2 else latest

in_lat, out_lat  = float(latest["Port_In"]), float(latest["Port_Out"])
net_lat          = in_lat - out_lat
ratio_lat        = in_lat / out_lat if out_lat else float("nan")

in_prev, out_prev = float(prev["Port_In"]), float(prev["Port_Out"])
net_prev          = in_prev - out_prev

in_avg  = float(pt["Port_In"].mean())
out_avg = float(pt["Port_Out"].mean())

in_ytd  = float(pt["Port_In"].sum())
out_ytd = float(pt["Port_Out"].sum())
net_ytd = in_ytd - out_ytd
ratio_ytd = in_ytd / out_ytd if out_ytd else float("nan")

in_spark  = pt["Port_In"].tolist()
out_spark = pt["Port_Out"].tolist()
net_spark = pt["Net"].tolist()


def _pct(cur, ref):
    return (cur - ref) / abs(ref) * 100 if ref else None


# ── KPI tiles ────────────────────────────────────────────────────────────────
GREEN, RED, GREY, BLUE = "#22c55e", "#ef4444", "#7788aa", "#4a9eff"


def _var_line(delta, pct, tag):
    if pct is None:
        return f"— {tag}"
    return f"{delta:+,.0f} | {pct:+.1f}% {tag}"


# Port-Ins — higher is better
in_mom_pct = _pct(in_lat, in_prev)
in_avg_pct = _pct(in_lat, in_avg)
c_in = _pre_kpi(
    "Port-Ins  (from Digicel)", f"{in_lat:,.0f}",
    _var_line(in_lat - in_prev, in_mom_pct, "MoM"), rev_var_rag(in_mom_pct),
    _var_line(in_lat - in_avg, in_avg_pct, "vs avg"), rev_var_rag(in_avg_pct),
    GREEN, in_spark,
)

# Port-Outs — higher is worse, so invert the sign feeding the RAG colour
out_mom_pct = _pct(out_lat, out_prev)
out_avg_pct = _pct(out_lat, out_avg)
c_out = _pre_kpi(
    "Port-Outs  (to Digicel)", f"{out_lat:,.0f}",
    _var_line(out_lat - out_prev, out_mom_pct, "MoM"),
    rev_var_rag(-out_mom_pct) if out_mom_pct is not None else GREY,
    _var_line(out_lat - out_avg, out_avg_pct, "vs avg"),
    rev_var_rag(-out_avg_pct) if out_avg_pct is not None else GREY,
    RED, out_spark,
)

# Net movement — positive = B-Mobile net gain
net_accent = GREEN if net_lat >= 0 else RED
net_mom_delta = net_lat - net_prev
c_net = _pre_kpi(
    "Net Movement", f"{net_lat:+,.0f}",
    f"{net_mom_delta:+,.0f} vs {prev['Month']}", GREEN if net_mom_delta >= 0 else RED,
    f"YTD net {net_ytd:+,.0f}", GREEN if net_ytd >= 0 else RED,
    net_accent, net_spark,
)

# ── Porting scorecard card (net + ratio, explicit) ───────────────────────────
ratio_col = GREEN if (ratio_lat == ratio_lat and ratio_lat >= 1) else RED
_score_rows = [
    ("Port-Ins",  f"+{in_lat:,.0f}",   GREEN),
    ("Port-Outs", f"−{out_lat:,.0f}", RED),
    ("Net",       f"{net_lat:+,.0f}",   GREEN if net_lat >= 0 else RED),
    ("Ratio",     f"{ratio_lat:.2f}×", ratio_col),
]
_score_html = "".join(
    f'<div style="display:flex;justify-content:space-between;padding:5px 0;'
    f'border-bottom:1px solid #1e2a4a;">'
    f'<span style="font-size:29px;color:#7788aa">{lbl}</span>'
    f'<span style="font-size:29px;font-weight:700;color:{col}">{val}</span>'
    f'</div>'
    for lbl, val, col in _score_rows
)
c_score = (
    f'<div style="background:#161B22;border-radius:10px;padding:16px 16px;'
    f'border:1px solid #2a2a4a;border-top:3px solid {BLUE};height:100%">'
    f'<div style="font-size:28px;color:#6677aa;font-weight:700;text-transform:uppercase;'
    f'letter-spacing:1.5px;margin-bottom:10px">Porting Scorecard — {latest["Month"]}</div>'
    f'{_score_html}'
    f'</div>'
)

st.markdown(
    f'<div style="display:flex;gap:12px;margin-bottom:16px">'
    f'<div style="flex:1">{c_in}</div>'
    f'<div style="flex:1">{c_out}</div>'
    f'<div style="flex:1">{c_net}</div>'
    f'<div style="flex:1">{c_score}</div>'
    f'</div>',
    unsafe_allow_html=True,
)


# ── Charts: In vs Out grouped bars | Ratio trend ─────────────────────────────
cl, cr = st.columns([55, 45])

with cl:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pt["Month"], y=pt["Port_In"], name="Port-Ins (from Digicel)",
        marker_color=GREEN,
    ))
    fig.add_trace(go.Bar(
        x=pt["Month"], y=pt["Port_Out"], name="Port-Outs (to Digicel)",
        marker_color=RED,
    ))
    fig.update_layout(barmode="group")
    _base_layout(fig, "Port-Ins vs Port-Outs", 400)
    st.plotly_chart(fig, use_container_width=True)

with cr:
    _ratio_marker = [GREEN if (r == r and r >= 1) else RED for r in pt["Ratio"]]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pt["Month"], y=pt["Ratio"], mode="lines+markers+text",
        name="In:Out ratio",
        line=dict(color="#44EEFF", width=3),
        marker=dict(size=9, color=_ratio_marker,
                    line=dict(color="#0d1117", width=1)),
        text=[f"{r:.2f}×" if r == r else "" for r in pt["Ratio"]],
        textposition="top center", textfont=dict(color="#aabbcc", size=12),
    ))
    fig.add_hline(
        y=1.0, line_dash="dot", line_color="rgba(255,255,255,0.4)",
        annotation_text="1.0× break-even", annotation_font_color="#7788aa",
        annotation_position="bottom right",
    )
    _base_layout(fig, "Port-In : Port-Out Ratio", 400)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
