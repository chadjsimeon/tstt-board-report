"""
build_board_data.py — ETL: Consolidated Contribution Statements.xlsx → TSTT_Board_Data.xlsx

Run whenever new financial data arrives:
    python build_board_data.py

Values are written as raw TTD$ — data_loader.py handles the /1,000,000 scaling.
"""

import numpy as np
import pandas as pd

# ── openpyxl monkey-patch for corrupted print-title in source workbook ────────
import openpyxl.reader.workbook as _wbr
_orig_assign = _wbr.WorkbookParser.assign_names
def _safe_assign(self, *a, **k):
    try: return _orig_assign(self, *a, **k)
    except Exception: pass
_wbr.WorkbookParser.assign_names = _safe_assign

# ── File paths ─────────────────────────────────────────────────────────────────
SRC          = "Consolidated Contribution Statements.xlsx"
DST          = "TSTT_Board_Data.xlsx"
SUBS_SRC     = "subscriber_base_apw.xlsx"
AMP_KPI_SRC  = "Amplia Metrics 2024-2025 February 2026.xlsx"
AOP_OPEX_SRC = "OPEX_AOP_FY2027.xlsx"

CUR_FY = "2026-27"
LY_FY  = "2025-26"
PY_FY  = "2024-25"

MONTH_ORDER = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March",
]
_Q4_MONTHS = {"January", "February", "March"}


def fmt_month(month_name: str, fy: str) -> str:
    """'April', '2026-27' → 'Apr-26'"""
    first_yr, second_yr = fy.split("-")
    suffix = second_yr if month_name in _Q4_MONTHS else first_yr[-2:]
    return pd.to_datetime(month_name, format="%B").strftime("%b") + "-" + suffix


def _g(lookup: dict, key: str, mon_yy: str, default=np.nan):
    return lookup.get((key, mon_yy), default)


def _safe(v):
    return float(v) if pd.notna(v) else np.nan


# ── Row index constants (0-based) for Consolidated P&L ───────────────────────
CPL = dict(
    TOT_REV=16,  CON_REV=11,  BIZ_REV=12,  DPDI_REV=13, AMP_REV=14,  OTH_REV=15,
    CON_COS=18,  BIZ_COS=19,  DPDI_COS=20, AMP_COS=21,  OTH_COS=22,
    DIR_COST=23, GP=25,       TOT_OPEX=166, EBITDA=168,  PAT=182,
    PERSONNEL=33, MAINT=67,   BAD_DEBT=161,
)
# First data column per FY in Consolidated P&L
FY_COL = {PY_FY: 15, LY_FY: 27, CUR_FY: 39}

# ── Row index constants for Consol P&L AoP (FY26-27 only) ────────────────────
CAOP = dict(
    TOT_REV=15, CON_REV=10, BIZ_REV=11, DPDI_REV=12, AMP_REV=13, OTH_REV=14,
    DIR_COST=22, GP=26, TOT_OPEX=162, EBITDA=164, PAT=178,
)

# ── OPEX categories ────────────────────────────────────────────────────────────
AOP_OPEX_CATEGORY_MAP = {
    "Personnel":                "Personnel",
    "Maintenance":              "Maintenance",
    "Consultancy & Other Fees": "Consultancy & Professional Fees",
    "Professional":             "Consultancy & Professional Fees",
    "Other Operating Expenses": "Other Operating Expenses",
    "Bad Debt":                 "Bad Debt",
    "Advertising & PR":         "Advertising & PR",
}
CANONICAL_OPEX_CATS = [
    "Personnel", "Maintenance", "Consultancy & Professional Fees",
    "Other Operating Expenses", "Bad Debt", "Advertising & PR",
]


# ── Sheet readers ──────────────────────────────────────────────────────────────

def _read_consol_pl(xl):
    """Return {(metric_key, 'Mon-YY'): raw_TTD}. Covers PY/LY/CUR FY."""
    df = xl.parse("Consolidated P&L", header=None)
    result = {}
    for fy, start_col in FY_COL.items():
        first_yr, second_yr = fy.split("-")
        for offset in range(12):
            col = start_col + offset
            raw_lbl = df.iloc[10, col]
            if pd.isna(raw_lbl):
                continue
            abbr = str(raw_lbl).strip()[:3]
            yr = second_yr if abbr in ("Jan", "Feb", "Mar") else first_yr[-2:]
            mon_yy = f"{abbr}-{yr}"
            for key, row_idx in CPL.items():
                result[(key, mon_yy)] = _safe(df.iloc[row_idx, col])
    return result


