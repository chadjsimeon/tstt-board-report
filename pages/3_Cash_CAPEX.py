import streamlit as st

st.set_page_config(page_title="TSTT | Cash & CAPEX", page_icon="💵", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data
from utils.charts import inject_css

inject_css()

st.markdown("""<style>
.main .block-container {
    padding-top: 0.5rem !important;
    padding-bottom: 0 !important;
    max-height: calc(100vh - 60px) !important;
    overflow: hidden !important;
}
</style>""", unsafe_allow_html=True)

# ── Data loaders ──────────────────────────────────────────────────────────────
@st.cache_data
def load_collections():
    try:
        df = pd.read_excel("collections (FULL).xlsx", sheet_name="Sheet 1")
        df["LOB"] = df["LOB"].ffill()
        return df
    except Exception:
        return None

@st.cache_data
def load_billings():
    try:
        df = pd.read_excel("billing (M).xlsx", sheet_name="Sheet 1")
        df["LOB"] = df["LOB"].ffill()
        return df
    except Exception:
        return None

@st.cache_data
def load_ar():
    try:
        df = pd.read_excel(
            "Receivables Executive Summary.xlsx",
            sheet_name="Exec. Summary Receivables",
            header=None,
        )
    except Exception:
        return None
    APR = 74
    def v(r):
        val = df.iloc[r, APR]
        return float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0.0
    gov = {"0_30": v(22)+v(40), "31_60": v(23)+v(41), "61_90": v(24)+v(42),
           "90_360": v(25)+v(26)+v(43)+v(44), "360p": v(27)+v(45), "total": v(28)+v(46)}
    tot = {"0_30": v(4), "31_60": v(5), "61_90": v(6),
           "90_360": v(7)+v(8), "360p": v(9), "total": v(10)}
    non_gov = {k: tot[k] - gov[k] for k in tot}
    return {"gov": gov, "non_gov": non_gov, "total": tot}

# ── Main data ─────────────────────────────────────────────────────────────────
data    = load_all_data()
cc      = data["Cash_CAPEX"]
coll_df = load_collections()
bill_df = load_billings()
ar      = load_ar()

latest = cc.iloc[-1]
first  = cc.iloc[0]

def _safe(val, d=0.0):
    return float(val) if pd.notna(val) else d

cash_val   = _safe(latest["Cash_Balance"])
cash_delta = cash_val - _safe(first["Cash_Balance"])
debt_val   = _safe(latest["Net_Debt"])
debt_delta = debt_val - _safe(first["Net_Debt"])
fcf_month  = _safe(latest["FCF"])

capex_act       = float(cc["CAPEX_Actual"].sum())
capex_plan_raw  = cc["CAPEX_Plan"].sum()
capex_plan      = float(capex_plan_raw) if pd.notna(capex_plan_raw) and capex_plan_raw > 0 else capex_act / 0.85
capex_remaining = capex_plan - capex_act
capex_progress  = min(capex_act / capex_plan * 100, 100) if capex_plan else 0

try:
    period_label = pd.to_datetime(latest["Month"], format="%b-%y").strftime("%B %Y")
except Exception:
    period_label = str(latest["Month"])

# ── Collections % = this month collections / prior month billings ─────────────
latest_month = str(latest["Month"])

def _month_cols(df):
    return [c for c in df.columns if c not in ("LOB", "Grouping")] if df is not None else []

def _prior_month(month, df):
    cols = _month_cols(df)
    if not cols or month not in cols:
        return None
    idx = cols.index(month)
    return cols[idx - 1] if idx > 0 else None

def _lookup(df, lob, grouping, month):
    if df is None or month is None or month not in df.columns:
        return None
    rows = df[(df["LOB"] == lob) & (df["Grouping"] == grouping)]
    if rows.empty:
        return None
    val = rows.iloc[0][month]
    return float(val) if pd.notna(val) else None

prior_month   = _prior_month(latest_month, bill_df)

govt_coll     = _lookup(coll_df, "Business Sales", "Govt",     latest_month)
nongov_coll   = _lookup(coll_df, "Business Sales", "Non-Govt", latest_month)
consumer_coll = _lookup(coll_df, "Consumer Sales", "Total",    latest_month)
amplia_coll   = None  # not yet in source data

govt_bill     = _lookup(bill_df, "Business Sales", "Govt",     prior_month)
nongov_bill   = _lookup(bill_df, "Business Sales", "Non-Govt", prior_month)
consumer_bill = _lookup(bill_df, "Consumer Sales", "Total",    prior_month)

def _pct(coll, bill):
    return (coll / bill * 100) if (coll is not None and bill and bill != 0) else None

govt_pct     = _pct(govt_coll,     govt_bill)
nongov_pct   = _pct(nongov_coll,   nongov_bill)
consumer_pct = _pct(consumer_coll, consumer_bill)

def _pct_color(pct):
    if pct is None: return "#4488ff"
    if pct >= 85:   return "#00e676"
    if pct >= 70:   return "#FFD700"
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
    pct_w = d["total"] / _ar_max * 100 if _ar_max else 0
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
        show_lbl = pv > 7 or (key == "360p" and capped)
        lbl = (
            f'<span style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
            f'font-size:0.72rem;font-weight:700;color:rgba(0,0,0,0.85);white-space:nowrap">'
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
                f'font-size:0.65rem;font-weight:900;color:rgba(255,255,255,0.78);'
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
        f'<span style="font-size:1.1rem;color:white;font-weight:600">{label}</span>'
        f'<span style="font-size:1.1rem;color:#aaaacc;font-weight:700">{d["total"]:,.1f}</span>'
        f'</div>'
        f'<div style="display:flex;gap:2px;height:38px;width:{pct_w:.1f}%">{"".join(parts)}</div>'
        f'</div>'
    )

ar_legend = "".join(
    f'<div style="display:flex;align-items:center;gap:5px">'
    f'<span style="width:10px;height:10px;border-radius:2px;background:{c};display:inline-block"></span>'
    f'<span style="font-size:0.85rem;color:#8899aa;white-space:nowrap">{bl}</span></div>'
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

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="padding:6px 0 10px 0;border-bottom:1px solid #21262d;margin-bottom:10px;'
    f'display:flex;justify-content:space-between;align-items:center">'
    f'<span style="font-size:1.4rem;font-weight:700;color:white">Cash · Working Capital · CAPEX</span>'
    f'<span style="font-size:1rem;color:#556677;background:#161B22;padding:4px 14px;'
    f'border-radius:20px;border:1px solid #21262d">{period_label}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── KPI row ───────────────────────────────────────────────────────────────────
def _kpi(label, value, sub, color):
    return (
        f'<div style="flex:1;background:#161B22;padding:12px 16px;border:1px solid #21262d;'
        f'border-left:3px solid {color};border-radius:10px">'
        f'<div style="font-size:0.85rem;font-weight:700;color:#556677;text-transform:uppercase;'
        f'letter-spacing:1.2px;margin-bottom:8px">{label}</div>'
        f'<div style="font-size:2rem;font-weight:800;color:white;line-height:1">{value}</div>'
        f'<div style="font-size:0.9rem;color:{color};font-weight:600;margin-top:6px">{sub}</div>'
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
        title=dict(text="<b>Cash Balance Trend</b>", font=dict(size=20, color="white"), x=0),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=17), showline=False),
        yaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=17),
                   range=[y_min - pad, y_max + pad], zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f'<div style="display:flex;gap:10px;margin-top:4px">'
        f'{_kpi("Cash Balance",   f"{cash_val:,.0f}",  f"{cash_delta:+,.0f} vs PY",  cash_dc)}'
        f'{_kpi("Net Debt",       f"{debt_val:,.0f}",  f"{debt_delta:+,.0f} vs LY",  debt_dc)}'
        f'{_kpi("Free Cash Flow", f"{fcf_month:,.0f}", str(latest["Month"]),          fcf_color)}'
        f'</div>',
        unsafe_allow_html=True,
    )

