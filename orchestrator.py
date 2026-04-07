"""
WealthPilot Orchestrator
========================
LangGraph-based multi-agent orchestration for comprehensive financial planning.

Flow:
    intake → document_parser (conditional) → data_validator →
    [tax_analyzer, health_scorer, portfolio_analyzer] (parallel) →
    goal_planner → report_generator → END
"""

import logging
import traceback
from typing import TypedDict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("wealthpilot.orchestrator")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    _console = logging.StreamHandler()
    _console.setLevel(logging.INFO)
    _fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _console.setFormatter(_fmt)
    logger.addHandler(_console)

    _file = logging.FileHandler("wealthpilot_orchestrator.log")
    _file.setLevel(logging.DEBUG)
    _file.setFormatter(_fmt)
    logger.addHandler(_file)


# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------
class WealthPilotState(TypedDict):
    """Typed state dictionary threaded through every node in the graph."""
    user_inputs: dict
    uploaded_files: list
    parsed_documents: dict
    validation_result: dict
    financial_profile: dict
    tax_analysis: dict
    health_score: dict
    portfolio_analysis: dict
    goal_plan: dict
    report: dict
    errors: list
    current_step: str


def _make_initial_state(
    user_data: dict | None = None,
    uploaded_files: list | None = None,
) -> WealthPilotState:
    """Return a blank state populated with the caller-supplied inputs."""
    return WealthPilotState(
        user_inputs=user_data or {},
        uploaded_files=uploaded_files or [],
        parsed_documents={},
        validation_result={},
        financial_profile={},
        tax_analysis={},
        health_score={},
        portfolio_analysis={},
        goal_plan={},
        report={},
        errors=[],
        current_step="initialized",
    )


# ---------------------------------------------------------------------------
# Helper: safe error recording
# ---------------------------------------------------------------------------
def _record_error(state: WealthPilotState, step: str, exc: Exception) -> None:
    """Append a structured error entry — never raises."""
    entry = {
        "step": step,
        "error_type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
        "timestamp": datetime.utcnow().isoformat(),
    }
    state["errors"].append(entry)
    logger.error("Step '%s' failed: %s — %s", step, type(exc).__name__, exc)


# ═══════════════════════════════════════════════════════════════════════════
# NODE 1 — Intake
# ═══════════════════════════════════════════════════════════════════════════
def intake_node(state: WealthPilotState) -> WealthPilotState:
    """
    Process raw user inputs and build a normalised UserProfile dict.

    Responsibilities:
      • Validate that mandatory top-level keys exist.
      • Normalise monetary values to float.
      • Build a *financial_profile* dict used downstream.
    """
    step = "intake"
    logger.info("▶ [%s] Processing user inputs …", step)
    state["current_step"] = step

    try:
        raw = state["user_inputs"]

        # ---- Mandatory field check ----------------------------------------
        required_keys = ["name", "age", "annual_income"]
        missing = [k for k in required_keys if k not in raw]
        if missing:
            raise ValueError(f"Missing required input fields: {missing}")

        # ---- Build financial profile --------------------------------------
        profile: dict[str, Any] = {
            "name": str(raw["name"]).strip(),
            "age": int(raw["age"]),
            "annual_income": float(raw.get("annual_income", 0)),
            "monthly_expenses": float(raw.get("monthly_expenses", 0)),
            "existing_investments": raw.get("existing_investments", {}),
            "liabilities": raw.get("liabilities", {}),
            "goals": raw.get("goals", []),
            "risk_tolerance": raw.get("risk_tolerance", "moderate"),
            "tax_regime_preference": raw.get("tax_regime_preference", "auto"),
            "dependents": int(raw.get("dependents", 0)),
            "retirement_age": int(raw.get("retirement_age", 60)),
            "city_tier": raw.get("city_tier", "tier1"),
            "health_insurance": raw.get("health_insurance", {}),
            "emergency_fund": float(raw.get("emergency_fund", 0)),
            "created_at": datetime.utcnow().isoformat(),
        }

        state["financial_profile"] = profile
        logger.info(
            "  ✓ UserProfile created for '%s', age %d, income ₹%,.0f",
            profile["name"],
            profile["age"],
            profile["annual_income"],
        )

    except Exception as exc:
        _record_error(state, step, exc)
        # Build a minimal profile so downstream nodes don't crash
        state["financial_profile"] = state.get("financial_profile") or {
            "name": state["user_inputs"].get("name", "Unknown"),
            "age": 0,
            "annual_income": 0,
        }

    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 2 — Document Parser