def _read_consol_aop(xl):
    """Return {(metric_key, 'Mon-YY'): raw_TTD}. Source is TTD thousands → ×1000."""
    df = xl.parse("Consol P&L AoP", header=None)
    result = {}
    first_yr, second_yr = CUR_FY.split("-")
    for offset in range(12):
        col = 2 + offset
        raw_lbl = df.iloc[9, col]
        if pd.isna(raw_lbl):
            continue
        abbr = str(raw_lbl).strip()[:3]
        yr = second_yr if abbr in ("Jan", "Feb", "Mar") else first_yr[-2:]
        mon_yy = f"{abbr}-{yr}"
        for key, row_idx in CAOP.items():
            v = df.iloc[row_idx, col]
            result[(key, mon_yy)] = _safe(v) * 1000 if pd.notna(v) else np.nan
    return result


def _read_wide_pl(xl, sheet, header_row, data_col_start, rows: dict, scale=1_000_000):
    """Read a wide-format P&L sheet with datetime column headers."""
    df = xl.parse(sheet, header=None)
    result = {}
    for col in range(data_col_start, df.shape[1]):
        dt = df.iloc[header_row, col]
        if pd.isna(dt) or not hasattr(dt, "strftime"):
            continue
        mon_yy = dt.strftime("%b-%y")
        for key, row_idx in rows.items():
            v = df.iloc[row_idx, col]
            result[(key, mon_yy)] = _safe(v) * scale if pd.notna(v) else np.nan
    return result


def _read_consumer_pl(xl):
    return _read_wide_pl(xl, "Consumer Sales P&L", 3, 3, dict(
        POSTPD_REV=5, PREPD_REV=6, WTTX_REV=11,
        TOT_REV=16, DIR_COST=20, GP=22, TOT_OPEX=27, EBITDA=29,
    ))


def _read_business_pl(xl):
    return _read_wide_pl(xl, "Business Sales P&L", 3, 4, dict(
        ENT_MOB=5, CIRCUIT=8, CLOUD=9, SECURITY=10, ENT_FIXED=12,
        CPE=13, WTTX=14, CARRIER=15, OTHER=16,
        TOT_REV=17, DIR_COST=21, GP=23, TOT_OPEX=28, EBITDA=30,
    ))


def _read_dpdi_pl(xl):
    return _read_wide_pl(xl, "DPD&I P&L", 2, 3, dict(
        E_TENDER=4, E_HEALTH=5, E_KIOSK=6, PAYPR=7, E_CASHBOOK=8,
        E_PAY=9, OTHER=10,
        TOT_REV=11, DIR_COST=15, GP=17, TOT_OPEX=26, EBITDA=28,
    ))


def _read_amplia_fin(xl):
    """Amplia formatted FY2526: raw TTD, date headers at row 5, data cols 9-44."""
    df = xl.parse("Amplia formatted FY2526", header=None)
    result = {}
    for col in range(9, 45):
        dt = df.iloc[5, col]
        if pd.isna(dt) or not hasattr(dt, "strftime"):
            continue
        mon_yy = dt.strftime("%b-%y")
        for key, row_idx in dict(TOT_REV=16, GP=30, EBITDA=75, PAT=88).items():
            result[(key, mon_yy)] = _safe(df.iloc[row_idx, col])
    return result


def _load_aop_opex_fy27():
    try:
        aop = pd.read_excel(AOP_OPEX_SRC, sheet_name="OPEX AOP")
        aop["Cat"] = aop["Group"].map(AOP_OPEX_CATEGORY_MAP)
        aop = aop.dropna(subset=["Cat"])
        return aop.groupby(["Cat", "Period"])["Amount"].sum().to_dict()
    except FileNotFoundError:
        print(f"  WARNING: {AOP_OPEX_SRC} not found — FY2027 OPEX plan will be empty.")
        return {}


# ── Build functions ────────────────────────────────────────────────────────────

