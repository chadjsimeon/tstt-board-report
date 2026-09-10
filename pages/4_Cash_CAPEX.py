import streamlit as st

st.set_page_config(page_title="TSTT | Cash & CAPEX", page_icon="💵", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data, load_ar, load_collections_billing
from utils.month_selector import focus_month_selector, filter_data_to_month
from utils.charts import inject_css

inject_css()
focus_month_selector()

st.markdown("""<style>
.main .block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 0 !important;
    max-height: calc(100vh - 60px) !important;
    overflow: auto !important;
}
</style>""", unsafe_allow_html=True)

# ── Main data ─────────────────────────────────────────────────────────────────
data = load_all_data()
cc   = data["Cash_CAPEX"]
cc = filter_data_to_month(cc)
ar   = load_ar()
cb   = load_collections_billing()
cb = filter_data_to_month(cb)

latest = cc.iloc[-1]
first  = cc.iloc[0]

def _safe(val, d=0.0):
    return float(val) if pd.notna(val) else d

cash_val   = _safe(latest["Cash_Balance"])
cash_delta = cash_val - _safe(first["Cash_Balance"])
debt_val   = _safe(latest["Net_Debt"])
debt_delta = debt_val - _safe(first["Net_Debt"])
fcf_month  = _safe(latest["FCF"])

# Filter CAPEX to current financial year (Apr–Mar)
_cc_dt    = pd.to_datetime(cc["Month"], format="%b-%y", errors="coerce")
_lat_dt   = pd.to_datetime(latest["Month"], format="%b-%y")
_fy_year  = _lat_dt.year if _lat_dt.month >= 4 else _lat_dt.year - 1
_cc_fy    = cc[(_cc_dt >= pd.Timestamp(_fy_year, 4, 1)) & (_cc_dt <= pd.Timestamp(_fy_year + 1, 3, 31))]

capex_act       = float(_cc_fy["CAPEX_Actual"].sum())
capex_plan_raw  = _cc_fy["CAPEX_Plan"].sum()
capex_plan      = float(capex_plan_raw) if pd.notna(capex_plan_raw) and capex_plan_raw > 0 else capex_act / 0.85
capex_remaining = capex_plan - capex_act
capex_progress  = min(capex_act / capex_plan * 100, 100) if capex_plan else 0

# ── Collections — read from Collections_Billing sheet ─────────────────────────
latest_month = str(latest["Month"])
prior_month  = None  # no longer derived from billing column headers

cb_latest = cb[cb["Month"] == latest_month] if not cb.empty else pd.DataFrame()

def _cb_val(group_filter, col, exclude=None):
    if cb_latest.empty or col not in cb_latest.columns:
        return None
    mask = cb_latest["Group"].str.upper().str.contains(group_filter.upper(), na=False)
    if exclude:
        mask &= ~cb_latest["Group"].str.upper().str.contains(exclude.upper(), na=False)
    rows = cb_latest[mask]
    if rows.empty:
        return None
    val = pd.to_numeric(rows.iloc[0][col], errors="coerce")
    return float(val) if pd.notna(val) else None

govt_coll     = _cb_val("GOV", "Collections", exclude="NON")
nongov_coll   = _cb_val("NON", "Collections")
consumer_coll = _cb_val("CONSUMER", "Collections")
amplia_coll   = _cb_val("AMPLIA", "Collections")

govt_pct     = _cb_val("GOV", "Collections_Pct", exclude="NON")
nongov_pct   = _cb_val("NON", "Collections_Pct")
consumer_pct = _cb_val("CONSUMER", "Collections_Pct")
amplia_pct   = _cb_val("AMPLIA", "Collections_Pct")

def _pct_color(pct, group="gov"):
    """RAG color for collections % using document thresholds.
    gov/nongov: Green >=95%, Amber >=90%, Red <90%.
    consumer/amplia: Green >=80%, Amber >=75%, Red <75%."""
    if pct is None:
        return "#4488ff"
    if group in ("consumer", "amplia"):
        if pct >= 80: return "#00e676"
        if pct >= 75: return "#f59e0b"
        return "#ef4444"
    else:
        if pct >= 95: return "#00e676"
        if pct >= 90: return "#f59e0b"
        return "#ef4444"

# ── AR aging ──────────────────────────────────────────────────────────────────
AR_BUCKETS = [
    ("0–30d",   "0_30",   "#00e676"),
    ("30–60d",  "31_60",  "#4488ff"),
    ("60–90d",  "61_90",  "#FFD700"),
    ("90–360d", "90_360", "#FF8844"),
    ("360+d",   "360p",   "#ef4444"),
]
if ar:
    gov, non_gov, total = ar["gov"], ar["non_gov"], ar["total"]
else:
    gov     = {"0_30": 26.4,  "31_60": 15.9, "61_90": 20.2, "90_360": 65.9,  "360p": 939.9,  "total": 1068.3}
    non_gov = {"0_30": 51.4,  "31_60": 13.8, "61_90": 15.6, "90_360": 66.3,  "360p": 352.8,  "total": 500.0}
    total   = {"0_30": 77.8,  "31_60": 29.7, "61_90": 35.8, "90_360": 132.2, "360p": 1292.7, "total": 1568.3}
AR_TOTAL = total["total"]
_ar_max  = max(gov["total"], non_gov["total"])

_CAP_360 = 38  # max visual % allocated to 360+d bar

def _pill_row(label, d):
    pct_w = 100
    total  = d["total"] or 1

    # Actual percentages used for labels — never distorted
    actuals = {key: d[key] / total * 100 for _, key, _ in AR_BUCKETS}

    # Visual percentages: cap 360+d and proportionally expand the rest
    capped = actuals.get("360p", 0) > _CAP_360
    if capped:
        non360_sum = sum(d[key] for _, key, _ in AR_BUCKETS if key != "360p" and d[key] > 0) or 1
        visual = {
            key: (_CAP_360 if key == "360p" else d[key] / non360_sum * (100 - _CAP_360))
            for _, key, _ in AR_BUCKETS
        }
    else:
        visual = dict(actuals)

    parts = []
    for bl, key, color in AR_BUCKETS:
        if d[key] <= 0:
            continue
        pa = actuals[key]   # actual % — goes in label
        pv = visual[key]    # visual flex width

        # Label always shows actual %, revealed if bar is wide enough
        show_lbl = pv > 2 or (key == "360p" and capped)
        lbl = (
            f'<span style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
            f'font-size:1.35rem;font-weight:700;color:rgba(0,0,0,0.85);white-space:nowrap">'
            f'{pa:.0f}%</span>'
        ) if show_lbl else ""

        # Axis-break indicator: diagonal hatching + "//" on left edge of capped 360+d bar
        bmark = ""
        if key == "360p" and capped:
            bmark = (
                f'<div style="position:absolute;left:0;top:0;bottom:0;width:22px;'
                f'background:repeating-linear-gradient(-55deg,'
                f'rgba(0,0,0,0) 0px,rgba(0,0,0,0) 3px,'
                f'rgba(22,27,34,0.82) 3px,rgba(22,27,34,0.82) 5px);'
                f'z-index:1;pointer-events:none"></div>'
                f'<span style="position:absolute;left:3px;top:50%;transform:translateY(-50%);'
                f'font-size:0.55rem;font-weight:900;color:rgba(255,255,255,0.78);'
                f'letter-spacing:-2px;z-index:2">//</span>'
            )

        min_w = "46" if (key == "360p" and capped) else "14"
        parts.append(
            f'<div title="{bl}: {d[key]:,.1f}  ({pa:.1f}% of total)" '
            f'style="flex:{max(pv, 0.001):.3f};min-width:{min_w}px;'
            f'background:{color};border-radius:4px;height:100%;position:relative;overflow:hidden">'
            f'{bmark}{lbl}</div>'
        )

    return (
        f'<div style="margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
        f'<span style="font-size:1.4rem;color:white;font-weight:600">{label}</span>'
        f'<span style="font-size:1.4rem;color:#aaaacc;font-weight:700">{d["total"]:,.1f}</span>'
        f'</div>'
        f'<div style="display:flex;gap:2px;height:38px;width:{pct_w:.1f}%">{"".join(parts)}</div>'
        f'</div>'
    )

ar_legend = "".join(
    f'<div style="display:flex;align-items:center;gap:5px">'
    f'<span style="width:10px;height:10px;border-radius:2px;background:{c};display:inline-block"></span>'
    f'<span style="font-size:1.35rem;color:#8899aa;white-space:nowrap">{bl}</span></div>'
    for bl, _, c in AR_BUCKETS
)

# ── Derived display values ────────────────────────────────────────────────────
cash_dc   = "#00e676" if cash_delta >= 0 else "#ef4444"
debt_dc   = "#ef4444" if debt_delta >= 0 else "#00e676"
fcf_color = "#00e676" if fcf_month  >= 0 else "#ef4444"

capex_over    = capex_act > capex_plan
cap_bar_color = "linear-gradient(90deg,#ef4444,#ff6b6b)" if capex_over else "linear-gradient(90deg,#1d4ed8,#4a9eff)"
cap_pct_color = "#ef4444" if capex_over else "#4a9eff"
cap_rem_color = "#ef4444" if capex_remaining < 0 else "#6688aa"
cap_rem_label = "over budget" if capex_remaining < 0 else "remaining"
cap_rem_sign  = "+" if capex_remaining < 0 else ""

# ── KPI row ───────────────────────────────────────────────────────────────────
def _kpi(label, value, sub, color):
    return (
        f'<div style="flex:1;background:#161B22;padding:12px 16px;border:1px solid #21262d;'
        f'border-left:3px solid {color};border-radius:10px">'
        f'<div style="font-size:1.35rem;font-weight:700;color:#556677;text-transform:uppercase;'
        f'letter-spacing:1.2px;margin-bottom:8px">{label}</div>'
        f'<div style="font-size:3.0rem;font-weight:800;color:white;line-height:1">{value}</div>'
        f'<div style="font-size:1.35rem;color:{color};font-weight:600;margin-top:6px">{sub}</div>'
        f'</div>'
    )

# ── Row 1: Cash chart + KPI cards  |  AR Aging ───────────────────────────────
c_chart, c_ar = st.columns([55, 45])

with c_chart:
    y = cc["Cash_Balance"].ffill().fillna(0)
    y_min, y_max = float(y.min()), float(y.max())
    pad = (y_max - y_min) * 0.18 if y_max != y_min else abs(y_max) * 0.12 or 50

    fig = go.Figure(go.Scatter(
        x=cc["Month"], y=y, mode="lines+markers",
        line=dict(color="#00e676", width=2.5),
        marker=dict(size=6, color="#00e676"),
        fill="tozeroy", fillcolor="rgba(0,230,118,0.07)",
        showlegend=False,
        hovertemplate="%{x}: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"), height=310, showlegend=False,
        margin=dict(l=8, r=8, t=32, b=8),
        title=dict(text="<b>Cash Balance Trend</b>", font=dict(size=22, color="white"), x=0),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=18), showline=False),
        yaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=18),
                   range=[y_min - pad, y_max + pad], zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f'<div style="display:flex;gap:10px;margin-top:4px">'
        f'{_kpi("Cash Balance",   f"{cash_val:,.0f}",  "",  cash_dc)}'
        f'{_kpi("Net Debt",       f"{debt_val:,.0f}",  "",  debt_dc)}'
        f'{_kpi("Free Cash Flow", f"{fcf_month:,.0f}", "",  fcf_color)}'
        f'</div>',
        unsafe_allow_html=True,
    )

