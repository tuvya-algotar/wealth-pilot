# config.py — Financial Planning App Constants
# FY 2024-25 (AY 2025-26)
# Pure Python — no external API dependencies.

import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# LLM Usage Map
# Gemini → Document parsing (Vision), Report narrative
# Groq → Chat/Intake agent (fast responses)
# Pure Python → All calculations (tax, health, XIRR, projections)


# ---------------------------------------------------------------------------
# Tax Constants — Old Regime
# ---------------------------------------------------------------------------

OLD_REGIME_STANDARD_DEDUCTION = 50_000       # ₹50,000 flat
SEC_80C_LIMIT                  = 1_50_000    # ₹1.5L cap
SEC_80CCD1B_LIMIT              = 50_000      # Additional NPS
SEC_80D_SELF_BELOW60           = 25_000      # Self + family, age < 60
SEC_80D_SELF_ABOVE60           = 50_000      # Self + family, age >= 60
SEC_80D_PARENTS_BELOW60        = 25_000      # Parents, age < 60
SEC_80D_PARENTS_ABOVE60        = 50_000      # Parents, age >= 60
HOME_LOAN_INTEREST_LIMIT       = 2_00_000    # Section 24(b), self-occupied
SEC_80E_LIMIT                  = None        # Education loan — no upper cap
SEC_80G_LIMIT                  = None        # Donations — depends on qualifying institution

# ---------------------------------------------------------------------------
# Tax Constants — New Regime (Budget 2024)
# ---------------------------------------------------------------------------

NEW_REGIME_STANDARD_DEDUCTION  = 75_000     # ₹75,000 standard deduction
REBATE_87A_NEW_INCOME_LIMIT     = 7_00_000  # 87A rebate if taxable income ≤ ₹7L
REBATE_87A_NEW                  = 25_000    # Maximum rebate under new regime

# ---------------------------------------------------------------------------
# Common Tax Constants
# ---------------------------------------------------------------------------

REBATE_87A_OLD_INCOME_LIMIT     = 5_00_000  # 87A rebate if taxable income ≤ ₹5L
REBATE_87A_OLD                  = 12_500    # Maximum rebate under old regime
CESS_RATE                       = 0.04      # Health & Education Cess — 4%

# ---------------------------------------------------------------------------
# FIRE / Projection Defaults
# ---------------------------------------------------------------------------

DEFAULT_EQUITY_RETURN           = 0.12      # 12% p.a.
DEFAULT_INFLATION_RATE          = 0.06      # 6% p.a. (Indian avg)
DEFAULT_WITHDRAWAL_RATE         = 0.04      # 4% safe withdrawal (25x rule)
DEFAULT_SIP_STEP_UP             = 0.10      # 10% annual SIP step-up

# ---------------------------------------------------------------------------
# Health Score Weights
# ---------------------------------------------------------------------------

HEALTH_SCORE_WEIGHTS = {
    "EMERGENCY_PREPAREDNESS":    0.15,
    "INSURANCE_COVERAGE":        0.20,
    "INVESTMENT_DIVERSIFICATION": 0.15,
    "DEBT_HEALTH":               0.20,
    "TAX_EFFICIENCY":            0.10,
    "RETIREMENT_READINESS":      0.20,
}