def build_financial_monthly(cpl, caop, act_months):
    rows = []
    for m in MONTH_ORDER:
        mon = fmt_month(m, LY_FY)
        py  = fmt_month(m, PY_FY)
        rev = _g(cpl, "TOT_REV", mon)
        ebi = _g(cpl, "EBITDA",  mon)
        pat = _g(cpl, "PAT",     mon)
        rows.append({
            "Month":         mon,
            "Revenue":       rev,
            "EBITDA":        ebi,
            "PAT":           pat,
            "EBITDA_Margin": ebi / rev if (pd.notna(ebi) and pd.notna(rev) and rev) else np.nan,
            "Revenue_AOP":   np.nan,
            "EBITDA_AOP":    np.nan,
            "PAT_AOP":       np.nan,
            "Revenue_PY":    _g(cpl, "TOT_REV", py),
            "EBITDA_PY":     _g(cpl, "EBITDA",  py),
            "PAT_PY":        _g(cpl, "PAT",     py),
        })
    for m in act_months:
        mon = fmt_month(m, CUR_FY)
        ly  = fmt_month(m, LY_FY)
        rev = _g(cpl,  "TOT_REV", mon)
        ebi = _g(cpl,  "EBITDA",  mon)
        pat = _g(cpl,  "PAT",     mon)
        rows.append({
            "Month":         mon,
            "Revenue":       rev,
            "EBITDA":        ebi,
            "PAT":           pat,
            "EBITDA_Margin": ebi / rev if (pd.notna(ebi) and pd.notna(rev) and rev) else np.nan,
            "Revenue_AOP":   _g(caop, "TOT_REV", mon),
            "EBITDA_AOP":    _g(caop, "EBITDA",  mon),
            "PAT_AOP":       _g(caop, "PAT",     mon),
            "Revenue_PY":    _g(cpl,  "TOT_REV", ly),
            "EBITDA_PY":     _g(cpl,  "EBITDA",  ly),
            "PAT_PY":        _g(cpl,  "PAT",     ly),
        })
    return pd.DataFrame(rows)


def build_pnl_breakdown(cpl, caop, act_months):
    SEGS = {"CON": "CONSUMER SALES", "BIZ": "BUSINESS SALES",
            "DPDI": "DPDI", "AMP": "AMPLIA", "OTH": "OTHER"}

    def make_row(mon, src, aop_src):
        r = {"Month": mon}
        for k, lbl in SEGS.items():
            r[f"{lbl}_Rev"]     = _g(src,     f"{k}_REV", mon, 0)
            r[f"{lbl}_Rev_AOP"] = _g(aop_src, f"{k}_REV", mon, 0)
            r[f"{lbl}_COS"]     = _g(src,     f"{k}_COS", mon, 0)
            r[f"{lbl}_COS_AOP"] = _g(aop_src, f"{k}_COS", mon, 0)
        r["Total_Rev"]      = _g(src,     "TOT_REV",  mon, 0)
        r["Total_Rev_AOP"]  = _g(aop_src, "TOT_REV",  mon, 0)
        r["Total_COS"]      = _g(src,     "DIR_COST", mon, 0)
        r["Total_COS_AOP"]  = _g(aop_src, "DIR_COST", mon, 0)
        r["Total_OPEX"]     = _g(src,     "TOT_OPEX", mon, 0)
        r["Total_OPEX_AOP"] = _g(aop_src, "TOT_OPEX", mon, 0)
        r["EBITDA"]         = _g(src,     "EBITDA",   mon, 0)
        r["EBITDA_AOP"]     = _g(aop_src, "EBITDA",   mon, 0)
        return r

    rows = [make_row(fmt_month(m, LY_FY), cpl, {}) for m in MONTH_ORDER]
    rows += [make_row(fmt_month(m, CUR_FY), cpl, caop) for m in act_months]
    return pd.DataFrame(rows)