# ═══════════════════════════════════════════════════════════════════════════
def document_parser_node(state: WealthPilotState) -> WealthPilotState:
    """
    Parse uploaded PDFs (Form-16, CAS statements, salary slips, etc.)
    and merge extracted data into *parsed_documents*.

    On failure → sets a flag and continues; manual data is used instead.
    """
    step = "document_parser"
    logger.info("▶ [%s] Parsing %d uploaded file(s) …", step, len(state["uploaded_files"]))
    state["current_step"] = step

    parsed: dict[str, Any] = {
        "form16": {},
        "cas_statement": {},
        "salary_slips": [],
        "other": [],
        "parser_success": True,
        "files_processed": 0,
        "files_failed": 0,
    }

    for file_info in state["uploaded_files"]:
        file_name = file_info.get("name", "unknown") if isinstance(file_info, dict) else str(file_info)
        try:
            logger.debug("  Parsing file: %s", file_name)

            # ------------------------------------------------------------------
            # In production, delegate to a real parser:
            #   from document_parser import parse_pdf
            #   result = parse_pdf(file_info)
            # ------------------------------------------------------------------
            # Simulated parsing logic for scaffolding:
            file_type = _classify_document(file_name)

            if file_type == "form16":
                parsed["form16"] = _parse_form16(file_info)
            elif file_type == "cas_statement":
                parsed["cas_statement"] = _parse_cas(file_info)
            elif file_type == "salary_slip":
                parsed["salary_slips"].append(_parse_salary_slip(file_info))
            else:
                parsed["other"].append({"file": file_name, "type": file_type})

            parsed["files_processed"] += 1
            logger.info("  ✓ Parsed '%s' as %s", file_name, file_type)

        except Exception as exc:
            _record_error(state, f"{step}/{file_name}", exc)
            parsed["files_failed"] += 1

    if parsed["files_failed"] > 0 and parsed["files_processed"] == 0:
        parsed["parser_success"] = False
        logger.warning("  ⚠ All files failed to parse — falling back to manual data")

    state["parsed_documents"] = parsed
    return state


# Stub helpers for document classification (replace with real implementations)
def _classify_document(filename: str) -> str:
    lower = filename.lower() if isinstance(filename, str) else ""
    if "form16" in lower or "form-16" in lower:
        return "form16"
    if "cas" in lower or "consolidated" in lower:
        return "cas_statement"
    if "salary" in lower or "payslip" in lower:
        return "salary_slip"
    return "other"


def _parse_form16(file_info: Any) -> dict:
    """Stub — replace with actual Form-16 parser."""
    return {
        "gross_salary": 0,
        "deductions_16": 0,
        "tax_paid": 0,
        "parsed": True,
    }


def _parse_cas(file_info: Any) -> dict:
    """Stub — replace with actual CAS parser."""
    return {"funds": [], "total_value": 0, "parsed": True}


def _parse_salary_slip(file_info: Any) -> dict:
    """Stub — replace with actual salary-slip parser."""
    return {"month": "", "gross": 0, "net": 0, "parsed": True}


# ═══════════════════════════════════════════════════════════════════════════
# NODE 3 — Data Validator
# ═══════════════════════════════════════════════════════════════════════════
def data_validator_node(state: WealthPilotState) -> WealthPilotState:
    """
    Cross-validate the financial profile against parsed documents and
    flag inconsistencies.

    Produces *validation_result* with an overall `is_valid` boolean,
    a list of `warnings`, and a list of `corrections` applied.
    """
    step = "data_validator"
    logger.info("▶ [%s] Validating consolidated data …", step)
    state["current_step"] = step

    result: dict[str, Any] = {
        "is_valid": True,
        "warnings": [],
        "corrections": [],
        "validated_at": datetime.utcnow().isoformat(),
    }

    try:
        profile = state["financial_profile"]
        parsed = state["parsed_documents"]

        # ---- Age sanity check ---------------------------------------------
        age = profile.get("age", 0)
        if not (18 <= age <= 100):
            result["warnings"].append(f"Age {age} is outside expected range (18-100)")
            result["is_valid"] = False

        # ---- Income sanity check ------------------------------------------
        income = profile.get("annual_income", 0)
        if income <= 0:
            result["warnings"].append("Annual income is zero or negative")
            result["is_valid"] = False

        # ---- Cross-check Form-16 with reported income --------------------
        form16_income = parsed.get("form16", {}).get("gross_salary", 0)
        if form16_income and income:
            diff_pct = abs(form16_income - income) / income * 100
            if diff_pct > 10:
                result["warnings"].append(
                    f"Form-16 gross (₹{form16_income:,.0f}) differs from "
                    f"reported income (₹{income:,.0f}) by {diff_pct:.1f}%"
                )
                # Auto-correct to the higher (more conservative) value
                corrected = max(form16_income, income)
                profile["annual_income"] = corrected
                result["corrections"].append(
                    f"annual_income adjusted to ₹{corrected:,.0f} (Form-16 override)"
                )

        # ---- Expense ratio check ------------------------------------------
        expenses = profile.get("monthly_expenses", 0) * 12
        if income > 0 and expenses > income:
            result["warnings"].append(
                "Annual expenses exceed annual income — please verify"
            )

        # ---- Emergency fund check -----------------------------------------
        monthly_exp = profile.get("monthly_expenses", 0)
        ef = profile.get("emergency_fund", 0)
        if monthly_exp > 0 and ef < monthly_exp * 3:
            result["warnings"].append(
                f"Emergency fund (₹{ef:,.0f}) is below 3-month expenses "
                f"(₹{monthly_exp * 3:,.0f})"
            )

        if result["warnings"]:
            logger.warning("  ⚠ %d validation warning(s):", len(result["warnings"]))
            for w in result["warnings"]:
                logger.warning("    • %s", w)
        else:
            logger.info("  ✓ All validations passed")

    except Exception as exc:
        _record_error(state, step, exc)
        result["is_valid"] = False
        result["warnings"].append(f"Validation itself failed: {exc}")

    state["validation_result"] = result
    state["financial_profile"] = state["financial_profile"]  # may have been corrected
    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 4a — Tax Analyzer  (runs in parallel branch)
