"""
utils/tax_engine.py — Indian Income Tax Calculator for FY 2024-25 (AY 2025-26)
================================================================================
Pure Python, fully deterministic. No external dependencies.

Covers:
  - Old Regime: age-based slabs, Section 87A rebate, surcharge with marginal relief, cess
  - New Regime: Budget 2024 slabs, ₹75,000 standard deduction, revised 87A rebate
  - HRA Exemption under Section 10(13A)
  - Deductions: 80C, 80D, 80CCD(1B), 24(b), 80E, 80CCD(2), 80G
  - Regime comparison with missed-deduction analysis
"""

from __future__ import annotations
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CESS_RATE = 0.04
REBATE_87A_OLD = 12_500
REBATE_87A_OLD_INCOME_LIMIT = 5_00_000
REBATE_87A_NEW = 25_000
REBATE_87A_NEW_INCOME_LIMIT = 7_00_000
STANDARD_DEDUCTION_NEW = 75_000
STANDARD_DEDUCTION_OLD = 50_000

SURCHARGE_BRACKETS: List[Tuple[float, float, float]] = [
    (50_00_000,  1_00_00_000, 0.10),
    (1_00_00_000, 2_00_00_000, 0.15),
    (2_00_00_000, 5_00_00_000, 0.25),
    (5_00_00_000, float('inf'), 0.37),
]

OLD_GENERAL_SLABS: List[Tuple[float, float, float]] = [
    (0,          2_50_000,  0.00),
    (2_50_000,   5_00_000,  0.05),
    (5_00_000,  10_00_000,  0.20),
    (10_00_000, float('inf'), 0.30),
]

OLD_SENIOR_SLABS: List[Tuple[float, float, float]] = [
    (0,          3_00_000,  0.00),
    (3_00_000,   5_00_000,  0.05),
    (5_00_000,  10_00_000,  0.20),
    (10_00_000, float('inf'), 0.30),
]

OLD_SUPER_SENIOR_SLABS: List[Tuple[float, float, float]] = [
    (0,          5_00_000,  0.00),
    (5_00_000,  10_00_000,  0.20),
    (10_00_000, float('inf'), 0.30),
]

NEW_REGIME_SLABS: List[Tuple[float, float, float]] = [
    (0,          3_00_000,  0.00),
    (3_00_000,   7_00_000,  0.05),
    (7_00_000,  10_00_000,  0.10),
    (10_00_000, 12_00_000,  0.15),
    (12_00_000, 15_00_000,  0.20),
    (15_00_000, float('inf'), 0.30),
]