def build_ebitda_bridge(cpl, caop, latest_mon):
    g  = lambda src, k: _g(src, k, latest_mon, 0)
    rv = g(cpl, "TOT_REV")  - g(caop, "TOT_REV")
    dc = g(cpl, "DIR_COST") - g(caop, "DIR_COST")
    ox = g(cpl, "TOT_OPEX") - g(caop, "TOT_OPEX")
    bt = lambda v: "Positive" if v >= 0 else "Negative"
    return pd.DataFrame([
        {"Category": "AOP EBITDA",           "Value": g(caop,"EBITDA"), "Type": "Absolute",  "Sort_Order": 1},
        {"Category": "Revenue Variance",      "Value": rv,               "Type": bt(rv),      "Sort_Order": 2},
        {"Category": "Direct Costs Variance", "Value": dc,               "Type": bt(dc),      "Sort_Order": 3},
        {"Category": "OPEX Variance",         "Value": ox,               "Type": bt(ox),      "Sort_Order": 4},
        {"Category": "Actual EBITDA",         "Value": 0,                "Type": "Total",     "Sort_Order": 5},
    ])


def build_kpi_summary(cpl, caop, latest_mon, ly_mon):
    ra = _g(cpl,  "TOT_REV", latest_mon, 0);  rp = _g(caop, "TOT_REV", latest_mon, 0);  rl = _g(cpl, "TOT_REV", ly_mon, 0)
    ea = _g(cpl,  "EBITDA",  latest_mon, 0);  ep = _g(caop, "EBITDA",  latest_mon, 0);  el = _g(cpl, "EBITDA",  ly_mon, 0)
    pa = _g(cpl,  "PAT",     latest_mon, 0);  pp = _g(caop, "PAT",     latest_mon, 0);  pl = _g(cpl, "PAT",     ly_mon, 0)
    ma = ea / ra if ra else 0;  mp = ep / rp if rp else 0;  ml = el / rl if rl else 0
    s  = lambda a, p: "🟢" if a >= p else "🔴"
    return pd.DataFrame([
        {"Month": latest_mon, "Section": "Financial", "KPI_Name": "Revenue",       "Actual": ra, "AOP": rp, "PY": rl, "Status": s(ra,rp), "Unit": ""},
        {"Month": latest_mon, "Section": "Financial", "KPI_Name": "EBITDA",        "Actual": ea, "AOP": ep, "PY": el, "Status": s(ea,ep), "Unit": ""},
        {"Month": latest_mon, "Section": "Financial", "KPI_Name": "PAT",           "Actual": pa, "AOP": pp, "PY": pl, "Status": s(pa,pp), "Unit": ""},
        {"Month": latest_mon, "Section": "Financial", "KPI_Name": "EBITDA Margin", "Actual": ma, "AOP": mp, "PY": ml, "Status": s(ma,mp), "Unit": "%"},
    ])


def build_opex(cpl, aop_fy27, act_months):
    rows = []

    def actuals_for(mon):
        p  = _g(cpl, "PERSONNEL", mon, np.nan)
        m  = _g(cpl, "MAINT",     mon, np.nan)
        bd = _g(cpl, "BAD_DEBT",  mon, np.nan)
        tot= _g(cpl, "TOT_OPEX",  mon, np.nan)
        oth = (tot - p - m - bd) if all(pd.notna(v) for v in [tot, p, m, bd]) else np.nan
        return {"Personnel": p, "Maintenance": m, "Bad Debt": bd,
                "Other Operating Expenses": oth,
                "Consultancy & Professional Fees": np.nan,
                "Advertising & PR": np.nan}

    for m in MONTH_ORDER:
        mon = fmt_month(m, LY_FY)
        vals = actuals_for(mon)
        for cat in CANONICAL_OPEX_CATS:
            rows.append({"Month": mon, "Category": cat,
                         "Actual": vals[cat], "Plan": np.nan,
                         "Variance": 0, "Variance_Pct": 0})

    for m in act_months:
        mon = fmt_month(m, CUR_FY)
        vals = actuals_for(mon)
        for cat in CANONICAL_OPEX_CATS:
            rows.append({"Month": mon, "Category": cat,
                         "Actual": vals[cat],
                         "Plan": aop_fy27.get((cat, mon), np.nan),
                         "Variance": 0, "Variance_Pct": 0})

    for m in [x for x in MONTH_ORDER if x not in act_months]:
        mon = fmt_month(m, CUR_FY)
        for cat in CANONICAL_OPEX_CATS:
            rows.append({"Month": mon, "Category": cat,
                         "Actual": np.nan,
                         "Plan": aop_fy27.get((cat, mon), np.nan),
                         "Variance": 0, "Variance_Pct": 0})

    return pd.DataFrame(rows)