# ═══════════════════════════════════════════════════════════════════════════
def tax_analyzer_node(state: WealthPilotState) -> WealthPilotState:
    """
    Compare old vs. new tax regime and produce an optimal recommendation.
    Delegates heavy lifting to tax_engine.py.
    """
    step = "tax_analyzer"
    logger.info("▶ [%s] Running tax regime comparison …", step)
    state["current_step"] = step

    try:
        profile = state["financial_profile"]

        # ------------------------------------------------------------------
        # Production call:
        #   from tax_engine import compare_regimes, suggest_deductions
        #   tax_result = compare_regimes(profile)
        #   suggestions = suggest_deductions(profile)
        # ------------------------------------------------------------------

        income = profile.get("annual_income", 0)
        deductions = profile.get("existing_investments", {})

        # Simulated old-regime calculation
        total_deductions_old = sum(
            float(v) for v in deductions.values() if isinstance(v, (int, float))
        )
        taxable_old = max(0, income - total_deductions_old - 50_000)  # std deduction
        tax_old = _slab_tax_old(taxable_old)

        # Simulated new-regime calculation
        taxable_new = max(0, income - 75_000)  # new regime std deduction (FY 2024-25)
        tax_new = _slab_tax_new(taxable_new)

        recommended = "old" if tax_old < tax_new else "new"
        savings = abs(tax_old - tax_new)

        analysis: dict[str, Any] = {
            "old_regime": {
                "taxable_income": taxable_old,
                "tax_liability": tax_old,
                "deductions_claimed": total_deductions_old,
            },
            "new_regime": {
                "taxable_income": taxable_new,
                "tax_liability": tax_new,
            },
            "recommended_regime": recommended,
            "potential_savings": savings,
            "additional_deduction_suggestions": _suggest_deductions(profile),
            "computed_at": datetime.utcnow().isoformat(),
        }

        state["tax_analysis"] = analysis
        logger.info(
            "  ✓ Recommended regime: %s | Savings: ₹%,.0f",
            recommended.upper(),
            savings,
        )

    except Exception as exc:
        _record_error(state, step, exc)
        state["tax_analysis"] = {
            "error": str(exc),
            "recommended_regime": "unable_to_compute",
            "computed_at": datetime.utcnow().isoformat(),
        }

    return state


def _slab_tax_old(taxable: float) -> float:
    """Simplified old-regime slab calc."""
    if taxable <= 250_000:
        return 0
    tax = 0.0
    slabs = [
        (250_000, 500_000, 0.05),
        (500_000, 1_000_000, 0.20),
        (1_000_000, float("inf"), 0.30),
    ]
    for lower, upper, rate in slabs:
        if taxable > lower:
            tax += (min(taxable, upper) - lower) * rate
    return round(tax)


def _slab_tax_new(taxable: float) -> float:
    """Simplified new-regime slab calc (FY 2024-25 Budget)."""
    if taxable <= 300_000:
        return 0
    tax = 0.0
    slabs = [
        (300_000, 700_000, 0.05),
        (700_000, 1_000_000, 0.10),
        (1_000_000, 1_200_000, 0.15),
        (1_200_000, 1_500_000, 0.20),
        (1_500_000, float("inf"), 0.30),
    ]
    for lower, upper, rate in slabs:
        if taxable > lower:
            tax += (min(taxable, upper) - lower) * rate
    return round(tax)


