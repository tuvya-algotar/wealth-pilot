"""
projections.py — Indian Financial Planning Projections

Comprehensive financial projection engine for Indian investors covering:
- SIP wealth projections with step-up
- FIRE (Financial Independence, Retire Early) planning
- Multi-goal planning with fund category suggestions
- Compound savings impact analysis (tax savings reinvestment)

All monetary values in INR (₹). Pure Python + scipy where needed.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future_value_sip(monthly_sip: float, months: int, monthly_rate: float) -> float:
    """Standard SIP future value (annuity due – payment at start of month)."""
    if monthly_rate == 0:
        return monthly_sip * months
    return monthly_sip * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)


def _future_value_lumpsum(principal: float, months: int, monthly_rate: float) -> float:
    """Lumpsum compounding."""
    return principal * (1 + monthly_rate) ** months


def _format_inr(amount: float) -> str:
    """Format number in Indian numbering system (lakhs / crores)."""
    amount = round(amount, 2)
    if amount < 0:
        return f"-{_format_inr(-amount)}"

    s = f"{amount:.2f}"
    integer_part, decimal_part = s.split(".")
    integer_part = integer_part.replace(",", "")

    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while rest:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        formatted = ",".join(groups) + "," + last3

    return f"₹{formatted}.{decimal_part}"


def _human_readable(amount: float) -> str:
    """Return human-friendly label like '₹1.23 Cr' or '₹4.50 L'."""
    abs_amount = abs(amount)
    sign = "-" if amount < 0 else ""
    if abs_amount >= 1_00_00_000:
        return f"{sign}₹{abs_amount / 1_00_00_000:.2f} Cr"
    elif abs_amount >= 1_00_000:
        return f"{sign}₹{abs_amount / 1_00_000:.2f} L"
    elif abs_amount >= 1_000:
        return f"{sign}₹{abs_amount / 1_000:.2f} K"
    else:
        return f"{sign}₹{abs_amount:.0f}"


# ---------------------------------------------------------------------------
# 1. project_wealth — SIP Future Value with Optional Annual Step-Up
# ---------------------------------------------------------------------------

@dataclass
class YearProjection:
    year: int
    monthly_sip: float
    invested_this_year: float
    cumulative_invested: float
    value: float
    gains: float


@dataclass
class WealthProjection:
    year_by_year: List[YearProjection]
    total_invested: float
    final_value: float
    total_gains: float
    wealth_multiplier: float
    annual_return: float
    step_up_percent: float
    summary: str


def project_wealth(
    monthly_sip: float,
    years: int,
    annual_return: float = 0.12,
    step_up_percent: float = 0.10,
) -> WealthProjection:
    """
    Calculate SIP future value with optional annual step-up.

    Parameters
    ----------
    monthly_sip : float
        Starting monthly SIP amount in ₹.
    years : int
        Investment horizon in years.
    annual_return : float
        Expected annual return (default 12%).
    step_up_percent : float
        Annual increase in SIP amount (default 10%). Set to 0 for flat SIP.

    Returns
    -------
    WealthProjection with year-by-year breakdown and summary statistics.
    """
    monthly_rate = annual_return / 12
    projections: List[YearProjection] = []
    cumulative_invested = 0.0
    corpus = 0.0
    current_sip = monthly_sip

    for yr in range(1, years + 1):
        invested_this_year = current_sip * 12
        cumulative_invested += invested_this_year

        # Grow existing corpus for 12 months and add this year's SIP contributions
        corpus = _future_value_lumpsum(corpus, 12, monthly_rate) + _future_value_sip(
            current_sip, 12, monthly_rate
        )

        gains = corpus - cumulative_invested

        projections.append(
            YearProjection(
                year=yr,
                monthly_sip=round(current_sip, 2),
                invested_this_year=round(invested_this_year, 2),
                cumulative_invested=round(cumulative_invested, 2),
                value=round(corpus, 2),
                gains=round(gains, 2),
            )
        )

        # Step-up for next year
        current_sip *= 1 + step_up_percent

    total_invested = round(cumulative_invested, 2)
    final_value = round(corpus, 2)
    total_gains = round(corpus - cumulative_invested, 2)
    multiplier = round(corpus / cumulative_invested, 2) if cumulative_invested else 0

    summary = (
        f"Starting SIP: {_format_inr(monthly_sip)}/month | "
        f"Step-up: {step_up_percent * 100:.0f}%/yr | "
        f"Return: {annual_return * 100:.0f}%/yr | "
        f"Horizon: {years} yrs\n"
        f"Total Invested: {_human_readable(total_invested)} | "
        f"Final Value: {_human_readable(final_value)} | "
        f"Gains: {_human_readable(total_gains)} | "
        f"Wealth Multiplier: {multiplier}x"
    )

    return WealthProjection(
        year_by_year=projections,
        total_invested=total_invested,
        final_value=final_value,
        total_gains=total_gains,
        wealth_multiplier=multiplier,
        annual_return=annual_return,
        step_up_percent=step_up_percent,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# 2. calculate_fire_number — FIRE Corpus Calculation
# ---------------------------------------------------------------------------

@dataclass
class FIRENumber:
    current_monthly_expenses: float
    inflation_rate: float
    years_to_retire: int
    inflation_adjusted_monthly_expenses: float
    inflation_adjusted_annual_expenses: float
    fire_number: float
    withdrawal_rate: float
    summary: str


def calculate_fire_number(
    monthly_expenses: float,
    inflation_rate: float = 0.06,
    years_to_retire: int = 30,
    withdrawal_rate: float = 0.04,
) -> FIRENumber:
    """
    Calculate FIRE corpus needed using the safe withdrawal rate rule.

    Parameters
    ----------
    monthly_expenses : float
        Current monthly expenses in ₹.
    inflation_rate : float
        Expected annual inflation (default 6% for India).
    years_to_retire : int
        Years until planned retirement.
    withdrawal_rate : float
        Safe withdrawal rate (default 4% — i.e., corpus = 25x annual expenses).

    Returns
    -------
    FIRENumber with corpus needed and inflation-adjusted expenses.
    """
    # Inflate current expenses to retirement year
    future_monthly = monthly_expenses * (1 + inflation_rate) ** years_to_retire
    future_annual = future_monthly * 12
    multiplier = 1 / withdrawal_rate  # 25x for 4%
    fire_number = future_annual * multiplier

    summary = (
        f"Current expenses: {_format_inr(monthly_expenses)}/month\n"
        f"Inflation-adjusted at retirement ({years_to_retire} yrs @ {inflation_rate*100:.0f}%): "
        f"{_format_inr(future_monthly)}/month\n"
        f"FIRE Number ({withdrawal_rate*100:.0f}% rule → {multiplier:.0f}x): "
        f"{_human_readable(fire_number)}"
    )

    return FIRENumber(
        current_monthly_expenses=monthly_expenses,
        inflation_rate=inflation_rate,
        years_to_retire=years_to_retire,
        inflation_adjusted_monthly_expenses=round(future_monthly, 2),
        inflation_adjusted_annual_expenses=round(future_annual, 2),
        fire_number=round(fire_number, 2),
        withdrawal_rate=withdrawal_rate,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# 3. fire_plan — Comprehensive FIRE Planning
# ---------------------------------------------------------------------------

@dataclass
class FIREPlan:
    current_age: int
    retirement_age: int
    years_to_retire: int
    monthly_income: float
    monthly_expenses: float
    savings_rate: float
    current_corpus: float
    current_monthly_sip: float
    expected_return: float
    fire_number: float
    projected_corpus_at_retirement: float
    gap: float  # positive = surplus, negative = shortfall
    on_track: bool
    required_monthly_sip: float  # SIP needed to exactly hit FIRE number
    fire_achievable_age: Optional[int]  # age at which FIRE is achievable with current SIP
    year_by_year: List[Dict]
    summary: str


def _compute_corpus_at_year(
    current_corpus: float,
    monthly_sip: float,
    years: int,
    annual_return: float,
    step_up: float = 0.0,
) -> float:
    """Compute corpus after `years` with existing corpus + monthly SIP (with optional step-up)."""
    monthly_rate = annual_return / 12
    corpus = current_corpus
    sip = monthly_sip
    for _ in range(years):
        corpus = _future_value_lumpsum(corpus, 12, monthly_rate) + _future_value_sip(
            sip, 12, monthly_rate
        )
        sip *= 1 + step_up
    return corpus


def _required_sip_for_target(
    current_corpus: float,
    target: float,
    years: int,
    annual_return: float,
) -> float:
    """
    Calculate flat monthly SIP needed to reach `target` from `current_corpus`
    over `years` at `annual_return`.

    Uses algebraic solution for flat SIP (no step-up).
    """
    monthly_rate = annual_return / 12
    months = years * 12

    # Future value of existing corpus
    fv_corpus = _future_value_lumpsum(current_corpus, months, monthly_rate)
    remaining = target - fv_corpus

    if remaining <= 0:
        return 0.0

    # SIP annuity factor
    if monthly_rate == 0:
        annuity_factor = months
    else:
        annuity_factor = (((1 + monthly_rate) ** months - 1) / monthly_rate) * (
            1 + monthly_rate
        )

    return remaining / annuity_factor


def _find_fire_age(
    current_age: int,
    current_corpus: float,
    monthly_sip: float,
    annual_return: float,
    fire_number: float,
    max_age: int = 100,
) -> Optional[int]:
    """Find earliest age at which corpus >= FIRE number with current SIP."""
    monthly_rate = annual_return / 12
    corpus = current_corpus
    age = current_age

    for yr in range(max_age - current_age + 1):
        if corpus >= fire_number:
            return age
        corpus = _future_value_lumpsum(corpus, 12, monthly_rate) + _future_value_sip(
            monthly_sip, 12, monthly_rate
        )
        age += 1

    return None  # Not achievable within max_age


def fire_plan(
    current_age: int,
    retirement_age: int,
    monthly_income: float,
    monthly_expenses: float,
    current_corpus: float,
    current_monthly_sip: float,
    expected_return: float = 0.12,
    inflation_rate: float = 0.06,
) -> FIREPlan:
    """
    Comprehensive FIRE plan calculation.

    Parameters
    ----------
    current_age : int
    retirement_age : int
    monthly_income : float
        Gross monthly income.
    monthly_expenses : float
        Current monthly expenses.
    current_corpus : float
        Existing invested corpus.
    current_monthly_sip : float
        Current monthly SIP amount.
    expected_return : float
        Expected annual return on investments (default 12%).
    inflation_rate : float
        Expected annual inflation (default 6%).

    Returns
    -------
    FIREPlan with complete analysis and year-by-year projections.
    """
    years_to_retire = retirement_age - current_age
    savings_rate = (
        ((monthly_income - monthly_expenses) / monthly_income * 100)
        if monthly_income > 0
        else 0
    )

    # FIRE number
    fire = calculate_fire_number(monthly_expenses, inflation_rate, years_to_retire)
    fire_number = fire.fire_number

    # Projected corpus at retirement with current SIP
    projected = _compute_corpus_at_year(
        current_corpus, current_monthly_sip, years_to_retire, expected_return
    )
    gap = projected - fire_number
    on_track = gap >= 0

    # Required SIP
    required_sip = _required_sip_for_target(
        current_corpus, fire_number, years_to_retire, expected_return
    )

    # FIRE achievable age
    fire_age = _find_fire_age(
        current_age, current_corpus, current_monthly_sip, expected_return, fire_number
    )

    # Year-by-year projection
    monthly_rate = expected_return / 12
    corpus = current_corpus
    year_by_year = []
    for yr in range(1, years_to_retire + 1):
        corpus = _future_value_lumpsum(corpus, 12, monthly_rate) + _future_value_sip(
            current_monthly_sip, 12, monthly_rate
        )
        inflated_annual_expense = monthly_expenses * 12 * (1 + inflation_rate) ** yr
        progress = min((corpus / fire_number) * 100, 100) if fire_number > 0 else 100

        year_by_year.append(
            {
                "year": yr,
                "age": current_age + yr,
                "corpus": round(corpus, 2),
                "fire_number_at_year": round(
                    monthly_expenses
                    * 12
                    * (1 + inflation_rate) ** yr
                    * (1 / 0.04),
                    2,
                ),
                "inflated_annual_expenses": round(inflated_annual_expense, 2),
                "progress_percent": round(progress, 2),
            }
        )

    # Summary
    lines = [
        f"═══ FIRE PLAN ═══",
        f"Age: {current_age} → {retirement_age} ({years_to_retire} years)",
        f"Income: {_format_inr(monthly_income)}/mo | Expenses: {_format_inr(monthly_expenses)}/mo | Savings rate: {savings_rate:.1f}%",
        f"Current corpus: {_human_readable(current_corpus)} | Current SIP: {_format_inr(current_monthly_sip)}/mo",
        f"",
        f"FIRE Number (inflation-adjusted): {_human_readable(fire_number)}",
        f"Projected corpus at {retirement_age}: {_human_readable(projected)}",
        f"",
    ]
    if on_track:
        lines.append(f"✅ ON TRACK — Surplus of {_human_readable(gap)}")
    else:
        lines.append(f"⚠️  SHORTFALL of {_human_readable(abs(gap))}")
        lines.append(
            f"Required SIP to bridge gap: {_format_inr(required_sip)}/mo"
        )
        additional = required_sip - current_monthly_sip
        if additional > 0:
            lines.append(
                f"Additional SIP needed: {_format_inr(additional)}/mo"
            )

    if fire_age is not None:
        lines.append(
            f"FIRE achievable age at current SIP: {fire_age}"
        )
    else:
        lines.append(
            f"FIRE not achievable at current SIP within age 100"
        )

    return FIREPlan(
        current_age=current_age,
        retirement_age=retirement_age,
        years_to_retire=years_to_retire,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        savings_rate=round(savings_rate, 2),
        current_corpus=current_corpus,
        current_monthly_sip=current_monthly_sip,
        expected_return=expected_return,
        fire_number=round(fire_number, 2),
        projected_corpus_at_retirement=round(projected, 2),
        gap=round(gap, 2),
        on_track=on_track,
        required_monthly_sip=round(required_sip, 2),
        fire_achievable_age=fire_age,
        year_by_year=year_by_year,
        summary="\n".join(lines),
    )


# ---------------------------------------------------------------------------
# 4. goal_planner — Multi-Goal SIP Planning
# ---------------------------------------------------------------------------

@dataclass
class GoalBreakdown:
    name: str
    target: float
    years: int
    current_savings: float
    gap: float
    required_monthly_sip: float
    suggested_category: str
    suggested_return: float
    reasoning: str


@dataclass
class GoalPlan:
    goals: List[GoalBreakdown]
    total_monthly_sip_needed: float
    summary: str


def _suggest_fund_category(years: int) -> Tuple[str, float, str]:
    """
    Suggest fund category based on investment timeframe (Indian context).

    Returns (category, expected_annual_return, reasoning).
    """
    if years <= 1:
        return (
            "Liquid / Overnight Fund",
            0.065,
            f"{years}yr horizon → Capital safety paramount. Use liquid/overnight funds.",
        )
    elif years <= 3:
        return (
            "Short-Duration Debt / Conservative Hybrid",
            0.08,
            f"{years}yr horizon → Low volatility needed. Short-duration debt or conservative hybrid.",
        )
    elif years <= 5:
        return (
            "Balanced Advantage / Aggressive Hybrid",
            0.10,
            f"{years}yr horizon → Moderate risk. Balanced advantage or aggressive hybrid funds.",
        )
    elif years <= 7:
        return (
            "Large-Cap Equity / Flexi-Cap",
            0.11,
            f"{years}yr horizon → Equity-oriented with stability. Large-cap or flexi-cap funds.",
        )
    elif years <= 15:
        return (
            "Flexi-Cap / Mid-Cap Equity",
            0.12,
            f"{years}yr horizon → Long enough for equity. Flexi-cap or mid-cap for growth.",
        )
    else:
        return (
            "Small-Cap / Mid-Cap Equity",
            0.13,
            f"{years}yr horizon → Very long term. Small/mid-cap for maximum compounding.",
        )


def goal_planner(goals_list: List[Dict]) -> GoalPlan:
    """
    Multi-goal SIP planner.

    Parameters
    ----------
    goals_list : list of dict
        Each dict: {'name': str, 'target': float, 'years': int, 'current': float}

    Returns
    -------
    GoalPlan with per-goal SIP breakdown and fund category suggestions.
    """
    breakdowns: List[GoalBreakdown] = []
    total_sip = 0.0

    for goal in goals_list:
        name = goal["name"]
        target = goal["target"]
        years = goal["years"]
        current = goal.get("current", 0)

        category, expected_return, reasoning = _suggest_fund_category(years)

        # Calculate required monthly SIP
        required_sip = _required_sip_for_target(current, target, years, expected_return)
        required_sip = max(required_sip, 0)

        gap = target - _future_value_lumpsum(
            current, years * 12, expected_return / 12
        )
        gap = max(gap, 0)

        breakdowns.append(
            GoalBreakdown(
                name=name,
                target=target,
                years=years,
                current_savings=current,
                gap=round(gap, 2),
                required_monthly_sip=round(required_sip, 2),
                suggested_category=category,
                suggested_return=expected_return,
                reasoning=reasoning,
            )
        )
        total_sip += required_sip

    # Build summary
    lines = ["═══ GOAL PLANNER ═══", ""]
    for i, g in enumerate(breakdowns, 1):
        lines.append(f"  {i}. {g.name}")
        lines.append(f"     Target: {_human_readable(g.target)} in {g.years} yrs")
        lines.append(f"     Current savings: {_human_readable(g.current_savings)}")
        lines.append(f"     Gap to fund: {_human_readable(g.gap)}")
        lines.append(
            f"     Required SIP: {_format_inr(g.required_monthly_sip)}/mo"
        )
        lines.append(f"     Suggested: {g.suggested_category} (~{g.suggested_return*100:.1f}% return)")
        lines.append(f"     Reason: {g.reasoning}")
        lines.append("")

    lines.append(f"  💰 Total monthly SIP across all goals: {_format_inr(total_sip)}")

    return GoalPlan(
        goals=breakdowns,
        total_monthly_sip_needed=round(total_sip, 2),
        summary="\n".join(lines),
    )


# ---------------------------------------------------------------------------
# 5. compound_savings_impact — Tax Savings Reinvested
# ---------------------------------------------------------------------------

@dataclass
class SavingsImpact:
    annual_savings: float
    monthly_equivalent: float
    years: int
    return_rate: float
    total_invested: float
    final_value: float
    wealth_gain: float
    narrative: str


def compound_savings_impact(
    annual_savings: float,
    years: int,
    return_rate: float = 0.12,
) -> SavingsImpact:
    """
    Show the compounding impact of investing annual tax savings.

    Great for illustrating WealthPilot value proposition:
    "Your ₹51,200 annual tax saving, invested for 20 years at 12% = ₹43,12,000"

    Parameters
    ----------
    annual_savings : float
        Annual savings amount (e.g., tax savings from 80C + NPS).
    years : int
        Investment horizon.
    return_rate : float
        Expected annual return (default 12%).

    Returns
    -------
    SavingsImpact with narrative string.
    """
    monthly_savings = annual_savings / 12
    monthly_rate = return_rate / 12
    months = years * 12

    total_invested = annual_savings * years
    final_value = _future_value_sip(monthly_savings, months, monthly_rate)
    wealth_gain = final_value - total_invested

    narrative = (
        f"Your {_format_inr(annual_savings)} annual tax saving, "
        f"invested as {_format_inr(monthly_savings)}/month SIP "
        f"for {years} years at {return_rate*100:.0f}% = {_human_readable(final_value)}\n"
        f"Total invested: {_human_readable(total_invested)} → "
        f"Wealth created: {_human_readable(final_value)} "
        f"({_human_readable(wealth_gain)} in pure gains!)\n"
        f"That's a {final_value/total_invested:.1f}x multiplier on your tax savings."
    )

    return SavingsImpact(
        annual_savings=annual_savings,
        monthly_equivalent=round(monthly_savings, 2),
        years=years,
        return_rate=return_rate,
        total_invested=round(total_invested, 2),
        final_value=round(final_value, 2),
        wealth_gain=round(wealth_gain, 2),
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def _separator(title: str) -> None:
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}\n")


def test_project_wealth():
    _separator("TEST 1: project_wealth — SIP with 10% Annual Step-Up")

    result = project_wealth(
        monthly_sip=25_000,
        years=20,
        annual_return=0.12,
        step_up_percent=0.10,
    )
    print(result.summary)
    print(f"\nFirst 5 years:")
    print(f"{'Year':>5} {'Monthly SIP':>14} {'Invested':>16} {'Value':>16} {'Gains':>16}")
    print("-" * 70)
    for p in result.year_by_year[:5]:
        print(
            f"{p.year:>5} {_format_inr(p.monthly_sip):>14} "
            f"{_human_readable(p.cumulative_invested):>16} "
            f"{_human_readable(p.value):>16} "
            f"{_human_readable(p.gains):>16}"
        )
    print(f"\nLast 3 years:")
    for p in result.year_by_year[-3:]:
        print(
            f"{p.year:>5} {_format_inr(p.monthly_sip):>14} "
            f"{_human_readable(p.cumulative_invested):>16} "
            f"{_human_readable(p.value):>16} "
            f"{_human_readable(p.gains):>16}"
        )

    # Assertions
    assert result.final_value > result.total_invested, "Final value should exceed invested"
    assert result.wealth_multiplier > 1, "Wealth multiplier should be > 1"
    assert len(result.year_by_year) == 20, "Should have 20 yearly projections"
    assert result.year_by_year[1].monthly_sip > result.year_by_year[0].monthly_sip, \
        "SIP should increase with step-up"

    # Test flat SIP (no step-up)
    flat = project_wealth(monthly_sip=25_000, years=20, step_up_percent=0.0)
    assert flat.total_invested == 25_000 * 12 * 20, "Flat SIP total invested should be exact"
    assert result.final_value > flat.final_value, "Step-up should yield higher corpus"

    print("\n✅ project_wealth tests passed!")


def test_calculate_fire_number():
    _separator("TEST 2: calculate_fire_number — FIRE Corpus Calculation")

    result = calculate_fire_number(
        monthly_expenses=50_000,
        inflation_rate=0.06,
        years_to_retire=25,
    )
    print(result.summary)

    # Manual verification
    expected_monthly = 50_000 * (1.06 ** 25)
    expected_fire = expected_monthly * 12 * 25
    assert abs(result.fire_number - round(expected_fire, 2)) < 1, \
        f"FIRE number mismatch: {result.fire_number} vs {expected_fire}"
    assert result.inflation_adjusted_monthly_expenses > 50_000, \
        "Inflated expenses should be higher"

    # Test with 3% withdrawal rate
    conservative = calculate_fire_number(
        monthly_expenses=50_000, years_to_retire=25, withdrawal_rate=0.03
    )
    assert conservative.fire_number > result.fire_number, \
        "Lower withdrawal rate should need bigger corpus"

    print(f"\n  FIRE Number: {_human_readable(result.fire_number)}")
    print(f"  Inflated monthly expenses: {_format_inr(result.inflation_adjusted_monthly_expenses)}")
    print("\n✅ calculate_fire_number tests passed!")


def test_fire_plan():
    _separator("TEST 3: fire_plan — Comprehensive FIRE Planning")

    plan = fire_plan(
        current_age=28,
        retirement_age=45,
        monthly_income=1_50_000,
        monthly_expenses=60_000,
        current_corpus=5_00_000,
        current_monthly_sip=40_000,
        expected_return=0.12,
        inflation_rate=0.06,
    )
    print(plan.summary)
    print(f"\n  Year-by-year (sample):")
    print(f"  {'Year':>4} {'Age':>4} {'Corpus':>14} {'Progress':>10}")
    print(f"  {'-'*36}")
    for entry in plan.year_by_year[::3]:  # every 3rd year
        print(
            f"  {entry['year']:>4} {entry['age']:>4} "
            f"{_human_readable(entry['corpus']):>14} "
            f"{entry['progress_percent']:>9.1f}%"
        )

    assert plan.years_to_retire == 17, "Years to retire should be 17"
    assert plan.fire_number > 0, "FIRE number should be positive"
    assert plan.projected_corpus_at_retirement > 0, "Projected corpus should be positive"
    assert len(plan.year_by_year) == 17, "Should have 17 yearly entries"
    assert plan.required_monthly_sip >= 0, "Required SIP should be non-negative"

    if plan.fire_achievable_age is not None:
        assert plan.fire_achievable_age >= plan.current_age, "FIRE age should be >= current age"

    # Test with someone already on track (high SIP)
    wealthy_plan = fire_plan(
        current_age=30,
        retirement_age=55,
        monthly_income=3_00_000,
        monthly_expenses=50_000,
        current_corpus=50_00_000,
        current_monthly_sip=1_50_000,
        expected_return=0.12,
    )
    assert wealthy_plan.on_track is True, "High SIP person should be on track"

    print("\n✅ fire_plan tests passed!")


def test_goal_planner():
    _separator("TEST 4: goal_planner — Multi-Goal SIP Planning")

    goals = [
        {"name": "Emergency Fund", "target": 3_60_000, "years": 1, "current": 1_00_000},
        {"name": "Car", "target": 8_00_000, "years": 3, "current": 0},
        {"name": "House Down Payment", "target": 20_00_000, "years": 5, "current": 2_00_000},
        {"name": "Child's Education", "target": 50_00_000, "years": 15, "current": 1_00_000},
        {"name": "Retirement", "target": 3_00_00_000, "years": 30, "current": 2_00_000},
    ]

    result = goal_planner(goals)
    print(result.summary)

    assert len(result.goals) == 5, "Should have 5 goals"
    assert result.total_monthly_sip_needed > 0, "Total SIP should be positive"

    # Verify fund category suggestions
    for g in result.goals:
        if g.years <= 1:
            assert "Liquid" in g.suggested_category, "Short-term should suggest liquid"
        if g.years >= 15:
            assert "Cap" in g.suggested_category, "Long-term should suggest equity"
        assert g.required_monthly_sip >= 0, f"SIP for {g.name} should be non-negative"

    # Test with a goal already achieved (current > target future value)
    easy_goals = [
        {"name": "Already Met", "target": 1_00_000, "years": 5, "current": 2_00_000},
    ]
    easy_result = goal_planner(easy_goals)
    assert easy_result.goals[0].required_monthly_sip == 0, \
        "Already-met goal should need 0 SIP"

    print("\n✅ goal_planner tests passed!")


def test_compound_savings_impact():
    _separator("TEST 5: compound_savings_impact — Tax Savings Reinvested")

    # WealthPilot tax savings scenario
    result = compound_savings_impact(
        annual_savings=51_200,
        years=20,
        return_rate=0.12,
    )
    print(result.narrative)

    assert result.total_invested == 51_200 * 20, "Total invested should be exact"
    assert result.final_value > result.total_invested, "Final should exceed invested"
    assert result.wealth_gain > 0, "Should have positive gains"
    assert result.monthly_equivalent == round(51_200 / 12, 2), "Monthly should be annual/12"

    # Second scenario: higher savings
    result2 = compound_savings_impact(
        annual_savings=1_50_000,  # full 80C
        years=30,
        return_rate=0.12,
    )
    print(f"\n--- Scenario 2: Full 80C ---")
    print(result2.narrative)

    assert result2.final_value > result.final_value, "Longer + higher savings should yield more"

    # Edge case: 0 years
    zero = compound_savings_impact(annual_savings=50_000, years=0)
    assert zero.final_value == 0, "0 years should give 0 value"
    assert zero.total_invested == 0, "0 years should give 0 invested"

    print("\n✅ compound_savings_impact tests passed!")


def test_edge_cases():
    _separator("TEST 6: Edge Cases")

    # Zero SIP
    result = project_wealth(monthly_sip=0, years=10)
    assert result.final_value == 0, "Zero SIP should yield zero"
    assert result.total_invested == 0, "Zero SIP should invest zero"

    # Zero return
    result = project_wealth(monthly_sip=10_000, years=10, annual_return=0.0, step_up_percent=0.0)
    assert abs(result.final_value - 12_00_000) < 1, "Zero return should equal total invested"

    # Very short horizon
    result = project_wealth(monthly_sip=50_000, years=1, annual_return=0.12, step_up_percent=0.0)
    assert len(result.year_by_year) == 1, "1 year should have 1 entry"
    assert result.total_invested == 6_00_000, "1 year, 50k/mo = 6L invested"

    # FIRE number with 0 inflation
    fire = calculate_fire_number(monthly_expenses=50_000, inflation_rate=0.0, years_to_retire=20)
    assert fire.fire_number == 50_000 * 12 * 25, "Zero inflation should be simple 25x"

    # Goal with 0 current savings
    plan = goal_planner([{"name": "Test", "target": 10_00_000, "years": 10, "current": 0}])
    assert plan.goals[0].required_monthly_sip > 0, "Should need positive SIP"

    print("  All edge cases handled correctly.")
    print("\n✅ Edge case tests passed!")


def test_format_helpers():
    _separator("TEST 7: Formatting Helpers")

    assert _format_inr(1_00_000) == "₹1,00,000.00"
    assert _format_inr(50_00_000) == "₹50,00,000.00"
    assert _format_inr(1_23_45_678.90) == "₹1,23,45,678.90"
    assert _format_inr(999) == "₹999.00"
    assert _format_inr(0) == "₹0.00"

    assert "Cr" in _human_readable(1_50_00_000)
    assert "L" in _human_readable(5_50_000)
    assert "K" in _human_readable(75_000)

    print("  _format_inr(1,00,000)    = ", _format_inr(1_00_000))
    print("  _format_inr(50,00,000)   = ", _format_inr(50_00_000))
    print("  _human_readable(1.5 Cr)  = ", _human_readable(1_50_00_000))
    print("  _human_readable(5.5 L)   = ", _human_readable(5_50_000))
    print("  _human_readable(75 K)    = ", _human_readable(75_000))

    print("\n✅ Format helper tests passed!")


def run_all_tests():
    """Run all test cases."""
    print("\n" + "█" * 70)
    print("  PROJECTIONS.PY — COMPREHENSIVE TEST SUITE")
    print("█" * 70)

    test_project_wealth()
    test_calculate_fire_number()
    test_fire_plan()
    test_goal_planner()
    test_compound_savings_impact()
    test_edge_cases()
    test_format_helpers()

    print("\n" + "█" * 70)
    print("  🎉 ALL TESTS PASSED!")
    print("█" * 70 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_all_tests()