def _mar26_props(pnl, keys):
    """Proportion of each key in total (using Mar-26 as the base month)."""
    vals = {k: max(_g(pnl, k, "Mar-26", 0), 0) for k in keys}
    total = sum(vals.values())
    return {k: (v / total if total > 0 else 0) for k, v in vals.items()}


def build_consumer_sales(cpl, caop, con_pl, subs_df, act_months):
    SEG_KEYS = {"POSTPD_REV": "Postpaid", "PREPD_REV": "Prepaid", "WTTX_REV": "WTTx"}
    props = _mar26_props(con_pl, list(SEG_KEYS))
    # Mar-26 "Other" proportion relative to CPL CON_REV total
    mar26_seg_sum = sum(_g(con_pl, k, "Mar-26", 0) for k in SEG_KEYS)
    mar26_tot_rev = _g(cpl, "CON_REV", "Mar-26", 0)
    other_prop = max(mar26_tot_rev - mar26_seg_sum, 0) / mar26_tot_rev if mar26_tot_rev else 0

    def get_subs(fy, month_full, seg):
        abbr = pd.to_datetime(month_full, format="%B").strftime("%b")
        row = subs_df[(subs_df["FY"] == fy) & (subs_df["Month"] == abbr)]
        if row.empty or seg not in ["Prepaid", "Postpaid", "WTTx"]:
            return 0
        v = row.iloc[0].get(seg, 0)
        return int(v) if pd.notna(v) else 0

    rows = []
    # LY: segment revenue directly from con_pl
    for m in MONTH_ORDER:
        mon = fmt_month(m, LY_FY)
        tot = _g(cpl, "CON_REV", mon)
        for k, seg in SEG_KEYS.items():
            rev = _g(con_pl, k, mon)
            subs = get_subs(LY_FY, m, seg)
            rows.append({"Month": mon, "Segment": seg, "Revenue": rev,
                         "Revenue_AOP": np.nan, "Subscribers": subs,
                         "Churn_Pct": 0, "ARPU": rev/subs if subs and pd.notna(rev) else 0,
                         "YoY_Change_Pct": 0})
        for seg in ["TV", "Residential Security"]:
            rows.append({"Month": mon, "Segment": seg, "Revenue": np.nan,
                         "Revenue_AOP": np.nan, "Subscribers": 0,
                         "Churn_Pct": 0, "ARPU": 0, "YoY_Change_Pct": 0})
        seg_sum = sum(_g(con_pl, k, mon, 0) for k in SEG_KEYS)
        other = (tot - seg_sum) if pd.notna(tot) else np.nan
        rows.append({"Month": mon, "Segment": "Other", "Revenue": other,
                     "Revenue_AOP": np.nan, "Subscribers": 0,
                     "Churn_Pct": 0, "ARPU": 0, "YoY_Change_Pct": 0})

    # CUR: proportional from Mar-26
    for m in act_months:
        mon = fmt_month(m, CUR_FY)
        ly  = fmt_month(m, LY_FY)
        tot = _g(cpl,  "CON_REV", mon)
        aop = _g(caop, "CON_REV", mon)
        for k, seg in SEG_KEYS.items():
            rev  = tot * props[k] if pd.notna(tot) else np.nan
            ly_r = _g(con_pl, k, ly)
            yoy  = (rev - ly_r) / abs(ly_r) if (pd.notna(ly_r) and ly_r and pd.notna(rev)) else 0
            subs = get_subs(CUR_FY, m, seg)
            rows.append({"Month": mon, "Segment": seg, "Revenue": rev,
                         "Revenue_AOP": aop * props[k] if pd.notna(aop) else np.nan,
                         "Subscribers": subs,
                         "Churn_Pct": 0, "ARPU": rev/subs if subs and pd.notna(rev) else 0,
                         "YoY_Change_Pct": yoy})
        for seg in ["TV", "Residential Security"]:
            rows.append({"Month": mon, "Segment": seg, "Revenue": np.nan,
                         "Revenue_AOP": np.nan, "Subscribers": 0,
                         "Churn_Pct": 0, "ARPU": 0, "YoY_Change_Pct": 0})
        other = tot * other_prop if pd.notna(tot) else np.nan
        rows.append({"Month": mon, "Segment": "Other", "Revenue": other,
                     "Revenue_AOP": np.nan, "Subscribers": 0,
                     "Churn_Pct": 0, "ARPU": 0, "YoY_Change_Pct": 0})

    return pd.DataFrame(rows)