def _suggest_deductions(profile: dict) -> list[str]:
    """Simple rule-based suggestion engine."""
    suggestions: list[str] = []
    inv = profile.get("existing_investments", {})
    if float(inv.get("section_80c", 0)) < 150_000:
        suggestions.append("Maximize Section 80C (ELSS/PPF/NPS) — up to ₹1,50,000")
    if not profile.get("health_insurance"):
        suggestions.append("Consider health insurance — Section 80D deduction up to ₹25,000")
    if float(inv.get("nps_80ccd", 0)) == 0:
        suggestions.append("NPS additional deduction under 80CCD(1B) — up to ₹50,000")
    return suggestions


# ═══════════════════════════════════════════════════════════════════════════
# NODE 4b — Health Scorer  (runs in parallel branch)
# ═══════════════════════════════════════════════════════════════════════════
def health_scorer_node(state: WealthPilotState) -> WealthPilotState:
    """
    Calculate a 0-100 financial-health score across multiple dimensions.
    Delegates to health_scorer.py.
    """
    step = "health_scorer"
    logger.info("▶ [%s] Computing financial health score …", step)
    state["current_step"] = step

    try:
        profile = state["financial_profile"]

        # ------------------------------------------------------------------
        # Production call:
        #   from health_scorer import compute_health_score
        #   score_result = compute_health_score(profile)
        # ------------------------------------------------------------------

        income = profile.get("annual_income", 0)
        monthly_exp = profile.get("monthly_expenses", 0)
        ef = profile.get("emergency_fund", 0)
        liabilities = profile.get("liabilities", {})
        total_debt = sum(
            float(v) for v in liabilities.values() if isinstance(v, (int, float))
        )

        # Sub-scores (each 0-100)
        savings_rate = (
            max(0, (income - monthly_exp * 12) / income * 100) if income else 0
        )
        savings_score = min(100, savings_rate * 2)  # 50% savings → 100

        ef_months = ef / monthly_exp if monthly_exp else 0
        ef_score = min(100, ef_months / 6 * 100)  # 6 months → 100

        dti = total_debt / income * 100 if income else 100
        debt_score = max(0, 100 - dti * 2.5)  # 40% DTI → 0

        insurance_score = 100 if profile.get("health_insurance") else 20

        inv = profile.get("existing_investments", {})
        investment_total = sum(
            float(v) for v in inv.values() if isinstance(v, (int, float))
        )
        inv_ratio = investment_total / income if income else 0
        investment_score = min(100, inv_ratio * 100)  # 1x income invested → 100

        # Weighted aggregate
        weights = {
            "savings_rate": 0.25,
            "emergency_fund": 0.20,
            "debt_management": 0.20,
            "insurance_coverage": 0.15,
            "investment_discipline": 0.20,
        }
        sub_scores = {
            "savings_rate": round(savings_score, 1),
            "emergency_fund": round(ef_score, 1),
            "debt_management": round(debt_score, 1),
            "insurance_coverage": round(insurance_score, 1),
            "investment_discipline": round(investment_score, 1),
        }
        overall = round(
            sum(sub_scores[k] * weights[k] for k in weights), 1
        )

        # Rating
        if overall >= 80:
            rating = "Excellent"
        elif overall >= 60:
            rating = "Good"
        elif overall >= 40:
            rating = "Needs Improvement"
        else:
            rating = "Critical"

        recommendations: list[str] = []
        if sub_scores["emergency_fund"] < 60:
            recommendations.append(
                f"Build emergency fund to at least 6 months' expenses "
                f"(₹{monthly_exp * 6:,.0f})"
            )
        if sub_scores["debt_management"] < 50:
            recommendations.append("Prioritize high-interest debt repayment")
        if sub_scores["insurance_coverage"] < 50:
            recommendations.append(
                "Get adequate health and term-life insurance"
            )
        if sub_scores["savings_rate"] < 50:
            recommendations.append("Aim to save at least 30% of income")

        state["health_score"] = {
            "overall_score": overall,
            "rating": rating,
            "sub_scores": sub_scores,
            "weights": weights,
            "recommendations": recommendations,
            "computed_at": datetime.utcnow().isoformat(),
        }
        logger.info("  ✓ Health score: %.1f / 100 (%s)", overall, rating)

    except Exception as exc:
        _record_error(state, step, exc)
        state["health_score"] = {
            "overall_score": 0,
            "rating": "Error",
            "error": str(exc),
            "computed_at": datetime.utcnow().isoformat(),
        }

    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 4c — Portfolio Analyzer  (runs in parallel branch)