DEDUCTION_LIMITS: Dict[str, float] = {
    "sec_80c":                   1_50_000,
    "sec_80d_self":                25_000,
    "sec_80d_self_senior":         50_000,
    "sec_80d_parents":             25_000,
    "sec_80d_parents_senior":      50_000,
    "sec_80ccd1b":                 50_000,
    "home_loan_interest":        2_00_000,
    "education_loan_interest":   float('inf'),
    "nps_employer_contribution": float('inf'),
    "other_80g":                 float('inf'),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_slab_tax(
    income: float,
    slabs: List[Tuple[float, float, float]],
) -> Tuple[float, List[Dict]]:
    total_tax = 0.0
    breakdown: List[Dict] = []
    for lower, upper, rate in slabs:
        if income <= lower:
            break
        taxable_in_slab = min(income, upper) - lower
        tax_in_slab = taxable_in_slab * rate
        total_tax += tax_in_slab
        breakdown.append({
            "slab": f"₹{lower:,.0f} – ₹{upper:,.0f}" if upper != float('inf') else f"Above ₹{lower:,.0f}",
            "rate_pct": rate * 100,
            "taxable_amount": taxable_in_slab,
            "tax": tax_in_slab,
        })
    return total_tax, breakdown


def _compute_surcharge(income: float, base_tax: float) -> float:
    applicable_rate = 0.0
    for lower, upper, rate in SURCHARGE_BRACKETS:
        if income > lower:
            applicable_rate = rate

    if applicable_rate == 0.0:
        return 0.0

    surcharge = base_tax * applicable_rate

    # Marginal relief: net tax increase must not exceed income increase above threshold
    threshold_map = [
        (50_00_000,  0.10),
        (1_00_00_000, 0.15),
        (2_00_00_000, 0.25),
        (5_00_00_000, 0.37),
    ]
    prev_threshold = 0
    for thresh, rate in threshold_map:
        if income > thresh:
            prev_threshold = thresh

    income_above_threshold = income - prev_threshold
    marginal_relief = max(0.0, surcharge - income_above_threshold)
    return max(0.0, surcharge - marginal_relief)


# ---------------------------------------------------------------------------
# 1. Old Regime
# ---------------------------------------------------------------------------

def calculate_old_regime_tax(taxable_income: float, age: int) -> Dict:
    """
    Calculate income tax under the Old Tax Regime for FY 2024-25.

    Parameters
    ----------
    taxable_income : float — Net taxable income after all deductions (₹). Must be >= 0.
    age           : int   — Age as of 31-Mar-2025. <60 General, 60-79 Senior, >=80 Super Senior.

    Returns
    -------
    dict: gross_tax, rebate_87a, tax_after_rebate, surcharge, cess,
          total_tax, effective_rate, slab_breakdown, regime, taxpayer_category
    """
    if taxable_income < 0:
        raise ValueError("taxable_income cannot be negative.")

    if age >= 80:
        slabs = OLD_SUPER_SENIOR_SLABS
        category = "Super Senior Citizen (>=80)"
    elif age >= 60:
        slabs = OLD_SENIOR_SLABS
        category = "Senior Citizen (60-79)"
    else:
        slabs = OLD_GENERAL_SLABS
        category = "General (<60)"

    gross_tax, slab_breakdown = _compute_slab_tax(taxable_income, slabs)

    rebate = 0.0
    if taxable_income <= REBATE_87A_OLD_INCOME_LIMIT:
        rebate = min(gross_tax, REBATE_87A_OLD)

    tax_after_rebate = max(0.0, gross_tax - rebate)
    surcharge = _compute_surcharge(taxable_income, tax_after_rebate)
    cess = (tax_after_rebate + surcharge) * CESS_RATE
    total_tax = tax_after_rebate + surcharge + cess
    effective_rate = (total_tax / taxable_income * 100) if taxable_income > 0 else 0.0

    return {
        "regime": "Old",
        "taxpayer_category": category,
        "taxable_income": taxable_income,
        "gross_tax": round(gross_tax, 2),
        "rebate_87a": round(rebate, 2),
        "tax_after_rebate": round(tax_after_rebate, 2),
        "surcharge": round(surcharge, 2),
        "cess": round(cess, 2),
        "total_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate, 4),
        "slab_breakdown": slab_breakdown,
    }


# ---------------------------------------------------------------------------
# 2. New Regime
# ---------------------------------------------------------------------------

def calculate_new_regime_tax(gross_income: float, age: int) -> Dict:
    """
    Calculate income tax under the New Tax Regime (Budget 2024) for FY 2024-25.

    Parameters
    ----------
    gross_income : float — Gross salary BEFORE standard deduction (₹). Must be >= 0.
    age          : int   — Taxpayer age.

    Returns
    -------
    dict: standard_deduction, taxable_income, gross_tax, rebate_87a,
          tax_after_rebate, surcharge, cess, total_tax, effective_rate, slab_breakdown
    """
    if gross_income < 0:
        raise ValueError("gross_income cannot be negative.")

    standard_deduction = min(STANDARD_DEDUCTION_NEW, gross_income)
    taxable_income = max(0.0, gross_income - standard_deduction)

    gross_tax, slab_breakdown = _compute_slab_tax(taxable_income, NEW_REGIME_SLABS)

    rebate = 0.0
    if taxable_income <= REBATE_87A_NEW_INCOME_LIMIT:
        rebate = min(gross_tax, REBATE_87A_NEW)

    tax_after_rebate = max(0.0, gross_tax - rebate)
    surcharge = _compute_surcharge(taxable_income, tax_after_rebate)
    cess = (tax_after_rebate + surcharge) * CESS_RATE
    total_tax = tax_after_rebate + surcharge + cess
    effective_rate = (total_tax / gross_income * 100) if gross_income > 0 else 0.0

    return {
        "regime": "New",
        "taxpayer_category": f"Age {age}",
        "gross_income": gross_income,
        "standard_deduction": standard_deduction,
        "taxable_income": taxable_income,
        "gross_tax": round(gross_tax, 2),
        "rebate_87a": round(rebate, 2),
        "tax_after_rebate": round(tax_after_rebate, 2),
        "surcharge": round(surcharge, 2),
        "cess": round(cess, 2),
        "total_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate, 4),
        "slab_breakdown": slab_breakdown,
    }


# ---------------------------------------------------------------------------
# 3. HRA Exemption  [Section 10(13A)]
# ---------------------------------------------------------------------------

def calculate_hra_exemption(
    basic_salary: float,
    hra_received: float,
    rent_paid_annual: float,
    is_metro: bool,
) -> Dict:
    """
    HRA exemption — minimum of three conditions:
      a) Actual HRA received
      b) Rent paid − 10% of basic
      c) 50% basic (metro) or 40% basic (non-metro)
    """
    cond_a = hra_received
    cond_b = max(0.0, rent_paid_annual - 0.10 * basic_salary)
    cond_c = basic_salary * (0.50 if is_metro else 0.40)

    hra_exempt = min(cond_a, cond_b, cond_c)
    hra_taxable = max(0.0, hra_received - hra_exempt)

    return {
        "actual_hra_received": hra_received,
        "rent_minus_10pct_basic": round(cond_b, 2),
        f"{'50' if is_metro else '40'}pct_of_basic": round(cond_c, 2),
        "hra_exempt": round(hra_exempt, 2),
        "hra_taxable": round(hra_taxable, 2),
        "city_type": "Metro (50% basic)" if is_metro else "Non-Metro (40% basic)",
        "conditions": {
            "a_actual_hra": round(cond_a, 2),
            "b_rent_minus_10pct_basic": round(cond_b, 2),
            "c_pct_of_basic": round(cond_c, 2),
            "minimum_applied": round(hra_exempt, 2),
        },
    }


# ---------------------------------------------------------------------------
# 4. Deductions (Old Regime)
# ---------------------------------------------------------------------------

def calculate_deductions(
    sec_80c: float = 0,
    sec_80d_self: float = 0,
    sec_80d_parents: float = 0,
    sec_80ccd1b: float = 0,
    home_loan_interest: float = 0,
    education_loan_interest: float = 0,
    nps_employer_contribution: float = 0,
    other_80g: float = 0,
    age: int = 35,
    parents_are_senior: bool = False,
) -> Dict:
    """
    Compute total eligible deductions under the Old Tax Regime with statutory caps.
    """
    limit_80c = DEDUCTION_LIMITS["sec_80c"]
    allowed_80c = min(sec_80c, limit_80c)

    limit_80d_self = (
        DEDUCTION_LIMITS["sec_80d_self_senior"] if age >= 60
        else DEDUCTION_LIMITS["sec_80d_self"]
    )
    allowed_80d_self = min(sec_80d_self, limit_80d_self)

    limit_80d_parents = (
        DEDUCTION_LIMITS["sec_80d_parents_senior"] if parents_are_senior
        else DEDUCTION_LIMITS["sec_80d_parents"]
    )
    allowed_80d_parents = min(sec_80d_parents, limit_80d_parents)

    limit_ccd1b = DEDUCTION_LIMITS["sec_80ccd1b"]
    allowed_ccd1b = min(sec_80ccd1b, limit_ccd1b)

    limit_hl = DEDUCTION_LIMITS["home_loan_interest"]
    allowed_hl = min(home_loan_interest, limit_hl)

    allowed_80e = education_loan_interest
    allowed_ccd2 = nps_employer_contribution
    allowed_80g = other_80g

    total = (
        allowed_80c + allowed_80d_self + allowed_80d_parents + allowed_ccd1b
        + allowed_hl + allowed_80e + allowed_ccd2 + allowed_80g
    )

    breakdown = {
        "sec_80c": {
            "claimed": sec_80c, "allowed": round(allowed_80c, 2),
            "limit": limit_80c, "section": "80C",
        },
        "sec_80d_self": {
            "claimed": sec_80d_self, "allowed": round(allowed_80d_self, 2),
            "limit": limit_80d_self, "section": "80D (Self & Family)",
        },
        "sec_80d_parents": {
            "claimed": sec_80d_parents, "allowed": round(allowed_80d_parents, 2),
            "limit": limit_80d_parents, "section": "80D (Parents)",
        },
        "sec_80ccd1b": {
            "claimed": sec_80ccd1b, "allowed": round(allowed_ccd1b, 2),
            "limit": limit_ccd1b, "section": "80CCD(1B) — NPS Additional",
        },
        "home_loan_interest": {
            "claimed": home_loan_interest, "allowed": round(allowed_hl, 2),
            "limit": limit_hl, "section": "24(b) — Home Loan Interest",
        },
        "education_loan_interest": {
            "claimed": education_loan_interest, "allowed": round(allowed_80e, 2),
            "limit": "No cap", "section": "80E — Education Loan",
        },
        "nps_employer_contribution": {
            "claimed": nps_employer_contribution, "allowed": round(allowed_ccd2, 2),
            "limit": "No absolute cap", "section": "80CCD(2) — Employer NPS",
        },
        "other_80g": {
            "claimed": other_80g, "allowed": round(allowed_80g, 2),
            "limit": "Varies", "section": "80G — Donations",
        },
    }

    return {
        "total_deductions": round(total, 2),
        "breakdown": breakdown,
    }


# ---------------------------------------------------------------------------
# 5. Regime Comparison
# ---------------------------------------------------------------------------

def compare_regimes(
    gross_salary: float,
    hra_received: float,
    rent_paid: float,
    is_metro: bool,
    age: int,
    sec_80c: float = 0,
    sec_80d_self: float = 0,
    sec_80d_parents: float = 0,
    sec_80ccd1b: float = 0,
    home_loan_interest: float = 0,
    epf_contribution: float = 0,
    education_loan_interest: float = 0,
    nps_employer_contribution: float = 0,
    other_80g: float = 0,
    basic_salary: float = 0,
    parents_are_senior: bool = False,
) -> Dict:
    """
    Compare Old Regime vs New Regime and recommend the more tax-efficient option.
    """
    if basic_salary == 0:
        basic_salary = gross_salary * 0.40

    # Old Regime
    hra_result = calculate_hra_exemption(basic_salary, hra_received, rent_paid, is_metro)
    hra_exempt = hra_result["hra_exempt"]

    deductions_result = calculate_deductions(
        sec_80c=sec_80c,
        sec_80d_self=sec_80d_self,
        sec_80d_parents=sec_80d_parents,
        sec_80ccd1b=sec_80ccd1b,
        home_loan_interest=home_loan_interest,
        education_loan_interest=education_loan_interest,
        nps_employer_contribution=nps_employer_contribution,
        other_80g=other_80g,
        age=age,
        parents_are_senior=parents_are_senior,
    )
    total_deductions = deductions_result["total_deductions"]

    old_taxable = max(
        0.0,
        gross_salary - hra_exempt - STANDARD_DEDUCTION_OLD - total_deductions,
    )
    old_result = calculate_old_regime_tax(old_taxable, age)
    old_result["standard_deduction"] = STANDARD_DEDUCTION_OLD
    old_result["hra_exempt"] = round(hra_exempt, 2)
    old_result["chapter_vi_deductions"] = total_deductions

    # New Regime
    new_result = calculate_new_regime_tax(gross_salary, age)

    old_tax = old_result["total_tax"]
    new_tax = new_result["total_tax"]

    if old_tax <= new_tax:
        recommendation = "Old"
        savings = round(new_tax - old_tax, 2)
    else:
        recommendation = "New"
        savings = round(old_tax - new_tax, 2)

    current_deductions_dict = {
        "sec_80c": sec_80c,
        "sec_80d_self": sec_80d_self,
        "sec_80d_parents": sec_80d_parents,
        "sec_80ccd1b": sec_80ccd1b,
        "home_loan_interest": home_loan_interest,
        "education_loan_interest": education_loan_interest,
    }
    missed = find_missed_deductions(current_deductions_dict, old_taxable, age, parents_are_senior)

    return {
        "gross_salary": gross_salary,
        "old_taxable_income": round(old_taxable, 2),
        "new_taxable_income": new_result["taxable_income"],
        "old_regime_result": old_result,
        "new_regime_result": new_result,
        "recommendation": recommendation,
        "savings": savings,
        "deductions_summary": deductions_result,
        "missed_deductions": missed,
    }


# ---------------------------------------------------------------------------
# 6. Missed Deductions Finder
# ---------------------------------------------------------------------------

def find_missed_deductions(
    current_deductions_dict: Dict[str, float],
    taxable_income: float = 10_00_000,
    age: int = 35,
    parents_are_senior: bool = False,
) -> List[Dict]:
    """
    Identify deductions below their statutory limits and estimate tax savings if fully used.
    """
    limits = {
        "sec_80c":    ("80C (PF / PPF / ELSS / LIC)", 1_50_000),
        "sec_80d_self": (
            "80D – Self & Family",
            50_000 if age >= 60 else 25_000,
        ),
        "sec_80d_parents": (
            "80D – Parents",
            50_000 if parents_are_senior else 25_000,
        ),
        "sec_80ccd1b": ("80CCD(1B) – Additional NPS", 50_000),
        "home_loan_interest": ("24(b) – Home Loan Interest", 2_00_000),
        "education_loan_interest": ("80E – Education Loan", None),  # No cap
    }

    def _marginal_rate(income: float) -> float:
        if income <= 2_50_000:   return 0.00
        if income <= 5_00_000:   return 0.05
        if income <= 10_00_000:  return 0.20
        return 0.30

    marginal = _marginal_rate(taxable_income)
    effective_marginal = marginal * (1 + CESS_RATE)

    missed: List[Dict] = []
    for key, (section_name, limit) in limits.items():
        current = current_deductions_dict.get(key, 0.0)
        if limit is None:
            continue
        gap = max(0.0, limit - current)
        if gap > 0:
            saving = round(gap * effective_marginal, 2)
            missed.append({
                "section": section_name,
                "current_amount": current,
                "limit": limit,
                "gap": round(gap, 2),
                "marginal_rate_pct": round(marginal * 100, 1),
                "potential_tax_saving": saving,
            })

    missed.sort(key=lambda x: x["potential_tax_saving"], reverse=True)
    return missed
