import pandas as pd
import streamlit as st

MASTER_PATH = "TSTT_Master_Data_Template.xlsx"
M = 1_000_000  # raw TTD → millions


# ── Sheet reader ───────────────────────────────────────────────────────────────
def _read_sheet(xls, sheet_name):
    """4-row header structure: title / subtitle / column headers / descriptions / data.
    header=2 uses row 3 as column names; skiprows=[3] drops the description row (row 4)."""
    df = pd.read_excel(xls, sheet_name=sheet_name, header=2, skiprows=[3])
    return df.reset_index(drop=True).dropna(how="all")


def _norm_month(series):
    """Normalise a Month column to 'Mon-YY' string.

    Tries strict '%b-%y' format first so 'Jan-25' → Jan 2025 (not Jan 25, 1900).
    Falls back to generic parsing for actual datetime/Timestamp objects.
    Rejects implausible years (< 2000 or > 2099) to eliminate Excel serial-0 artefacts.
    """
    strict = pd.to_datetime(series, format="%b-%y", errors="coerce")
    loose  = pd.to_datetime(series, errors="coerce")
    # Prefer the strict parse; use generic only where strict produced NaT
    as_dt  = strict.where(strict.notna(), loose)
    valid  = as_dt.notna() & (as_dt.dt.year >= 2000) & (as_dt.dt.year <= 2099)
    result = series.astype(str).str.strip().copy()
    result[valid]  = as_dt[valid].dt.strftime("%b-%y")
    result[~valid] = pd.NA
    return result


def _scale(df, cols):
    """Divide listed columns by 1 000 000 (raw TTD → millions)."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce") / M
    return df


def _pct_col(df, cols):
    """Multiply listed columns by 100 (decimal 0.025 → display 2.5)."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce") * 100
    return df


