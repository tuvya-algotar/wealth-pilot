"""
utils/adapter.py — WealthPilot Analysis Adapter
================================================
Central connector between user-facing data and the three calculation engines:
  - utils/tax_engine.py
  - utils/health_scorer.py
  - utils/projections.py

All functions are pure Python, deterministic, and raise no LLM calls.
"""

from __future__ import annotations
from typing import Dict, List, Any

from utils.tax_engine import compare_regimes, find_missed_deductions
from utils.health_scorer import calculate_financial_health
from utils.projections import fire_plan, calculate_fire_number


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


METRO_CITIES = {
    "mumbai", "delhi", "chennai", "kolkata", "bangalore",
    "bengaluru", "hyderabad", "new delhi",
}


def _is_metro(city: str) -> bool:
    return city.lower().strip() in METRO_CITIES if city else False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_tax_analysis(user_data: dict) -> dict:
    """
    Run Old vs New regime comparison and missed-deduction analysis.

    Parameters
    ----------
    user_data : dict
        age             : int
        annual_income   : float   — gross CTC / annual salary
        hra_received    : float   — annual HRA received from employer
        monthly_rent    : float   — monthly rent paid (converted to annual internally)
        is_metro        : bool    — metro city flag (or derive from city str)
        sec_80c         : float   — total 80C investments (EPF + PPF + ELSS + LIC etc.)
        sec_80d         : float   — health insurance premium, self & family
        nps_annual      : float   — NPS contribution (80CCD 1B), max ₹50k
        home_loan_interest : float
        epf_annual      : float   — employee EPF contribution (subset of 80C)

    Returns
    -------
    dict:
        old_regime_tax   : float
        new_regime_tax   : float
        recommended      : "Old" | "New"
        savings          : float  — tax saved by choosing recommended regime
        missed_deductions: list[dict] — {section, current_amount, limit, gap,
                                          marginal_rate_pct, potential_tax_saving}
        old_breakdown    : list[dict] — slab-level breakdown for old regime
        new_breakdown    : list[dict] — slab-level breakdown for new regime
    """
    age = _safe_int(user_data.get("age"), 30)
    annual_income = _safe_float(user_data.get("annual_income"))
    hra_received = _safe_float(user_data.get("hra_received"))
    monthly_rent = _safe_float(user_data.get("monthly_rent"))
    rent_paid_annual = monthly_rent * 12

    # is_metro: accept bool or derive from city string
    is_metro = user_data.get("is_metro")
    if not isinstance(is_metro, bool):
        is_metro = _is_metro(str(user_data.get("city", "")))

    # 80C: combine sec_80c field + epf_annual
    sec_80c_raw = _safe_float(user_data.get("sec_80c"))
    epf_annual = _safe_float(user_data.get("epf_annual"))
    sec_80c_total = sec_80c_raw + epf_annual

    sec_80d = _safe_float(user_data.get("sec_80d"))
    nps_annual = _safe_float(user_data.get("nps_annual"))
    home_loan_interest = _safe_float(user_data.get("home_loan_interest"))

    result = compare_regimes(
        gross_salary=annual_income,
        hra_received=hra_received,
        rent_paid=rent_paid_annual,
        is_metro=is_metro,
        age=age,
        sec_80c=sec_80c_total,
        sec_80d_self=sec_80d,
        sec_80ccd1b=nps_annual,
        home_loan_interest=home_loan_interest,
        epf_contribution=epf_annual,
    )

    old_r = result["old_regime_result"]
    new_r = result["new_regime_result"]

    return {
        "old_regime_tax": old_r["total_tax"],
        "new_regime_tax": new_r["total_tax"],
        "recommended": result["recommendation"],
        "savings": result["savings"],
        "missed_deductions": result["missed_deductions"],
        "old_breakdown": old_r.get("slab_breakdown", []),
        "new_breakdown": new_r.get("slab_breakdown", []),
        # Extra fields useful for the UI
        "old_effective_rate": old_r["effective_rate"],
        "new_effective_rate": new_r["effective_rate"],
        "old_taxable_income": result["old_taxable_income"],
        "new_taxable_income": result["new_taxable_income"],
    }


