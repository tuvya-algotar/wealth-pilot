"""
agents/document_parser.py — Form 16 PDF Parser using Gemini Vision
====================================================================
Uses google.generativeai (gemini-1.5-flash) for visual extraction.
No OpenAI references.

Public API:
    parse_form16_safe(pdf_path, api_key) -> dict | None
        Returns a canonical user_data dict (or None on total failure).
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image


# ---------------------------------------------------------------------------
# Canonical field mapping
# ---------------------------------------------------------------------------

CANONICAL_DEFAULTS: Dict[str, Any] = {
    "age": None,
    "annual_income": None,
    "city": None,
    "is_metro": None,
    "monthly_rent": 0.0,
    "hra_received": 0.0,
    "has_term_insurance": False,
    "term_cover": 0.0,
    "has_health_insurance": False,
    "health_cover": 0.0,
    "sec_80c": 0.0,
    "sec_80d": 0.0,
    "nps_annual": 0.0,
    "epf_annual": 0.0,
    "home_loan_interest": 0.0,
    "monthly_expenses": 0.0,
    "monthly_sip": 0.0,
    "emergency_fund": 0.0,
    "total_equity": 0.0,
    "total_debt": 0.0,
    "retirement_age": 60,
}


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def _pdf_page_to_image(pdf_path: str, page_num: int, dpi: int = 200) -> Image.Image:
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    doc.close()
    return Image.open(io.BytesIO(img_bytes))


def _get_page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    n = len(doc)
    doc.close()
    return n


def _extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text


# ---------------------------------------------------------------------------
# Gemini extraction
# ---------------------------------------------------------------------------

_GEMINI_PROMPT = """
You are an expert at parsing Indian Income Tax Form 16 documents.
Analyse the image and extract these fields EXACTLY. Return ONLY a valid JSON object:

{
  "gross_salary": <number or null>,
  "basic_salary": <number or null>,
  "hra_received": <number or null>,
  "standard_deduction": <number or null>,
  "section_80c": <number or null>,
  "section_80d": <number or null>,
  "section_80ccd_1b": <number or null>,
  "home_loan_interest": <number or null>,
  "epf_employee": <number or null>,
  "net_taxable_income": <number or null>,
  "tax_payable": <number or null>,
  "tds_deducted": <number or null>,
  "financial_year": <string or null>,
  "employee_name": <string or null>,
  "pan": <string or null>
}

Rules:
- Use numeric values for amounts (not strings with commas).
- If a field is not found or unclear, use null.
- Return ONLY the JSON object — no extra text, no markdown fences.
"""


def _parse_one_page_gemini(model: Any, image: Image.Image) -> Optional[Dict]:
    try:
        response = model.generate_content([_GEMINI_PROMPT, image])
        text = response.text.strip()
        # Strip potential markdown
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
    except Exception as exc:
        print(f"[document_parser] Gemini page error: {exc}")
    return None


def _merge_pages(pages: List[Dict]) -> Dict:
    """Merge multi-page results — pick non-null value for each key."""
    merged: Dict[str, Any] = {}
    for page in pages:
        for k, v in page.items():
            if k not in merged or merged[k] is None:
                merged[k] = v
    return merged


# ---------------------------------------------------------------------------
# Text fallback (regex)
# ---------------------------------------------------------------------------

def _parse_text_fallback(text: str) -> Dict:
    result: Dict[str, Any] = {}
    # Gross Salary
    m = re.search(r"Gross\s+Salary[\s:₹Rs.]*([0-9,]+)", text, re.IGNORECASE)
    if m:
        result["gross_salary"] = float(m.group(1).replace(",", ""))
    # PAN
    m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
    if m:
        result["pan"] = m.group(1)
    # 80C
    m = re.search(r"80C[\s:₹Rs.]*([0-9,]+)", text, re.IGNORECASE)
    if m:
        result["section_80c"] = float(m.group(1).replace(",", ""))
    # TDS
    m = re.search(r"TDS\s+[Dd]educt[ed]*[\s:₹Rs.]*([0-9,]+)", text, re.IGNORECASE)
    if m:
        result["tds_deducted"] = float(m.group(1).replace(",", ""))
    return result


# ---------------------------------------------------------------------------
# Mapping: raw Gemini fields -> canonical user_data fields
# ---------------------------------------------------------------------------

def _gemini_to_canonical(raw: Dict) -> Dict[str, Any]:
    def _f(key: str) -> float:
        v = raw.get(key)
        try:
            return float(v) if v is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    profile = dict(CANONICAL_DEFAULTS)

    profile["annual_income"] = _f("gross_salary")
    profile["hra_received"] = _f("hra_received")
    profile["sec_80c"] = _f("section_80c")
    profile["sec_80d"] = _f("section_80d")
    profile["nps_annual"] = _f("section_80ccd_1b")
    profile["home_loan_interest"] = _f("home_loan_interest")
    profile["epf_annual"] = _f("epf_employee")

    return profile


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_form16_pdf(pdf_path: str, api_key: str) -> Dict[str, Any]:
    """
    Parse Form 16 using Gemini Vision.

    Parameters
    ----------
    pdf_path : str — path to PDF file
    api_key  : str — Google Gemini API key

    Returns
    -------
    Canonical user_data dict with fields populated from the document.
    Fields not found in the document retain their defaults.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    n_pages = _get_page_count(pdf_path)
    page_results: List[Dict] = []

    for i in range(min(n_pages, 4)):  # process up to 4 pages
        image = _pdf_page_to_image(pdf_path, i)
        parsed = _parse_one_page_gemini(model, image)
        if parsed:
            page_results.append(parsed)

    if not page_results:
        raise ValueError("Gemini could not extract data from any page.")

    merged = _merge_pages(page_results)
    return _gemini_to_canonical(merged)


def parse_form16_safe(pdf_path: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Safe wrapper — returns canonical dict or None on failure.
    Falls back to text extraction if Gemini vision fails.
    """
    # Try Gemini Vision
    try:
        return parse_form16_pdf(pdf_path, api_key)
    except Exception as exc:
        print(f"[document_parser] Gemini Vision failed: {exc}")

    # Text fallback
    try:
        text = _extract_text(pdf_path)
        raw = _parse_text_fallback(text)
        return _gemini_to_canonical(raw)
    except Exception as exc2:
        print(f"[document_parser] Text fallback failed: {exc2}")

    return None