with c_ar:
    # AR Aging
    st.markdown(f"""
<div style="background:#161B22;border-radius:8px;padding:12px 18px;
            border:1px solid #21262d;margin-top:8px">
  <div style="font-size:1.35rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:8px">AR Aging</div>
  <div style="font-size:1.4rem;color:#556677;margin-bottom:12px">
    Total <strong style="color:#aaaacc">{AR_TOTAL:,.1f}</strong>
    &nbsp;·&nbsp; Gov <strong style="color:#aaaacc">{gov['total']:,.1f}</strong>
    &nbsp;·&nbsp; Non-Gov <strong style="color:#aaaacc">{non_gov['total']:,.1f}</strong>
  </div>
  {_pill_row("Government", gov)}
  {_pill_row("Non-Government", non_gov)}
  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:6px">{ar_legend}</div>
</div>""", unsafe_allow_html=True)

    # Collections
    def _coll_box(label, coll_val, pct_val, accent, group="gov"):
        color = _pct_color(pct_val, group)
        if pct_val is not None:
            main = f'<div style="font-size:3.0rem;font-weight:800;color:{color};line-height:1">{pct_val:.1f}%</div>'
        elif coll_val is not None:
            main = '<div style="font-size:1.4rem;font-weight:600;color:#556677;margin-top:4px">Billings pending</div>'
        else:
            main = '<div style="font-size:1.4rem;font-weight:600;color:#3a4455;line-height:1.3">Data pending</div>'
        return (
            f'<div style="flex:1;background:#161B22;border:1px solid #21262d;'
            f'border-top:2px solid {accent};border-radius:8px;padding:14px 16px">'
            f'<div style="font-size:1.35rem;font-weight:700;color:{accent};text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:8px">{label}</div>'
            f'{main}</div>'
        )

    st.markdown(
        f'<div style="font-size:1.35rem;font-weight:700;color:#556677;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-top:10px;margin-bottom:8px">'
        f'Collections — {latest_month}</div>'
        f'<div style="display:flex;gap:8px;margin-bottom:8px">'
        f'{_coll_box("Government",     govt_coll,     govt_pct,     "#4488ff", "gov")}'
        f'{_coll_box("Non-Government", nongov_coll,   nongov_pct,   "#a78bfa", "nongov")}'
        f'</div>'
        f'<div style="display:flex;gap:8px">'
        f'{_coll_box("Consumer Sales", consumer_coll, consumer_pct, "#00e676", "consumer")}'
        f'{_coll_box("Amplia",         amplia_coll,   amplia_pct,   "#FF8844", "amplia")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # CAPEX
    st.markdown(f"""
<div style="background:#161B22;border-radius:8px;padding:12px 18px;
            border:1px solid #21262d;margin-top:10px">
  <div style="font-size:1.35rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:12px">CAPEX Spend to Date</div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="color:#aaaacc;font-size:20px">YTD vs Annual Budget</span>
    <span style="color:{cap_pct_color};font-weight:800;font-size:44px">{capex_progress:.1f}%</span>
  </div>
  <div style="background:#1e1e3a;border-radius:6px;height:16px;overflow:hidden;margin-bottom:16px">
    <div style="background:{cap_bar_color};width:{capex_progress:.1f}%;height:100%;border-radius:6px"></div>
  </div>
  <div style="display:flex;justify-content:space-between">
    <div>
      <div style="color:{cap_pct_color};font-size:27px;font-weight:700">{capex_act:,.0f}</div>
      <div style="color:#6688aa;font-size:20px;margin-top:4px">spent YTD</div>
    </div>
    <div style="text-align:center">
      <div style="color:{cap_rem_color};font-size:27px;font-weight:700">{cap_rem_sign}{abs(capex_remaining):,.0f}</div>
      <div style="color:#6688aa;font-size:20px;margin-top:4px">{cap_rem_label}</div>
    </div>
    <div style="text-align:right">
      <div style="color:#aaaacc;font-size:27px;font-weight:700">{capex_plan:,.0f}</div>
      <div style="color:#6688aa;font-size:20px;margin-top:4px">annual budget</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