def build_business_sales(cpl, caop, biz_pl, act_months):
    SEG_MAP = {
        "Circuit/Data": ["CIRCUIT"],
        "Cloud":        ["CLOUD"],
        "Carrier":      ["CARRIER"],
        "Enterprise":   ["ENT_MOB", "ENT_FIXED", "CPE"],
        "Security":     ["SECURITY"],
        "WTTx":         ["WTTX"],
        "Other":        ["OTHER"],
        "IoT":          [],
    }

    def seg_rev_from(pnl, keys, mon):
        if not keys:
            return np.nan
        vals = [_g(pnl, k, mon) for k in keys]
        valid = [v for v in vals if pd.notna(v)]
        return sum(valid) if valid else np.nan

    # Build Mar-26 proportions for CPL-level breakdown in CUR months
    mar_segs = {seg: max(seg_rev_from(biz_pl, keys, "Mar-26") or 0, 0)
                for seg, keys in SEG_MAP.items() if keys}
    mar_tot = sum(mar_segs.values())
    mar_props = {seg: (v / mar_tot if mar_tot else 0) for seg, v in mar_segs.items()}
    # IoT gets 0 proportion
    mar_props["IoT"] = 0

    rows = []
    # LY: use biz_pl directly (Sep-22 to Mar-26 covers all LY months)
    for m in MONTH_ORDER:
        mon = fmt_month(m, LY_FY)
        for seg, keys in SEG_MAP.items():
            rev = seg_rev_from(biz_pl, keys, mon)
            rows.append({"Month": mon, "Segment": seg, "Revenue": rev,
                         "Revenue_AOP": np.nan, "Gross_Profit": 0,
                         "GP_Margin_Pct": 0, "Contribution": 0,
                         "MRR": 0, "Direct_Costs": 0})

    # CUR: proportional breakdown
    for m in act_months:
        mon = fmt_month(m, CUR_FY)
        tot = _g(cpl,  "BIZ_REV", mon)
        aop = _g(caop, "BIZ_REV", mon)
        for seg in SEG_MAP:
            p = mar_props.get(seg, 0)
            rows.append({"Month": mon, "Segment": seg,
                         "Revenue": tot * p if pd.notna(tot) else np.nan,
                         "Revenue_AOP": aop * p if pd.notna(aop) else np.nan,
                         "Gross_Profit": 0, "GP_Margin_Pct": 0,
                         "Contribution": 0, "MRR": 0, "Direct_Costs": 0})

    return pd.DataFrame(rows)


def build_dpdi(cpl, caop, dpdi_pl, act_months):
    PRODS = [
        ("E-Tender",   "E_TENDER"),
        ("E-Health",   "E_HEALTH"),
        ("E-Kiosk",    "E_KIOSK"),
        ("PayPr",      "PAYPR"),
        ("E-Cashbook", "E_CASHBOOK"),
        ("E-Pay",      "E_PAY"),
        ("Other",      "OTHER"),
    ]
    # Mar-26 proportions for CUR months
    mar_vals = {name: max(_g(dpdi_pl, k, "Mar-26", 0), 0) for name, k in PRODS}
    mar_tot  = sum(mar_vals.values())
    mar_props = {name: (v / mar_tot if mar_tot else 0) for name, v in mar_vals.items()}

    rows = []
    for m in MONTH_ORDER:
        mon = fmt_month(m, LY_FY)
        tot_dc = _g(dpdi_pl, "DIR_COST", mon) or 0.0
        for name, key in PRODS:
            rev = _g(dpdi_pl, key, mon)
            dc  = tot_dc * mar_props[name]
            gp  = (rev - dc) if pd.notna(rev) else np.nan
            rows.append({"Month": mon, "Product": name,
                         "Revenue": rev,
                         "Revenue_AOP": np.nan,
                         "Gross_Profit": gp, "GP_Margin_Pct": 0,
                         "EBITDA": 0, "Direct_Costs": dc})

    for m in act_months:
        mon     = fmt_month(m, CUR_FY)
        tot     = _g(cpl,  "DPDI_REV", mon)
        aop     = _g(caop, "DPDI_REV", mon)
        tot_dc  = _g(cpl,  "DPDI_COS", mon) or 0.0
        aop_dc  = _g(caop, "DPDI_COS", mon) or 0.0
        for name, _ in PRODS:
            p   = mar_props[name]
            rev = tot * p if pd.notna(tot) else np.nan
            dc  = tot_dc * p
            gp  = (rev - dc) if pd.notna(rev) else np.nan
            rows.append({"Month": mon, "Product": name,
                         "Revenue": rev,
                         "Revenue_AOP": aop * p if pd.notna(aop) else np.nan,
                         "Gross_Profit": gp, "GP_Margin_Pct": 0,
                         "EBITDA": 0, "Direct_Costs": dc,
                         "Direct_Costs_AOP": aop_dc * p})

    return pd.DataFrame(rows)