# ── Main data loader ───────────────────────────────────────────────────────────
@st.cache_data
def load_all_data():
    xls  = pd.ExcelFile(MASTER_PATH)
    data = {}

    # ── P&L_Segments ─────────────────────────────────────────────────────────
    pnl_seg = _read_sheet(xls, "P&L_Segments")
    pnl_seg["Month"]   = _norm_month(pnl_seg["Month"])
    pnl_seg["Segment"] = pnl_seg["Segment"].astype(str).str.strip().str.upper()
    _money_cols = ["Revenue", "Revenue_AOP", "Revenue_PY",
                   "COS", "COS_AOP", "Gross_Profit", "GP_AOP",
                   "OPEX", "OPEX_AOP", "EBITDA", "EBITDA_AOP",
                   "PAT", "PAT_AOP", "Bad_Debt"]
    for c in _money_cols:
        if c in pnl_seg.columns:
            pnl_seg[c] = pd.to_numeric(pnl_seg[c], errors="coerce")

    # ── Financial_Monthly ────────────────────────────────────────────────────
    _agg = ["Revenue", "Revenue_AOP", "Revenue_PY",
            "EBITDA", "EBITDA_AOP", "PAT", "PAT_AOP"]
    fin = pnl_seg.groupby("Month")[_agg].sum().reset_index()
    # EBITDA_Margin computed before scaling (ratio unchanged by scaling)
    fin["EBITDA_Margin"] = (fin["EBITDA"] / fin["Revenue"].replace(0, pd.NA)).fillna(0)
    fin = _scale(fin, ["Revenue", "Revenue_AOP", "Revenue_PY",
                        "EBITDA", "EBITDA_AOP", "PAT", "PAT_AOP"])
    fin["EBITDA_Margin"] = fin["EBITDA_Margin"] * 100  # decimal → %
    fin["_dt"] = pd.to_datetime(fin["Month"], format="%b-%y", errors="coerce")
    fin = fin.sort_values("_dt", na_position="last").reset_index(drop=True)
    for col in ["Revenue", "EBITDA", "PAT"]:
        lk = fin.dropna(subset=["_dt"]).set_index("_dt")[col]
        fin[f"{col}_PY"] = fin["_dt"].apply(
            lambda dt, lk=lk: lk.get(dt - pd.DateOffset(months=12))
        )
    fin.drop(columns=["_dt"], inplace=True)
    data["Financial_Monthly"] = fin

    # ── PnL_Breakdown ────────────────────────────────────────────────────────
    # Wide format: one row per Month; per-segment and aggregate columns
    METRIC_MAP = {
        "Revenue": "Rev", "Revenue_AOP": "Rev_AOP", "Revenue_PY": "Rev_PY",
        "COS": "COS",     "COS_AOP": "COS_AOP",
        "Gross_Profit": "GP", "GP_AOP": "GP_AOP",
        "OPEX": "OPEX",   "OPEX_AOP": "OPEX_AOP",
        "EBITDA": "EBITDA", "EBITDA_AOP": "EBITDA_AOP",
    }
    months_order = list(dict.fromkeys(pnl_seg["Month"].dropna().tolist()))
    bd_rows = []
    for month in months_order:
        m_data = pnl_seg[pnl_seg["Month"] == month]
        row = {"Month": month}
        for _, sr in m_data.iterrows():
            seg = sr["Segment"]
            for src, short in METRIC_MAP.items():
                if src in pnl_seg.columns:
                    row[f"{seg}_{short}"] = sr[src]
        row["Total_Rev"]     = m_data["Revenue"].sum()
        row["Total_Rev_AOP"] = m_data["Revenue_AOP"].sum()
        row["Total_Rev_PY"]  = m_data["Revenue_PY"].sum()
        row["Total_COS"]     = m_data["COS"].sum()
        row["Total_COS_AOP"] = m_data["COS_AOP"].sum()
        row["Total_GP"]      = m_data["Gross_Profit"].sum()
        row["Total_OPEX"]    = m_data["OPEX"].sum()
        row["EBITDA"]        = m_data["EBITDA"].sum()
        bd_rows.append(row)

    breakdown = pd.DataFrame(bd_rows) if bd_rows else pd.DataFrame(columns=["Month"])
    # Scale all non-Month columns (raw TTD → millions)
    breakdown = _scale(breakdown, [c for c in breakdown.columns if c != "Month"])
    # Ensure all columns expected by dashboard pages always exist (default 0)
    _required_cols = [
        "Total_Rev", "Total_Rev_AOP", "Total_Rev_PY",
        "Total_COS", "Total_COS_AOP", "Total_GP", "Total_OPEX", "EBITDA",
    ]
    for seg in ["CONSUMER SALES", "BUSINESS SALES", "AMPLIA", "DPDI", "OTHER"]:
        for sfx in ["Rev", "COS", "GP", "Rev_AOP", "COS_AOP", "GP_AOP", "OPEX", "EBITDA"]:
            _required_cols.append(f"{seg}_{sfx}")
    for col in _required_cols:
        if col not in breakdown.columns:
            breakdown[col] = 0.0
    data["PnL_Breakdown"] = breakdown

    # ── KPI_Summary ─────────────────────────────────────────────────────────
    # Derived from the latest month of Financial_Monthly
    if not fin.empty:
        fl   = fin.iloc[-1]
        _mon = fl["Month"]

        def _kpi(section, name, actual, aop, py, unit):
            try:
                if pd.notna(actual) and pd.notna(aop) and aop != 0:
                    diff_pct = (float(actual) - float(aop)) / abs(float(aop))
                    status = "A" if abs(diff_pct) < 0.02 else ("G" if float(actual) >= float(aop) else "R")
                else:
                    status = "A"
            except Exception:
                status = "A"
            return {"Month": _mon, "Section": section, "KPI_Name": name,
                    "Actual": actual, "AOP": aop, "PY": py, "Status": status, "Unit": unit}

        _ebitda_m_aop = (
            float(fl.get("EBITDA_AOP", 0)) / float(fl.get("Revenue_AOP", 1)) * 100
            if fl.get("Revenue_AOP") else pd.NA
        )
        data["KPI_Summary"] = pd.DataFrame([
            _kpi("Financial", "Revenue",      fl["Revenue"],        fl.get("Revenue_AOP"),  fl.get("Revenue_PY"), ""),
            _kpi("Financial", "EBITDA",        fl["EBITDA"],          fl.get("EBITDA_AOP"),   fl.get("EBITDA_PY"),  ""),
            _kpi("Financial", "PAT",           fl["PAT"],             fl.get("PAT_AOP"),      fl.get("PAT_PY"),     ""),
            _kpi("Financial", "EBITDA Margin", fl.get("EBITDA_Margin"), _ebitda_m_aop,       pd.NA,                "%"),
        ])
    else:
        data["KPI_Summary"] = pd.DataFrame(
            columns=["Month", "Section", "KPI_Name", "Actual", "AOP", "PY", "Status", "Unit"]
        )

    # ── EBITDA_Bridge ────────────────────────────────────────────────────────
    # Derived from P&L_Segments latest month
    if not fin.empty:
        fl     = fin.iloc[-1]
        latest_m = fl["Month"]
        pm      = pnl_seg[pnl_seg["Month"] == latest_m]
        rev_a  = fl["Revenue"]
        rev_aop = fl.get("Revenue_AOP", rev_a) or rev_a
        ebi_a   = fl["EBITDA"]
        ebi_aop = fl.get("EBITDA_AOP", ebi_a) or ebi_a
        cos_a   = pm["COS"].sum() / M if "COS" in pm.columns else 0.0
        cos_aop = pm["COS_AOP"].sum() / M if "COS_AOP" in pm.columns else cos_a
        opex_a  = pm["OPEX"].sum() / M if "OPEX" in pm.columns else 0.0
        opex_aop = pm["OPEX_AOP"].sum() / M if "OPEX_AOP" in pm.columns else opex_a
        data["EBITDA_Bridge"] = pd.DataFrame([
            {"Category": "AOP EBITDA",       "Value": ebi_aop,                 "Type": "Absolute", "Sort_Order": 1},
            {"Category": "Revenue Variance", "Value": rev_a - rev_aop,          "Type": "Positive" if rev_a >= rev_aop else "Negative", "Sort_Order": 2},
            {"Category": "COS Variance",     "Value": cos_aop - cos_a,          "Type": "Positive" if cos_a <= cos_aop else "Negative", "Sort_Order": 3},
            {"Category": "OPEX Variance",    "Value": opex_aop - opex_a,        "Type": "Positive" if opex_a <= opex_aop else "Negative", "Sort_Order": 4},
            {"Category": "Actual EBITDA",    "Value": ebi_a,                   "Type": "Total",    "Sort_Order": 5},
        ])
    else:
        data["EBITDA_Bridge"] = pd.DataFrame(
            columns=["Category", "Value", "Type", "Sort_Order"]
        )

    # ── Consumer_Products → Consumer_Sales ───────────────────────────────────
    cs = _read_sheet(xls, "Consumer_Products")
    cs["Month"] = _norm_month(cs["Month"])
    cs = cs.dropna(subset=["Month"])
    cs = cs.rename(columns={"Product": "Segment"})
    cs = _scale(cs, ["Revenue", "Revenue_AOP", "Revenue_PY"])
    for c in ["Subscribers", "Subscribers_AOP", "Gross_Adds", "Gross_Adds_AOP"]:
        if c in cs.columns:
            cs[c] = pd.to_numeric(cs[c], errors="coerce").fillna(0)
    for c in ["ARPU", "ARPU_AOP"]:
        if c in cs.columns:
            cs[c] = pd.to_numeric(cs[c], errors="coerce")
    if "ARPU" not in cs.columns or cs["ARPU"].isna().all():
        cs["ARPU"] = (cs["Revenue"] * M / cs["Subscribers"].replace(0, pd.NA)).fillna(0)
    if "ARPU_AOP" not in cs.columns or cs["ARPU_AOP"].isna().all():
        cs["ARPU_AOP"] = 0.0
    cs["_dt"] = pd.to_datetime(cs["Month"], format="%b-%y", errors="coerce")
    cs = cs.sort_values(["Segment", "_dt"]).reset_index(drop=True)
    cs["_prev_subs"] = cs.groupby("Segment")["Subscribers"].shift(1)
    cs["_derived_churn"] = (
        (cs["_prev_subs"] - cs["Subscribers"]) / cs["_prev_subs"] * 100
    ).where(cs["_prev_subs"] > 0)
    if "Churn_Pct" in cs.columns:
        _user = pd.to_numeric(cs["Churn_Pct"], errors="coerce")
        cs["Churn_Pct"] = _user.where(_user.notna() & (_user != 0), cs["_derived_churn"])
    else:
        cs["Churn_Pct"] = cs["_derived_churn"]
    cs.drop(columns=["_dt", "_prev_subs", "_derived_churn"], inplace=True)
    if "YoY_Change_Pct" in cs.columns:
        cs = _pct_col(cs, ["YoY_Change_Pct"])
    data["Consumer_Sales"] = cs

    # ── Business_Products → Business_Sales ───────────────────────────────────
    bs = _read_sheet(xls, "Business_Products")
    bs["Month"] = _norm_month(bs["Month"])
    bs = bs.rename(columns={"Product": "Segment"})
    bs = _scale(bs, ["Revenue", "Revenue_AOP", "Revenue_PY",
                      "Direct_Costs", "Direct_Costs_AOP", "Gross_Profit",
                      "MRR", "MRR_AOP", "Contribution"])
    for c in ["GP_AOP", "Mobile", "Mobile_AOP", "USAGE", "USAGE_AOP", "OCC", "OCC_AOP"]:
        if c not in bs.columns:
            bs[c] = 0.0
    # Fill missing Direct_Costs from P&L_Segments BUSINESS SALES COS
    bs_pnl = (
        pnl_seg[pnl_seg["Segment"].str.contains("BUSINESS", na=False)]
        .groupby("Month")[["COS", "COS_AOP"]].sum().reset_index()
    )
    bs_pnl.columns = ["Month", "_pnl_dc_raw", "_pnl_dc_aop_raw"]
    bs = bs.merge(bs_pnl, on="Month", how="left")
    segs_per_month = bs.groupby("Month")["Segment"].transform("count")
    for col, src in [("Direct_Costs", "_pnl_dc_raw"), ("Direct_Costs_AOP", "_pnl_dc_aop_raw")]:
        if col not in bs.columns:
            bs[col] = 0.0
        if src in bs.columns:
            blank = bs[col].isna() | (bs[col] == 0)
            bs.loc[blank, col] = bs.loc[blank, src] / M / segs_per_month[blank]
    bs.drop(columns=["_pnl_dc_raw", "_pnl_dc_aop_raw"], inplace=True, errors="ignore")
    bs["Gross_Profit"] = bs["Revenue"] - bs["Direct_Costs"]
    aop_ok = (bs["Revenue_AOP"].notna() & (bs["Revenue_AOP"] != 0) &
              bs["Direct_Costs_AOP"].notna() & (bs["Direct_Costs_AOP"] != 0))
    bs.loc[aop_ok, "GP_AOP"] = bs.loc[aop_ok, "Revenue_AOP"] - bs.loc[aop_ok, "Direct_Costs_AOP"]
    if "GP_Margin_Pct" in bs.columns:
        bs = _pct_col(bs, ["GP_Margin_Pct"])
    data["Business_Sales"]     = bs
    data["Business_Sales_MRR"] = pd.DataFrame()  # not in master template
    data["PP_Plans"]           = pd.DataFrame()  # not in master template
    data["WTTx_Plans"]         = pd.DataFrame()  # not in master template

    # ── DPDI_Products → DPDI ─────────────────────────────────────────────────
    dp = _read_sheet(xls, "DPDI_Products")
    dp["Month"] = _norm_month(dp["Month"])
    dp = _scale(dp, ["Revenue", "Revenue_AOP", "Revenue_PY", "Direct_Costs", "Gross_Profit"])
    if "EBITDA" not in dp.columns:
        dp["EBITDA"] = dp.get("Gross_Profit", pd.Series(0, index=dp.index))
    if "Direct_Costs_AOP" not in dp.columns:
        dp["Direct_Costs_AOP"] = 0.0
    if "GP_Margin_Pct" not in dp.columns:
        dp["GP_Margin_Pct"] = (
            dp["Gross_Profit"] / dp["Revenue"].replace(0, pd.NA) * 100
        ).fillna(0)
    # Fill Direct_Costs from P&L_Segments DPDI COS
    dp_pnl = (
        pnl_seg[pnl_seg["Segment"].str.contains("DPDI", na=False)]
        .groupby("Month")[["COS", "COS_AOP"]].sum().reset_index()
    )
    dp_pnl.columns = ["Month", "_pnl_dc_raw", "_pnl_dc_aop_raw"]
    dp = dp.merge(dp_pnl, on="Month", how="left")
    prods_per_month = dp.groupby("Month")["Product"].transform("count")
    blank = dp["Direct_Costs"].isna() | (dp["Direct_Costs"] == 0)
    if "_pnl_dc_raw" in dp.columns:
        dp.loc[blank, "Direct_Costs"] = dp.loc[blank, "_pnl_dc_raw"] / M / prods_per_month[blank]
    blank_aop = dp["Direct_Costs_AOP"].isna() | (dp["Direct_Costs_AOP"] == 0)
    if "_pnl_dc_aop_raw" in dp.columns:
        dp.loc[blank_aop, "Direct_Costs_AOP"] = dp.loc[blank_aop, "_pnl_dc_aop_raw"] / M / prods_per_month[blank_aop]
    dp["Gross_Profit"] = dp["Revenue"] - dp["Direct_Costs"]
    dp.drop(columns=["_pnl_dc_raw", "_pnl_dc_aop_raw"], inplace=True, errors="ignore")
    data["DPDI"] = dp

    # ── P&L_Segments AMPLIA row → AMPLIA_Financial ───────────────────────────
    amplia_seg = pnl_seg[pnl_seg["Segment"].str.contains("AMPLIA", na=False)].copy()
    amplia_fin = amplia_seg.rename(
        columns={"COS": "Direct_Costs", "COS_AOP": "Direct_Costs_AOP"}
    ).reset_index(drop=True)
    amplia_fin = _scale(amplia_fin, [
        "Revenue", "Revenue_AOP", "Gross_Profit",
        "EBITDA", "EBITDA_AOP", "PAT", "OPEX", "Direct_Costs",
    ])
    data["AMPLIA_Financial"] = amplia_fin

    # ── Amplia_Commercial ─────────────────────────────────────────────────────
    amp_comm = _read_sheet(xls, "Amplia_Commercial")
    amp_comm["Month"] = _norm_month(amp_comm["Month"])
    amp_comm = amp_comm.rename(columns={
        "Gross_Adds":        "Gross_Additions",
        "Monthly_Churn_AOP": "Churn_AOP",
    })
    data["AMPLIA_Commercial"] = amp_comm

    # ── Cash_CAPEX ────────────────────────────────────────────────────────────
    cc = _read_sheet(xls, "Cash_CAPEX")
    cc["Month"] = _norm_month(cc["Month"])
    cc = _scale(cc, ["Cash_Balance", "Net_Debt", "FCF",
                      "CAPEX_Actual", "CAPEX_Plan",
                      "CAPEX_Monthly_Actual", "CAPEX_Monthly_Plan"])
    # Merge Collections_Pct per group from Collections_Billing
    try:
        cb = _read_sheet(xls, "Collections_Billing")
        cb["Month"] = _norm_month(cb["Month"])
        cb["Group"] = cb["Group"].astype(str).str.strip()
        cb["Collections_Pct"] = pd.to_numeric(cb["Collections_Pct"], errors="coerce")
        cb_piv = cb.pivot_table(
            index="Month", columns="Group", values="Collections_Pct", aggfunc="first"
        ).reset_index()
        ren = {}
        for col in cb_piv.columns:
            if col == "Month":
                continue
            cu = col.upper()
            if "NON" in cu:
                ren[col] = "Collections_Pct_NonGov"
            elif "GOV" in cu:
                ren[col] = "Collections_Pct_Gov"
            elif "CONSUMER" in cu:
                ren[col] = "Collections_Pct_Consumer"
        cc = cc.merge(cb_piv.rename(columns=ren), on="Month", how="left")
    except Exception:
        pass
    data["Cash_CAPEX"] = cc

    # ── Pipeline ─────────────────────────────────────────────────────────────
    pip = _read_sheet(xls, "Pipeline")
    pip["Month"] = _norm_month(pip["Month"])
    pip = _scale(pip, ["Value_TTD", "Avg_Deal_Size", "Weighted_Value"])
    pip = pip.rename(columns={"Value_TTD": "Value_TTD_M"})
    for c in ["Deal_Count", "Win_Rate_Pct"]:
        if c in pip.columns:
            pip[c] = pd.to_numeric(pip[c], errors="coerce").fillna(0)
    data["Pipeline"] = pip

    # ── Renewals ─────────────────────────────────────────────────────────────
    ren = _read_sheet(xls, "Renewals")
    ren = _scale(ren, ["ACV_TTD"])
    ren = ren.rename(columns={"ACV_TTD": "ACV_TTD_M"})
    data["Renewals"] = ren

    # ── OPEX_Detail → OPEX ───────────────────────────────────────────────────
    opex = _read_sheet(xls, "OPEX_Detail")
    opex["Month"] = _norm_month(opex["Month"])
    opex = opex.rename(columns={"AOP": "Plan"})
    opex_grp = opex.groupby(["Month", "Category"])[["Actual", "Plan", "PY"]].sum().reset_index()
    opex_grp = _scale(opex_grp, ["Actual", "Plan", "PY"])
    opex_grp["Variance"] = opex_grp["Actual"] - opex_grp["Plan"]
    opex_grp["Variance_Pct"] = pd.to_numeric(
        (opex_grp["Actual"] - opex_grp["Plan"]) / opex_grp["Plan"].replace(0, float("nan")) * 100,
        errors="coerce",
    ).round(1)
    data["OPEX"] = opex_grp

    return data


