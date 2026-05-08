"""
build_board_data.py — ETL: financial_data.xlsx → TSTT_Board_Data.xlsx

Run this whenever new financial data arrives:
    python build_board_data.py

The script reads normalized long-format data from financial_data.xlsx and writes
the wide-format sheets expected by the Streamlit dashboard (data_loader.py).

Values are written as raw TTD$ — data_loader.py handles the /1,000,000 scaling
and decimal-to-percent conversions.
"""

import numpy as np
import pandas as pd

SRC = "financial_data.xlsx"
DST = "TSTT_Board_Data.xlsx"

CUR_FY = "2026-27"
LY_FY  = "2025-26"

# Month order within a TSTT financial year (April = Period 1)
MONTH_ORDER = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March",
]
# In an April-to-March financial year, Jan/Feb/Mar fall in the second calendar year
_Q4_MONTHS = {"January", "February", "March"}


def fmt_month(month_name: str, fy: str) -> str:
    """Return 'Mon-YY' with the correct calendar year.
    FY format 'YYYY-YY': Apr-Dec use the first year; Jan-Mar use the second.
    """
    first_yr, second_yr = fy.split("-")
    suffix = second_yr if month_name in _Q4_MONTHS else first_yr[-2:]
    return pd.to_datetime(month_name, format="%B").strftime("%b") + "-" + suffix


def _get(src: pd.DataFrame, bu: str, desc: str, month: str, default=np.nan):
    """Return a single value matching BU / description / month; default if not found."""
    mask = (src["BU"] == bu) & (src["Description"] == desc) & (src["Month"] == month)
    v = src.loc[mask, "Value"]
    return float(v.iloc[0]) if len(v) else default


def _get_sum(src: pd.DataFrame, bu: str, descs: list, month: str, default=np.nan):
    """Sum values across multiple descriptions for one BU / month."""
    if not descs:
        return default
    mask = (src["BU"] == bu) & (src["Description"].isin(descs)) & (src["Month"] == month)
    rows = src.loc[mask, "Value"]
    return float(rows.sum()) if len(rows) else default


def build_financial_monthly(act, aop, ly, ly_aop, act_months):
    """
    Build a rolling 13-month dataset:
      - FY 2025-26 (all 12 months): ACT from ly, AOP from ly_aop, LY = NaN (FY24-25 not available)
      - FY 2026-27 (ACT months only): ACT from act, AOP from aop, LY = same month from ly

    This ensures fin.iloc[-1] always lands on the most recent month with real ACT data,
    which the Financial Performance page requires for its metric cards.
    """
    rows = []

    # Historical full year: FY 2025-26
    for m in MONTH_ORDER:
        rows.append({
            "Month":         fmt_month(m, LY_FY),
            "Revenue":       _get(ly,     "Consolidated", "TOTAL REVENUE", m),
            "EBITDA":        _get(ly,     "Consolidated", "EBITDA", m),
            "PAT":           _get(ly,     "Consolidated", "Profit After Taxation", m),
            "EBITDA_Margin": _get(ly,     "Consolidated", "EBITDA %", m),
            "Revenue_AOP":   _get(ly_aop, "Consolidated", "TOTAL REVENUE", m),
            "EBITDA_AOP":    _get(ly_aop, "Consolidated", "EBITDA", m),
            "PAT_AOP":       _get(ly_aop, "Consolidated", "Profit After Taxation", m),
            "Revenue_LY":    np.nan,   # FY 2024-25 not in source data
            "EBITDA_LY":     np.nan,
            "PAT_LY":        np.nan,
        })

    # Current year: FY 2026-27 ACT months (April onward)
    for m in act_months:
        rows.append({
            "Month":         fmt_month(m, CUR_FY),
            "Revenue":       _get(act, "Consolidated", "TOTAL REVENUE", m),
            "EBITDA":        _get(act, "Consolidated", "EBITDA", m),
            "PAT":           _get(act, "Consolidated", "Profit After Taxation", m),
            "EBITDA_Margin": _get(act, "Consolidated", "EBITDA %", m),
            "Revenue_AOP":   _get(aop, "Consolidated", "TOTAL REVENUE", m),
            "EBITDA_AOP":    _get(aop, "Consolidated", "EBITDA", m),
            "PAT_AOP":       _get(aop, "Consolidated", "Profit After Taxation", m),
            "Revenue_LY":    _get(ly,  "Consolidated", "TOTAL REVENUE", m),  # same month, prior FY
            "EBITDA_LY":     _get(ly,  "Consolidated", "EBITDA", m),
            "PAT_LY":        _get(ly,  "Consolidated", "Profit After Taxation", m),
        })

    return pd.DataFrame(rows)


