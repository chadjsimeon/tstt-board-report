"""
Pure Plotly figure builders for PowerPoint export.
No Streamlit imports or side-effects — returns go.Figure instances only.

Export pixel targets (rendered at scale=2 via kaleido → 2× density):
  Full-width chart : 2400 × 800 px  → ~12.5 in @ 192 dpi
  Half-width chart : 1180 × 800 px  → ~6.15 in @ 192 dpi
  Tall chart       : 2400 × 960 px  → waterfall / bridge slides
"""

import pandas as pd
import plotly.graph_objects as go

from utils.charts import (
    line_chart, waterfall_chart, grouped_bar, stacked_bar,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE, CYAN,
    BLUE_DIM, GREEN_DIM, WHITE_DIM, GREEN_FAINT, BLUE_FAINT,
    BLUE_MED, GREEN_MED, dim,
)
from utils.data_loader import pivot_by_group, get_month_order

# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_col(df, col, default=0.0):
    return df[col] if col in df.columns else default


def _transparent(fig):
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


# ── Financial Performance ─────────────────────────────────────────────────────

def fig_revenue_trend(data: dict, height: int = 440) -> go.Figure:
    fin = data["Financial_Monthly"]
    cols = [c for c in ["Revenue", "Revenue_AOP", "Revenue_PY"] if c in fin.columns]
    colors = [BLUE, BLUE_DIM, WHITE_DIM][: len(cols)]
    dash = [c for c in ["Revenue_AOP", "Revenue_PY"] if c in fin.columns]
    return _transparent(line_chart(fin, x="Month", y_cols=cols,
                                   title="Revenue vs AOP vs PY (TT$M)",
                                   colors=colors, dash_cols=dash, height=height))


def fig_ebitda_trend(data: dict, height: int = 440) -> go.Figure:
    fin = data["Financial_Monthly"]
    cols = [c for c in ["EBITDA", "EBITDA_AOP", "EBITDA_PY"] if c in fin.columns]
    colors = [GREEN, GREEN_DIM, WHITE_DIM][: len(cols)]
    dash = [c for c in ["EBITDA_AOP", "EBITDA_PY"] if c in fin.columns]
    return _transparent(line_chart(fin, x="Month", y_cols=cols,
                                   title="EBITDA vs AOP vs PY (TT$M)",
                                   colors=colors, dash_cols=dash, height=height))


def fig_pat_trend(data: dict, height: int = 440) -> go.Figure:
    fin = data["Financial_Monthly"]
    cols = [c for c in ["PAT", "PAT_AOP", "PAT_PY"] if c in fin.columns]
    colors = [PURPLE, dim(PURPLE, 0.40), WHITE_DIM][: len(cols)]
    dash = [c for c in ["PAT_AOP", "PAT_PY"] if c in fin.columns]
    return _transparent(line_chart(fin, x="Month", y_cols=cols,
                                   title="PAT vs AOP vs PY (TT$M)",
                                   colors=colors, dash_cols=dash, height=height))


def fig_revenue_ebitda_combo(data: dict, height: int = 440) -> go.Figure:
    fin = data["Financial_Monthly"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=fin["Month"], y=fin["Revenue"],
        name="Revenue", marker_color=BLUE_MED, yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=fin["Month"], y=fin["EBITDA"],
        name="EBITDA", line=dict(color=GREEN, width=2.5),
        mode="lines+markers", marker=dict(size=6), yaxis="y1",
    ))
    if "EBITDA_Margin" in fin.columns:
        fig.add_trace(go.Scatter(
            x=fin["Month"], y=fin["EBITDA_Margin"],
            name="EBITDA Margin %", line=dict(color=YELLOW, width=2, dash="dot"),
            mode="lines+markers", marker=dict(size=5), yaxis="y2",
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"),
        height=height,
        title=dict(text="<b>Revenue / EBITDA / Margin</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=10)),
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                   title=dict(text="TT$M", font=dict(color="#8888aa", size=11))),
        yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                    tickfont=dict(color="#8888aa"), showgrid=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                    y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=44, b=10),
        barmode="overlay",
    )
    return fig


# ── EBITDA Bridge ─────────────────────────────────────────────────────────────

def fig_ebitda_bridge(data: dict, height: int = 500) -> go.Figure:
    bridge = data.get("EBITDA_Bridge", pd.DataFrame())
    if bridge.empty:
        return go.Figure()
    return _transparent(waterfall_chart(
        bridge, x_col="Category", y_col="Value", type_col="Type",
        title="EBITDA Bridge: AOP → Actual (TT$M)", height=height,
    ))


