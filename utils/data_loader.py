import pandas as pd
import streamlit as st

EXCEL_PATH       = "TSTT_Board_Data.xlsx"
ARPU_BUCKET_PATH      = "Prepaid Subs and REV by ARPU buckets.xlsx"
PREPAID_USAGE_PATH    = "dd_prepaid_data_usage_mth.xlsx"
M = 1_000_000  # raw  →  conversion factor


def _scale(df, cols):
    """Divide named monetary columns by 1,000,000 (raw  → )."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce") / M
    return df


def _pct(df, cols):
    """Multiply percentage columns from decimal form (0.44) to display form (44)."""
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce") * 100
    return df


@st.cache_data
def load_all_data():
    xls = pd.ExcelFile(EXCEL_PATH)
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(xls, sheet_name=sheet)

    # ── Scale monetary columns from raw  to  ──────────────────────────
    if "Financial_Monthly" in data:
        data["Financial_Monthly"] = _scale(data["Financial_Monthly"], [
            "Revenue", "EBITDA", "PAT",
            "Revenue_AOP", "EBITDA_AOP", "PAT_AOP",
        ])
        data["Financial_Monthly"] = _pct(data["Financial_Monthly"], ["EBITDA_Margin"])
        # Derive PY columns from 12 months prior in the same series
        fin = data["Financial_Monthly"].copy()
        fin["_dt"] = pd.to_datetime(fin["Month"], format="%b-%y", errors="coerce")
        for col in ["Revenue", "EBITDA", "PAT"]:
            lk = fin.dropna(subset=["_dt"]).set_index("_dt")[col]
            fin[f"{col}_PY"] = fin["_dt"].apply(
                lambda dt, lk=lk: lk.get(dt - pd.DateOffset(months=12))
            )
        fin.drop(columns=["_dt"], inplace=True)
        data["Financial_Monthly"] = fin

    if "Cash_CAPEX" in data:
        data["Cash_CAPEX"] = _scale(data["Cash_CAPEX"], [
            "Cash_Balance", "Net_Debt", "FCF", "CAPEX_Actual", "CAPEX_Plan",
        ])
        data["Cash_CAPEX"] = _pct(data["Cash_CAPEX"], [
            "Collections_Pct", "Collections_Pct_Gov", "Collections_Pct_NonGov",
        ])

    if "Consumer_Sales" in data:
        cs = data["Consumer_Sales"]
        if "ARPU" not in cs.columns:
            cs["ARPU"] = (cs["Revenue"] / cs["Subscribers"].replace(0, pd.NA)).fillna(0)
        if "ARPU_AOP" not in cs.columns:
            cs["ARPU_AOP"] = 0.0
        data["Consumer_Sales"] = cs
        data["Consumer_Sales"] = _scale(data["Consumer_Sales"], [
            "Revenue", "Revenue_AOP",
        ])
        data["Consumer_Sales"] = _pct(data["Consumer_Sales"], ["YoY_Change_Pct"])
        cs = data["Consumer_Sales"].copy()
        cs["_dt"] = pd.to_datetime(cs["Month"], format="%b-%y", errors="coerce")
        cs = cs.sort_values(["Segment", "_dt"]).reset_index(drop=True)
        cs["_prev_subs"] = cs.groupby("Segment")["Subscribers"].shift(1)
        cs["_derived_churn"] = (
            (cs["_prev_subs"] - cs["Subscribers"]) / cs["_prev_subs"] * 100
        ).where(cs["_prev_subs"] > 0)
        # Use user-supplied Churn_Pct (entered as %, e.g. 2 = 2%) where present;
        # fall back to the derived subscriber-movement estimate where blank or zero.
        if "Churn_Pct" in cs.columns:
            _user = pd.to_numeric(cs["Churn_Pct"], errors="coerce")
            cs["Churn_Pct"] = _user.where(_user.notna() & (_user != 0), cs["_derived_churn"])
        else:
            cs["Churn_Pct"] = cs["_derived_churn"]
        cs.drop(columns=["_dt", "_prev_subs", "_derived_churn"], inplace=True)
        data["Consumer_Sales"] = cs

    if "Business_Sales" in data:
        data["Business_Sales"] = _scale(data["Business_Sales"], [
            "Revenue", "Revenue_AOP", "Gross_Profit", "GP_AOP", "Contribution",
            "MRR", "MRR_AOP", "Direct_Costs", "Direct_Costs_AOP",
            "Mobile", "Mobile_AOP", "USAGE", "USAGE_AOP", "OCC", "OCC_AOP",
        ])
        data["Business_Sales"] = _pct(data["Business_Sales"], ["GP_Margin_Pct"])

        # Auto-populate Direct_Costs and Direct_Costs_AOP from PnL_Breakdown
        # PnL_Breakdown hasn't been scaled yet here, so divide raw values by M
        if "PnL_Breakdown" in data:
            pnl = data["PnL_Breakdown"][["Month", "BUSINESS SALES_COS", "BUSINESS SALES_COS_AOP"]].copy()
            pnl["_pnl_dc"]     = pd.to_numeric(pnl["BUSINESS SALES_COS"],     errors="coerce") / M
            pnl["_pnl_dc_aop"] = pd.to_numeric(pnl["BUSINESS SALES_COS_AOP"], errors="coerce") / M
            pnl = pnl[["Month", "_pnl_dc", "_pnl_dc_aop"]]
            bs = data["Business_Sales"].merge(pnl, on="Month", how="left")
            segs_per_month = bs.groupby("Month")["Segment"].transform("count")
            for col, src in [("Direct_Costs", "_pnl_dc"), ("Direct_Costs_AOP", "_pnl_dc_aop")]:
                if col not in bs.columns:
                    bs[col] = 0.0
                blank = bs[col].isna() | (bs[col] == 0)
                bs.loc[blank, col] = bs.loc[blank, src] / segs_per_month[blank]
            bs.drop(columns=["_pnl_dc", "_pnl_dc_aop"], inplace=True)
            # Derive Gross_Profit and GP_AOP from Revenue - Direct_Costs
            bs["Gross_Profit"] = bs["Revenue"] - bs["Direct_Costs"]
            aop_available = bs["Revenue_AOP"].notna() & (bs["Revenue_AOP"] != 0) & \
                            bs["Direct_Costs_AOP"].notna() & (bs["Direct_Costs_AOP"] != 0)
            bs.loc[aop_available, "GP_AOP"] = (
                bs.loc[aop_available, "Revenue_AOP"] - bs.loc[aop_available, "Direct_Costs_AOP"]
            )
            data["Business_Sales"] = bs

    if "Business_Sales_MRR" in data:
        mrr = data["Business_Sales_MRR"].copy()
        mrr["Month"] = (
            pd.to_datetime(mrr["Month"].astype(str), format="%b %Y", errors="coerce")
            .dt.strftime("%b-%y")
        )
        data["Business_Sales_MRR"] = _scale(mrr, ["MRR", "USAGE", "OCC"])

    if "Pipeline" in data:
        data["Pipeline"] = _scale(data["Pipeline"], ["Value_TTD_M", "Avg_Deal_Size"])
        data["Pipeline"] = _pct(data["Pipeline"], ["Win_Rate_Pct"])

    if "Renewals" in data:
        data["Renewals"] = _scale(data["Renewals"], ["ACV_TTD_M"])

    if "DPDI" in data:
        data["DPDI"] = _scale(data["DPDI"], [
            "Revenue", "Revenue_AOP", "Gross_Profit", "EBITDA", "Direct_Costs",
        ])
        data["DPDI"] = _pct(data["DPDI"], ["GP_Margin_Pct"])

        if "PnL_Breakdown" in data:
            pnl = data["PnL_Breakdown"][["Month", "DPDI_COS", "DPDI_COS_AOP"]].copy()
            pnl["_pnl_dc"]     = pd.to_numeric(pnl["DPDI_COS"],     errors="coerce") / M
            pnl["_pnl_dc_aop"] = pd.to_numeric(pnl["DPDI_COS_AOP"], errors="coerce") / M
            pnl = pnl[["Month", "_pnl_dc", "_pnl_dc_aop"]]
            dp = data["DPDI"].merge(pnl, on="Month", how="left")
            prods_per_month = dp.groupby("Month")["Product"].transform("count")
            for col, src in [("Direct_Costs", "_pnl_dc")]:
                blank = dp[col].isna() | (dp[col] == 0)
                dp.loc[blank, col] = dp.loc[blank, src] / prods_per_month[blank]
            dp["Gross_Profit"] = dp["Revenue"] - dp["Direct_Costs"]
            dp.drop(columns=["_pnl_dc", "_pnl_dc_aop"], inplace=True)
            data["DPDI"] = dp

    if "AMPLIA_Financial" in data:
        data["AMPLIA_Financial"] = _scale(data["AMPLIA_Financial"], [
            "Revenue", "Revenue_AOP", "Gross_Profit",
            "EBITDA", "EBITDA_AOP", "PAT", "OPEX", "Direct_Costs",
        ])

    # ── OPEX: strip DPDI Cost of Sales, scale, recalculate Variance ─────────
    if "OPEX" in data:
        df = data["OPEX"].copy()
        # "DIG. PROD DEV & INNOV" is Cost of Sales for the DPDI LoB, not OPEX
        dpdi_cos = df[df["Category"] == "DIG. PROD DEV & INNOV"].copy()
        dpdi_cos = _scale(dpdi_cos, ["Actual", "Plan"])
        data["DPDI_CoS"] = dpdi_cos
        df = df[df["Category"] != "DIG. PROD DEV & INNOV"].copy()
        df = _scale(df, ["Actual", "Plan"])
        df["Variance"] = df["Actual"] - df["Plan"]
        df["Variance_Pct"] = ((df["Actual"] - df["Plan"]) / df["Plan"].replace(0, pd.NA) * 100).round(1)
        data["OPEX"] = df

    # ── EBITDA Bridge: compute total row, then scale ──────────────────────────
    if "EBITDA_Bridge" in data:
        bridge = data["EBITDA_Bridge"].copy()
        bridge["Value"] = pd.to_numeric(bridge["Value"], errors="coerce")
        computed_total = bridge["Value"].iloc[:-1].sum()
        bridge.loc[bridge.index[-1], "Value"] = computed_total
        bridge.loc[bridge.index[-1], "Type"] = "Total"
        bridge = bridge.sort_values("Sort_Order").reset_index(drop=True)
        bridge["Value"] = bridge["Value"] / M
        data["EBITDA_Bridge"] = bridge

    if "PnL_Breakdown" in data:
        mon_cols = [c for c in data["PnL_Breakdown"].columns if c != "Month"]
        data["PnL_Breakdown"] = _scale(data["PnL_Breakdown"], mon_cols)

    # ── KPI Summary: scale only  rows ────────────────────────────────────
    if "KPI_Summary" in data:
        kpi = data["KPI_Summary"].copy()
        # Accept 7 columns (no PY) or 8 columns (with PY placeholder)
        if kpi.shape[1] >= 8:
            kpi = kpi.iloc[:, :8]
            kpi.columns = ["Month", "Section", "KPI_Name", "Actual", "AOP", "PY", "Status", "Unit"]
        else:
            kpi = kpi.iloc[:, :7]
            kpi.columns = ["Month", "Section", "KPI_Name", "Actual", "AOP", "Status", "Unit"]
            kpi["PY"] = pd.NA
        kpi = kpi.dropna(subset=["Section", "KPI_Name"])
        ttm_mask = kpi["Unit"] == ""
        pct_mask = kpi["Unit"] == "%"
        for col in ["Actual", "AOP"]:
            kpi.loc[ttm_mask, col] = pd.to_numeric(kpi.loc[ttm_mask, col], errors="coerce") / M
            kpi.loc[pct_mask, col] = pd.to_numeric(kpi.loc[pct_mask, col], errors="coerce") * 100
        # Derive PY from Actual 12 months prior for each KPI
        kpi["_dt"] = pd.to_datetime(kpi["Month"], format="%b-%y", errors="coerce")
        py_lk = kpi.dropna(subset=["_dt"]).set_index(["_dt", "KPI_Name"])["Actual"]
        kpi["PY"] = kpi.apply(
            lambda r: py_lk.get((r["_dt"] - pd.DateOffset(months=12), r["KPI_Name"]))
            if pd.notna(r["_dt"]) else pd.NA,
            axis=1,
        )
        kpi.drop(columns=["_dt"], inplace=True)
        data["KPI_Summary"] = kpi

    # ── PP_Plans: raw export has header on row 2, count col = "Sub Count" ────
    if "PP_Plans" in data:
        try:
            df = pd.read_excel(xls, sheet_name="PP_Plans", header=2)
            df = df.rename(columns={"Sub Count": "Subscribers"})
            df["Subscribers"] = pd.to_numeric(df["Subscribers"], errors="coerce").fillna(0)
            df = df[["Legacy/Active", "Plan", "Subscribers"]].dropna(subset=["Plan"])
            active = df[df["Legacy/Active"] == "Active"].sort_values("Subscribers", ascending=False)
            legacy_total = int(df[df["Legacy/Active"] == "Legacy"]["Subscribers"].sum())
            top5 = active.iloc[:5][["Plan", "Subscribers"]].copy()
            other_active = int(active.iloc[5:]["Subscribers"].sum())
            rows = top5.to_dict("records")
            if other_active > 0:
                rows.append({"Plan": "Other Active", "Subscribers": other_active})
            if legacy_total > 0:
                rows.append({"Plan": "Legacy Plans", "Subscribers": legacy_total})
            data["PP_Plans"] = pd.DataFrame(rows)
        except Exception:
            data["PP_Plans"] = pd.DataFrame()

    # ── WTTx_Plans: header on row 1; group by Voice/Data/Bundle type ─────────
    if "WTTx_Plans" in data:
        try:
            df = pd.read_excel(xls, sheet_name="WTTx_Plans", header=1)
            type_col = "Voice/Data/Bundle"
            count_col = df.columns[-1]  # date column holds the subscriber counts
            df = df[[type_col, count_col]].copy()
            df.columns = ["Plan", "Subscribers"]
            df["Subscribers"] = pd.to_numeric(df["Subscribers"], errors="coerce").fillna(0)
            df = df[df["Subscribers"] > 0].groupby("Plan")["Subscribers"].sum().reset_index()
            df = df.sort_values("Subscribers", ascending=False).reset_index(drop=True)
            data["WTTx_Plans"] = df
        except Exception:
            data["WTTx_Plans"] = pd.DataFrame()

    return data


@st.cache_data
def load_prepaid_arpu():
    """Load prepaid subscribers by ARPU bucket from the external Excel file.

    Returns a long-format DataFrame with columns:
        Month (str, e.g. 'Jan-25'), Category (str), Subscribers (float), Revenue (float, 0.0)
    Skips Grand Total rows — caller filters as needed.
    """
    CAT_MAP = {
        "a. VLV -  < $5":      "Very Low (0-5)",
        "a. VLV - < $5":       "Very Low (0-5)",
        "b. LV - $5 -$30":     "Low (5-30)",
        "c. MV - $30 - $120":  "Medium (30-120)",
        "d. HV - $120 - $300": "High (120-300)",
        "e. VHV - >= $300":    "Very High (>300)",
    }
    try:
        # header=1: use the second Excel row (Row Labels + date cols) as column names
        df = pd.read_excel(ARPU_BUCKET_PATH, sheet_name="Export", header=1)
    except Exception:
        return pd.DataFrame()

    cat_col = df.columns[0]  # "Row Labels"
    records = []
    for col in df.columns[1:]:
        try:
            month_fmt = pd.to_datetime(col).strftime("%b-%y")
        except Exception:
            continue
        for _, row in df.iterrows():
            raw_cat = str(row[cat_col]).strip()
            cat = CAT_MAP.get(raw_cat)
            if cat is None:
                continue
            val = pd.to_numeric(row[col], errors="coerce")
            if pd.isna(val):
                continue
            records.append({
                "Month":       month_fmt,
                "Category":    cat,
                "Subscribers": val,
                "Revenue":     0.0,
            })

    return pd.DataFrame(records)


@st.cache_data
def load_prepaid_data_usage():
    """Load prepaid data usage from dd_prepaid_data_usage_mth.xlsx.

    Returns a DataFrame sorted by month with derived columns:
        Month (str, e.g. 'Sep-25'), unique_data_users, bundle_users, payg_users,
        total_data_usage (MB), in_bundle_usage (MB), payg_data_usage (MB),
        gb_per_user, bundle_pct,
        data_bundle_rev, payg_data_charges, total_data_rev
    """
    try:
        df = pd.read_excel(PREPAID_USAGE_PATH, sheet_name="Result 1")
    except Exception:
        return pd.DataFrame()

    df = df.sort_values("Month_Code").reset_index(drop=True)
    df["Month"] = (
        pd.to_datetime(df["Month_Code"].astype(str), format="%Y%m")
        .dt.strftime("%b-%y")
    )
    df["gb_per_user"]       = df["total_data_usage"] / df["unique_data_users"] / 1024
    df["bundle_pct"]        = df["bundle_users"]     / df["unique_data_users"] * 100
    df["data_bundle_rev"]   = df["data_bundle_rev"]  / M
    df["payg_data_charges"] = df["payg_data_charges"] / M
    df["total_data_rev"]    = df["data_bundle_rev"]  + df["payg_data_charges"]
    return df


def get_month_order(df, col="Month"):
    """Return unique months in their original DataFrame order."""
    return list(dict.fromkeys(df[col].dropna().tolist()))


def pivot_by_group(df, index_col, group_col, value_col):
    """Pivot df preserving original row order of index_col."""
    month_order = get_month_order(df, index_col)
    pivot = df.pivot_table(index=index_col, columns=group_col, values=value_col, aggfunc="sum")
    pivot = pivot.reindex(month_order).reset_index()
    return pivot
