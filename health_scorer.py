"""
utils/health_scorer.py — Financial Health Scorer for Indian Individuals
========================================================================
Pure Python, no LLM, no external dependencies.

Six scoring dimensions (weighted):
  1. Emergency Preparedness     — 15%
  2. Insurance Coverage         — 20%
  3. Investment Diversification — 15%
  4. Debt Health                — 20%
  5. Tax Efficiency             — 10%
  6. Retirement Readiness       — 20%

Input field names are normalised from the adapter's canonical schema:
  annual_income, monthly_expenses, emergency_fund, has_term_insurance,
  term_cover, has_health_insurance, health_cover, total_equity, total_debt,
  monthly_sip, sec_80c, nps_annual, age.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple


# ---------------------------------------------------------------------------
# Category weights
# ---------------------------------------------------------------------------

_WEIGHTS: Dict[str, float] = {
    "EMERGENCY_PREPAREDNESS":     0.15,
    "INSURANCE_COVERAGE":         0.20,
    "INVESTMENT_DIVERSIFICATION": 0.15,
    "DEBT_HEALTH":                0.20,
    "TAX_EFFICIENCY":             0.10,
    "RETIREMENT_READINESS":       0.20,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _linear_score(value: float, zero_at: float, hundred_at: float) -> float:
    if hundred_at == zero_at:
        return 100.0 if value >= hundred_at else 0.0
    raw = (value - zero_at) / (hundred_at - zero_at) * 100.0
    return _clamp(raw)


def _fv_sip(monthly_sip: float, annual_return: float, years: int) -> float:
    """Future value of monthly SIP compounded monthly (annuity due)."""
    if annual_return == 0 or years <= 0:
        return monthly_sip * years * 12
    r = annual_return / 12
    n = years * 12
    return monthly_sip * (((1 + r) ** n - 1) / r) * (1 + r)


def _fv_lumpsum(pv: float, annual_return: float, years: int) -> float:
    if years <= 0:
        return pv
    return pv * ((1 + annual_return) ** years)


# ---------------------------------------------------------------------------
# Individual scorers
# All accept the *normalised* data dict produced by the adapter.
# ---------------------------------------------------------------------------

def score_emergency_preparedness(data: Dict[str, Any]) -> Tuple[float, str]:
    """Target: 6 months of monthly_expenses in liquid emergency fund."""
    monthly_expenses: float = data.get("monthly_expenses", 0)
    emergency_fund: float = data.get("emergency_fund", 0)
    target = 6 * monthly_expenses

    if target == 0:
        return 100.0, "No expenses declared — emergency fund score defaulted to 100."

    score = _linear_score(emergency_fund, 0, target)
    months_covered = round(emergency_fund / monthly_expenses, 1) if monthly_expenses else 0

    if score >= 90:
        explanation = (
            f"Excellent! Emergency fund ₹{emergency_fund:,.0f} covers "
            f"{months_covered} months (target: 6 months)."
        )
    elif score >= 50:
        explanation = (
            f"Decent buffer. Emergency fund ₹{emergency_fund:,.0f} covers "
            f"{months_covered} months. Build to ₹{target:,.0f} for full safety."
        )
    else:
        explanation = (
            f"Needs attention. Emergency fund ₹{emergency_fund:,.0f} covers only "
            f"{months_covered} months. Target ₹{target:,.0f} (6 months) in a liquid fund."
        )
    return round(score, 2), explanation


def score_insurance_coverage(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    Two sub-scores (50% weight each):
      A) Term insurance  — target: 10× annual income
      B) Health insurance — target: ₹10L if age < 40, else ₹25L
    """
    age: int = data.get("age", 30)
    annual_income: float = data.get("annual_income", 0)

    has_term: bool = data.get("has_term_insurance", False)
    term_cover: float = data.get("term_cover", 0) if has_term else 0
    term_target = 10 * annual_income
    if term_target == 0:
        term_score = 100.0
    else:
        term_score = _linear_score(term_cover, 0, term_target) if has_term else 0.0

    has_health: bool = data.get("has_health_insurance", False)
    health_cover: float = data.get("health_cover", 0) if has_health else 0
    health_target = 25_00_000 if age >= 40 else 10_00_000
    health_score = _linear_score(health_cover, 0, health_target) if has_health else 0.0

    combined = 0.5 * term_score + 0.5 * health_score
    if not has_term and not has_health:
        combined = _clamp(combined - 10)

    parts: List[str] = []
    if has_term:
        pct_term = (term_cover / term_target * 100) if term_target else 100
        parts.append(
            f"Term cover ₹{term_cover / 1e7:.1f} Cr is "
            f"{pct_term:.0f}% of recommended 10× income (₹{term_target / 1e7:.1f} Cr)."
        )
    else:
        parts.append(
            f"No term insurance. Get a plan for at least ₹{term_target / 1e7:.1f} Cr immediately."
        )

    if has_health:
        parts.append(
            f"Health cover ₹{health_cover / 1e5:.0f}L vs recommended ₹{health_target / 1e5:.0f}L."
        )
    else:
        parts.append(
            f"No health insurance. Get a policy with at least ₹{health_target / 1e5:.0f}L cover."
        )

    return round(combined, 2), " ".join(parts)


