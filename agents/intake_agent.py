"""
agents/intake_agent.py — Conversational Financial Profiling Agent
=================================================================
Uses Groq API (llama-3.1-70b-versatile) for chat.
No OpenAI references.

Final extracted profile format matches the canonical user_data dict
consumed by utils/adapter.py.
"""

from __future__ import annotations

import re
import json
from typing import Dict, List, Optional, Any, Tuple

from groq import Groq


# ---------------------------------------------------------------------------
# Number parser
# ---------------------------------------------------------------------------

def parse_indian_number(text: str) -> float:
    """
    Parse Indian number formats to float.

    Examples:
        '12 lakh'    -> 1200000
        '1.2L'       -> 120000
        '12,00,000'  -> 1200000
        '50k'        -> 50000
        '1.5 crore'  -> 15000000
        'nil'/'none' -> 0
    """
    if text is None:
        return 0.0
    text = str(text).strip().lower()
    if text in {"nil", "none", "no", "nothing", "zero", "na", "n/a", "-", ""}:
        return 0.0
    text_clean = text.replace(",", "").replace(" ", "")
    try:
        return float(text_clean)
    except ValueError:
        pass
    crore_m = re.search(r"(\d+\.?\d*)\s*(?:cr|crore|crores)", text.replace(",", ""))
    if crore_m:
        return float(crore_m.group(1)) * 10_000_000
    lakh_m = re.search(r"(\d+\.?\d*)\s*(?:l|lac|lakh|lakhs|lacs)", text.replace(",", ""))
    if lakh_m:
        return float(lakh_m.group(1)) * 100_000
    k_m = re.search(r"(\d+\.?\d*)\s*k", text.replace(",", ""))
    if k_m:
        return float(k_m.group(1)) * 1_000
    nums = re.sub(r"[^\d.]", "", text)
    if nums:
        try:
            return float(nums)
        except ValueError:
            pass
    return 0.0


# ---------------------------------------------------------------------------
# Metro city detection
# ---------------------------------------------------------------------------

METRO_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "kolkata",
    "hyderabad", "pune", "ahmedabad", "new delhi", "ncr", "gurgaon",
    "gurugram", "noida", "ghaziabad", "faridabad", "navi mumbai",
    "thane", "calcutta", "bombay",
}


def is_metro_city(city: str) -> bool:
    if not city:
        return False
    city_lower = city.lower().strip()
    return any(metro in city_lower or city_lower in metro for metro in METRO_CITIES)


# ---------------------------------------------------------------------------
# Canonical empty profile
# ---------------------------------------------------------------------------

def _empty_profile() -> Dict[str, Any]:
    return {
        "age": None,
        "annual_income": None,
        "city": None,
        "is_metro": None,
        "monthly_rent": None,
        "hra_received": 0.0,
        "has_term_insurance": None,
        "term_cover": 0.0,
        "has_health_insurance": None,
        "health_cover": 0.0,
        "sec_80c": 0.0,
        "sec_80d": 0.0,
        "nps_annual": 0.0,
        "epf_annual": 0.0,
        "home_loan_interest": 0.0,
        "monthly_expenses": None,
        "monthly_sip": 0.0,
        "emergency_fund": 0.0,
        "total_equity": 0.0,
        "total_debt": 0.0,
        "retirement_age": 60,
    }


# ---------------------------------------------------------------------------
# IntakeAgent
# ---------------------------------------------------------------------------