# ── AR Aging loader ────────────────────────────────────────────────────────────
@st.cache_data
def load_ar():
    """Load AR aging data from AR_Aging sheet.
    Returns {"gov": {...}, "non_gov": {...}, "total": {...}} with values in millions.
    """
    try:
        xls    = pd.ExcelFile(MASTER_PATH)
        ar_raw = _read_sheet(xls, "AR_Aging")
        ar_raw["Group"]  = ar_raw["Group"].astype(str).str.strip()
        ar_raw["Bucket"] = ar_raw["Bucket"].astype(str).str.strip()
        ar_raw["Amount"] = pd.to_numeric(ar_raw["Amount"], errors="coerce").fillna(0) / M
        ar_raw["Month"]  = _norm_month(ar_raw["Month"])

        BUCKET_MAP = {
            "0-30d": "0_30",   "0-30": "0_30",   "0_30": "0_30",   "0–30": "0_30",
            "31-60d": "31_60", "31-60": "31_60", "31_60": "31_60", "31–60": "31_60",
            "61-90d": "61_90", "61-90": "61_90", "61_90": "61_90", "61–90": "61_90",
            "90-360d": "90_360", "90-360": "90_360", "90_360": "90_360", "90–360": "90_360",
            "360+d": "360p",  "360+": "360p",  "360p": "360p",  ">360": "360p",  "360 +": "360p",
        }
        ar_raw["Bucket_key"] = ar_raw["Bucket"].map(BUCKET_MAP).fillna(ar_raw["Bucket"])

        months_avail = ar_raw["Month"].dropna().unique().tolist()
        if not months_avail:
            return None
        latest_m = months_avail[-1]
        ar_m     = ar_raw[ar_raw["Month"] == latest_m]

        BUCKETS = ["0_30", "31_60", "61_90", "90_360", "360p"]

        def _grp(pattern, exclude=None):
            mask = ar_m["Group"].str.upper().str.contains(pattern, na=False)
            if exclude:
                mask &= ~ar_m["Group"].str.upper().str.contains(exclude, na=False)
            rows = ar_m[mask]
            d = {b: float(rows[rows["Bucket_key"] == b]["Amount"].sum()) for b in BUCKETS}
            d["total"] = sum(d.values())
            return d

        gov     = _grp("GOV", exclude="NON")
        non_gov = _grp("NON")
        total   = {k: gov[k] + non_gov[k] for k in BUCKETS + ["total"]}
        return {"gov": gov, "non_gov": non_gov, "total": total}
    except Exception:
        return None


