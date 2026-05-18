import streamlit as st

st.set_page_config(page_title="TSTT | Amplia", page_icon="📶", layout="wide")

import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import load_all_data, get_month_order
from utils.charts import (
    inject_css,
    grouped_bar, line_chart,
    GREEN, RED, BLUE, YELLOW, PURPLE, ORANGE,
)

inject_css()

data    = load_all_data()
amp_raw = data["AMPLIA_Financial"].copy()
amp_com = data["AMPLIA_Commercial"] if "AMPLIA_Commercial" in data else pd.DataFrame()

# ── Derive PY columns (12 months prior) ───────────────────────────────────────
amp_raw["_dt"] = pd.to_datetime(amp_raw["Month"], format="%b-%y", errors="coerce")
for col in ["Revenue", "Gross_Profit", "EBITDA", "PAT"]:
    if col in amp_raw.columns:
        lk = amp_raw.dropna(subset=["_dt"]).set_index("_dt")[col]
        amp_raw[f"{col}_PY"] = amp_raw["_dt"].apply(
            lambda dt, lk=lk: lk.get(dt - pd.DateOffset(months=12))
        )
amp_raw.drop(columns=["_dt"], inplace=True)

last12  = amp_raw.tail(13).reset_index(drop=True)
latest  = amp_raw.iloc[-1]

# ── Colors ────────────────────────────────────────────────────────────────────
REV_COLOR = "#00d4a0"
GP_COLOR  = "#FF8844"
EBI_COLOR = "#4a9eff"
PAT_COLOR = "#aa44ff"
CARD_BG   = "#1a2234"
MUTED     = "#8888aa"
GRID      = "#1e2a3a"


# ── Helpers (same pattern as Financial Performance v2) ────────────────────────
def make_svg_sparkline(series, color, width=220, height=56):
    vals = [float(v) if pd.notna(v) else 0.0 for v in series]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    pts = []
    for i, v in enumerate(vals):
        x = i * width / max(len(vals) - 1, 1)
        y = height - (v - mn) / rng * height * 0.75 - height * 0.12
        pts.append(f"{x:.1f},{y:.1f}")
    line_pts = " ".join(pts)
    fill_pts = f"0,{height} {line_pts} {width},{height}"
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none" style="display:block;margin-top:8px;">'
        f'<polygon points="{fill_pts}" fill="rgba({r},{g},{b},0.15)"/>'
        f'<polyline points="{line_pts}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
    )


def _badge(label, delta, pos_color, neg_color):
    color = pos_color if delta >= 0 else neg_color
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<span style="font-size:14px;font-weight:600;padding:2px 8px;border-radius:3px;'
        f'background:rgba({r},{g},{b},0.15);color:{color};">{label}</span>'
    )


def kpi_card(label, col, aop_col, ly_col, color, is_margin=False):
    actual = latest[col] if col in latest.index else None
    if actual is None or pd.isna(actual):
        return f'<div style="background:{CARD_BG};border-radius:12px;padding:20px 16px;min-height:230px;">—</div>'

    val_str = f"{actual:.1f}%" if is_margin else f"{actual:,.0f}"
    unit    = "pp" if is_margin else "%"

    badges = []
    if aop_col and aop_col in latest.index:
        aop = latest[aop_col]
        if pd.notna(aop) and aop != 0:
            d = (actual - aop) if is_margin else (actual - aop) / abs(aop) * 100
            lbl = f"vs AOP {'+' if d >= 0 else ''}{d:.1f}{unit}"
            badges.append(_badge(lbl, d, "#00d4a0", "#FF4444"))

    if ly_col and ly_col in latest.index:
        ly = latest[ly_col]
        if pd.notna(ly) and ly != 0:
            d = (actual - ly) if is_margin else (actual - ly) / abs(ly) * 100
            lbl = f"vs PY {'+' if d >= 0 else ''}{d:.1f}{unit}"
            badges.append(_badge(lbl, d, "#4a9eff", "#FFD700"))

    spark_col = col if col in last12.columns else None
    sparkline = make_svg_sparkline(last12[spark_col].fillna(0).tolist(), color) if spark_col else ""
    badges_html = "&nbsp;".join(badges) if badges else "&nbsp;"

    return f"""
<div style="background:{CARD_BG};border-radius:12px;padding:20px 16px;
            border:1px solid rgba(74,158,255,0.08);border-top:3px solid {color};height:100%;min-height:230px;">
    <div style="color:{MUTED};font-size:14px;font-weight:500;margin-bottom:4px;">{label}</div>
    <div style="color:white;font-size:64px;font-weight:800;line-height:1;margin:4px 0 10px 0;">{val_str}</div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:4px;">{badges_html}</div>
    {sparkline}
</div>"""


