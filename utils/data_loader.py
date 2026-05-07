import pandas as pd
import streamlit as st

EXCEL_PATH = "TSTT_Board_Data.xlsx"


@st.cache_data
def load_all_data():
    xls = pd.ExcelFile(EXCEL_PATH)
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(xls, sheet_name=sheet)

    # OPEX: recalculate variance pct (source has formulas as strings)
    if "OPEX" in data:
        df = data["OPEX"].copy()
        df["Variance"] = df["Actual"] - df["Plan"]
        df["Variance_Pct"] = ((df["Actual"] - df["Plan"]) / df["Plan"].replace(0, pd.NA) * 100).round(1)
        data["OPEX"] = df

    # EBITDA Bridge: compute the total row value (source has =SUM formula)
    if "EBITDA_Bridge" in data:
        bridge = data["EBITDA_Bridge"].copy()
        bridge["Value"] = pd.to_numeric(bridge["Value"], errors="coerce")
        computed_total = bridge["Value"].iloc[:-1].sum()
        bridge.loc[bridge.index[-1], "Value"] = computed_total
        bridge.loc[bridge.index[-1], "Type"] = "Total"
        bridge = bridge.sort_values("Sort_Order").reset_index(drop=True)
        data["EBITDA_Bridge"] = bridge

    # KPI Summary: drop spurious last column, clean up
    if "KPI_Summary" in data:
        kpi = data["KPI_Summary"].copy()
        kpi = kpi.iloc[:, :8]  # keep first 8 cols only
        kpi.columns = ["Month", "Section", "KPI_Name", "Actual", "AOP", "LY", "Status", "Unit"]
        kpi = kpi.dropna(subset=["Section", "KPI_Name"])
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