# ═══════════════════════════════════════════════════════════════════════════
def portfolio_analyzer_node(state: WealthPilotState) -> WealthPilotState:
    """
    Analyze mutual-fund portfolio for overlap, allocation, and performance.
    Delegates to portfolio_analyzer.py.
    """
    step = "portfolio_analyzer"
    logger.info("▶ [%s] Analyzing investment portfolio …", step)
    state["current_step"] = step

    try:
        profile = state["financial_profile"]
        cas_data = state["parsed_documents"].get("cas_statement", {})

        # ------------------------------------------------------------------
        # Production call:
        #   from portfolio_analyzer import analyze_portfolio
        #   result = analyze_portfolio(profile, cas_data)
        # ------------------------------------------------------------------

        funds = cas_data.get("funds", [])
        investments = profile.get("existing_investments", {})

        total_value = sum(
            float(v) for v in investments.values() if isinstance(v, (int, float))
        )

        # Simulated allocation breakdown
        allocation = {
            "equity": round(total_value * 0.60, 2),
            "debt": round(total_value * 0.25, 2),
            "gold": round(total_value * 0.10, 2),
            "cash": round(total_value * 0.05, 2),
        }

        # Risk-based target allocation
        risk = profile.get("risk_tolerance", "moderate")
        target_allocations = {
            "aggressive": {"equity": 0.80, "debt": 0.10, "gold": 0.05, "cash": 0.05},
            "moderate": {"equity": 0.60, "debt": 0.25, "gold": 0.10, "cash": 0.05},
            "conservative": {"equity": 0.35, "debt": 0.45, "gold": 0.10, "cash": 0.10},
        }
        target = target_allocations.get(risk, target_allocations["moderate"])

        rebalancing_suggestions: list[str] = []
        for asset, target_pct in target.items():
            current_pct = allocation.get(asset, 0) / total_value if total_value else 0
            diff = current_pct - target_pct
            if abs(diff) > 0.05:
                direction = "Reduce" if diff > 0 else "Increase"
                rebalancing_suggestions.append(
                    f"{direction} {asset} by {abs(diff) * 100:.1f}pp "
                    f"(current {current_pct * 100:.1f}% → target {target_pct * 100:.1f}%)"
                )

        state["portfolio_analysis"] = {
            "total_portfolio_value": total_value,
            "current_allocation": allocation,
            "target_allocation": {k: v * total_value for k, v in target.items()},
            "risk_profile": risk,
            "num_funds_analyzed": len(funds),
            "overlap_warnings": [],  # populated by real analyzer
            "expense_ratio_avg": 0.0,  # populated by real analyzer
            "rebalancing_suggestions": rebalancing_suggestions,
            "computed_at": datetime.utcnow().isoformat(),
        }
        logger.info(
            "  ✓ Portfolio: ₹%,.0f across %d funds | %d rebalancing tip(s)",
            total_value,
            len(funds),
            len(rebalancing_suggestions),
        )

    except Exception as exc:
        _record_error(state, step, exc)
        state["portfolio_analysis"] = {
            "error": str(exc),
            "total_portfolio_value": 0,
            "computed_at": datetime.utcnow().isoformat(),
        }

    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 5 — Goal Planner
