"""RAG color helpers — thresholds from TSTT Key Risk Indicator Risk Levels May 2026."""
import pandas as pd

GREEN = "#15803D"
AMBER = "#B45309"
RED   = "#B91C1C"
GREY  = "#5B6675"


def _v(val):
    try:
        if val is None:
            return None
        v = float(val)
        return None if pd.isna(v) else v
    except Exception:
        return None


def rag(val, green_thresh, amber_thresh, higher=True):
    """Return RAG hex color. Returns GREY when val is None/NaN."""
    v = _v(val)
    if v is None:
        return GREY
    if higher:
        return GREEN if v >= green_thresh else (AMBER if v >= amber_thresh else RED)
    else:
        return GREEN if v <= green_thresh else (AMBER if v <= amber_thresh else RED)


# ── Revenue Generation ────────────────────────────────────────────────────────

def rev_var_rag(pct_variance):
    """Actual Revenue vs Budget (pct variance already computed).
    Green >=0% (at/above AOP), Amber >=-10% (within 10% below), Red <-10%."""
    v = _v(pct_variance)
    if v is None:
        return GREY
    return GREEN if v >= 0 else (AMBER if v >= -10 else RED)


def rev_vs_aop(actual, aop):
    """Compute pct variance then apply rev_var_rag."""
    a, b = _v(actual), _v(aop)
    if a is None or b is None or b == 0:
        return GREY
    return rev_var_rag(a / abs(b) * 100 - 100)


def ebitda_abs_rag(actual_m):
    """EBITDA $: Green >=TT$55m, Amber >=TT$45m, Red <TT$45m."""
    return rag(actual_m, 55, 45)


def ebitda_margin_rag(pct):
    """Operating margin (EBITDA/Revenue): Green >=35%, Amber >=30%, Red <30%."""
    return rag(pct, 35, 30)


def gp_margin_rag(pct):
    """Gross margin (GP/Revenue): Green >=75%, Amber >=65%, Red <65%."""
    return rag(pct, 75, 65)


def pat_margin_rag(pct):
    """Profit margin (PAT/Revenue): Green >=7.4%, Amber >=0%, Red <0%."""
    return rag(pct, 7.4, 0.0)


def opex_pct_rag(pct):
    """Efficiency ratio (OPEX/Revenue): Green <=40%, Amber <=45%, Red >45%."""
    return rag(pct, 40, 45, higher=False)


# ── Liquidity — Collections ───────────────────────────────────────────────────

def collections_gov_rag(pct):
    """Government collections: Green >=95%, Amber >=90%, Red <90%."""
    return rag(pct, 95, 90)


def collections_nongov_rag(pct):
    """Non-Government collections: Green >=95%, Amber >=90%, Red <90%."""
    return rag(pct, 95, 90)


def collections_consumer_rag(pct):
    """Consumer/monthly cash collections: Green >=80%, Amber >=75%, Red <75%."""
    return rag(pct, 80, 75)


# ── Customer Experience — Churn ───────────────────────────────────────────────

def churn_prepaid_rag(pct):
    """Prepaid monthly churn: Green <=2%, Amber <=2.49%, Red >2.5%."""
    return rag(pct, 2.0, 2.49, higher=False)


def churn_postpaid_rag(pct):
    """Postpaid voluntary churn: Green <=0.60%, Amber <=1.24%, Red >1.25%."""
    return rag(pct, 0.60, 1.24, higher=False)


def churn_wttx_rag(pct):
    """WTTx churn: Green <=1%, Amber <=1.49%, Red >1.5%."""
    return rag(pct, 1.0, 1.49, higher=False)