def run_health_analysis(user_data: dict) -> dict:
    """
    Calculate financial health score across 6 dimensions.

    Parameters
    ----------
    user_data : dict
        age                  : int
        annual_income        : float
        monthly_expenses     : float
        emergency_fund       : float
        has_term_insurance   : bool
        term_cover           : float
        has_health_insurance : bool
        health_cover         : float
        total_equity         : float
        total_debt           : float
        monthly_sip          : float
        sec_80c              : float
        nps_annual           : float

    Returns
    -------
    dict:
        overall_score   : float  0-100
        scores          : dict {emergency, insurance, investment, debt, tax, retirement}
                          each value is a float score (0-100)
        recommendations : list[str]  — top 3 action items
    """
    age = _safe_int(user_data.get("age"), 30)
    annual_income = _safe_float(user_data.get("annual_income"))
    monthly_expenses = _safe_float(user_data.get("monthly_expenses"))
    retirement_age = _safe_int(user_data.get("retirement_age"), 60)

    normalised: Dict[str, Any] = {
        "age": age,
        "annual_income": annual_income,
        "monthly_expenses": monthly_expenses,
        "emergency_fund": _safe_float(user_data.get("emergency_fund")),
        "has_term_insurance": bool(user_data.get("has_term_insurance", False)),
        "term_cover": _safe_float(user_data.get("term_cover")),
        "has_health_insurance": bool(user_data.get("has_health_insurance", False)),
        "health_cover": _safe_float(user_data.get("health_cover")),
        "total_equity": _safe_float(user_data.get("total_equity")),
        "total_debt": _safe_float(user_data.get("total_debt")),
        "total_gold": _safe_float(user_data.get("total_gold")),
        "total_real_estate": _safe_float(user_data.get("total_real_estate")),
        "monthly_sip": _safe_float(user_data.get("monthly_sip")),
        "sec_80c": _safe_float(user_data.get("sec_80c")),
        "nps_annual": _safe_float(user_data.get("nps_annual")),
        "retirement_age": retirement_age,
        # debt_health scorer uses this
        "total_emi_per_month": _safe_float(user_data.get("total_emi_per_month")),
    }

    raw = calculate_financial_health(normalised)

    # Flatten scores to {category_short: score_float}
    short_keys = {
        "EMERGENCY_PREPAREDNESS": "emergency",
        "INSURANCE_COVERAGE": "insurance",
        "INVESTMENT_DIVERSIFICATION": "investment",
        "DEBT_HEALTH": "debt",
        "TAX_EFFICIENCY": "tax",
        "RETIREMENT_READINESS": "retirement",
    }
    flat_scores = {
        short_keys[k]: v["score"]
        for k, v in raw["scores"].items()
    }

    return {
        "overall_score": raw["overall_score"],
        "scores": flat_scores,
        "recommendations": raw["top_3_recommendations"],
        # Expose full detail for UI drill-down
        "score_detail": raw["scores"],
        "radar_chart_data": raw["radar_chart_data"],
    }


def run_fire_analysis(user_data: dict) -> dict:
    """
    Run FIRE (Financial Independence, Retire Early) analysis.

    Parameters
    ----------
    user_data : dict
        age            : int
        retirement_age : int
        annual_income  : float
        monthly_expenses : float
        total_equity   : float
        total_debt     : float
        monthly_sip    : float

    Returns
    -------
    dict:
        fire_number          : float  — inflation-adjusted corpus needed
        current_projection   : float  — projected corpus at retirement age
        gap                  : float  — surplus (positive) or shortfall (negative)
        required_sip         : float  — monthly SIP to exactly hit FIRE number
        projections          : list[dict]  — [{year, invested, value, gains}]
    """
    age = _safe_int(user_data.get("age"), 30)
    retirement_age = _safe_int(user_data.get("retirement_age"), 60)
    annual_income = _safe_float(user_data.get("annual_income"))
    monthly_income = annual_income / 12
    monthly_expenses = _safe_float(user_data.get("monthly_expenses"))

    # Current corpus = total equity + total debt
    total_equity = _safe_float(user_data.get("total_equity"))
    total_debt = _safe_float(user_data.get("total_debt"))
    current_corpus = total_equity + total_debt

    monthly_sip = _safe_float(user_data.get("monthly_sip"))

    plan = fire_plan(
        current_age=age,
        retirement_age=retirement_age,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        current_corpus=current_corpus,
        current_monthly_sip=monthly_sip,
        expected_return=0.12,
        inflation_rate=0.06,
    )

    # Build projections in the adapter's canonical format
    projections = [
        {
            "year": entry["year"],
            "age": entry["age"],
            "invested": round(monthly_sip * 12 * entry["year"] + current_corpus, 2),
            "value": entry["corpus"],
            "gains": round(entry["corpus"] - (monthly_sip * 12 * entry["year"] + current_corpus), 2),
            "progress_percent": entry["progress_percent"],
        }
        for entry in plan["year_by_year"]
    ]

    return {
        "fire_number": plan["fire_number"],
        "current_projection": plan["projected_corpus_at_retirement"],
        "gap": plan["gap"],
        "required_sip": plan["required_monthly_sip"],
        "projections": projections,
        # Extra metadata for UI
        "on_track": plan["on_track"],
        "fire_achievable_age": plan["fire_achievable_age"],
        "years_to_retire": plan["years_to_retire"],
        "savings_rate": plan["savings_rate"],
        "summary": plan["summary"],
    }


def run_full_analysis(user_data: dict) -> dict:
    """
    Run all three analyses and return a combined result dict.

    Parameters
    ----------
    user_data : dict — superset of all three individual function inputs.

    Returns
    -------
    dict:
        tax    : result of run_tax_analysis()
        health : result of run_health_analysis()
        fire   : result of run_fire_analysis()
        user_data : the original input (for report generation)
    """
    return {
        "tax": run_tax_analysis(user_data),
        "health": run_health_analysis(user_data),
        "fire": run_fire_analysis(user_data),
        "user_data": user_data,
    }