def build_opex(act, aop, ly, ly_aop, act_months):
    # Union of OPEX categories across all four frames
    opex_cats = sorted(
        set(act.loc[act["Category"] == "OPEX", "Description"].unique())
        | set(aop.loc[aop["Category"] == "OPEX", "Description"].unique())
        | set(ly.loc[ly["Category"] == "OPEX", "Description"].unique())
        | set(ly_aop.loc[ly_aop["Category"] == "OPEX", "Description"].unique())
    )

    rows = []
    # Pass 1: FY 2025-26 full year
    for m in MONTH_ORDER:
        for cat in opex_cats:
            rows.append({
                "Month":        fmt_month(m, LY_FY),
                "Category":     cat,
                "Actual":       _get(ly,     "Consolidated", cat, m),
                "Plan":         _get(ly_aop, "Consolidated", cat, m),
                "Variance":     0,
                "Variance_Pct": 0,
            })
    # Pass 2: FY 2026-27 ACT months
    for m in act_months:
        for cat in opex_cats:
            rows.append({
                "Month":        fmt_month(m, CUR_FY),
                "Category":     cat,
                "Actual":       _get(act, "Consolidated", cat, m),
                "Plan":         _get(aop, "Consolidated", cat, m),
                "Variance":     0,
                "Variance_Pct": 0,
            })
    return pd.DataFrame(rows)


def build_cash_capex(act, aop, ly, act_months):
    """
    Cash flow and balance sheet data is only available for FY 2025-26 (last year).
    For months where FY 2026-27 ACT cash data exists, use it; otherwise fall back
    to FY 2025-26 actuals (labeled with their original LY month stamps) so the
    board sees real figures rather than blanks.
    """
    # BS items in financial_data are stored in TTD$'000 (not raw TTD$) — multiply by 1000
    BS_SCALE = 1000

    def _cash_row(src_act, src_aop, month, fy):
        cash_bal  = _get(src_act, "Consolidated", "CF: Closing Cash Balance", month, np.nan)
        capex_act = _get(src_act, "Consolidated", "CF: Capex", month, np.nan)
        capex_act = abs(capex_act) if not np.isnan(capex_act) else np.nan
        # Use Cash Generated from Operations (positive = inflow) as proxy for operating CF
        cgo       = _get(src_act, "Consolidated", "CF: Cash Generated from Operations", month, np.nan)
        fcf       = (cgo - capex_act) if (not np.isnan(cgo) and not np.isnan(capex_act)) else np.nan
        # BS items are in TTD$'000 — scale to raw TTD$
        borrow_c  = _get(src_act, "Consolidated", "BS: Borrowings Current Portion", month, np.nan)
        borrow_lt = _get(src_act, "Consolidated", "BS: Long-term Borrowings", month, np.nan)
        cash_inv  = _get(src_act, "Consolidated", "BS: Cash & Short-term Investments", month, np.nan)
        if not any(np.isnan(v) for v in [borrow_c, borrow_lt, cash_inv]):
            net_debt = (abs(borrow_c) + abs(borrow_lt) - cash_inv) * BS_SCALE
        else:
            net_debt = np.nan
        capex_plan_val = _get(src_aop, "Consolidated", "CF: Capex", month, np.nan)
        capex_plan = abs(capex_plan_val) if not np.isnan(capex_plan_val) else np.nan
        return {
            "Month":           fmt_month(month, fy),
            "Cash_Balance":    cash_bal,
            "Net_Debt":        net_debt,
            "Collections_Pct": 0,       # not available in financial_data
            "FCF":             fcf,
            "CAPEX_Actual":    capex_act,
            "CAPEX_Plan":      capex_plan,
        }

    # Check whether CUR FY ACT contains any cash flow data
    has_cf_in_cur = (act["Category"] == "Cash Flow").any() or (act["Category"] == "Balance Sheet").any()

    rows = []
    if has_cf_in_cur:
        # Use current FY data where available
        for m in MONTH_ORDER:
            rows.append(_cash_row(act if m in act_months else pd.DataFrame(columns=act.columns),
                                  aop, m, CUR_FY))
    else:
        # Fall back to FY 2025-26 full-year actuals (most recent complete cash picture)
        for m in MONTH_ORDER:
            rows.append(_cash_row(ly, aop, m, LY_FY))

    return pd.DataFrame(rows)