# ── Collections & Billing loader ──────────────────────────────────────────────
@st.cache_data
def load_collections_billing():
    """Load Collections_Billing sheet.
    Returns long-format DataFrame: Month, Group, Billings, Collections, Collections_Pct.
    """
    try:
        xls = pd.ExcelFile(MASTER_PATH)
        cb  = _read_sheet(xls, "Collections_Billing")
        cb["Month"] = _norm_month(cb["Month"])
        cb["Group"] = cb["Group"].astype(str).str.strip()
        for c in ["Billings", "Collections", "Collections_Pct"]:
            if c in cb.columns:
                cb[c] = pd.to_numeric(cb[c], errors="coerce")
        return cb
    except Exception:
        return pd.DataFrame()


# ── Prepaid ARPU Buckets ───────────────────────────────────────────────────────
@st.cache_data
def load_prepaid_arpu():
    """Load Prepaid_ARPU_Buckets sheet.
    Returns DataFrame: Month, Category, Subscribers, Revenue (millions).
    """
    try:
        xls = pd.ExcelFile(MASTER_PATH)
        df  = _read_sheet(xls, "Prepaid_ARPU_Buckets")
        df["Month"] = _norm_month(df["Month"])
        df = df.rename(columns={"ARPU_Bucket": "Category"})
        for c in ["Subscribers"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        if "Revenue" in df.columns:
            df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0) / M
        else:
            df["Revenue"] = 0.0
        return df[["Month", "Category", "Subscribers", "Revenue"]]
    except Exception:
        return pd.DataFrame()