def fig_pnl_waterfall(data: dict, height: int = 500) -> go.Figure:
    pnl = data.get("PnL_Breakdown", pd.DataFrame())
    if pnl.empty:
        return go.Figure()
    latest = pnl.iloc[-1]
    month = latest.get("Month", "")
    total_rev  = float(latest.get("Total_Rev", 0) or 0)
    total_cos  = abs(float(latest.get("Total_COS", 0) or 0))
    gross_prof = total_rev - total_cos
    total_opex = abs(float(latest.get("Total_OPEX", 0) or 0))
    ebitda     = float(latest.get("EBITDA", 0) or 0)
    wf = pd.DataFrame([
        {"Category": "Revenue",      "Value": total_rev,   "Type": "Absolute"},
        {"Category": "Direct Costs", "Value": -total_cos,  "Type": "Negative"},
        {"Category": "Gross Profit", "Value": gross_prof,  "Type": "Total"},
        {"Category": "OPEX",         "Value": -total_opex, "Type": "Negative"},
        {"Category": "EBITDA",       "Value": ebitda,      "Type": "Total"},
    ])
    return _transparent(waterfall_chart(
        wf, x_col="Category", y_col="Value", type_col="Type",
        title=f"P&L Waterfall — {month} (TT$M)", height=height,
    ))


# ── OPEX ──────────────────────────────────────────────────────────────────────

def fig_opex_bullet(data: dict, height: int = 500) -> go.Figure:
    opex = data.get("OPEX", pd.DataFrame())
    if opex.empty or "Month" not in opex.columns:
        return go.Figure()
    latest_month = opex["Month"].iloc[-1]
    cats = opex[opex["Month"] == latest_month].sort_values("Plan", ascending=True).copy()
    bar_colors = ["#22c55e" if v <= 0 else "#ef4444"
                  for v in cats.get("Variance", [0] * len(cats))]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=cats["Category"], x=cats["Plan"], orientation="h", name="Plan",
        marker_color="rgba(90,90,130,0.28)",
        marker_line=dict(color="rgba(140,140,180,0.55)", width=1),
        width=0.70,
    ))
    fig.add_trace(go.Bar(
        y=cats["Category"], x=cats["Actual"], orientation="h", name="Actual",
        marker_color=bar_colors, width=0.42,
        text=[f"TT${v:,.1f}M" for v in cats["Actual"]],
        textposition="outside", textfont=dict(color="white", size=10),
    ))
    fig.update_layout(
        barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"), height=height,
        title=dict(text=f"<b>OPEX — {latest_month} Actual vs Plan (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=10),
                   zeroline=True, zerolinecolor="#3a3a5a"),
        yaxis=dict(tickfont=dict(color="white", size=11)),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.05, x=0),
        margin=dict(l=10, r=140, t=44, b=10),
    )
    return fig


# ── Cash & CAPEX ──────────────────────────────────────────────────────────────

def fig_cash_trend(data: dict, height: int = 380) -> go.Figure:
    cc = data.get("Cash_CAPEX", pd.DataFrame())
    if cc.empty:
        return go.Figure()
    y_vals = cc["Cash_Balance"].ffill().fillna(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cc["Month"], y=y_vals,
        mode="lines+markers",
        line=dict(color="#00e676", width=2.5),
        marker=dict(size=5, color="#00e676"),
        fill="tozeroy", fillcolor="rgba(0,230,118,0.07)",
        name="Cash Balance",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"), height=height,
        title=dict(text="<b>Closing Cash Balance Trend (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=10)),
        yaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=10)),
        margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
    )
    return fig


def fig_ar_aging(gov: dict, non_gov: dict, height: int = 340) -> go.Figure:
    BUCKETS = [
        ("0–30d",   "0_30",   "#00e676"),
        ("30–60d",  "31_60",  "#4488ff"),
        ("60–90d",  "61_90",  "#FFD700"),
        ("90–360d", "90_360", "#FF8844"),
        ("360+d",   "360p",   "#ef4444"),
    ]
    categories = ["Non-Government", "Government"]
    fig = go.Figure()
    for label, key, color in BUCKETS:
        fig.add_trace(go.Bar(
            y=categories, x=[non_gov.get(key, 0), gov.get(key, 0)],
            name=label, orientation="h", marker_color=color,
        ))
    _x_max = max(non_gov.get("total", 1), gov.get("total", 1)) * 1.18
    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"), height=height,
        title=dict(text="<b>AR Aging — Government vs Non-Government (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#21262d", tickfont=dict(color="#556677", size=10),
                   ticksuffix="M", range=[0, _x_max]),
        yaxis=dict(tickfont=dict(color="white", size=11), showgrid=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=9.5),
                    orientation="h", y=1.22, x=0),
        margin=dict(l=10, r=10, t=56, b=10),
    )
    return fig