def build_consumer_sales(act, aop, ly, ly_aop, act_months, subs_df):
    segment_map = {
        "Prepaid":              ["Prepd Revenue."],
        "Postpaid":             ["Postpd. Revenue."],
        "WTTx":                 ["WTTX"],
        "TV":                   ["TV"],
        "Residential Security": ["Residential Security"],
        "Other":                ["OTHER SERVICES", "Other Mobile Revenue.", "DATA", "Voice"],
    }
    _SUB_COLS = {"Prepaid": "Prepaid", "Postpaid": "Postpaid", "WTTx": "WTTx"}

    def get_subs(fy, month_full, segment):
        col = _SUB_COLS.get(segment)
        if col is None:
            return 0
        abbr = pd.to_datetime(month_full, format="%B").strftime("%b")
        row = subs_df[(subs_df["FY"] == fy) & (subs_df["Month"] == abbr)]
        if row.empty:
            return 0
        val = row.iloc[0][col]
        return int(val) if pd.notna(val) else 0

    rows = []
    # Pass 1: FY 2025-26 full year
    for m in MONTH_ORDER:
        for seg, descs in segment_map.items():
            rev  = _get_sum(ly, "Consumer Sales", descs, m)
            subs = get_subs(LY_FY, m, seg)
            arpu = rev / subs if subs > 0 and pd.notna(rev) else 0
            rows.append({
                "Month":          fmt_month(m, LY_FY),
                "Segment":        seg,
                "Revenue":        rev,
                "Revenue_AOP":    _get_sum(ly_aop, "Consumer Sales", descs, m),
                "Subscribers":    subs,
                "Churn_Pct":      0,
                "ARPU":           arpu,
                "YoY_Change_Pct": 0,
            })
    # Pass 2: FY 2026-27 ACT months
    for m in act_months:
        for seg, descs in segment_map.items():
            act_rev = _get_sum(act, "Consumer Sales", descs, m)
            ly_rev  = _get_sum(ly,  "Consumer Sales", descs, m)
            subs    = get_subs(CUR_FY, m, seg)
            arpu    = act_rev / subs if subs > 0 and pd.notna(act_rev) else 0
            yoy     = ((act_rev - ly_rev) / abs(ly_rev)
                       if pd.notna(ly_rev) and ly_rev != 0 and pd.notna(act_rev) else 0)
            rows.append({
                "Month":          fmt_month(m, CUR_FY),
                "Segment":        seg,
                "Revenue":        act_rev,
                "Revenue_AOP":    _get_sum(aop, "Consumer Sales", descs, m),
                "Subscribers":    subs,
                "Churn_Pct":      0,
                "ARPU":           arpu,
                "YoY_Change_Pct": yoy,
            })
    return pd.DataFrame(rows)


