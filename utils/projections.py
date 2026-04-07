"""
utils/projections.py — Financial Projection Engine for Indian Investors
========================================================================
Pure Python. No external dependencies.

Functions:
  project_wealth()           — SIP wealth projection with step-up
  calculate_fire_number()    — FIRE corpus (inflation-adjusted)
  fire_plan()                — Comprehensive FIRE plan
  goal_planner()             — Multi-goal SIP planning
  compound_savings_impact()  — Compounding of tax savings
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future_value_sip(monthly_sip: float, months: int, monthly_rate: float) -> float:
    """Annuity-due FV of monthly SIP."""
    if monthly_rate == 0:
        return monthly_sip * months
    return monthly_sip * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)


def _future_value_lumpsum(principal: float, months: int, monthly_rate: float) -> float:
    return principal * (1 + monthly_rate) ** months


def _human_readable(amount: float) -> str:
    abs_a = abs(amount)
    sign = "-" if amount < 0 else ""
    if abs_a >= 1_00_00_000:
        return f"{sign}Rs {abs_a / 1_00_00_000:.2f} Cr"
    elif abs_a >= 1_00_000:
        return f"{sign}Rs {abs_a / 1_00_000:.2f} L"
    elif abs_a >= 1_000:
        return f"{sign}Rs {abs_a / 1_000:.2f} K"
    return f"{sign}Rs {abs_a:.0f}"


# ---------------------------------------------------------------------------
# 1. SIP Wealth Projection
# ---------------------------------------------------------------------------

def project_wealth(
    monthly_sip: float,
    years: int,
    annual_return: float = 0.12,
    step_up_percent: float = 0.10,
) -> Dict:
    """
    SIP wealth projection with optional annual step-up.

    Returns
    -------
    dict:
        year_by_year      — list of {year, monthly_sip, invested_this_year,
                            cumulative_invested, value, gains}
        total_invested    — float
        final_value       — float
        total_gains       — float
        wealth_multiplier — float
        annual_return     — float
        step_up_percent   — float
        summary           — str
    """
    monthly_rate = annual_return / 12
    projections: List[Dict] = []
    cumulative_invested = 0.0
    corpus = 0.0
    current_sip = monthly_sip

    for yr in range(1, years + 1):
        invested_this_year = current_sip * 12
        cumulative_invested += invested_this_year

        corpus = (
            _future_value_lumpsum(corpus, 12, monthly_rate)
            + _future_value_sip(current_sip, 12, monthly_rate)
        )
        gains = corpus - cumulative_invested

        projections.append({
            "year": yr,
            "monthly_sip": round(current_sip, 2),
            "invested_this_year": round(invested_this_year, 2),
            "cumulative_invested": round(cumulative_invested, 2),
            "value": round(corpus, 2),
            "gains": round(gains, 2),
        })

        current_sip *= 1 + step_up_percent

    total_invested = round(cumulative_invested, 2)
    final_value = round(corpus, 2)
    total_gains = round(corpus - cumulative_invested, 2)
    multiplier = round(corpus / cumulative_invested, 2) if cumulative_invested else 0

    return {
        "year_by_year": projections,
        "total_invested": total_invested,
        "final_value": final_value,
        "total_gains": total_gains,
        "wealth_multiplier": multiplier,
        "annual_return": annual_return,
        "step_up_percent": step_up_percent,
        "summary": (
            f"SIP: Rs {monthly_sip:,.0f}/mo | Step-up: {step_up_percent*100:.0f}%/yr | "
            f"Return: {annual_return*100:.0f}%/yr | Horizon: {years} yrs\n"
            f"Invested: {_human_readable(total_invested)} | "
            f"Final: {_human_readable(final_value)} | "
            f"Gains: {_human_readable(total_gains)} | "
            f"Multiplier: {multiplier}x"
        ),
    }


# ---------------------------------------------------------------------------
# 2. FIRE Number
# ---------------------------------------------------------------------------

def calculate_fire_number(
    monthly_expenses: float,
    inflation_rate: float = 0.06,
    years_to_retire: int = 30,
    withdrawal_rate: float = 0.04,
) -> Dict:
    """
    FIRE corpus using safe withdrawal rate.

    Returns
    -------
    dict:
        current_monthly_expenses, inflation_rate, years_to_retire,
        inflation_adjusted_monthly_expenses, inflation_adjusted_annual_expenses,
        fire_number, withdrawal_rate, summary
    """
    future_monthly = monthly_expenses * (1 + inflation_rate) ** years_to_retire
    future_annual = future_monthly * 12
    multiplier = 1 / withdrawal_rate
    fire_number = future_annual * multiplier

    return {
        "current_monthly_expenses": monthly_expenses,
        "inflation_rate": inflation_rate,
        "years_to_retire": years_to_retire,
        "inflation_adjusted_monthly_expenses": round(future_monthly, 2),
        "inflation_adjusted_annual_expenses": round(future_annual, 2),
        "fire_number": round(fire_number, 2),
        "withdrawal_rate": withdrawal_rate,
        "summary": (
            f"Current expenses: Rs {monthly_expenses:,.0f}/mo\n"
            f"Inflation-adjusted at retirement ({years_to_retire} yrs @ {inflation_rate*100:.0f}%): "
            f"Rs {future_monthly:,.0f}/mo\n"
            f"FIRE Number ({withdrawal_rate*100:.0f}% rule = {multiplier:.0f}x): "
            f"{_human_readable(fire_number)}"
        ),
    }


# ---------------------------------------------------------------------------
# Helpers for FIRE Plan
# ---------------------------------------------------------------------------

def _compute_corpus_at_year(
    current_corpus: float,
    monthly_sip: float,
    years: int,
    annual_return: float,
) -> float:
    monthly_rate = annual_return / 12
    corpus = current_corpus
    for _ in range(years):
        corpus = (
            _future_value_lumpsum(corpus, 12, monthly_rate)
            + _future_value_sip(monthly_sip, 12, monthly_rate)
        )
    return corpus


def _required_sip_for_target(
    current_corpus: float,
    target: float,
    years: int,
    annual_return: float,
) -> float:
    monthly_rate = annual_return / 12
    months = years * 12
    fv_corpus = _future_value_lumpsum(current_corpus, months, monthly_rate)
    remaining = target - fv_corpus
    if remaining <= 0:
        return 0.0
    if monthly_rate == 0:
        annuity_factor = months
    else:
        annuity_factor = (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
    return remaining / annuity_factor


def _find_fire_age(
    current_age: int,
    current_corpus: float,
    monthly_sip: float,
    annual_return: float,
    fire_number: float,
    max_age: int = 100,
) -> Optional[int]:
    monthly_rate = annual_return / 12
    corpus = current_corpus
    age = current_age
    for _ in range(max_age - current_age + 1):
        if corpus >= fire_number:
            return age
        corpus = (
            _future_value_lumpsum(corpus, 12, monthly_rate)
            + _future_value_sip(monthly_sip, 12, monthly_rate)
        )
        age += 1
    return None


# ---------------------------------------------------------------------------
# 3. FIRE Plan
# ---------------------------------------------------------------------------

def fire_plan(
    current_age: int,
    retirement_age: int,
    monthly_income: float,
    monthly_expenses: float,
    current_corpus: float,
    current_monthly_sip: float,
    expected_return: float = 0.12,
    inflation_rate: float = 0.06,
) -> Dict:
    """
    Comprehensive FIRE plan.

    Returns
    -------
    dict:
        current_age, retirement_age, years_to_retire, monthly_income,
        monthly_expenses, savings_rate, current_corpus, current_monthly_sip,
        expected_return, fire_number, projected_corpus_at_retirement, gap,
        on_track, required_monthly_sip, fire_achievable_age,
        year_by_year: [{year, age, corpus, fire_number_at_year,
                        inflated_annual_expenses, progress_percent}],
        summary
    """
    years_to_retire = max(0, retirement_age - current_age)
    savings_rate = (
        (monthly_income - monthly_expenses) / monthly_income * 100
        if monthly_income > 0 else 0
    )

    fire_data = calculate_fire_number(monthly_expenses, inflation_rate, years_to_retire)
    fire_number = fire_data["fire_number"]

    projected = _compute_corpus_at_year(
        current_corpus, current_monthly_sip, years_to_retire, expected_return
    )
    gap = projected - fire_number
    on_track = gap >= 0

    required_sip = _required_sip_for_target(
        current_corpus, fire_number, years_to_retire, expected_return
    )

    fire_age = _find_fire_age(
        current_age, current_corpus, current_monthly_sip, expected_return, fire_number
    )

    monthly_rate = expected_return / 12
    corpus = current_corpus
    year_by_year: List[Dict] = []
    for yr in range(1, years_to_retire + 1):
        corpus = (
            _future_value_lumpsum(corpus, 12, monthly_rate)
            + _future_value_sip(current_monthly_sip, 12, monthly_rate)
        )
        fire_at_year = monthly_expenses * 12 * (1 + inflation_rate) ** yr / 0.04
        progress = min(corpus / fire_number * 100, 100) if fire_number > 0 else 100
        year_by_year.append({
            "year": yr,
            "age": current_age + yr,
            "corpus": round(corpus, 2),
            "fire_number_at_year": round(fire_at_year, 2),
            "inflated_annual_expenses": round(monthly_expenses * 12 * (1 + inflation_rate) ** yr, 2),
            "progress_percent": round(progress, 2),
        })

    lines = [
        f"FIRE Plan | Age {current_age} -> {retirement_age} ({years_to_retire} years)",
        f"Income: Rs {monthly_income:,.0f}/mo | Expenses: Rs {monthly_expenses:,.0f}/mo | "
        f"Savings rate: {savings_rate:.1f}%",
        f"Current corpus: {_human_readable(current_corpus)} | "
        f"Current SIP: Rs {current_monthly_sip:,.0f}/mo",
        f"FIRE Number (inflation-adjusted): {_human_readable(fire_number)}",
        f"Projected corpus at {retirement_age}: {_human_readable(projected)}",
    ]
    if on_track:
        lines.append(f"ON TRACK — Surplus of {_human_readable(gap)}")
    else:
        lines.append(f"SHORTFALL of {_human_readable(abs(gap))}")
        lines.append(f"Required SIP to bridge gap: Rs {required_sip:,.0f}/mo")
    if fire_age is not None:
        lines.append(f"FIRE achievable age at current SIP: {fire_age}")
    else:
        lines.append("FIRE not achievable at current SIP within age 100.")

    return {
        "current_age": current_age,
        "retirement_age": retirement_age,
        "years_to_retire": years_to_retire,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses,
        "savings_rate": round(savings_rate, 2),
        "current_corpus": current_corpus,
        "current_monthly_sip": current_monthly_sip,
        "expected_return": expected_return,
        "fire_number": round(fire_number, 2),
        "projected_corpus_at_retirement": round(projected, 2),
        "gap": round(gap, 2),
        "on_track": on_track,
        "required_monthly_sip": round(required_sip, 2),
        "fire_achievable_age": fire_age,
        "year_by_year": year_by_year,
        "summary": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# 4. Goal Planner
# ---------------------------------------------------------------------------

def _suggest_fund_category(years: int) -> Tuple[str, float, str]:
    if years <= 1:
        return ("Liquid / Overnight Fund", 0.065,
                f"{years}yr: Capital safety paramount. Use liquid/overnight funds.")
    elif years <= 3:
        return ("Short-Duration Debt / Conservative Hybrid", 0.08,
                f"{years}yr: Low volatility needed. Short-duration debt or conservative hybrid.")
    elif years <= 5:
        return ("Balanced Advantage / Aggressive Hybrid", 0.10,
                f"{years}yr: Moderate risk. Balanced advantage or aggressive hybrid funds.")
    elif years <= 7:
        return ("Large-Cap Equity / Flexi-Cap", 0.11,
                f"{years}yr: Equity-oriented with stability. Large-cap or flexi-cap.")
    elif years <= 15:
        return ("Flexi-Cap / Mid-Cap Equity", 0.12,
                f"{years}yr: Long enough for equity. Flexi-cap or mid-cap for growth.")
    else:
        return ("Small-Cap / Mid-Cap Equity", 0.13,
                f"{years}yr: Very long term. Small/mid-cap for maximum compounding.")


def goal_planner(goals_list: List[Dict]) -> Dict:
    """
    Multi-goal SIP planner.

    Parameters
    ----------
    goals_list : list of dict
        Each dict: {name, target, years, current (optional, default 0)}

    Returns
    -------
    dict:
        goals — list of {name, target, years, current_savings, gap,
                         required_monthly_sip, suggested_category,
                         suggested_return, reasoning}
        total_monthly_sip_needed — float
        summary — str
    """
    goals_out: List[Dict] = []
    total_sip = 0.0

    for goal in goals_list:
        name = goal["name"]
        target = float(goal["target"])
        years = int(goal["years"])
        current = float(goal.get("current", 0))

        category, expected_return, reasoning = _suggest_fund_category(years)
        required_sip = max(0.0, _required_sip_for_target(current, target, years, expected_return))

        gap = max(
            0.0,
            target - _future_value_lumpsum(current, years * 12, expected_return / 12),
        )

        goals_out.append({
            "name": name,
            "target": target,
            "years": years,
            "current_savings": current,
            "gap": round(gap, 2),
            "required_monthly_sip": round(required_sip, 2),
            "suggested_category": category,
            "suggested_return": expected_return,
            "reasoning": reasoning,
        })
        total_sip += required_sip

    lines = ["GOAL PLANNER", ""]
    for i, g in enumerate(goals_out, 1):
        lines.append(f"  {i}. {g['name']}")
        lines.append(f"     Target: {_human_readable(g['target'])} in {g['years']} yrs")
        lines.append(f"     Current savings: {_human_readable(g['current_savings'])}")
        lines.append(f"     Required SIP: Rs {g['required_monthly_sip']:,.0f}/mo")
        lines.append(f"     Suggested: {g['suggested_category']} (~{g['suggested_return']*100:.1f}%)")
        lines.append("")
    lines.append(f"  Total monthly SIP needed: Rs {total_sip:,.0f}")

    return {
        "goals": goals_out,
        "total_monthly_sip_needed": round(total_sip, 2),
        "summary": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# 5. Compound Savings Impact
# ---------------------------------------------------------------------------

def compound_savings_impact(
    annual_savings: float,
    years: int,
    return_rate: float = 0.12,
) -> Dict:
    """
    Show compounding impact of investing annual savings (e.g., tax savings).

    Returns
    -------
    dict:
        annual_savings, monthly_equivalent, years, return_rate,
        total_invested, final_value, wealth_gain, narrative
    """
    monthly_savings = annual_savings / 12
    monthly_rate = return_rate / 12
    months = years * 12

    total_invested = annual_savings * years
    final_value = _future_value_sip(monthly_savings, months, monthly_rate)
    wealth_gain = final_value - total_invested
    multiplier = final_value / total_invested if total_invested > 0 else 0

    return {
        "annual_savings": annual_savings,
        "monthly_equivalent": round(monthly_savings, 2),
        "years": years,
        "return_rate": return_rate,
        "total_invested": round(total_invested, 2),
        "final_value": round(final_value, 2),
        "wealth_gain": round(wealth_gain, 2),
        "narrative": (
            f"Rs {annual_savings:,.0f}/yr tax saving invested as "
            f"Rs {monthly_savings:,.0f}/mo SIP "
            f"for {years} yrs at {return_rate*100:.0f}% = {_human_readable(final_value)}\n"
            f"Invested: {_human_readable(total_invested)} -> "
            f"Wealth: {_human_readable(final_value)} "
            f"({_human_readable(wealth_gain)} pure gains)\n"
            f"That's a {multiplier:.1f}x multiplier on your savings."
        ),
    }