# ── Consumer ──────────────────────────────────────────────────────────────────

def fig_consumer_revenue(data: dict, height: int = 380) -> go.Figure:
    consumer = data.get("Consumer_Sales", pd.DataFrame())
    if consumer.empty:
        return go.Figure()
    rev_pivot = pivot_by_group(consumer, "Month", "Segment", "Revenue")
    seg_cols  = [c for c in rev_pivot.columns if c != "Month"]
    colors    = [BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW][: len(seg_cols)]
    return _transparent(stacked_bar(rev_pivot, x="Month", y_cols=seg_cols,
                                    title="Consumer Revenue by Segment (TT$M)",
                                    colors=colors, height=height))


def fig_consumer_subscribers(data: dict, height: int = 380) -> go.Figure:
    consumer = data.get("Consumer_Sales", pd.DataFrame())
    if consumer.empty:
        return go.Figure()
    sub_pivot = pivot_by_group(consumer, "Month", "Segment", "Subscribers")
    seg_cols  = [c for c in sub_pivot.columns if c != "Month"]
    colors    = [BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW][: len(seg_cols)]
    return _transparent(line_chart(sub_pivot, x="Month", y_cols=seg_cols,
                                   title="Subscribers by Segment",
                                   colors=colors, height=height))


# ── Business Sales ────────────────────────────────────────────────────────────

def fig_business_revenue(data: dict, height: int = 380) -> go.Figure:
    bs = data.get("Business_Sales", pd.DataFrame())
    if bs.empty:
        return go.Figure()
    rev_pivot = pivot_by_group(bs, "Month", "Segment", "Revenue")
    seg_cols  = [c for c in rev_pivot.columns if c != "Month"]
    colors    = [BLUE, GREEN, PURPLE, ORANGE, CYAN, YELLOW][: len(seg_cols)]
    return _transparent(stacked_bar(rev_pivot, x="Month", y_cols=seg_cols,
                                    title="Business Sales Revenue by Segment (TT$M)",
                                    colors=colors, height=height))


def fig_business_gp(data: dict, height: int = 380) -> go.Figure:
    bs = data.get("Business_Sales", pd.DataFrame())
    if bs.empty:
        return go.Figure()
    gp_agg = bs.groupby("Month")[["Revenue", "Gross_Profit"]].sum().reset_index()
    months = get_month_order(bs)
    gp_agg["_ord"] = gp_agg["Month"].apply(
        lambda m: months.index(m) if m in months else 99)
    gp_agg = gp_agg.sort_values("_ord").drop(columns=["_ord"])
    gp_agg["GP_Margin"] = (gp_agg["Gross_Profit"] / gp_agg["Revenue"] * 100).where(
        gp_agg["Revenue"] > 0)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=gp_agg["Month"], y=gp_agg["Revenue"],
        name="Revenue", marker_color=BLUE_MED, yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=gp_agg["Month"], y=gp_agg["Gross_Profit"],
        name="Gross Profit", line=dict(color=GREEN, width=2.5),
        mode="lines+markers", marker=dict(size=6), yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=gp_agg["Month"], y=gp_agg["GP_Margin"],
        name="GP Margin %", line=dict(color=YELLOW, width=2, dash="dot"),
        mode="lines+markers", marker=dict(size=5), yaxis="y2",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"), height=height,
        title=dict(text="<b>Business Sales — Revenue & Gross Profit (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa", size=10)),
        yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
        yaxis2=dict(overlaying="y", side="right", ticksuffix="%",
                    tickfont=dict(color="#8888aa"), showgrid=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                    y=1.02, x=1, xanchor="right"),
        margin=dict(l=10, r=10, t=44, b=10),
        barmode="overlay",
    )
    return fig


def fig_business_mrr(data: dict, height: int = 380) -> go.Figure:
    bs = data.get("Business_Sales", pd.DataFrame())
    if bs.empty or "MRR" not in bs.columns:
        return go.Figure()
    mrr_agg = bs.groupby("Month")["MRR"].sum().reset_index()
    months = get_month_order(bs)
    mrr_agg["_ord"] = mrr_agg["Month"].apply(
        lambda m: months.index(m) if m in months else 99)
    mrr_agg = mrr_agg.sort_values("_ord").drop(columns=["_ord"])
    return _transparent(line_chart(mrr_agg, x="Month", y_cols=["MRR"],
                                   title="Monthly Recurring Revenue (TT$M)",
                                   colors=[GREEN], height=height))


# ── DPDI ──────────────────────────────────────────────────────────────────────