# ═══════════════════════════════════════════════════════════════════════════
def goal_planner_node(state: WealthPilotState) -> WealthPilotState:
    """
    Create FIRE / goal-based financial projections.
    Delegates to projections.py.
    """
    step = "goal_planner"
    logger.info("▶ [%s] Creating goal-based financial plan …", step)
    state["current_step"] = step

    try:
        profile = state["financial_profile"]
        tax = state.get("tax_analysis", {})
        health = state.get("health_score", {})
        portfolio = state.get("portfolio_analysis", {})

        # ------------------------------------------------------------------
        # Production call:
        #   from projections import project_goals, fire_calculator
        #   goals = project_goals(profile, tax, portfolio)
        #   fire = fire_calculator(profile)
        # ------------------------------------------------------------------

        income = profile.get("annual_income", 0)
        expenses = profile.get("monthly_expenses", 0) * 12
        age = profile.get("age", 30)
        retire_age = profile.get("retirement_age", 60)
        years_to_retire = max(0, retire_age - age)

        annual_savings = income - expenses
        savings_rate = annual_savings / income if income else 0

        # FIRE number (25× annual expenses, inflation-adjusted)
        inflation_rate = 0.06
        expected_return = 0.10
        real_return = (1 + expected_return) / (1 + inflation_rate) - 1

        future_annual_expenses = expenses * ((1 + inflation_rate) ** years_to_retire)
        fire_number = future_annual_expenses * 25

        # Projected corpus at retirement (simple FV of annual savings)
        existing_corpus = portfolio.get("total_portfolio_value", 0)
        projected_corpus = existing_corpus * ((1 + real_return) ** years_to_retire)
        if real_return > 0:
            projected_corpus += annual_savings * (
                ((1 + real_return) ** years_to_retire - 1) / real_return
            )
        else:
            projected_corpus += annual_savings * years_to_retire

        fire_achievable = projected_corpus >= fire_number
        gap = max(0, fire_number - projected_corpus)

        # Per-goal breakdown
        goal_details: list[dict] = []
        for g in profile.get("goals", []):
            goal_name = g.get("name", "Unnamed")
            target = float(g.get("target_amount", 0))
            timeline = int(g.get("years", 5))
            future_target = target * ((1 + inflation_rate) ** timeline)

            monthly_sip = (
                future_target
                * (real_return / 12)
                / (((1 + real_return / 12) ** (timeline * 12)) - 1)
                if real_return > 0 and timeline > 0
                else future_target / max(timeline * 12, 1)
            )

            goal_details.append({
                "name": goal_name,
                "target_today": target,
                "target_inflation_adjusted": round(future_target),
                "timeline_years": timeline,
                "monthly_sip_required": round(monthly_sip),
                "feasible": monthly_sip * 12 <= annual_savings * 0.5,
            })

        state["goal_plan"] = {
            "fire": {
                "fire_number": round(fire_number),
                "projected_corpus": round(projected_corpus),
                "gap": round(gap),
                "achievable": fire_achievable,
                "years_to_retirement": years_to_retire,
                "additional_monthly_investment_needed": round(
                    gap
                    * (real_return / 12)
                    / (((1 + real_return / 12) ** (years_to_retire * 12)) - 1)
                )
                if gap > 0 and years_to_retire > 0 and real_return > 0
                else 0,
            },
            "goals": goal_details,
            "assumptions": {
                "inflation_rate": inflation_rate,
                "expected_return": expected_return,
                "real_return": round(real_return, 4),
            },
            "savings_rate": round(savings_rate * 100, 1),
            "computed_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            "  ✓ FIRE number: ₹%,.0f | Projected corpus: ₹%,.0f | %s",
            fire_number,
            projected_corpus,
            "ON TRACK ✅" if fire_achievable else f"GAP ₹{gap:,.0f} ❌",
        )

    except Exception as exc:
        _record_error(state, step, exc)
        state["goal_plan"] = {
            "error": str(exc),
            "fire": {"achievable": False},
            "goals": [],
            "computed_at": datetime.utcnow().isoformat(),
        }

    return state


# ═══════════════════════════════════════════════════════════════════════════
# NODE 6 — Report Generator
# ═══════════════════════════════════════════════════════════════════════════
def report_generator_node(state: WealthPilotState) -> WealthPilotState:
    """
    Compile all analyses into a single structured report.
    Marks sections as 'unavailable' if their upstream node failed.
    """
    step = "report_generator"
    logger.info("▶ [%s] Compiling final WealthPilot report …", step)
    state["current_step"] = step

    try:
        profile = state["financial_profile"]

        # Determine section availability
        def _section_status(data: dict, key: str = "error") -> str:
            if not data:
                return "not_computed"
            if key in data:
                return "partial"
            return "complete"

        report: dict[str, Any] = {
            "title": f"WealthPilot Financial Report — {profile.get('name', 'N/A')}",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "health_score": state["health_score"].get("overall_score", "N/A"),
                "health_rating": state["health_score"].get("rating", "N/A"),
                "recommended_tax_regime": state["tax_analysis"].get(
                    "recommended_regime", "N/A"
                ),
                "tax_savings": state["tax_analysis"].get("potential_savings", "N/A"),
                "fire_achievable": (
                    state["goal_plan"].get("fire", {}).get("achievable", "N/A")
                ),
                "portfolio_value": state["portfolio_analysis"].get(
                    "total_portfolio_value", "N/A"
                ),
            },
            "sections": {
                "profile": {
                    "status": "complete",
                    "data": profile,
                },
                "validation": {
                    "status": _section_status(state["validation_result"]),
                    "data": state["validation_result"],
                },
                "tax_analysis": {
                    "status": _section_status(state["tax_analysis"]),
                    "data": state["tax_analysis"],
                },
                "health_score": {
                    "status": _section_status(state["health_score"]),
                    "data": state["health_score"],
                },
                "portfolio_analysis": {
                    "status": _section_status(state["portfolio_analysis"]),
                    "data": state["portfolio_analysis"],
                },
                "goal_plan": {
                    "status": _section_status(state["goal_plan"]),
                    "data": state["goal_plan"],
                },
            },
            "action_items": _compile_action_items(state),
            "errors_encountered": len(state["errors"]),
            "error_details": state["errors"],
        }

        state["report"] = report
        state["current_step"] = "completed"

        complete_sections = sum(
            1 for s in report["sections"].values() if s["status"] == "complete"
        )
        total_sections = len(report["sections"])
        logger.info(
            "  ✓ Report generated — %d/%d sections complete | %d action items | %d errors",
            complete_sections,
            total_sections,
            len(report["action_items"]),
            len(state["errors"]),
        )

    except Exception as exc:
        _record_error(state, step, exc)
        state["report"] = {
            "title": "WealthPilot Report (Partial)",
            "error": str(exc),
            "generated_at": datetime.utcnow().isoformat(),
            "raw_state_keys": list(state.keys()),
        }
        state["current_step"] = "completed_with_errors"

    return state