def build_business_sales(act, aop, ly, ly_aop, act_months):
    # Segment revenue sourced from financial_data; margin/contribution/MRR zeroed
    # Note: "Total Carrier Revenue." is wholesale telecom; separate from enterprise circuits.
    segment_map = {
        "Circuit/Data": ["Domestic Circuit Revenues.", "International Circuit Revenues.", "Metro E"],
        "Cloud":        ["Cloud Application Revenues."],
        "Carrier":      ["Total Carrier Revenue."],
        "Enterprise":   ["Enterprise Fixed", "Enterprise Mobile", "Enterprise Wireless Broadband"],
        "Security":     [],
        "Managed":      [],
        "IoT":          [],
    }
    rows = []
    # Pass 1: FY 2025-26 full year
    for m in MONTH_ORDER:
        for seg, descs in segment_map.items():
            rows.append({
                "Month":         fmt_month(m, LY_FY),
                "Segment":       seg,
                "Revenue":       _get_sum(ly,     "Business Sales", descs, m) if descs else np.nan,
                "Revenue_AOP":   _get_sum(ly_aop, "Business Sales", descs, m) if descs else 0,
                "Gross_Profit":  0,
                "GP_Margin_Pct": 0,
                "Contribution":  0,
                "MRR":           0,
                "Direct_Costs":  0,
            })
    # Pass 2: FY 2026-27 ACT months
    for m in act_months:
        for seg, descs in segment_map.items():
            rows.append({
                "Month":         fmt_month(m, CUR_FY),
                "Segment":       seg,
                "Revenue":       _get_sum(act, "Business Sales", descs, m) if descs else np.nan,
                "Revenue_AOP":   _get_sum(aop, "Business Sales", descs, m) if descs else 0,
                "Gross_Profit":  0,
                "GP_Margin_Pct": 0,
                "Contribution":  0,
                "MRR":           0,
                "Direct_Costs":  0,
            })
    return pd.DataFrame(rows)


def build_dpdi(raw_df, act_months):
    # DPDI appears under two BU name variants in the source data
    dpdi_bus = [
        "Data, Product Development & Innovation",
        "Dig, Product Development & Innovation",
    ]
    dpdi_data   = raw_df[raw_df["BU"].isin(dpdi_bus)]
    dpdi_act    = dpdi_data[(dpdi_data["FY"] == CUR_FY) & (dpdi_data["DataType"] == "ACT")]
    dpdi_aop    = dpdi_data[(dpdi_data["FY"] == CUR_FY) & (dpdi_data["DataType"] == "AOP")]
    dpdi_ly     = dpdi_data[(dpdi_data["FY"] == LY_FY)  & (dpdi_data["DataType"] == "ACT")]
    dpdi_ly_aop = dpdi_data[(dpdi_data["FY"] == LY_FY)  & (dpdi_data["DataType"] == "AOP")]
    products    = sorted(dpdi_data["Description"].unique())  # union across both FYs

    def _dpdi_row(src_act, src_aop, prod, month, fy):
        rev_s = src_act.loc[(src_act["Description"] == prod) & (src_act["Month"] == month), "Value"]
        aop_s = src_aop.loc[(src_aop["Description"] == prod) & (src_aop["Month"] == month), "Value"]
        return {
            "Month":         fmt_month(month, fy),
            "Product":       prod,
            "Revenue":       float(rev_s.iloc[0]) if len(rev_s) else np.nan,
            "Revenue_AOP":   float(aop_s.iloc[0]) if len(aop_s) else np.nan,
            "Gross_Profit":  0,
            "GP_Margin_Pct": 0,
            "EBITDA":        0,
            "Direct_Costs":  0,
        }

    rows = []
    # Pass 1: FY 2025-26 full year
    for m in MONTH_ORDER:
        for prod in products:
            rows.append(_dpdi_row(dpdi_ly, dpdi_ly_aop, prod, m, LY_FY))
    # Pass 2: FY 2026-27 ACT months
    for m in act_months:
        for prod in products:
            rows.append(_dpdi_row(dpdi_act, dpdi_aop, prod, m, CUR_FY))
    return pd.DataFrame(rows)


