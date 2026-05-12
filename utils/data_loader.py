import pandas as pd
import streamlit as st

EXCEL_PATH = "TSTT_Board_Data.xlsx"
M = 1_000_000  # raw TT$ → TT$M conversion factor


def _scale(df, cols):
    """Divide named monetary columns by 1,000,000 (raw TT$ → TT$M)."""
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

    # ── Scale monetary columns from raw TT$ to TT$M ──────────────────────────
    if "Financial_Monthly" in data:
        data["Financial_Monthly"] = _scale(data["Financial_Monthly"], [
            "Revenue", "EBITDA", "PAT",
            "Revenue_AOP", "EBITDA_AOP", "PAT_AOP",
        ])
        data["Financial_Monthly"] = _pct(data["Financial_Monthly"], ["EBITDA_Margin"])
        # Derive LY columns from 12 months prior in the same series
        fin = data["Financial_Monthly"].copy()
        fin["_dt"] = pd.to_datetime(fin["Month"], format="%b-%y", errors="coerce")
        for col in ["Revenue", "EBITDA", "PAT"]:
            lk = fin.dropna(subset=["_dt"]).set_index("_dt")[col]
            fin[f"{col}_LY"] = fin["_dt"].apply(
                lambda dt, lk=lk: lk.get(dt - pd.DateOffset(months=12))
            )
        fin.drop(columns=["_dt"], inplace=True)
        data["Financial_Monthly"] = fin

    if "Cash_CAPEX" in data:
        data["Cash_CAPEX"] = _scale(data["Cash_CAPEX"], [
            "Cash_Balance", "Net_Debt", "FCF", "CAPEX_Actual", "CAPEX_Plan",
        ])
        data["Cash_CAPEX"] = _pct(data["Cash_CAPEX"], ["Collections_Pct"])

    if "Consumer_Sales" in data:
        data["Consumer_Sales"] = _scale(data["Consumer_Sales"], [
            "Revenue", "Revenue_AOP",
        ])
        data["Consumer_Sales"] = _pct(data["Consumer_Sales"], ["YoY_Change_Pct"])
        # Derive Churn_Pct = (prev_subs - curr_subs) / prev_subs, per segment
        cs = data["Consumer_Sales"].copy()
        cs["_dt"] = pd.to_datetime(cs["Month"], format="%b-%y", errors="coerce")
        cs = cs.sort_values(["Segment", "_dt"]).reset_index(drop=True)
        cs["_prev_subs"] = cs.groupby("Segment")["Subscribers"].shift(1)
        cs["Churn_Pct"] = (
            (cs["_prev_subs"] - cs["Subscribers"]) / cs["_prev_subs"] * 100
        ).where(cs["_prev_subs"] > 0)
        cs.drop(columns=["_dt", "_prev_subs"], inplace=True)
        data["Consumer_Sales"] = cs

    if "Business_Sales" in data:
        data["Business_Sales"] = _scale(data["Business_Sales"], [
            "Revenue", "Revenue_AOP", "Gross_Profit", "Contribution", "MRR", "Direct_Costs",
        ])
        data["Business_Sales"] = _pct(data["Business_Sales"], ["GP_Margin_Pct"])

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

    # ── KPI Summary: scale only TT$M rows ────────────────────────────────────
    if "KPI_Summary" in data:
        kpi = data["KPI_Summary"].copy()
        # Accept 7 columns (no LY) or 8 columns (with LY placeholder)
        if kpi.shape[1] >= 8:
            kpi = kpi.iloc[:, :8]
            kpi.columns = ["Month", "Section", "KPI_Name", "Actual", "AOP", "LY", "Status", "Unit"]
        else:
            kpi = kpi.iloc[:, :7]
            kpi.columns = ["Month", "Section", "KPI_Name", "Actual", "AOP", "Status", "Unit"]
            kpi["LY"] = pd.NA
        kpi = kpi.dropna(subset=["Section", "KPI_Name"])
        ttm_mask = kpi["Unit"] == "TT$M"
        pct_mask = kpi["Unit"] == "%"
        for col in ["Actual", "AOP"]:
            kpi.loc[ttm_mask, col] = pd.to_numeric(kpi.loc[ttm_mask, col], errors="coerce") / M
            kpi.loc[pct_mask, col] = pd.to_numeric(kpi.loc[pct_mask, col], errors="coerce") * 100
        # Derive LY from Actual 12 months prior for each KPI
        kpi["_dt"] = pd.to_datetime(kpi["Month"], format="%b-%y", errors="coerce")
        ly_lk = kpi.dropna(subset=["_dt"]).set_index(["_dt", "KPI_Name"])["Actual"]
        kpi["LY"] = kpi.apply(
            lambda r: ly_lk.get((r["_dt"] - pd.DateOffset(months=12), r["KPI_Name"]))
            if pd.notna(r["_dt"]) else pd.NA,
            axis=1,
        )
        kpi.drop(columns=["_dt"], inplace=True)
        data["KPI_Summary"] = kpi

    return data


def get_month_order(df, col="Month"):
    """Return unique months in their original DataFrame order."""
    return list(dict.fromkeys(df[col].dropna().tolist()))


def pivot_by_group(df, index_col, group_col, value_col):
    """Pivot df preserving original row order of index_col."""
    month_order = get_month_order(df, index_col)
    pivot = df.pivot_table(index=index_col, columns=group_col, values=value_col, aggfunc="sum")
    pivot = pivot.reindex(month_order).reset_index()
    return pivot