def driver_block(label, color, col, aop_col, ly_col, is_margin=False, last_entry=False):
    actual = latest[col] if col in latest.index else None
    if actual is None or pd.isna(actual):
        return ""
    val_str = f"{actual:.1f}%" if is_margin else f"{actual:,.0f}"
    unit    = "pp" if is_margin else "%"
    month   = latest["Month"]

    line1 = f"<b>{val_str}</b> in {month}"
    if aop_col and aop_col in latest.index:
        aop = latest[aop_col]
        if pd.notna(aop) and aop != 0:
            d = (actual - aop) if is_margin else (actual - aop) / abs(aop) * 100
            line1 += f"&nbsp;&nbsp;{'↑' if d >= 0 else '↓'} {abs(d):.1f}{unit} vs AOP"

    line2 = ""
    if ly_col and ly_col in latest.index:
        ly = latest[ly_col]
        if pd.notna(ly) and ly != 0:
            d = (actual - ly) if is_margin else (actual - ly) / abs(ly) * 100
            ly_str = f"{ly:.1f}%" if is_margin else f"{ly:,.0f}"
            line2 = f"{'↑' if d >= 0 else '↓'} {abs(d):.1f}{unit} vs prior year ({ly_str})"

    divider = "" if last_entry else "border-bottom:1px solid #1e3050;"
    return f"""
<div style="margin-bottom:18px;padding-bottom:16px;{divider}">
    <div style="font-size:14px;font-weight:700;color:{color};margin-bottom:6px;">{label}</div>
    <div style="color:#c0c8d8;font-size:14px;line-height:1.6;">{line1}</div>
    {"<div style='color:#8888aa;font-size:13px;line-height:1.6;'>" + line2 + "</div>" if line2 else ""}
</div>"""


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Financial Performance", "Commercial Performance"])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — Financial Performance (v2 style)
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    # Header
    st.markdown(f"""
<div style="display:flex;justify-content:space-between;align-items:center;
            margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #1e3050;">
    <div style="display:flex;align-items:center;gap:12px;">
        <span style="background:#A78BFA;color:#000;font-size:13px;font-weight:800;
                     padding:4px 10px;border-radius:4px;">AMP</span>
        <span style="font-size:26px;font-weight:800;color:white;">Amplia Financial Performance</span>
    </div>
    <div style="color:{MUTED};font-size:12px;">All figures in  unless otherwise stated</div>
</div>""", unsafe_allow_html=True)

    # KPI Cards
    METRICS = [
        ("Revenue",      "Revenue",      "Revenue_AOP",  "Revenue_PY",      REV_COLOR, False),
        ("Gross Profit", "Gross_Profit", None,           "Gross_Profit_PY", GP_COLOR,  False),
        ("EBITDA",       "EBITDA",       "EBITDA_AOP",   "EBITDA_PY",       EBI_COLOR, False),
        ("PAT",          "PAT",          None,           "PAT_PY",          PAT_COLOR, False),
    ]

    c1, c2, c3, c4 = st.columns(4)
    for col_obj, (lbl, col, aop_col, ly_col, clr, is_m) in zip([c1, c2, c3, c4], METRICS):
        with col_obj:
            st.markdown(kpi_card(lbl, col, aop_col, ly_col, clr, is_m), unsafe_allow_html=True)

    # 60/40 split — trend chart + key drivers
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    chart_col, driver_col = st.columns([3, 2])

    with chart_col:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=last12["Month"], y=last12["Revenue"],
            mode="lines", name="Revenue",
            line=dict(color=REV_COLOR, width=2.5),
            fill="tozeroy", fillcolor="rgba(0,212,160,0.07)",
        ))
        if "Gross_Profit" in last12.columns:
            fig.add_trace(go.Scatter(
                x=last12["Month"], y=last12["Gross_Profit"],
                mode="lines", name="Gross Profit",
                line=dict(color=GP_COLOR, width=2),
                fill="tozeroy", fillcolor="rgba(255,136,68,0.07)",
            ))
        fig.add_trace(go.Scatter(
            x=last12["Month"], y=last12["EBITDA"],
            mode="lines", name="EBITDA",
            line=dict(color=EBI_COLOR, width=2.5),
            fill="tozeroy", fillcolor="rgba(74,158,255,0.07)",
        ))
        fig.update_layout(
            height=560,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            title=dict(text="<b>Revenue, Gross Profit & EBITDA — 13-Month Trend</b>",
                       font=dict(size=13, color="white"), x=0),
            xaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED, size=13), showline=False, tickangle=-30),
            yaxis=dict(gridcolor=GRID, tickfont=dict(color=MUTED, size=13), showline=False, zeroline=False),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
                        orientation="h", y=1.02, x=1, xanchor="right"),
            margin=dict(l=10, r=10, t=44, b=30),
        )
        st.plotly_chart(fig, use_container_width=True)

    with driver_col:
        blocks = "".join([
            driver_block("Revenue",      REV_COLOR, "Revenue",      "Revenue_AOP",  "Revenue_PY",      False),
            driver_block("Gross Profit", GP_COLOR,  "Gross_Profit", None,           "Gross_Profit_PY", False),
            driver_block("EBITDA",       EBI_COLOR, "EBITDA",       "EBITDA_AOP",   "EBITDA_PY",       False),
            driver_block("PAT",          PAT_COLOR, "PAT",          None,           "PAT_PY",          False, last_entry=True),
        ])
        st.markdown(f"""
<div style="background:{CARD_BG};border-radius:12px;padding:24px;
            border:1px solid rgba(74,158,255,0.08);">
    <div style="color:white;font-size:15px;font-weight:700;margin-bottom:20px;">
        Key Drivers — {latest['Month']}</div>
    {blocks}
</div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — Commercial Performance (unchanged)
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    if amp_com.empty:
        st.info("Commercial data not yet available.")
    else:
        monthly_com = amp_com.drop_duplicates(subset=["Month"], keep="first").copy()
        channels_df = amp_com.copy()
        channel_months = get_month_order(amp_com)
        sel_com_month  = st.sidebar.selectbox("Commercial Month",
                                              channel_months,
                                              index=len(channel_months) - 1)

        latest_com = monthly_com.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ARPU",            f"{latest_com['ARPU']:,.0f}")
        c2.metric("Gross Additions",  f"{latest_com['Gross_Additions']:,.0f}",
                  f"AOP: {latest_com['Gross_Additions_AOP']:,.0f}")
        c3.metric("Monthly Churn",   f"{latest_com['Monthly_Churn']:,.0f}",
                  f"AOP: {latest_com['Churn_AOP']:,.0f}",
                  delta_color="inverse")
        c4.metric("Net Port",        f"{latest_com['Net_Port']:+,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            fig = grouped_bar(
                monthly_com, x="Month",
                y_cols=["Gross_Additions", "Gross_Additions_AOP"],
                title="Gross Additions vs AOP",
                colors=[GREEN, "#224422"],
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = grouped_bar(
                monthly_com, x="Month",
                y_cols=["Monthly_Churn", "Churn_AOP"],
                title="Monthly Churn vs AOP",
                colors=[RED, "#442222"],
            )
            st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            monthly_com_copy = monthly_com.copy()
            monthly_com_copy["Net_Additions"] = (
                monthly_com_copy["Gross_Additions"] - monthly_com_copy["Monthly_Churn"]
            )
            colors_list = [GREEN if v >= 0 else RED for v in monthly_com_copy["Net_Additions"]]
            fig = go.Figure(go.Bar(
                x=monthly_com_copy["Month"], y=monthly_com_copy["Net_Additions"],
                marker_color=colors_list,
                text=[f"{v:+,.0f}" for v in monthly_com_copy["Net_Additions"]],
                textposition="outside", textfont=dict(color="white", size=10),
            ))
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"), height=360,
                title=dict(text="<b>Net Subscriber Additions</b>",
                           font=dict(size=13, color="white"), x=0),
                xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                           zeroline=True, zerolinecolor="#3a3a5a"),
                margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col4:
            fig = line_chart(
                monthly_com, x="Month", y_cols=["ARPU"],
                title="ARPU Trend ()",
                colors=[YELLOW],
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.markdown("#### Channel Performance")

        channel_sel = channels_df[channels_df["Month"] == sel_com_month].copy()

        if not channel_sel.empty:
            col5, col6 = st.columns(2)
            with col5:
                fig = go.Figure(go.Bar(
                    x=channel_sel["Channel"],
                    y=channel_sel["Sales_Count"],
                    marker_color=[BLUE, GREEN, PURPLE][:len(channel_sel)],
                    text=[f"{v:,.0f}" for v in channel_sel["Sales_Count"]],
                    textposition="outside", textfont=dict(color="white", size=11),
                    customdata=channel_sel["Sales_Target"],
                    hovertemplate="<b>%{x}</b><br>Sales: %{y:,.0f}<br>Target: %{customdata:,.0f}<extra></extra>",
                ))
                for _, row in channel_sel.iterrows():
                    fig.add_shape(type="line",
                                  x0=row["Channel"], x1=row["Channel"],
                                  y0=row["Sales_Target"] - 50, y1=row["Sales_Target"] + 50,
                                  xref="x", yref="y",
                                  line=dict(color=YELLOW, width=3))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"), height=360,
                    title=dict(text=f"<b>{sel_com_month} Sales by Channel (yellow = target)</b>",
                               font=dict(size=13, color="white"), x=0),
                    xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                    yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                    margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

            with col6:
                channel_sel["vs_target_pct"] = (
                    (channel_sel["Sales_Count"] - channel_sel["Sales_Target"])
                    / channel_sel["Sales_Target"] * 100
                ).round(1)
                colors_t = [GREEN if v >= 0 else RED for v in channel_sel["vs_target_pct"]]
                fig = go.Figure(go.Bar(
                    x=channel_sel["Channel"], y=channel_sel["vs_target_pct"],
                    marker_color=colors_t,
                    text=[f"{v:+.1f}%" for v in channel_sel["vs_target_pct"]],
                    textposition="outside", textfont=dict(color="white", size=11),
                ))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"), height=360,
                    title=dict(text=f"<b>{sel_com_month} Sales vs Target (%)</b>",
                               font=dict(size=13, color="white"), x=0),
                    xaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa")),
                    yaxis=dict(gridcolor="#1e1e3a", tickfont=dict(color="#8888aa"),
                               zeroline=True, zerolinecolor="#3a3a5a"),
                    margin=dict(l=10, r=10, t=44, b=10), showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)

            rows = ""
            for _, r in channel_sel.iterrows():
                vs_t = r["Sales_Count"] - r["Sales_Target"]
                t_class = "green-text" if vs_t >= 0 else "red-text"
                rows += f"""<tr>
                    <td>{r['Channel']}</td>
                    <td style="text-align:right">{r['Sales_Count']:,.0f}</td>
                    <td style="text-align:right">{r['Sales_Target']:,.0f}</td>
                    <td style="text-align:right" class="{t_class}">{vs_t:+,.0f}</td>
                    <td style="text-align:right" class="{t_class}">{r['vs_target_pct']:+.1f}%</td>
                </tr>"""
            st.markdown(f"""
            <table class="data-table">
                <thead><tr>
                    <th>Channel</th>
                    <th style="text-align:right">Sales</th>
                    <th style="text-align:right">Target</th>
                    <th style="text-align:right">Variance</th>
                    <th style="text-align:right">Var %</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table>""", unsafe_allow_html=True)