with c_ar:
    st.markdown(f"""
<div style="background:#161B22;border-radius:8px;padding:12px 18px;
            border:1px solid #21262d;margin-top:8px">
  <div style="font-size:0.85rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:8px">AR Aging</div>
  <div style="font-size:0.95rem;color:#556677;margin-bottom:12px">
    Total <strong style="color:#aaaacc">{AR_TOTAL:,.1f}</strong>
    &nbsp;·&nbsp; Gov <strong style="color:#aaaacc">{gov['total']:,.1f}</strong>
    &nbsp;·&nbsp; Non-Gov <strong style="color:#aaaacc">{non_gov['total']:,.1f}</strong>
  </div>
  {_pill_row("Government", gov)}
  {_pill_row("Non-Government", non_gov)}
  <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:6px">{ar_legend}</div>
</div>""", unsafe_allow_html=True)

# ── Row 2: Collections  |  CAPEX ─────────────────────────────────────────────
c_coll, c_capex = st.columns([55, 45])

with c_coll:
    prior_lbl = f" | prior month: {prior_month}" if prior_month else ""

    def _coll_box(label, coll_val, pct_val, accent):
        color = _pct_color(pct_val)
        if pct_val is not None:
            main = f'<div style="font-size:2.6rem;font-weight:800;color:{color};line-height:1">{pct_val:.1f}%</div>'
        elif coll_val is not None:
            main = '<div style="font-size:1rem;font-weight:600;color:#556677;margin-top:4px">Billings pending</div>'
        else:
            main = '<div style="font-size:1rem;font-weight:600;color:#3a4455;line-height:1.3">Data pending</div>'
        return (
            f'<div style="flex:1;background:#161B22;border:1px solid #21262d;'
            f'border-top:2px solid {accent};border-radius:8px;padding:14px 16px">'
            f'<div style="font-size:0.85rem;font-weight:700;color:{accent};text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:8px">{label}</div>'
            f'{main}</div>'
        )

    st.markdown(
        f'<div style="font-size:0.9rem;font-weight:700;color:#556677;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:8px">Collections — {latest_month} vs {prior_month or "—"} billings</div>'
        f'<div style="display:flex;gap:8px;margin-bottom:8px">'
        f'{_coll_box("Government",     govt_coll,     govt_pct,     "#4488ff")}'
        f'{_coll_box("Non-Government", nongov_coll,   nongov_pct,   "#a78bfa")}'
        f'</div>'
        f'<div style="display:flex;gap:8px">'
        f'{_coll_box("Consumer Sales", consumer_coll, consumer_pct, "#00e676")}'
        f'{_coll_box("Amplia",         amplia_coll,   None,         "#FF8844")}'
        f'</div>',
        unsafe_allow_html=True,
    )