def build_amplia_financial(caop, amp_fin, act_months):
    rows = []
    for m in MONTH_ORDER:
        mon = fmt_month(m, LY_FY)
        rev = _g(amp_fin, "TOT_REV", mon)
        gp  = _g(amp_fin, "GP",      mon)
        ebi = _g(amp_fin, "EBITDA",  mon)
        pat = _g(amp_fin, "PAT",     mon)
        dc  = (rev - gp) if (pd.notna(rev) and pd.notna(gp)) else np.nan
        rows.append({"Month": mon, "Revenue": rev, "Revenue_AOP": np.nan,
                     "Gross_Profit": gp, "EBITDA": ebi, "EBITDA_AOP": np.nan,
                     "PAT": pat, "OPEX": 0, "Direct_Costs": dc})

    for m in act_months:
        mon = fmt_month(m, CUR_FY)
        rev = _g(amp_fin, "TOT_REV", mon)
        gp  = _g(amp_fin, "GP",      mon)
        ebi = _g(amp_fin, "EBITDA",  mon)
        pat = _g(amp_fin, "PAT",     mon)
        dc  = (rev - gp) if (pd.notna(rev) and pd.notna(gp)) else np.nan
        rows.append({"Month": mon, "Revenue": rev,
                     "Revenue_AOP": _g(caop, "AMP_REV", mon),
                     "Gross_Profit": gp, "EBITDA": ebi, "EBITDA_AOP": np.nan,
                     "PAT": pat, "OPEX": 0, "Direct_Costs": dc})

    return pd.DataFrame(rows)


# ── Amplia commercial (from separate KPI file, unchanged logic) ───────────────

def _amp_metric(df, metric_label, fy_label):
    idx = df[df[0] == metric_label].index
    if len(idx) == 0:
        return [np.nan] * 12
    for i in range(idx[0], min(idx[0] + 20, len(df))):
        if df.loc[i, 1] == fy_label:
            return df.loc[i, 2:13].tolist()
    return [np.nan] * 12


