"""
agents/report_generator.py — WealthPilot PDF Report Generator
=============================================================
Uses fpdf2 for PDF layout.
Uses Google Gemini for the narrative executive summary paragraph.

Public API:
    generate_report(analysis_results: dict) -> bytes
        analysis_results = output of utils/adapter.run_full_analysis()
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

# Gemini is used for narrative text generation only
try:
    import google.generativeai as genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------

class C:
    PRIMARY   = (41, 65, 122)
    SECONDARY = (70, 130, 180)
    LIGHT_BG  = (230, 240, 250)
    GREEN     = (34, 139, 34)
    GREEN_BG  = (220, 245, 220)
    RED       = (220, 53, 69)
    RED_BG    = (255, 230, 230)
    ORANGE    = (255, 140, 0)
    ORANGE_BG = (255, 245, 220)
    WHITE     = (255, 255, 255)
    BLACK     = (0, 0, 0)
    GRAY      = (128, 128, 128)
    LGRAY     = (245, 245, 245)
    DGRAY     = (64, 64, 64)


# ---------------------------------------------------------------------------
# Custom PDF
# ---------------------------------------------------------------------------

class WPPDF(FPDF):

    def header(self):
        if self.page_no() > 1:
            self.set_draw_color(*C.PRIMARY)
            self.set_line_width(0.5)
            self.line(10, 10, 200, 10)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*C.PRIMARY)
            self.set_xy(10, 12)
            self.cell(0, 5, "WealthPilot Financial Report", align="L")
            self.set_xy(-30, 12)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*C.GRAY)
            self.cell(0, 5, f"Page {self.page_no()}", align="R")
            self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C.GRAY)
        self.cell(
            0, 10,
            f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')} | Confidential",
            align="C",
        )

    # --- helpers ---

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(*C.PRIMARY)
        self.cell(0, 12, title, ln=True)
        self.set_draw_color(*C.PRIMARY)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(8)

    def sub_title(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*C.SECONDARY)
        self.cell(0, 8, title, ln=True)
        self.ln(2)

    def info_box(self, text: str, kind: str = "info"):
        bg = {
            "info": C.LIGHT_BG, "success": C.GREEN_BG,
            "warning": C.ORANGE_BG, "danger": C.RED_BG,
        }.get(kind, C.LIGHT_BG)
        tc = {
            "info": C.PRIMARY, "success": C.GREEN,
            "warning": C.ORANGE, "danger": C.RED,
        }.get(kind, C.PRIMARY)
        self.set_fill_color(*bg)
        self.set_text_color(*tc)
        self.set_font("Helvetica", "", 10)
        self.set_x(15)
        self.multi_cell(180, 7, text, fill=True, border=0)
        self.ln(4)
        self.set_text_color(*C.BLACK)

    def table(
        self,
        headers: List[str],
        rows: List[List[str]],
        widths: Optional[List[int]] = None,
    ):
        if widths is None:
            widths = [190 // len(headers)] * len(headers)
        # Header
        self.set_fill_color(*C.PRIMARY)
        self.set_text_color(*C.WHITE)
        self.set_font("Helvetica", "B", 9)
        for h, w in zip(headers, widths):
            self.cell(w, 8, h, border=1, fill=True, align="C")
        self.ln()
        # Rows
        self.set_text_color(*C.BLACK)
        self.set_font("Helvetica", "", 9)
        for i, row in enumerate(rows):
            self.set_fill_color(*C.LGRAY if i % 2 == 0 else C.WHITE)
            for cell, w in zip(row, widths):
                self.cell(w, 7, str(cell), border=1, fill=True, align="C")
            self.ln()
        self.ln(4)
        self.set_text_color(*C.BLACK)


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def _fmt(amount: float) -> str:
    return f"Rs {amount:,.0f}"


def _page_cover(pdf: WPPDF, user_data: Dict, health_score: float):
    pdf.add_page()
    pdf.set_fill_color(*C.PRIMARY)
    pdf.rect(0, 0, 210, 90, "F")

    pdf.set_y(25)
    pdf.set_font("Helvetica", "B", 34)
    pdf.set_text_color(*C.WHITE)
    pdf.cell(0, 16, "WealthPilot", align="C", ln=True)
    pdf.set_font("Helvetica", "", 17)
    pdf.cell(0, 10, "Personal Financial Report", align="C", ln=True)
    pdf.set_draw_color(*C.WHITE)
    pdf.set_line_width(1)
    pdf.line(70, 68, 140, 68)

    pdf.set_y(100)
    pdf.set_text_color(*C.DGRAY)
    pdf.set_font("Helvetica", "", 13)
    pdf.cell(0, 10, f"Report Date: {datetime.now().strftime('%B %d, %Y')}", align="C", ln=True)

    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*C.PRIMARY)
    pdf.cell(0, 10, "YOUR FINANCIAL HEALTH SCORE", align="C", ln=True)

    score_color = C.GREEN if health_score >= 70 else (C.ORANGE if health_score >= 45 else C.RED)
    grade = "EXCELLENT" if health_score >= 70 else ("GOOD" if health_score >= 50 else "NEEDS ATTENTION")
    pdf.set_font("Helvetica", "B", 64)
    pdf.set_text_color(*score_color)
    pdf.cell(0, 35, str(int(health_score)), align="C", ln=True)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, f"out of 100 — {grade}", align="C", ln=True)

    pdf.ln(12)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*C.DGRAY)
    age = user_data.get("age", "—")
    income = user_data.get("annual_income", 0)
    city = user_data.get("city", "—")
    pdf.cell(63, 8, f"Age: {age}", align="C")
    pdf.cell(63, 8, f"Income: {_fmt(income)}/yr", align="C")
    pdf.cell(63, 8, f"City: {city}", align="C", ln=True)


def _page_tax(pdf: WPPDF, tax: Dict):
    pdf.add_page()
    pdf.section_title("Tax Analysis — FY 2024-25")

    old_tax = tax.get("old_regime_tax", 0)
    new_tax = tax.get("new_regime_tax", 0)
    rec = tax.get("recommended", "New")
    savings = tax.get("savings", 0)
    old_eff = tax.get("old_effective_rate", 0)
    new_eff = tax.get("new_effective_rate", 0)

    pdf.sub_title("Regime Comparison")
    pdf.table(
        headers=["Component", "Old Regime", "New Regime"],
        rows=[
            ["Tax Payable", _fmt(old_tax), _fmt(new_tax)],
            ["Effective Rate", f"{old_eff:.2f}%", f"{new_eff:.2f}%"],
            ["Standard Deduction", "Rs 50,000", "Rs 75,000"],
        ],
        widths=[80, 55, 55],
    )

    rec_text = f"RECOMMENDED: {rec} Regime   You save {_fmt(savings)}/year by choosing this regime."
    pdf.info_box(rec_text, "success")

    missed = tax.get("missed_deductions", [])
    if missed:
        pdf.ln(4)
        pdf.sub_title("Missed Tax-Saving Opportunities")
        rows = []
        for m in missed[:6]:
            rows.append([
                m.get("section", ""),
                _fmt(m.get("current_amount", 0)),
                _fmt(m.get("limit", 0)),
                _fmt(m.get("gap", 0)),
                _fmt(m.get("potential_tax_saving", 0)),
            ])
        pdf.table(
            headers=["Section", "Claimed", "Limit", "Gap", "Tax Saving"],
            rows=rows,
            widths=[50, 30, 30, 30, 50],
        )
        total_saving = sum(m.get("potential_tax_saving", 0) for m in missed)
        pdf.info_box(f"Total potential tax saving: {_fmt(total_saving)}/year", "success")


def _page_health(pdf: WPPDF, health: Dict):
    pdf.add_page()
    pdf.section_title("Financial Health Score Breakdown")

    scores = health.get("scores", {})
    label_map = {
        "emergency":   "Emergency Preparedness",
        "insurance":   "Insurance Coverage",
        "investment":  "Investment Diversification",
        "debt":        "Debt Health",
        "tax":         "Tax Efficiency",
        "retirement":  "Retirement Readiness",
    }

    rows = []
    for key, label in label_map.items():
        sc = scores.get(key, 0)
        if sc >= 70:
            status = "Excellent"
        elif sc >= 50:
            status = "Good"
        elif sc >= 30:
            status = "Fair"
        else:
            status = "Needs Work"
        rows.append([label, f"{sc:.0f}/100", status])

    pdf.table(
        headers=["Dimension", "Score", "Status"],
        rows=rows,
        widths=[90, 40, 60],
    )

    recs = health.get("recommendations", [])
    if recs:
        pdf.ln(4)
        pdf.sub_title("Top Recommendations")
        for i, rec in enumerate(recs[:3], 1):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*C.BLACK)
            pdf.multi_cell(0, 6, f"{i}. {rec}")
            pdf.ln(2)
        pdf.set_text_color(*C.BLACK)


def _page_fire(pdf: WPPDF, fire: Dict, user_data: Dict):
    pdf.add_page()
    pdf.section_title("FIRE Plan — Financial Independence")

    fire_num = fire.get("fire_number", 0)
    projection = fire.get("current_projection", 0)
    gap = fire.get("gap", 0)
    req_sip = fire.get("required_sip", 0)
    years = fire.get("years_to_retire", 0)
    fire_age = fire.get("fire_achievable_age")

    pdf.sub_title("Key Metrics")
    pdf.table(
        headers=["Metric", "Value"],
        rows=[
            ["FIRE Number (inflation-adjusted)", _fmt(fire_num)],
            ["Projected Corpus at Retirement", _fmt(projection)],
            ["Gap (surplus if positive)", _fmt(gap)],
            ["Required Monthly SIP to hit FIRE", _fmt(req_sip)],
            ["Years to Retirement", str(years)],
            ["FIRE Achievable Age", str(fire_age) if fire_age else "—"],
        ],
        widths=[110, 80],
    )

    box_text = (
        f"ON TRACK — Surplus of {_fmt(gap)}" if gap >= 0
        else f"SHORTFALL of {_fmt(abs(gap))}. Increase SIP by {_fmt(req_sip)}/mo."
    )
    pdf.info_box(box_text, "success" if gap >= 0 else "warning")

    projections = fire.get("projections", [])
    if projections:
        pdf.ln(4)
        pdf.sub_title("Year-by-Year Projection (every 3 years)")
        rows = []
        for entry in projections:
            if entry["year"] % 3 == 0 or entry["year"] == 1:
                rows.append([
                    f"Year {entry['year']}",
                    f"Age {entry.get('age', '—')}",
                    _fmt(entry.get("value", 0)),
                    f"{entry.get('progress_percent', 0):.0f}%",
                ])
        pdf.table(
            headers=["Year", "Age", "Portfolio Value", "FIRE Progress"],
            rows=rows[:10],
            widths=[30, 30, 80, 50],
        )


def _page_action(pdf: WPPDF, tax: Dict, health: Dict):
    pdf.add_page()
    pdf.section_title("Action Checklist")

    actions: List[Dict] = []

    # Tax actions
    for m in tax.get("missed_deductions", [])[:3]:
        actions.append({
            "priority": "HIGH" if m.get("potential_tax_saving", 0) > 15_000 else "MEDIUM",
            "action": f"Use {m.get('section','?')}: invest ₹{m.get('gap',0):,.0f} more to save ₹{m.get('potential_tax_saving',0):,.0f}/yr",
            "category": "Tax",
        })

    # Regime switch
    if tax.get("recommended") == "Old":
        actions.append({
            "priority": "HIGH",
            "action": f"Switch to Old Regime — saves {_fmt(tax.get('savings', 0))}/yr",
            "category": "Tax",
        })

    # Health recs
    for rec in health.get("recommendations", []):
        actions.append({"priority": "MEDIUM", "action": rec[:80], "category": "Health"})

    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    actions.sort(key=lambda x: priority_order.get(x.get("priority", "LOW"), 2))

    rows = []
    for i, a in enumerate(actions[:12], 1):
        rows.append([str(i), a["priority"], a["action"][:55], a["category"]])

    pdf.table(
        headers=["#", "Priority", "Action", "Category"],
        widths=[10, 22, 120, 38],
        rows=rows,
    )


# ---------------------------------------------------------------------------
# Gemini narrative (optional)
# ---------------------------------------------------------------------------

def _gemini_narrative(analysis_results: Dict, api_key: Optional[str] = None) -> Optional[str]:
    if not _GEMINI_AVAILABLE or not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        health_score = analysis_results.get("health", {}).get("overall_score", 0)
        rec = analysis_results.get("tax", {}).get("recommended", "New")
        savings = analysis_results.get("tax", {}).get("savings", 0)
        fire_gap = analysis_results.get("fire", {}).get("gap", 0)
        prompt = (
            f"Write a 3-sentence professional financial summary for a client report:\n"
            f"- Health score: {health_score}/100\n"
            f"- Recommended tax regime: {rec} (saves Rs {savings:,.0f}/year)\n"
            f"- FIRE gap: {'surplus of Rs ' + f'{fire_gap:,.0f}' if fire_gap >= 0 else 'shortfall of Rs ' + f'{abs(fire_gap):,.0f}'}\n"
            f"Be encouraging, professional, and specific. No bullet points."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        print(f"[report_generator] Gemini narrative error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(analysis_results: dict, gemini_api_key: Optional[str] = None) -> bytes:
    """
    Generate a multi-page PDF financial report.

    Parameters
    ----------
    analysis_results : dict — output of utils/adapter.run_full_analysis()
    gemini_api_key   : str  — optional, used for executive summary paragraph

    Returns
    -------
    PDF document as bytes.
    """
    tax = analysis_results.get("tax", {})
    health = analysis_results.get("health", {})
    fire = analysis_results.get("fire", {})
    user_data = analysis_results.get("user_data", {})

    health_score = health.get("overall_score", 0)

    pdf = WPPDF()
    pdf.set_title("WealthPilot Financial Report")
    pdf.set_author("WealthPilot")
    pdf.set_auto_page_break(auto=True, margin=20)

    # Cover
    _page_cover(pdf, user_data, health_score)

    # Executive narrative (Gemini, if available)
    narrative = _gemini_narrative(analysis_results, gemini_api_key)
    if narrative:
        pdf.add_page()
        pdf.section_title("Executive Summary")
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*C.DGRAY)
        pdf.multi_cell(0, 7, narrative)

    # Tax page
    _page_tax(pdf, tax)

    # Health page
    _page_health(pdf, health)

    # FIRE page
    _page_fire(pdf, fire, user_data)

    # Action checklist
    _page_action(pdf, tax, health)

    return bytes(pdf.output())