with c_capex:
    st.markdown(f"""
<div style="background:#161B22;border-radius:8px;padding:12px 18px;
            border:1px solid #21262d;margin-top:8px">
  <div style="font-size:0.85rem;font-weight:700;color:#00e676;text-transform:uppercase;
              letter-spacing:2px;margin-bottom:12px">CAPEX Spend to Date</div>
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <span style="color:#aaaacc;font-size:16px">YTD vs Annual Budget</span>
    <span style="color:{cap_pct_color};font-weight:800;font-size:30px">{capex_progress:.1f}%</span>
  </div>
  <div style="background:#1e1e3a;border-radius:6px;height:16px;overflow:hidden;margin-bottom:16px">
    <div style="background:{cap_bar_color};width:{capex_progress:.1f}%;height:100%;border-radius:6px"></div>
  </div>
  <div style="display:flex;justify-content:space-between">
    <div>
      <div style="color:{cap_pct_color};font-size:22px;font-weight:700">{capex_act:,.0f}</div>
      <div style="color:#6688aa;font-size:15px;margin-top:4px">spent YTD</div>
    </div>
    <div style="text-align:center">
      <div style="color:{cap_rem_color};font-size:22px;font-weight:700">{cap_rem_sign}{abs(capex_remaining):,.0f}</div>
      <div style="color:#6688aa;font-size:15px;margin-top:4px">{cap_rem_label}</div>
    </div>
    <div style="text-align:right">
      <div style="color:#aaaacc;font-size:22px;font-weight:700">{capex_plan:,.0f}</div>
      <div style="color:#6688aa;font-size:15px;margin-top:4px">annual budget</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