def build_amplia_financial(act, aop, ly, ly_aop, act_months):
    # Divisional EBITDA/PAT/OPEX not broken out in financial_data; revenue & COS available via Consolidated
    def _amplia_row(src_act, src_aop, month, fy):
        rev = _get(src_act, "Consolidated", "AMPLIA REVENUE", month)
        dc  = abs(_get(src_act, "Consolidated", "AMPLIA COS", month, 0))
        gp  = (rev - dc) if (not np.isnan(rev) and not np.isnan(dc)) else np.nan
        return {
            "Month":        fmt_month(month, fy),
            "Revenue":      rev,
            "Revenue_AOP":  _get(src_aop, "Consolidated", "AMPLIA REVENUE", month),
            "Gross_Profit": gp,
            "EBITDA":       0,
            "EBITDA_AOP":   0,
            "PAT":          0,
            "OPEX":         0,
            "Direct_Costs": dc,
        }

    rows = []
    # Pass 1: FY 2025-26 full year
    for m in MONTH_ORDER:
        rows.append(_amplia_row(ly, ly_aop, m, LY_FY))
    # Pass 2: FY 2026-27 ACT months
    for m in act_months:
        rows.append(_amplia_row(act, aop, m, CUR_FY))
    return pd.DataFrame(rows)


def build_ebitda_bridge(act, aop, latest_month):
    """Single-month waterfall: AOP EBITDA → actual EBITDA for latest_month."""
    def g(src, desc, default=0):
        return _get(src, "Consolidated", desc, latest_month, default)

    ebitda_aop = g(aop, "EBITDA")
    rev_act    = g(act, "TOTAL REVENUE")
    rev_aop    = g(aop, "TOTAL REVENUE")
    dc_act     = g(act, "DIRECT COSTS")   # negative in source; ACT - AOP gives EBITDA impact
    dc_aop     = g(aop, "DIRECT COSTS")
    opex_act   = g(act, "Total OPEX")     # negative in source (Category='EBITDA')
    opex_aop   = g(aop, "Total OPEX")

    rev_var  = rev_act  - rev_aop
    dc_var   = dc_act   - dc_aop    # less-negative ACT → positive (costs below plan → EBITDA up)
    opex_var = opex_act - opex_aop  # same convention

    def btype(v):
        return "Positive" if v >= 0 else "Negative"

    # Last row (Sort_Order=5) is overwritten by data_loader with sum of rows 1-4 = ACT EBITDA
    return pd.DataFrame([
        {"Category": "AOP EBITDA",            "Value": ebitda_aop, "Type": "Absolute",      "Sort_Order": 1},
        {"Category": "Revenue Variance",       "Value": rev_var,    "Type": btype(rev_var),  "Sort_Order": 2},
        {"Category": "Direct Costs Variance",  "Value": dc_var,     "Type": btype(dc_var),   "Sort_Order": 3},
        {"Category": "OPEX Variance",          "Value": opex_var,   "Type": btype(opex_var), "Sort_Order": 4},
        {"Category": "Actual EBITDA",          "Value": 0,          "Type": "Total",         "Sort_Order": 5},
    ])


def build_kpi_summary(act, aop, ly, latest_month):
    def g(src, desc):
        return _get(src, "Consolidated", desc, latest_month, 0)

    label = fmt_month(latest_month, CUR_FY)
    status = lambda a, p: "🟢" if a >= p else "🔴"

    rev_a, rev_p, rev_l   = g(act,"TOTAL REVENUE"), g(aop,"TOTAL REVENUE"), g(ly,"TOTAL REVENUE")
    ebi_a, ebi_p, ebi_l   = g(act,"EBITDA"),        g(aop,"EBITDA"),        g(ly,"EBITDA")
    pat_a, pat_p, pat_l   = g(act,"Profit After Taxation"), g(aop,"Profit After Taxation"), g(ly,"Profit After Taxation")
    mgn_a, mgn_p, mgn_l   = g(act,"EBITDA %"),      g(aop,"EBITDA %"),      g(ly,"EBITDA %")

    # TT$M rows: raw TTD$ values (data_loader divides by 1,000,000)
    # % rows:    decimal values (data_loader multiplies by 100)
    return pd.DataFrame([
        {"Month": label, "Section": "Financial", "KPI_Name": "Revenue",       "Actual": rev_a, "AOP": rev_p, "LY": rev_l, "Status": status(rev_a, rev_p), "Unit": "TT$M"},
        {"Month": label, "Section": "Financial", "KPI_Name": "EBITDA",        "Actual": ebi_a, "AOP": ebi_p, "LY": ebi_l, "Status": status(ebi_a, ebi_p), "Unit": "TT$M"},
        {"Month": label, "Section": "Financial", "KPI_Name": "PAT",           "Actual": pat_a, "AOP": pat_p, "LY": pat_l, "Status": status(pat_a, pat_p), "Unit": "TT$M"},
        {"Month": label, "Section": "Financial", "KPI_Name": "EBITDA Margin", "Actual": mgn_a, "AOP": mgn_p, "LY": mgn_l, "Status": status(mgn_a, mgn_p), "Unit": "%"},
    ])