# ── Prepaid Data Usage ─────────────────────────────────────────────────────────
@st.cache_data
def load_prepaid_data_usage():
    """Load Prepaid_Data_Usage sheet.
    Returns DataFrame with columns matching the old dd_prepaid_data_usage_mth.xlsx output.
    """
    try:
        xls = pd.ExcelFile(MASTER_PATH)
        df  = _read_sheet(xls, "Prepaid_Data_Usage")
        df["Month"] = _norm_month(df["Month"])
        df["_dt"]   = pd.to_datetime(df["Month"], format="%b-%y", errors="coerce")
        df = df.sort_values("_dt", na_position="last").reset_index(drop=True)
        df.drop(columns=["_dt"], inplace=True)

        # Map template column names → legacy names expected by the Consumer page
        RENAMES = {
            "Total_GB":           "total_data_usage",
            "Data_Users":         "unique_data_users",
            "MoU_Per_User":       "mou_per_user",
            "Bundle_Subscribers": "bundle_users",
            "Bundle_Revenue":     "data_bundle_rev",
            "GB_Per_User":        "gb_per_user",
            "Bundle_Pct":         "bundle_pct",
        }
        df = df.rename(columns={k: v for k, v in RENAMES.items() if k in df.columns})

        for c in ["unique_data_users", "bundle_users", "total_data_usage", "gb_per_user"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # Derive GB_Per_User from Total_GB / Data_Users when template cell is blank
        if ("total_data_usage" in df.columns and "unique_data_users" in df.columns):
            mask = df["unique_data_users"] > 0
            df["gb_per_user"] = 0.0
            df.loc[mask, "gb_per_user"] = (
                df.loc[mask, "total_data_usage"] / df.loc[mask, "unique_data_users"]
            )

        if "mou_per_user" in df.columns:
            df["mou_per_user"] = pd.to_numeric(df["mou_per_user"], errors="coerce").fillna(0)

        if "data_bundle_rev" in df.columns:
            df["data_bundle_rev"] = pd.to_numeric(df["data_bundle_rev"], errors="coerce").fillna(0) / M
        if "payg_data_charges" not in df.columns:
            df["payg_data_charges"] = 0.0
        df["total_data_rev"] = df.get("data_bundle_rev", 0) + df.get("payg_data_charges", 0)

        if "bundle_pct" in df.columns:
            df["bundle_pct"] = pd.to_numeric(df["bundle_pct"], errors="coerce").fillna(0)
            if df["bundle_pct"].max() <= 1.0:  # stored as decimal → convert
                df["bundle_pct"] = df["bundle_pct"] * 100

        return df
    except Exception:
        return pd.DataFrame()


# ── Postpaid by Active Plan ────────────────────────────────────────────────────
@st.cache_data
def load_postpaid_plans():
    """Load 'Postpaid by active Plan' sheet.
    Returns DataFrame with columns: Rank, Type, Plan, Sub_Count.
    """
    try:
        xls = pd.ExcelFile(MASTER_PATH)
        df  = pd.read_excel(xls, "Postpaid by active Plan", header=1)
        df.columns = ["Rank", "Type", "Plan", "Sub_Count", "Pct_Base"]
        df = df.dropna(subset=["Rank"])
        df["Sub_Count"] = pd.to_numeric(df["Sub_Count"], errors="coerce").fillna(0)
        df["Rank"]      = pd.to_numeric(df["Rank"],      errors="coerce")
        return df[df["Sub_Count"] > 0].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


# ── WTTx by Category ───────────────────────────────────────────────────────────
@st.cache_data
def load_wttx_categories():
    """Load 'WTTX by Category' sheet.
    Returns DataFrame with columns: Category, Subscribers (summed by category).
    """
    try:
        xls = pd.ExcelFile(MASTER_PATH)
        df  = pd.read_excel(xls, "WTTX by Category", header=0)
        df.columns = ["_skip", "Bill_System", "Category", "Package", "Subscribers"]
        df = df.dropna(subset=["Category"])
        df["Subscribers"] = pd.to_numeric(df["Subscribers"], errors="coerce").fillna(0)
        return df[df["Subscribers"] > 0].reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


# ── Utilities ──────────────────────────────────────────────────────────────────
def get_month_order(df, col="Month"):
    """Return unique months in their original DataFrame order."""
    return list(dict.fromkeys(df[col].dropna().tolist()))


def pivot_by_group(df, index_col, group_col, value_col):
    """Pivot df preserving original row order of index_col."""
    month_order = get_month_order(df, index_col)
    pivot = df.pivot_table(index=index_col, columns=group_col, values=value_col, aggfunc="sum")
    return pivot.reindex(month_order).reset_index()
