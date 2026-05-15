import pandas as pd
import streamlit as st

AR_FILE  = "Receivables Executive Summary.xlsx"
AR_SHEET = "Exec. Summary Receivables"
APR_COL  = 74  # April 2026 column index (confirmed from date row 3)

# Fallback values for Apr-26 if the file cannot be read
_FALLBACK_GOV     = {"0_30": 26.4, "31_60": 15.9, "61_90": 20.2,
                     "90_360": 65.9, "360p": 939.9, "total": 1068.3}
_FALLBACK_NON_GOV = {"0_30": 51.4, "31_60": 13.8, "61_90": 15.6,
                     "90_360": 66.3, "360p": 352.8, "total": 500.0}
_FALLBACK_TOTAL   = {"0_30": 77.8, "31_60": 29.7, "61_90": 35.8,
                     "90_360": 132.2, "360p": 1292.7, "total": 1568.3}


@st.cache_data
def load_ar_aging():
    """Load AR aging buckets from the Receivables Executive Summary workbook.

    Returns a dict with keys 'gov', 'non_gov', 'total', each being a dict of
    bucket values in TT$M.  Returns fallback hard-coded values on failure.
    """
    try:
        df = pd.read_excel(AR_FILE, sheet_name=AR_SHEET, header=None)
    except Exception:
        return {"gov": _FALLBACK_GOV, "non_gov": _FALLBACK_NON_GOV,
                "total": _FALLBACK_TOTAL}

    def v(row):
        val = df.iloc[row, APR_COL]
        return float(val) if pd.notna(val) and isinstance(val, (int, float)) else 0.0

    # Government = Fixed Enterprise Gov (rows 22–28) + Mobile Enterprise Gov (rows 40–46)
    gov = {
        "0_30":   v(22) + v(40),
        "31_60":  v(23) + v(41),
        "61_90":  v(24) + v(42),
        "90_360": v(25) + v(26) + v(43) + v(44),
        "360p":   v(27) + v(45),
        "total":  v(28) + v(46),
    }

    # Total aged receivables (rows 4–10)
    tot = {
        "0_30":   v(4),
        "31_60":  v(5),
        "61_90":  v(6),
        "90_360": v(7) + v(8),
        "360p":   v(9),
        "total":  v(10),
    }

    non_gov = {k: tot[k] - gov[k] for k in tot}
    return {"gov": gov, "non_gov": non_gov, "total": tot}