SUBS_SRC = "subscriber_base_apw.xlsx"


def main():
    print(f"Reading {SRC} ...")
    raw = pd.read_excel(SRC, sheet_name="financial_data", header=1)
    raw.columns = ["FY", "Period", "Month", "DataType", "BU", "Description", "Category", "Value"]

    act    = raw[(raw["FY"] == CUR_FY) & (raw["DataType"] == "ACT")].copy()
    aop    = raw[(raw["FY"] == CUR_FY) & (raw["DataType"] == "AOP")].copy()
    ly     = raw[(raw["FY"] == LY_FY)  & (raw["DataType"] == "ACT")].copy()
    ly_aop = raw[(raw["FY"] == LY_FY)  & (raw["DataType"] == "AOP")].copy()

    act_months = [m for m in MONTH_ORDER if m in act["Month"].values]
    latest_month = act_months[-1] if act_months else MONTH_ORDER[0]
    ly_months = [m for m in MONTH_ORDER if m in ly["Month"].values]
    print(f"  Current FY ({CUR_FY}) ACT months: {act_months or ['(none)']}")
    print(f"  Last Year  ({LY_FY}) ACT months:  {ly_months}")

    print(f"Reading {SUBS_SRC} ...")
    subs_df = pd.read_excel(SUBS_SRC, sheet_name="monthly_pivot", header=1)

    sheets = {
        "KPI_Summary":       build_kpi_summary(act, aop, ly, latest_month) if act_months
                             else pd.DataFrame(columns=["Month","Section","KPI_Name","Actual","AOP","LY","Status","Unit"]),
        "Financial_Monthly": build_financial_monthly(act, aop, ly, ly_aop, act_months),
        "EBITDA_Bridge":     build_ebitda_bridge(act, aop, latest_month) if act_months
                             else pd.DataFrame(columns=["Category","Value","Type","Sort_Order"]),
        "OPEX":              build_opex(act, aop, ly, ly_aop, act_months),
        "Cash_CAPEX":        build_cash_capex(act, aop, ly, act_months),
        "Consumer_Sales":    build_consumer_sales(act, aop, ly, ly_aop, act_months, subs_df),
        "Business_Sales":    build_business_sales(act, aop, ly, ly_aop, act_months),
        "Pipeline":          pd.DataFrame(columns=["Month","Stage","Deal_Count","Value_TTD_M","Avg_Deal_Size","Win_Rate_Pct"]),
        "Renewals":          pd.DataFrame(columns=["Customer","Product_Service","ACV_TTD_M","Expiry_Date","Risk_Level","Status","Action_Plan"]),
        "DPDI":              build_dpdi(raw, act_months),
        "AMPLIA_Financial":  build_amplia_financial(act, aop, ly, ly_aop, act_months),
        "AMPLIA_Commercial": pd.DataFrame(columns=["Month","ARPU","Gross_Additions","Gross_Additions_AOP","Monthly_Churn","Churn_AOP","Net_Port","Channel","Sales_Count","Sales_Target"]),
    }

    print(f"\nWriting {DST} ...")
    with pd.ExcelWriter(DST, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            print(f"  {name:<22} {len(df):>4} rows")

    print("\nDone. Run:  streamlit run app.py")


if __name__ == "__main__":
    main()
