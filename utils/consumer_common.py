"""Shared helpers for the Consumer dashboard pages.

Extracted from the former single-page pages/4_Consumer.py so the split
Consumer Sales / Prepaid / Postpaid / WTTx pages can reuse them.
"""

import pandas as pd


def _sparkline(series, color, height=44):
    vals = [float(v) if pd.notna(v) else 0.0 for v in series]
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    w = 220
    pts = []
    for i, v in enumerate(vals):
        x = i * w / max(len(vals) - 1, 1)
        y = height - (v - mn) / rng * height * 0.78 - height * 0.11
        pts.append(f"{x:.1f},{y:.1f}")
    line_pts = " ".join(pts)
    fill_pts  = f"0,{height} {line_pts} {w},{height}"
    r, g, b   = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return (
        f'<svg width="100%" height="{height}" viewBox="0 0 {w} {height}" '
        f'preserveAspectRatio="none" style="display:block;margin-top:8px">'
        f'<polygon points="{fill_pts}" fill="rgba({r},{g},{b},0.15)"/>'
        f'<polyline points="{line_pts}" fill="none" stroke="{color}" stroke-width="1.5"/>'
        f'</svg>'
    )


def _fmt_k(n):
    n = float(n)
    if n >= 1_000_000: return f"{n/1_000_000:.1f}"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(int(n))


def _latest_row_with(df, col):
    """Return the last row where col > 0."""
    valid = df[df[col] > 0]
    return valid.iloc[-1] if not valid.empty else None


def _base_layout(fig, title, height, y_range=None):
    kw = dict(gridcolor="#E6EAF0", tickfont=dict(color="#5B6675", size=14))
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1F2328"), height=height,
        title=dict(text=f"<b>{title}</b>", font=dict(size=28, color="#1F2328"), x=0),
        xaxis=kw,
        yaxis=dict(**kw, range=y_range),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h",
                    y=1.08, x=0, font=dict(size=14)),
        margin=dict(l=10, r=10, t=44, b=10),
    )
    return fig


def _pre_kpi(label, value, line1, l1_col, line2, l2_col, accent, spark, badge=None):
    b_html = (
        f'<span style="display:inline-block;background:rgba(185,28,28,0.12);'
        f'border:1px solid rgba(185,28,28,0.35);border-radius:20px;padding:2px 10px;'
        f'font-size:10px;color:#D14343;font-weight:600;margin-top:6px">{badge}</span>'
    ) if badge else ""
    sp_html = (
        f'<div style="margin-top:6px;opacity:0.9">{_sparkline(spark, accent, 44)}</div>'
    ) if spark else ""
    return (
        f'<div style="background:#F6F8FA;border-radius:10px;padding:7px 12px;'
        f'border:1px solid #D0D7DE;border-top:3px solid {accent};'
        f'height:100%;box-sizing:border-box">'
        f'<div style="font-size:28px;color:#5B6675;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:2px">{label}</div>'
        f'<div style="font-size:62px;font-weight:800;color:#1F2328;line-height:1.05;'
        f'margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
        f'{value}</div>'
        f'<div style="font-size:29px;color:{l1_col};font-weight:600;margin-bottom:0px;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{line1}</div>'
        f'<div style="font-size:29px;color:{l2_col};font-weight:600;'
        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{line2}</div>'
        f'{b_html}{sp_html}'
        f'</div>'
    )