class IntakeAgent:
    """
    Conversational agent using Groq (Llama-3.1-70B) to gather user financial data.
    WhatsApp-like tone, JSON-extraction loop, returns canonical profile dict.
    """

    MODEL = "llama-3.1-70b-versatile"

    QUESTIONS_FLOW = [
        "age", "income", "city", "rent", "insurance",
        "investments", "expenses", "sip", "emergency_fund",
        "retirement_age",
    ]

    SYSTEM_PROMPT = """You are a friendly financial advisor assistant helping someone understand their finances.
Communicate in a warm, WhatsApp-like conversational tone.

Job:
1. Understand the user's response to the CURRENT QUESTION only.
2. Extract the relevant data points.
3. Generate a short, friendly next message.

Rules:
- Keep responses SHORT (1-3 sentences max). Use casual language and occasional emojis.
- Handle Indian number formats (lakh, crore, L, k, etc.)
- If unclear, ask for clarification.

ALWAYS respond in valid JSON:
{
    "extracted_data": { ...fields extracted... },
    "needs_clarification": false,
    "next_message": "Your response and next question"
}"""

    QUESTION_PROMPTS = {
        "age": (
            "Extract: age (int). If birth year given, calculate age (current year 2025).\n"
            'Example: "28" -> {"age": 28}, "born 1996" -> {"age": 29}'
        ),
        "income": (
            "Extract: annual_income (float). Handle Indian formats.\n"
            'Example: "12 lakh CTC" -> {"annual_income": 1200000}, '
            '"80k per month" -> {"annual_income": 960000}'
        ),
        "city": (
            "Extract: city (str).\n"
            'Example: "I live in Mumbai" -> {"city": "Mumbai"}'
        ),
        "rent": (
            "Extract: monthly_rent (float). Own house or parents = 0.\n"
            'Example: "25k per month" -> {"monthly_rent": 25000}, "own house" -> {"monthly_rent": 0}'
        ),
        "insurance": (
            "Extract: has_term_insurance (bool), term_cover (float), "
            "has_health_insurance (bool), health_cover (float).\n"
            '"Both, term 1Cr health 10L" -> '
            '{"has_term_insurance": true, "term_cover": 10000000, "has_health_insurance": true, "health_cover": 1000000}'
        ),
        "investments": (
            "Extract: epf_annual (float), sec_80c (float - PPF/ELSS/LIC excluding EPF), nps_annual (float).\n"
            '"50k PPF, 1L ELSS, EPF 1.8L" -> {"sec_80c": 150000, "epf_annual": 180000, "nps_annual": 0}'
        ),
        "expenses": (
            "Extract: monthly_expenses (float). Total monthly spend.\n"
            '"Around 40k per month" -> {"monthly_expenses": 40000}'
        ),
        "sip": (
            "Extract: monthly_sip (float).\n"
            '"15k per month in SIPs" -> {"monthly_sip": 15000}, "none" -> {"monthly_sip": 0}'
        ),
        "emergency_fund": (
            "Extract: emergency_fund (float). Liquid savings.\n"
            '"3 lakh in savings" -> {"emergency_fund": 300000}'
        ),
        "retirement_age": (
            "Extract: retirement_age (int). Default 60 if not specified.\n"
            '"Want to retire at 50" -> {"retirement_age": 50}'
        ),
    }

    NEXT_QUESTION_HINTS = {
        "income": "Ask about annual income (CTC or in-hand). Be casual.",
        "city": "Ask which city they live in (helps with HRA calculations).",
        "rent": "Ask monthly rent. OK if they own the place or stay with family.",
        "insurance": "Ask about term and health insurance — have both, one, or neither?",
        "investments": "Ask about 80C investments: EPF, PPF, ELSS, NPS — yearly amounts.",
        "expenses": "Ask total monthly expenses (rent is already captured).",
        "sip": "Ask if they have any running SIPs and the monthly amount.",
        "emergency_fund": "Ask about emergency fund — quick-access savings.",
        "retirement_age": "Last question! Ask what age they'd like to retire. Default 60 is fine.",
    }

    def __init__(self, groq_api_key: str):
        self.client = Groq(api_key=groq_api_key)
        self.profile = _empty_profile()
        self.current_question_idx = 0

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _current_q(self) -> str:
        return self.QUESTIONS_FLOW[self.current_question_idx]

    def _call_groq(self, messages: List[Dict], question_type: str) -> Dict:
        extra = self.QUESTION_PROMPTS.get(question_type, "")
        system = f"{self.SYSTEM_PROMPT}\n\nCurrent question type: {question_type}\n{extra}"

        api_messages = [{"role": "system", "content": system}] + messages

        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=api_messages,
            temperature=0.6,
            max_tokens=400,
        )
        content = response.choices[0].message.content

        # Strip markdown fences
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            content = json_match.group(1)
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {
            "extracted_data": {},
            "needs_clarification": True,
            "next_message": "Sorry, I didn't quite catch that. Could you rephrase? 🤔",
        }

    def _update_profile(self, extracted: Dict) -> None:
        if not extracted:
            return
        numeric_fields = {
            "annual_income", "monthly_rent", "term_cover", "health_cover",
            "sec_80c", "epf_annual", "nps_annual", "sec_80d",
            "home_loan_interest", "monthly_expenses", "monthly_sip",
            "emergency_fund", "total_equity", "total_debt",
        }
        for field, value in extracted.items():
            if field not in self.profile and field != "primary_goal":
                continue
            if value is None:
                continue
            if field in numeric_fields:
                value = parse_indian_number(str(value)) if isinstance(value, str) else float(value)
            self.profile[field] = value

        if self.profile.get("city"):
            self.profile["is_metro"] = is_metro_city(str(self.profile["city"]))

    def _is_complete(self, q: str) -> bool:
        checks = {
            "age":           lambda: self.profile["age"] is not None,
            "income":        lambda: self.profile["annual_income"] is not None,
            "city":          lambda: self.profile["city"] is not None,
            "rent":          lambda: self.profile["monthly_rent"] is not None,
            "insurance":     lambda: (
                self.profile["has_term_insurance"] is not None
                and self.profile["has_health_insurance"] is not None
            ),
            "investments":   lambda: True,
            "expenses":      lambda: self.profile["monthly_expenses"] is not None,
            "sip":           lambda: True,
            "emergency_fund": lambda: True,
            "retirement_age": lambda: True,
        }
        return checks.get(q, lambda: True)()

    def _hra_estimate(self) -> float:
        """Estimate HRA as 40% of annual income if not explicitly provided."""
        ai = self.profile.get("annual_income") or 0
        return round(ai * 0.40, 2)

    def _completion_message(self) -> str:
        p = self.profile
        income_l = (p["annual_income"] or 0) / 1e5
        return (
            f"Awesome, all done! 🎉\n\n"
            f"**Your Profile Summary:**\n"
            f"• Age: {p['age']} | Income: ₹{income_l:.1f}L/yr | City: {p['city']} "
            f"({'Metro' if p['is_metro'] else 'Non-Metro'})\n"
            f"• Rent: ₹{p['monthly_rent']:,.0f}/mo | Expenses: ₹{(p['monthly_expenses'] or 0):,.0f}/mo\n"
            f"• Term: {'₹' + f\"{p['term_cover']/1e5:.0f}L\" if p['has_term_insurance'] else 'None'} | "
            f"Health: {'₹' + f\"{p['health_cover']/1e5:.0f}L\" if p['has_health_insurance'] else 'None'}\n"
            f"• 80C: ₹{p['sec_80c']:,.0f} | EPF: ₹{p['epf_annual']:,.0f} | NPS: ₹{p['nps_annual']:,.0f}\n"
            f"• SIP: ₹{p['monthly_sip']:,.0f}/mo | Emergency fund: ₹{p['emergency_fund']:,.0f}\n"
            f"• Retirement target: age {p['retirement_age']}\n\n"
            f"Let me calculate your personalised plan! 💪"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_opening_message(self) -> str:
        return (
            "Hey there! 👋\n\n"
            "I'm here to help you understand your finances. Think of me as that friend "
            "who's good with money stuff!\n\n"
            "I'll ask you a few quick questions (about 2-3 mins) to build your profile.\n\n"
            "Let's start simple — **how old are you?**"
        )

    def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
    ) -> Tuple[str, bool, Optional[Dict]]:
        """
        Process a user message.

        Returns
        -------
        (response_text, is_complete, profile_or_None)
        """
        if not conversation_history:
            return self.get_opening_message(), False, None

        q = self._current_q()
        messages = conversation_history + [{"role": "user", "content": user_message}]
        hint = self.NEXT_QUESTION_HINTS.get(
            self.QUESTIONS_FLOW[min(self.current_question_idx + 1, len(self.QUESTIONS_FLOW) - 1)], ""
        )
        context = (
            f"Profile so far: {json.dumps(self.profile, default=str)}\n"
            f"Next question hint: {hint}"
        )
        messages_with_ctx = messages[:-1] + [
            {"role": "user", "content": user_message + "\n\n[SYSTEM CTX]" + context}
        ]

        response = self._call_groq(messages_with_ctx, q)
        self._update_profile(response.get("extracted_data", {}))

        if not response.get("needs_clarification", False) and self._is_complete(q):
            self.current_question_idx += 1

        if self.current_question_idx >= len(self.QUESTIONS_FLOW):
            # Fill HRA if not set
            if not self.profile.get("hra_received"):
                self.profile["hra_received"] = self._hra_estimate()
            return self._completion_message(), True, self.profile.copy()

        return response.get("next_message", "Could you tell me more?"), False, None

    def reset(self) -> None:
        self.profile = _empty_profile()
        self.current_question_idx = 0