def score_investment_diversification(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    Ideal equity allocation ≈ (100 − age)%.
    Scores based on mean absolute deviation from ideal split across equity / debt / gold+re.
    """
    age: int = data.get("age", 30)
    equity: float = data.get("total_equity", 0)
    debt: float = data.get("total_debt", 0)
    gold: float = data.get("total_gold", 0)
    real_estate: float = data.get("total_real_estate", 0)

    total = equity + debt + gold + real_estate
    if total == 0:
        return 0.0, "Zero investments. Start investing — even small SIPs help."

    eq_pct = equity / total * 100
    debt_pct = debt / total * 100
    gold_pct = gold / total * 100
    re_pct = real_estate / total * 100

    ideal_eq = max(0, min(100, 100 - age))
    ideal_debt = (100 - ideal_eq) * 0.6
    ideal_gold_re = (100 - ideal_eq) * 0.4

    actual_gold_re = gold_pct + re_pct
    deviation = (
        abs(eq_pct - ideal_eq)
        + abs(debt_pct - ideal_debt)
        + abs(actual_gold_re - ideal_gold_re)
    ) / 3.0

    base_score = _linear_score(deviation, 66.7, 0)

    max_single = max(eq_pct, debt_pct, gold_pct, re_pct)
    if max_single >= 100:
        base_score = _clamp(base_score - 30)
    elif max_single >= 80:
        base_score = _clamp(base_score - 15)

    if equity == 0 and age < 55:
        base_score = _clamp(base_score - 20)

    explanation = (
        f"Portfolio mix — Equity: {eq_pct:.0f}%, Debt: {debt_pct:.0f}%, "
        f"Gold: {gold_pct:.0f}%, RE: {re_pct:.0f}%. "
        f"Ideal equity for age {age}: ~{ideal_eq}%. "
    )
    if abs(eq_pct - ideal_eq) <= 10:
        explanation += "Equity allocation is well-aligned."
    elif eq_pct < ideal_eq:
        explanation += (
            f"Increase equity by ~{ideal_eq - eq_pct:.0f}pp for better long-term growth."
        )
    else:
        explanation += (
            f"Equity is {eq_pct - ideal_eq:.0f}pp above ideal — aggressive; rebalance if needed."
        )

    return round(base_score, 2), explanation


def score_debt_health(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    EMI-to-income ratio scoring (piecewise linear).
    Uses monthly_income derived from annual_income.
    """
    annual_income: float = data.get("annual_income", 0)
    monthly_income: float = annual_income / 12 if annual_income > 0 else 0
    total_emi: float = data.get("total_emi_per_month", 0)

    if monthly_income <= 0:
        ratio = 100.0 if total_emi > 0 else 0.0
    else:
        ratio = total_emi / monthly_income * 100

    if ratio <= 10:
        score = 100.0
        quality, advice = "Excellent", "Debt obligations are very low — great position."
    elif ratio <= 20:
        score = 100 - (ratio - 10) * 2
        quality, advice = "Good", "Debt is manageable. Avoid large new EMIs."
    elif ratio <= 40:
        score = 80 - (ratio - 20) * 2
        quality = "Moderate"
        advice = "EMI burden is significant. Prioritise paying off high-interest loans."
    elif ratio <= 60:
        score = 40 - (ratio - 40) * 2
        quality = "Danger zone"
        advice = "EMI burden is dangerously high. Restructure or prepay loans urgently."
    else:
        score = 0.0
        quality = "Danger zone"
        advice = "EMI exceeds 60% of income. Seek immediate financial restructuring."

    score = _clamp(score)
    explanation = (
        f"EMI-to-income ratio: {ratio:.1f}% ({quality}). "
        f"Monthly EMI ₹{total_emi:,.0f} on income ₹{monthly_income:,.0f}. {advice}"
    )
    return round(score, 2), explanation


def score_tax_efficiency(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    Ratio of tax deductions actually claimed vs. total available under 80C + NPS + 80D.
    """
    annual_income: float = data.get("annual_income", 0)
    sec_80c: float = data.get("sec_80c", 0)
    nps_annual: float = data.get("nps_annual", 0)

    # Available deductions: statutory caps
    available_80c = 1_50_000
    available_nps = 50_000
    # 80D (estimate: ₹25,000 for self if no data)
    available_80d = 25_000
    total_available = available_80c + available_nps + available_80d

    # Claimed: cap each at its limit
    claimed_80c = min(sec_80c, available_80c)
    claimed_nps = min(nps_annual, available_nps)
    # 80D not directly in health_scorer input; assume not tracked = 0 claimed
    total_claimed = claimed_80c + claimed_nps

    if total_available <= 0:
        return 100.0, "No tax deductions applicable — score defaulted to 100."

    utilization_pct = total_claimed / total_available * 100
    score = _clamp(utilization_pct)
    unused = total_available - total_claimed

    if score >= 90:
        explanation = (
            f"Great tax planning! ₹{total_claimed:,.0f} of ₹{total_available:,.0f} "
            f"available deductions utilised ({utilization_pct:.0f}%)."
        )
    elif score >= 50:
        explanation = (
            f"Partial utilisation: ₹{total_claimed:,.0f} of ₹{total_available:,.0f} "
            f"({utilization_pct:.0f}%). Leaving ₹{unused:,.0f} on the table. "
            "Explore ELSS, NPS (80CCD), health insurance (80D)."
        )
    else:
        explanation = (
            f"Significant tax savings missed. Only ₹{total_claimed:,.0f} of "
            f"₹{total_available:,.0f} ({utilization_pct:.0f}%) claimed. "
            "Invest in 80C (ELSS/PPF/EPF), buy health insurance (80D), explore NPS (80CCD1B)."
        )
    return round(score, 2), explanation


def score_retirement_readiness(data: Dict[str, Any]) -> Tuple[float, str]:
    """
    Target corpus = monthly_expenses × 12 × 25 (4% rule).
    Projects corpus from current total_equity + total_debt corpus + monthly_sip at 12% p.a.
    """
    age: int = data.get("age", 30)
    monthly_expenses: float = data.get("monthly_expenses", 0)
    retirement_age: int = data.get("retirement_age", 60)
    monthly_sip: float = data.get("monthly_sip", 0)

    # Use total_equity + total_debt as retirement corpus proxy
    current_corpus: float = data.get("total_equity", 0) + data.get("total_debt", 0)
    annual_return = 0.12

    years_to_retire = max(0, retirement_age - age)
    target_corpus = monthly_expenses * 12 * 25

    projected_lumpsum = _fv_lumpsum(current_corpus, annual_return, years_to_retire)
    projected_sip = _fv_sip(monthly_sip, annual_return, years_to_retire)
    projected_total = projected_lumpsum + projected_sip

    if target_corpus <= 0:
        return 100.0, "No expenses declared — retirement target is zero. Score: 100."

    achievement_pct = projected_total / target_corpus * 100
    score = _clamp(achievement_pct)

    explanation = (
        f"Target corpus: ₹{target_corpus / 1e7:.2f} Cr (25× annual expenses). "
        f"With corpus ₹{current_corpus / 1e5:.1f}L + SIP ₹{monthly_sip:,.0f}/mo "
        f"at {annual_return*100:.0f}% for {years_to_retire} yrs → "
        f"projected ₹{projected_total / 1e7:.2f} Cr ({achievement_pct:.0f}% of target). "
    )
    if achievement_pct >= 100:
        explanation += "On track — keep it up!"
    elif achievement_pct >= 60:
        explanation += "Decent progress. Increase SIP by 10% annually to close the gap."
    else:
        gap = target_corpus - projected_total
        explanation += f"Shortfall of ₹{gap / 1e7:.2f} Cr. Aggressively increase SIP contributions."

    return round(score, 2), explanation


# ---------------------------------------------------------------------------
# Recommendation Engine
# ---------------------------------------------------------------------------

def _generate_recommendations(scores: Dict[str, Dict]) -> List[str]:
    """Return top-3 actionable recommendations, sorted by lowest score first."""
    ranked = sorted(scores.items(), key=lambda kv: kv[1]["score"])

    category_rec_map = {
        "EMERGENCY_PREPAREDNESS": (
            "[Emergency Fund] Build your emergency fund to cover 6 months of expenses. "
            "Automate a monthly transfer to a liquid fund."
        ),
        "INSURANCE_COVERAGE": (
            "[Insurance] Adequate term + health insurance is non-negotiable. "
            "Increase coverage immediately."
        ),
        "INVESTMENT_DIVERSIFICATION": (
            "[Diversification] Rebalance portfolio to align equity:debt with your age profile."
        ),
        "DEBT_HEALTH": (
            "[Debt] Reduce EMI burden — prepay high-interest loans or consolidate debt."
        ),
        "TAX_EFFICIENCY": (
            "[Tax] Utilise all available deductions: 80C (ELSS/PPF), 80D (health insurance), "
            "80CCD(1B) (NPS). You're leaving money on the table."
        ),
        "RETIREMENT_READINESS": (
            "[Retirement] Increase monthly SIP and review equity allocation to close the retirement gap."
        ),
    }

    recs: List[str] = []
    for category, info in ranked:
        if len(recs) >= 3:
            break
        if info["score"] < 80 and category in category_rec_map:
            recs.append(f"{category_rec_map[category]} Current score: {info['score']}/100.")

    if not recs:
        recs = [
            "Great financial health! Keep reviewing annually and increase SIPs with income growth.",
            "Consider estate planning — write a will and nominate beneficiaries for all accounts.",
            "Explore NPS for an additional ₹50,000 deduction under 80CCD(1B).",
        ]

    while len(recs) < 3:
        recs.append("Maintain current discipline and review your financial plan every 6 months.")

    return recs[:3]


# ---------------------------------------------------------------------------
# Master Scorer
# ---------------------------------------------------------------------------

def calculate_financial_health(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute financial health score across 6 dimensions.

    Parameters
    ----------
    data : dict — Normalised financial profile. Key fields:
        age, annual_income, monthly_expenses, emergency_fund,
        has_term_insurance, term_cover, has_health_insurance, health_cover,
        total_equity, total_debt, monthly_sip, sec_80c, nps_annual,
        retirement_age, total_emi_per_month (optional),
        total_gold (optional), total_real_estate (optional).

    Returns
    -------
    dict:
        scores              — {category: {score, explanation}}
        overall_score       — weighted average 0-100
        top_3_recommendations — list[str]
        radar_chart_data    — plotly-ready dict
    """
    scorers = {
        "EMERGENCY_PREPAREDNESS":     score_emergency_preparedness,
        "INSURANCE_COVERAGE":         score_insurance_coverage,
        "INVESTMENT_DIVERSIFICATION": score_investment_diversification,
        "DEBT_HEALTH":                score_debt_health,
        "TAX_EFFICIENCY":             score_tax_efficiency,
        "RETIREMENT_READINESS":       score_retirement_readiness,
    }

    scores: Dict[str, Dict[str, Any]] = {}
    for category, fn in scorers.items():
        sc, expl = fn(data)
        scores[category] = {"score": sc, "explanation": expl}

    overall = sum(scores[cat]["score"] * w for cat, w in _WEIGHTS.items())
    overall = round(_clamp(overall), 2)

    recommendations = _generate_recommendations(scores)

    categories_list = list(scores.keys())
    values = [scores[c]["score"] for c in categories_list]
    radar_chart_data = {
        "categories": categories_list + [categories_list[0]],
        "values": values + [values[0]],
        "title": f"Financial Health Radar (Overall: {overall}/100)",
    }

    return {
        "scores": scores,
        "overall_score": overall,
        "top_3_recommendations": recommendations,
        "radar_chart_data": radar_chart_data,
    }