def fig_dpdi_by_product(data: dict, height: int = 380) -> go.Figure:
    dpdi = data.get("DPDI", pd.DataFrame())
    if dpdi.empty:
        return go.Figure()
    months = get_month_order(dpdi)
    ytd = dpdi.groupby("Product")[["Revenue", "Revenue_AOP"]].sum()
    products = ytd.index.tolist()
    actual_vals = [float(ytd.loc[p, "Revenue"]) for p in products]
    aop_vals    = [float(ytd.loc[p, "Revenue_AOP"]) if "Revenue_AOP" in ytd.columns
                   else 0 for p in products]
    safe_max = max(max(actual_vals + [0.001]), max(aop_vals + [0.001]))
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=products, x=aop_vals, name="AOP Target", orientation="h",
        marker=dict(color="rgba(100,220,100,0.10)",
                    line=dict(color="#55aa66", width=1.5)),
    ))
    fig.add_trace(go.Bar(
        y=products, x=actual_vals, name="YTD Actual",
        orientation="h", marker_color="#00cc55",
    ))
    fig.update_layout(
        barmode="overlay",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white", family="Inter, sans-serif"), height=height,
        title=dict(text="<b>DPDI Revenue by Product — YTD vs AOP (TT$M)</b>",
                   font=dict(size=13, color="white"), x=0),
        xaxis=dict(gridcolor="#111111", tickfont=dict(color="#556677", size=10),
                   range=[0, safe_max * 1.6]),
        yaxis=dict(tickfont=dict(color="white", size=11), showgrid=False,
                   autorange="reversed"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#aaaaaa", size=10),
                    orientation="h", y=-0.12, x=0),
        margin=dict(l=10, r=130, t=44, b=40),
    )
    return fig


def fig_dpdi_monthly_trend(data: dict, height: int = 380) -> go.Figure:
    dpdi = data.get("DPDI", pd.DataFrame())
    if dpdi.empty:
        return go.Figure()
    months = get_month_order(dpdi)
    excl = dpdi[dpdi["Product"] != "e-GOVTT"].groupby("Month")[
        ["Revenue", "Revenue_AOP"]
    ].sum().reset_index()
    excl["_ord"] = excl["Month"].apply(lambda m: months.index(m) if m in months else 99)
    excl = excl.sort_values("_ord").drop(columns=["_ord"])
    cols = [c for c in ["Revenue", "Revenue_AOP"] if c in excl.columns]
    colors = [GREEN, YELLOW][: len(cols)]
    dash = ["Revenue_AOP"] if "Revenue_AOP" in cols else []
    return _transparent(line_chart(excl, x="Month", y_cols=cols,
                                   title="DPDI Monthly Revenue excl. e-GOVTT (TT$M)",
                                   colors=colors, dash_cols=dash, height=height))


# ── Amplia ────────────────────────────────────────────────────────────────────

def fig_amplia_revenue(data: dict, height: int = 380) -> go.Figure:
    amp = data.get("AMPLIA_Financial", pd.DataFrame())
    if amp.empty:
        return go.Figure()
    cols = [c for c in ["Revenue", "Revenue_AOP"] if c in amp.columns]
    colors = [BLUE, BLUE_FAINT][: len(cols)]
    dash = ["Revenue_AOP"] if "Revenue_AOP" in cols else []
    return _transparent(line_chart(amp, x="Month", y_cols=cols,
                                   title="Amplia Revenue vs AOP (TT$M)",
                                   colors=colors, dash_cols=dash, height=height))


def fig_amplia_ebitda(data: dict, height: int = 380) -> go.Figure:
    amp = data.get("AMPLIA_Financial", pd.DataFrame())
    if amp.empty:
        return go.Figure()
    cols = [c for c in ["EBITDA", "EBITDA_AOP"] if c in amp.columns]
    colors = [GREEN, GREEN_FAINT][: len(cols)]
    dash = ["EBITDA_AOP"] if "EBITDA_AOP" in cols else []
    return _transparent(line_chart(amp, x="Month", y_cols=cols,
                                   title="Amplia EBITDA vs AOP (TT$M)",
                                   colors=colors, dash_cols=dash, height=height))


def fig_amplia_pat(data: dict, height: int = 380) -> go.Figure:
    amp = data.get("AMPLIA_Financial", pd.DataFrame())
    if amp.empty:
        return go.Figure()
    cols = [c for c in ["PAT"] if c in amp.columns]
    return _transparent(line_chart(amp, x="Month", y_cols=cols,
                                   title="Amplia Profit After Tax (TT$M)",
                                   colors=[PURPLE], height=height))
