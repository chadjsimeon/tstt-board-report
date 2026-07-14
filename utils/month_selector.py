import pandas as pd
import streamlit as st
from utils.data_loader import load_all_data


def get_months_list():
    """Get all unique months from financial data, sorted chronologically."""
    data = load_all_data()
    fin = data.get("Financial_Monthly", pd.DataFrame())
    if fin.empty:
        return []

    months = fin["Month"].dropna().unique().tolist()
    # Parse months to datetime for proper sorting
    months_dt = pd.to_datetime(months, format="%b-%y", errors="coerce")
    # Convert to Series for proper indexing
    months_dt_series = pd.Series(months_dt)
    sorted_indices = months_dt_series.argsort().values
    return [months[i] for i in sorted_indices if pd.notna(months_dt_series.iloc[i])]


def get_last_actual_data_month():
    """
    Identify the last month with actual (non-budget) data.
    Assumes budget months are those after the last month with actual revenue data.
    """
    data = load_all_data()
    fin = data.get("Financial_Monthly", pd.DataFrame())
    if fin.empty:
        return None

    # Get all months in order
    months_list = get_months_list()
    if not months_list:
        return None

    # For now, return the last available month
    # You can enhance this by checking if certain columns indicate budget vs actual
    return months_list[-1]


def init_focus_month():
    """Initialize focus month in session state."""
    months_list = get_months_list()
    if not months_list:
        return

    if "focus_month" not in st.session_state:
        # A ?focus_month=<Mon-YY> query param (used by the PPTX exporter's
        # headless session) wins; otherwise default to the last month.
        qp_month = st.query_params.get("focus_month")
        st.session_state.focus_month = (
            qp_month if qp_month in months_list else months_list[-1]
        )


def focus_month_selector():
    """
    Create a focus month dropdown in the sidebar.
    Returns the selected month.
    """
    init_focus_month()
    months_list = get_months_list()

    if not months_list:
        return None

    with st.sidebar:
        st.markdown("---")
        selected_month = st.selectbox(
            "📅 Focus Month",
            options=months_list,
            index=months_list.index(st.session_state.focus_month) if st.session_state.focus_month in months_list else len(months_list) - 1,
            key="focus_month_selector",
            help="Select the month to display. Charts and trend lines will end at this month."
        )
        if selected_month != st.session_state.focus_month:
            st.session_state.focus_month = selected_month

    return selected_month


def filter_data_to_month(df, month_col="Month", target_month=None):
    """
    Filter a dataframe to include only rows up to and including the target month.

    Args:
        df: DataFrame with a month column
        month_col: Name of the month column
        target_month: The target month (e.g., "Apr-26"). If None, uses session state focus_month.

    Returns:
        Filtered DataFrame
    """
    if df.empty or month_col not in df.columns:
        return df

    if target_month is None:
        target_month = st.session_state.get("focus_month")

    if target_month is None:
        return df

    # Parse months to datetime for comparison
    df_copy = df.copy()
    df_copy["_dt"] = pd.to_datetime(df_copy[month_col], format="%b-%y", errors="coerce")
    target_dt = pd.to_datetime(target_month, format="%b-%y", errors="coerce")

    if pd.isna(target_dt):
        return df

    filtered = df_copy[df_copy["_dt"] <= target_dt].drop(columns=["_dt"])
    return filtered