def _compile_action_items(state: WealthPilotState) -> list[dict]:
    """Aggregate all recommended actions from every node's output."""
    items: list[dict] = []
    priority = 0

    # Health score recommendations
    for rec in state.get("health_score", {}).get("recommendations", []):
        priority += 1
        items.append({"priority": priority, "category": "health", "action": rec})

    # Tax suggestions
    for sug in state.get("tax_analysis", {}).get(
        "additional_deduction_suggestions", []
    ):
        priority += 1
        items.append({"priority": priority, "category": "tax", "action": sug})

    # Rebalancing
    for rb in state.get("portfolio_analysis", {}).get(
        "rebalancing_suggestions", []
    ):
        priority += 1
        items.append({"priority": priority, "category": "portfolio", "action": rb})

    # FIRE gap
    fire = state.get("goal_plan", {}).get("fire", {})
    if fire.get("gap", 0) > 0:
        monthly = fire.get("additional_monthly_investment_needed", 0)
        items.insert(
            0,
            {
                "priority": 0,
                "category": "retirement",
                "action": (
                    f"Increase monthly investments by ₹{monthly:,.0f} to "
                    f"bridge the FIRE gap of ₹{fire['gap']:,.0f}"
                ),
            },
        )

    # Re-number
    for i, item in enumerate(items, 1):
        item["priority"] = i

    return items