def build_amplia_commercial(amp_kpi):
    arpu_act  = _amp_metric(amp_kpi, "Amplia ARPU",  "FY25/26 Actual")
    gross_act = _amp_metric(amp_kpi, "Gross Adds",   "FY25/26 Actual")
    gross_bud = _amp_metric(amp_kpi, "Gross Adds",   "FY25/26 Budget")
    churn_act = _amp_metric(amp_kpi, "Amplia Churn", "FY25/26 Actual")
    churn_bud = _amp_metric(amp_kpi, "Amplia Churn", "FY25/26 Budget")
    rows = []
    for i, m in enumerate(MONTH_ORDER):
        ga = gross_act[i]
        if pd.isna(ga):
            continue
        rows.append({
            "Month":               fmt_month(m, LY_FY),
            "ARPU":                round(arpu_act[i], 2) if pd.notna(arpu_act[i]) else 0,
            "Gross_Additions":     int(ga),
            "Gross_Additions_AOP": int(gross_bud[i]) if pd.notna(gross_bud[i]) else 0,
            "Monthly_Churn":       int(churn_act[i]) if pd.notna(churn_act[i]) else 0,
            "Churn_AOP":           int(churn_bud[i]) if pd.notna(churn_bud[i]) else 0,
            "Net_Port": 0, "Channel": "Total",
            "Sales_Count":  int(ga),
            "Sales_Target": int(gross_bud[i]) if pd.notna(gross_bud[i]) else 0,
        })
    return pd.DataFrame(rows)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"Reading {SRC} ...")
    xl = pd.ExcelFile(SRC)

    # Detect which CUR FY months have actual data in Consolidated P&L
    cpl_raw = xl.parse("Consolidated P&L", header=None)
    act_months = []
    for offset, m in enumerate(MONTH_ORDER):
        col = FY_COL[CUR_FY] + offset
        v = cpl_raw.iloc[CPL["TOT_REV"], col]
        if pd.notna(v) and v != 0:
            act_months.append(m)

    latest_month = act_months[-1] if act_months else MONTH_ORDER[0]
    latest_mon   = fmt_month(latest_month, CUR_FY)
    ly_mon       = fmt_month(latest_month, LY_FY)
    print(f"  CUR FY ({CUR_FY}) ACT months: {act_months or ['(none)']}")
    print(f"  Latest month: {latest_mon}")

    print("  Parsing sheets ...")
    cpl    = _read_consol_pl(xl)
    caop   = _read_consol_aop(xl)
    con_pl = _read_consumer_pl(xl)
    biz_pl = _read_business_pl(xl)
    dpdi_pl= _read_dpdi_pl(xl)
    amp_fin= _read_amplia_fin(xl)

    print(f"Reading {SUBS_SRC} ...")
    subs_df = pd.read_excel(SUBS_SRC, sheet_name="monthly_pivot", header=1)

    print(f"Reading {AMP_KPI_SRC} ...")
    amp_kpi = pd.read_excel(AMP_KPI_SRC, sheet_name="Sheet1", header=None)

    print(f"Reading {AOP_OPEX_SRC} ...")
    aop_fy27 = _load_aop_opex_fy27()
    print(f"  FY2027 OPEX plan entries: {len(aop_fy27)}")

    # Preserve Cash_CAPEX from existing output (not available in new source)
    print(f"Preserving Cash_CAPEX from {DST} ...")
    try:
        cash_capex_df = pd.read_excel(DST, sheet_name="Cash_CAPEX")
        print(f"  Loaded {len(cash_capex_df)} rows")
    except Exception:
        cash_capex_df = pd.DataFrame(columns=[
            "Month","Cash_Balance","Net_Debt","Collections_Pct",
            "Collections_Pct_Gov","Collections_Pct_NonGov",
            "FCF","CAPEX_Actual","CAPEX_Plan",
        ])
        print("  No existing Cash_CAPEX found — using empty DataFrame")

    sheets = {
        "KPI_Summary":       build_kpi_summary(cpl, caop, latest_mon, ly_mon)
                             if act_months else pd.DataFrame(
                                 columns=["Month","Section","KPI_Name","Actual","AOP","PY","Status","Unit"]),
        "Financial_Monthly": build_financial_monthly(cpl, caop, act_months),
        "EBITDA_Bridge":     build_ebitda_bridge(cpl, caop, latest_mon)
                             if act_months else pd.DataFrame(
                                 columns=["Category","Value","Type","Sort_Order"]),
        "OPEX":              build_opex(cpl, aop_fy27, act_months),
        "Cash_CAPEX":        cash_capex_df,
        "Consumer_Sales":    build_consumer_sales(cpl, caop, con_pl, subs_df, act_months),
        "Business_Sales":    build_business_sales(cpl, caop, biz_pl, act_months),
        "Pipeline":          pd.DataFrame(columns=["Month","Stage","Deal_Count","Value_TTD_M","Avg_Deal_Size","Win_Rate_Pct"]),
        "Renewals":          pd.DataFrame(columns=["Customer","Product_Service","ACV_TTD_M","Expiry_Date","Risk_Level","Status","Action_Plan"]),
        "DPDI":              build_dpdi(cpl, caop, dpdi_pl, act_months),
        "AMPLIA_Financial":  build_amplia_financial(caop, amp_fin, act_months),
        "AMPLIA_Commercial": build_amplia_commercial(amp_kpi),
        "PnL_Breakdown":     build_pnl_breakdown(cpl, caop, act_months),
    }

    print(f"\nWriting {DST} ...")
    with pd.ExcelWriter(DST, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            print(f"  {name:<22} {len(df):>4} rows")

    print("\nDone. Run:  streamlit run app.py")


if __name__ == "__main__":
    main()