# ═══════════════════════════════════════════════════════════════════════════
# ROUTING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════
def should_parse_documents(state: WealthPilotState) -> str:
    """
    Conditional edge after intake:
    → 'parse'       if uploaded files exist
    → 'skip_parse'  otherwise
    """
    if state.get("uploaded_files"):
        logger.info("  ↳ Files detected — routing to document_parser")
        return "parse"
    logger.info("  ↳ No files uploaded — skipping document parser")
    return "skip_parse"


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ═══════════════════════════════════════════════════════════════════════════
def build_graph() -> StateGraph:
    """
    Construct the WealthPilot LangGraph workflow.

    Topology:
        intake ─┬─ (files?) ── document_parser ──┐
                └─ (no files) ───────────────────┤
                                                  ▼
                                          data_validator
                                                  │
                            ┌─────────────────────┼─────────────────────┐
                            ▼                     ▼                     ▼
                     tax_analyzer          health_scorer        portfolio_analyzer
                            └─────────────────────┼─────────────────────┘
                                                  ▼
                                           goal_planner
                                                  ▼
                                         report_generator
                                                  ▼
                                                 END
    """
    graph = StateGraph(WealthPilotState)

    # ---- Add nodes --------------------------------------------------------
    graph.add_node("intake", intake_node)
    graph.add_node("document_parser", document_parser_node)
    graph.add_node("data_validator", data_validator_node)
    graph.add_node("tax_analyzer", tax_analyzer_node)
    graph.add_node("health_scorer", health_scorer_node)
    graph.add_node("portfolio_analyzer", portfolio_analyzer_node)
    graph.add_node("goal_planner", goal_planner_node)
    graph.add_node("report_generator", report_generator_node)

    # ---- Entry point ------------------------------------------------------
    graph.set_entry_point("intake")

    # ---- Conditional edge: intake → parse / skip --------------------------
    graph.add_conditional_edges(
        "intake",
        should_parse_documents,
        {
            "parse": "document_parser",
            "skip_parse": "data_validator",
        },
    )

    # ---- document_parser → data_validator ---------------------------------
    graph.add_edge("document_parser", "data_validator")

    # ---- Parallel fan-out: data_validator → 3 analyzers -------------------
    #   LangGraph executes all targets of multiple edges from the same node
    #   concurrently when using the async runner or ThreadPoolExecutor.
    graph.add_edge("data_validator", "tax_analyzer")
    graph.add_edge("data_validator", "health_scorer")
    graph.add_edge("data_validator", "portfolio_analyzer")

    # ---- Fan-in: 3 analyzers → goal_planner ------------------------------
    graph.add_edge("tax_analyzer", "goal_planner")
    graph.add_edge("health_scorer", "goal_planner")
    graph.add_edge("portfolio_analyzer", "goal_planner")

    # ---- Sequential tail: goal_planner → report → END --------------------
    graph.add_edge("goal_planner", "report_generator")
    graph.add_edge("report_generator", END)

    return graph


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════
def run_analysis(
    user_data: dict,
    uploaded_files: list | None = None,
) -> dict:
    """
    Main entry point for WealthPilot analysis.

    Parameters
    ----------
    user_data : dict
        User-supplied financial information.  Must include at minimum:
        ``name``, ``age``, ``annual_income``.
    uploaded_files : list, optional
        List of file descriptors (dicts with ``name``, ``path``, ``content``
        keys or plain filename strings).

    Returns
    -------
    dict
        The final ``report`` dict from the state.  Contains a full
        breakdown of all analyses, action items, and any errors.

    Examples
    --------
    >>> result = run_analysis(
    ...     user_data={
    ...         "name": "Arjun Mehta",
    ...         "age": 32,
    ...         "annual_income": 2_400_000,
    ...         "monthly_expenses": 80_000,
    ...         "emergency_fund": 300_000,
    ...         "risk_tolerance": "moderate",
    ...         "retirement_age": 55,
    ...         "existing_investments": {
    ...             "section_80c": 120_000,
    ...             "equity_mf": 800_000,
    ...             "ppf": 200_000,
    ...         },
    ...         "goals": [
    ...             {"name": "Child Education", "target_amount": 5_000_000, "years": 15},
    ...             {"name": "House Down-payment", "target_amount": 3_000_000, "years": 5},
    ...         ],
    ...     },
    ...     uploaded_files=[{"name": "Form16_2024.pdf", "path": "/tmp/f16.pdf"}],
    ... )
    >>> print(result["summary"]["health_rating"])
    """
    logger.info("=" * 72)
    logger.info("WealthPilot Analysis — START")
    logger.info("=" * 72)

    initial_state = _make_initial_state(user_data, uploaded_files or [])

    # Build and compile the graph
    workflow = build_graph()
    app = workflow.compile()

    # Execute
    try:
        final_state = app.invoke(initial_state)
    except Exception as exc:
        # Ultimate safety net — should never happen given per-node handling,
        # but guarantees we *always* return something.
        logger.critical("Graph execution failed catastrophically: %s", exc)
        return {
            "title": "WealthPilot Report (Critical Failure)",
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "generated_at": datetime.utcnow().isoformat(),
        }

    report = final_state.get("report", {})

    logger.info("=" * 72)
    logger.info(
        "WealthPilot Analysis — COMPLETE  |  Errors: %d",
        len(final_state.get("errors", [])),
    )
    logger.info("=" * 72)

    return report


# ═══════════════════════════════════════════════════════════════════════════
# CLI / Quick Test
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    sample_user = {
        "name": "Priya Sharma",
        "age": 34,
        "annual_income": 1_800_000,
        "monthly_expenses": 65_000,
        "emergency_fund": 200_000,
        "risk_tolerance": "moderate",
        "retirement_age": 55,
        "dependents": 1,
        "city_tier": "tier1",
        "tax_regime_preference": "auto",
        "health_insurance": {"sum_insured": 1_000_000, "premium": 15_000},
        "existing_investments": {
            "section_80c": 100_000,
            "equity_mf": 500_000,
            "ppf": 300_000,
            "nps_80ccd": 0,
            "fd": 200_000,
        },
        "liabilities": {
            "home_loan": 3_000_000,
            "car_loan": 400_000,
        },
        "goals": [
            {"name": "Child Higher Education", "target_amount": 5_000_000, "years": 14},
            {"name": "Dream Vacation", "target_amount": 500_000, "years": 3},
            {"name": "Retirement Corpus", "target_amount": 30_000_000, "years": 21},
        ],
    }

    sample_files = [
        {"name": "Form16_FY2024.pdf", "path": "/uploads/form16.pdf"},
        {"name": "CAS_Dec2024.pdf", "path": "/uploads/cas.pdf"},
    ]

    import json

    result = run_analysis(sample_user, sample_files)
    print("\n" + "=" * 72)
    print("FINAL REPORT (JSON)")
    print("=" * 72)
    print(json.dumps(result, indent=2, default=str))