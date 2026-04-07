"""
app.py — WealthPilot Streamlit Application
==========================================
Run with:  streamlit run app.py
"""

from __future__ import annotations
from datetime import datetime

import io
import os
import tempfile
from typing import Any, Dict, Optional

import plotly.graph_objects as go
import streamlit as st

# ── project imports ──────────────────────────────────────────────────────────
import config
from utils.adapter import run_tax_analysis, run_health_analysis, run_fire_analysis, run_full_analysis
from agents.document_parser import parse_form16_safe
from agents.report_generator import generate_report

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WealthPilot",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── ANIMATIONS ───────────────────────────────────────────────────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.03); }
    }
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.3); }
        50% { box-shadow: 0 0 30px rgba(99, 102, 241, 0.5); }
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    /* ── GLOBAL STYLES ─────────────────────────────────────────────────────────── */
    .main { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); }
    .stApp { background: transparent; }

    /* ── GLASSMORPHISM BASE ────────────────────────────────────────────────────── */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
    }

    /* ── SIDEBAR ────────────────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 27, 75, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(99, 102, 241, 0.2);
    }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    section[data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] select {
        background: rgba(99, 102, 241, 0.1) !important;
        border: 1px solid rgba(99, 102, 241, 0.3) !important;
        color: #fff !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
    }
    section[data-testid="stSidebar"] input:focus,
    section[data-testid="stSidebar"] select:focus {
        border-color: #a855f7 !important;
        box-shadow: 0 0 20px rgba(168, 85, 247, 0.3) !important;
    }
    section[data-testid="stSidebar"] label {
        font-weight: 600 !important;
        color: #c7d2fe !important;
    }

    /* ── METRIC CARDS ──────────────────────────────────────────────────────────── */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 20px !important;
        transition: all 0.3s ease;
        animation: fadeInUp 0.5s ease forwards;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        border-color: #a855f7;
        box-shadow: 0 8px 32px rgba(168, 85, 247, 0.2);
    }
    [data-testid="metric-container"] label { color: #a5b4fc !important; font-weight: 600 !important; }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #fff !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-weight: 600 !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricDeltaUp"] { color: #10b981 !important; }
    [data-testid="metric-container"] [data-testid="stMetricDeltaDown"] { color: #ef4444 !important; }

    /* ── TABS ──────────────────────────────────────────────────────────────────── */
    .stTabs { gap: 8px; }
    button[data-baseweb="tab"] {
        font-size: 15px !important;
        font-weight: 600 !important;
        background: rgba(99, 102, 241, 0.1) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 12px !important;
        color: #c7d2fe !important;
        padding: 12px 24px !important;
        transition: all 0.3s ease !important;
    }
    button[data-baseweb="tab"]:hover {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: #6366f1 !important;
        transform: translateY(-2px);
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        border-color: #a855f7 !important;
        color: #fff !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
    }
    [data-testid="stTabContent"] {
        background: rgba(15, 23, 42, 0.5);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }

    /* ── MAIN CTA BUTTON ───────────────────────────────────────────────────────── */
    div[data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        background-size: 200% 200%;
        color: white;
        border: none;
        border-radius: 14px;
        padding: 0.75rem 2rem;
        font-weight: 700;
        font-size: 16px;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
        transition: all 0.3s ease;
        animation: gradientShift 3s ease infinite;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 8px 30px rgba(168, 85, 247, 0.5);
    }
    div[data-testid="stButton"] > button[kind="primary"]:active {
        transform: scale(0.98);
    }

    /* ── SECONDARY BUTTONS ─────────────────────────────────────────────────────── */
    div[data-testid="stButton"] > button:not([kind="primary"]) {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #c7d2fe;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    div[data-testid="stButton"] > button:not([kind="primary"]):hover {
        background: rgba(99, 102, 241, 0.2);
        border-color: #a855f7;
        color: #fff;
    }

    /* ── SECTION DIVIDER ────────────────────────────────────────────────────────── */
    .wp-section {
        margin: 1.5rem 0 0.5rem;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #a855f7;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .wp-section::before {
        content: '';
        display: inline-block;
        width: 4px;
        height: 16px;
        background: linear-gradient(180deg, #6366f1, #a855f7);
        border-radius: 2px;
    }

    /* ── SCORE BADGES ───────────────────────────────────────────────────────────── */
    .score-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 24px;
        font-weight: 700;
        font-size: 1rem;
        margin: 6px;
        transition: all 0.3s ease;
        animation: fadeInUp 0.5s ease forwards;
    }
    .score-badge:hover { transform: scale(1.05); }
    .score-good {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(52, 211, 153, 0.2));
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.4);
    }
    .score-ok {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(251, 191, 36, 0.2));
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.4);
    }
    .score-bad {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(248, 113, 113, 0.2));
        color: #f87171;
        border: 1px solid rgba(248, 113, 113, 0.4);
    }

    /* ── RECOMMENDATION CARDS ──────────────────────────────────────────────────── */
    .rec-card {
        border-left: 4px solid;
        border-image: linear-gradient(180deg, #6366f1, #a855f7) 1;
        background: rgba(99, 102, 241, 0.1);
        padding: 16px 20px;
        border-radius: 0 16px 16px 0;
        margin: 12px 0;
        font-size: 0.95rem;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    .rec-card:hover {
        transform: translateX(8px);
        background: rgba(99, 102, 241, 0.15);
    }

    /* ── HERO SECTION ───────────────────────────────────────────────────────────── */
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899, #f472b6);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 4s ease infinite;
        font-family: 'Space Grotesk', sans-serif;
    }

    /* ── FEATURE CARDS ──────────────────────────────────────────────────────────── */
    .feature-card {
        background: rgba(99, 102, 241, 0.05);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 20px;
        padding: 24px;
        text-align: center;
        transition: all 0.4s ease;
        position: relative;
        overflow: hidden;
    }
    .feature-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        transform: scaleX(0);
        transition: transform 0.4s ease;
    }
    .feature-card:hover {
        transform: translateY(-8px);
        border-color: #a855f7;
        box-shadow: 0 20px 40px rgba(168, 85, 247, 0.2);
    }
    .feature-card:hover::before { transform: scaleX(1); }

    /* ── CHARTS ─────────────────────────────────────────────────────────────────── */
    .js-plotly-plot .plotly .bg { fill: transparent !important; }
    .js-plotly-plot .plotly .gridlayer { stroke: rgba(99, 102, 241, 0.1) !important; }

    /* ── EXPANDERS ──────────────────────────────────────────────────────────────── */
    .streamlit-expanderHeader {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px !important;
        transition: all 0.3s ease;
    }
    .streamlit-expanderHeader:hover {
        background: rgba(99, 102, 241, 0.15);
        border-color: #a855f7;
    }

    /* ── FILE UPLOADER ──────────────────────────────────────────────────────────── */
    .stFileUploader {
        border: 2px dashed rgba(99, 102, 241, 0.4) !important;
        border-radius: 16px !important;
        background: rgba(99, 102, 241, 0.05) !important;
        transition: all 0.3s ease;
    }
    .stFileUploader:hover {
        border-color: #a855f7 !important;
        background: rgba(99, 102, 241, 0.1) !important;
    }

    /* ── SLIDERS ────────────────────────────────────────────────────────────────── */
    .stSlider [data-testid="stSlider"] {
        background: rgba(99, 102, 241, 0.1);
    }
    .stSlider [role="slider"] {
        background: linear-gradient(135deg, #6366f1, #a855f7) !important;
    }

    /* ── SUCCESS/ERROR/WARNING BOXES ───────────────────────────────────────────── */
    .element-container .stSuccess {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(52, 211, 153, 0.4);
        border-radius: 12px;
        color: #34d399;
    }
    .element-container .stWarning {
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(251, 191, 36, 0.4);
        border-radius: 12px;
        color: #fbbf24;
    }
    .element-container .stError {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(248, 113, 113, 0.4);
        border-radius: 12px;
        color: #f87171;
    }

    /* ── SPINNER ────────────────────────────────────────────────────────────────── */
    .stSpinner > div {
        border-color: #6366f1 transparent transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── constants ─────────────────────────────────────────────────────────────────
METRO_CITIES = {"Mumbai", "Delhi", "Chennai", "Kolkata", "Bangalore", "Hyderabad"}

CITY_LIST = [
    "Mumbai", "Delhi", "Bangalore", "Chennai",
    "Kolkata", "Hyderabad", "Pune", "Other",
]

DEMO_DATA: Dict[str, Any] = {
    "age": 28,
    "annual_income": 1_200_000,
    "city": "Mumbai",
    "is_metro": True,
    "monthly_rent": 20_000,
    "hra_received": 2_40_000,
    "home_loan_interest": 0,
    "has_term_insurance": True,
    "term_cover": 1_00_00_000,
    "has_health_insurance": True,
    "health_cover": 5_00_000,
    "epf_annual": 21_600,
    "sec_80c": 50_000,
    "nps_annual": 0,
    "sec_80d": 15_000,
    "monthly_sip": 10_000,
    "total_equity": 3_00_000,
    "total_debt": 1_00_000,
    "monthly_expenses": 40_000,
    "emergency_fund": 1_00_000,
    "retirement_age": 55,
}

# ── session defaults ──────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "analysis_done": False,
        "results": None,
        "user_data": None,
        # sidebar form state (for pre-fill from Form 16 or demo)
        "sb": DEMO_DATA.copy(),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_session()


# ── helpers ───────────────────────────────────────────────────────────────────
def _score_color(score: float) -> str:
    if score >= 70: return "score-good"
    if score >= 45: return "score-ok"
    return "score-bad"


def _inr(val: float) -> str:
    return f"₹{val:,.0f}"


def _inr_lakh(val: float) -> str:
    if abs(val) >= 1_00_00_000:
        return f"₹{val/1_00_00_000:.2f} Cr"
    if abs(val) >= 1_00_000:
        return f"₹{val/1_00_000:.2f} L"
    return f"₹{val:,.0f}"


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
        <div style="text-align:center; padding: 10px 0 20px;">
            <h2 style="font-size: 1.8rem; font-weight: 800; margin: 0;
                background: linear-gradient(135deg, #6366f1, #a855f7, #ec4899);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                💰 WealthPilot
            </h2>
            <p style="color: #a5b4fc; font-size: 0.9rem; margin-top: 4px;">
                Your AI-powered financial co-pilot
            </p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

    sb = st.session_state["sb"]

    # ── Personal Info ─────────────────────────────────────────────────────────
    st.markdown('<p class="wp-section">👤 Personal Info</p>', unsafe_allow_html=True)

    age = st.number_input("Age", min_value=18, max_value=80, value=int(sb.get("age", 28)), step=1)
    annual_income = st.number_input(
        "Annual Income (CTC) ₹",
        min_value=0, max_value=10_00_00_000,
        value=int(sb.get("annual_income", 12_00_000)), step=1_00_000,
    )
    city = st.selectbox(
        "City",
        CITY_LIST,
        index=CITY_LIST.index(sb.get("city", "Mumbai")) if sb.get("city", "Mumbai") in CITY_LIST else 0,
    )
    is_metro = city in METRO_CITIES

    # ── Housing ───────────────────────────────────────────────────────────────
    st.markdown('<p class="wp-section">🏠 Housing</p>', unsafe_allow_html=True)

    monthly_rent = st.number_input(
        "Monthly Rent ₹", min_value=0, max_value=5_00_000,
        value=int(sb.get("monthly_rent", 20_000)), step=1_000,
    )
    hra_received = st.number_input(
        "HRA Received (Annual) ₹", min_value=0, max_value=50_00_000,
        value=int(sb.get("hra_received", 2_40_000)), step=10_000,
    )
    home_loan_interest = st.number_input(
        "Home Loan Interest (Annual) ₹", min_value=0, max_value=20_00_000,
        value=int(sb.get("home_loan_interest", 0)), step=10_000,
    )

    # ── Insurance ─────────────────────────────────────────────────────────────
    st.markdown('<p class="wp-section">🛡️ Insurance</p>', unsafe_allow_html=True)

    has_term = st.checkbox("Has Term Insurance", value=bool(sb.get("has_term_insurance", False)))
    term_cover = 0
    if has_term:
        term_cover = st.number_input(
            "Term Cover Amount ₹", min_value=0, max_value=50_00_00_000,
            value=int(sb.get("term_cover", 1_00_00_000)), step=10_00_000,
        )

    has_health = st.checkbox("Has Health Insurance", value=bool(sb.get("has_health_insurance", False)))
    health_cover = 0
    if has_health:
        health_cover = st.number_input(
            "Health Cover Amount ₹", min_value=0, max_value=2_00_00_000,
            value=int(sb.get("health_cover", 5_00_000)), step=1_00_000,
        )

    # ── Investments & Deductions ──────────────────────────────────────────────
    st.markdown('<p class="wp-section">💰 Investments & Deductions</p>', unsafe_allow_html=True)

    epf_annual = st.number_input(
        "EPF Annual ₹", min_value=0, max_value=5_00_000,
        value=int(sb.get("epf_annual", 21_600)), step=1_000,
    )
    sec_80c = st.number_input(
        "Section 80C (PPF/ELSS/LIC excl. EPF) ₹",
        min_value=0, max_value=1_50_000, value=int(sb.get("sec_80c", 0)), step=5_000,
    )
    nps_annual = st.number_input(
        "NPS 80CCD(1B) Annual ₹", min_value=0, max_value=50_000,
        value=int(sb.get("nps_annual", 0)), step=5_000,
    )
    sec_80d = st.number_input(
        "Section 80D (Health Insurance Premium) ₹",
        min_value=0, max_value=1_00_000, value=int(sb.get("sec_80d", 0)), step=1_000,
    )
    monthly_sip = st.number_input(
        "Monthly SIP ₹", min_value=0, max_value=5_00_000,
        value=int(sb.get("monthly_sip", 10_000)), step=1_000,
    )
    total_equity = st.number_input(
        "Total Equity Investments ₹", min_value=0, max_value=50_00_00_000,
        value=int(sb.get("total_equity", 0)), step=10_000,
    )
    total_debt = st.number_input(
        "Total Debt Investments ₹", min_value=0, max_value=50_00_00_000,
        value=int(sb.get("total_debt", 0)), step=10_000,
    )

    # ── Lifestyle ────────────────────────────────────────────────────────────
    st.markdown('<p class="wp-section">📊 Lifestyle</p>', unsafe_allow_html=True)

    monthly_expenses = st.number_input(
        "Monthly Expenses ₹", min_value=0, max_value=10_00_000,
        value=int(sb.get("monthly_expenses", 40_000)), step=1_000,
    )
    emergency_fund = st.number_input(
        "Emergency Fund Available ₹", min_value=0, max_value=50_00_00_000,
        value=int(sb.get("emergency_fund", 1_00_000)), step=10_000,
    )
    retirement_age = st.number_input(
        "Target Retirement Age", min_value=30, max_value=80,
        value=int(sb.get("retirement_age", 55)), step=1,
    )

    # ── Upload Form 16 ────────────────────────────────────────────────────────
    st.markdown('<p class="wp-section">📄 Upload Documents (Optional)</p>', unsafe_allow_html=True)

    form16_file = st.file_uploader(
        "Upload Form 16 PDF",
        type=["pdf"],
        help="Gemini Vision will auto-extract your salary and deduction data",
    )

    if form16_file is not None:
        with st.spinner("Parsing Form 16 with Gemini Vision…"):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(form16_file.read())
                    tmp_path = tmp.name
                parsed = parse_form16_safe(tmp_path, config.GEMINI_API_KEY)
                os.unlink(tmp_path)
                if parsed:
                    st.success("✅ Form 16 parsed! Fields auto-filled below.")
                    # Merge parsed values into session state for next render
                    for k, v in parsed.items():
                        if v is not None:
                            st.session_state["sb"][k] = v
                    st.rerun()
                else:
                    st.warning("⚠️ Could not fully parse Form 16. Please fill in manually.")
            except Exception as e:
                st.warning(f"⚠️ Form 16 parsing failed: {e}. Please fill in manually.")

    st.divider()

    # ── Demo button ───────────────────────────────────────────────────────────
    if st.button("📋 Load Demo Data", use_container_width=True):
        st.session_state["sb"] = DEMO_DATA.copy()
        st.session_state["analysis_done"] = False
        st.rerun()

    # ── Analyse ───────────────────────────────────────────────────────────────
    analyze_clicked = st.button(
        "🚀 Analyze My Finances",
        type="primary",
        use_container_width=True,
    )


# ── Build user_data from sidebar ────────────────────────────────────────────
user_data: Dict[str, Any] = {
    "age": int(age),
    "annual_income": float(annual_income),
    "city": city,
    "is_metro": is_metro,
    "monthly_rent": float(monthly_rent),
    "hra_received": float(hra_received),
    "home_loan_interest": float(home_loan_interest),
    "has_term_insurance": has_term,
    "term_cover": float(term_cover),
    "has_health_insurance": has_health,
    "health_cover": float(health_cover),
    "epf_annual": float(epf_annual),
    "sec_80c": float(sec_80c),
    "nps_annual": float(nps_annual),
    "sec_80d": float(sec_80d),
    "monthly_sip": float(monthly_sip),
    "total_equity": float(total_equity),
    "total_debt": float(total_debt),
    "monthly_expenses": float(monthly_expenses),
    "emergency_fund": float(emergency_fund),
    "retirement_age": int(retirement_age),
}

# ── Trigger analysis ─────────────────────────────────────────────────────────
if analyze_clicked:
    with st.spinner("Crunching your numbers…"):
        try:
            results = run_full_analysis(user_data)
            st.session_state["results"] = results
            st.session_state["user_data"] = user_data
            st.session_state["analysis_done"] = True
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            st.session_state["analysis_done"] = False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════

if not st.session_state["analysis_done"]:
    # ── Hero / landing ───────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; padding: 3rem 0 2rem;">
          <h1 class="hero-title">💰 WealthPilot</h1>
          <p style="font-size:1.25rem; color:#a5b4fc; margin-top:-0.5rem; font-weight:500;">
            Your AI-powered personal finance co-pilot for India
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    for col, icon, title, desc in [
        (col1, "🧾", "Tax Optimiser", "Old vs New Regime comparison with missed-deduction finder"),
        (col2, "❤️", "Money Health", "6-dimension financial health score with personalised tips"),
        (col3, "🔥", "FIRE Planner", "Your path to financial independence with SIP projections"),
        (col4, "📥", "PDF Report", "Professional report with Gemini-powered executive summary"),
    ]:
        with col:
            st.markdown(
                f"""<div class="feature-card" style="height:180px;">
                  <div style="font-size:2.5rem; margin-bottom:12px;">{icon}</div>
                  <div style="font-weight:700; margin:8px 0 4px; color:#a5b4fc; font-size:1.1rem;">{title}</div>
                  <div style="font-size:0.85rem; color:#818cf8;">{desc}</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<p style='text-align:center; color:#64748b; margin-top:2rem;'>"
        "Fill in your details in the left sidebar and click <b style='color:#a855f7;'>🚀 Analyze My Finances</b></p>",
        unsafe_allow_html=True,
    )
    st.stop()


# ── Results available ─────────────────────────────────────────────────────────
results: Dict = st.session_state["results"]
ud: Dict = st.session_state["user_data"]
tax: Dict = results.get("tax", {})
health: Dict = results.get("health", {})
fire: Dict = results.get("fire", {})

# Top KPI strip
st.markdown("---")
kc1, kc2, kc3, kc4 = st.columns(4)
kc1.metric("💰 Annual Income", _inr_lakh(ud["annual_income"]))
kc2.metric(
    "🧾 Recommended Regime",
    tax.get("recommended", "—") + " Regime",
    delta=f"Saves {_inr(tax.get('savings', 0))}",
    delta_color="normal",
)
kc3.metric(
    "❤️ Health Score",
    f"{health.get('overall_score', 0):.0f} / 100",
    delta=None,
)
kc4.metric(
    "🔥 FIRE Gap",
    _inr_lakh(fire.get("gap", 0)),
    delta="On Track" if fire.get("gap", 0) >= 0 else "Shortfall",
    delta_color="normal" if fire.get("gap", 0) >= 0 else "inverse",
)
st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧾 Tax Optimizer",
    "❤️ Money Health",
    "🔥 FIRE Planner",
    "📊 Portfolio",
    "📥 Download Report",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — TAX OPTIMIZER
# ════════════════════════════════════════════════════════════════════════════════

with tab1:
    old_tax = tax.get("old_regime_tax", 0)
    new_tax = tax.get("new_regime_tax", 0)
    rec = tax.get("recommended", "New")
    savings = tax.get("savings", 0)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 🏛️ Old Regime")
        st.metric("Tax Payable", _inr(old_tax), delta=None)
        eff_old = tax.get("old_effective_rate", 0)
        st.caption(f"Effective rate: {eff_old:.2f}%  |  Taxable income: {_inr(tax.get('old_taxable_income',0))}")
    with c2:
        st.markdown("### 🆕 New Regime")
        st.metric("Tax Payable", _inr(new_tax), delta=None)
        eff_new = tax.get("new_effective_rate", 0)
        st.caption(f"Effective rate: {eff_new:.2f}%  |  Taxable income: {_inr(tax.get('new_taxable_income',0))}")

    # Recommendation banner
    banner_gradient = "linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(52, 211, 153, 0.1))" if rec == "Old" else "linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.1))"
    text_color   = "#34d399" if rec == "Old" else "#a78bfa"
    border_color  = "#34d399" if rec == "Old" else "#a855f7"
    st.markdown(
        f"""<div style="background:{banner_gradient}; border-radius:16px; padding:20px 24px; margin:20px 0;
                        border-left:4px solid {border_color}; backdrop-filter:blur(10px);">
          <span style="font-size:1.2rem; font-weight:700; color:{text_color};">
            ✅ Switch to {rec} Regime — Save <span style="color:#fff;">{_inr(savings)}/year</span>
          </span>
        </div>""",
        unsafe_allow_html=True,
    )

    # Bar comparison chart
    fig_bar = go.Figure(data=[
        go.Bar(name="Old Regime", x=["Old Regime"], y=[old_tax],
               marker_color="#ef4444", text=[_inr(old_tax)], textposition="auto",
               marker_line_color="#f87171", marker_line_width=2),
        go.Bar(name="New Regime", x=["New Regime"], y=[new_tax],
               marker_color="#10b981", text=[_inr(new_tax)], textposition="auto",
               marker_line_color="#34d399", marker_line_width=2),
    ])
    fig_bar.update_layout(
        title=dict(text="Old vs New Regime Tax Comparison", font=dict(color="#e2e8f0")),
        yaxis_title=dict(text="Tax Payable (₹)", font=dict(color="#a5b4fc")),
        yaxis=dict(gridcolor="rgba(99, 102, 241, 0.1)", color="#a5b4fc"),
        xaxis=dict(color="#a5b4fc"),
        barmode="group",
        plot_bgcolor="rgba(15, 23, 42, 0)",
        paper_bgcolor="rgba(15, 23, 42, 0)",
        font=dict(color="#e2e8f0"),
        height=320,
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # Missed deductions table
    missed = tax.get("missed_deductions", [])
    if missed:
        st.markdown("#### 💡 Missed Deduction Opportunities")
        rows_html = ""
        for m in missed:
            pot = m.get("potential_tax_saving", 0)
            rows_html += (
                f"<tr style='border-bottom:1px solid rgba(99, 102, 241, 0.1);'>"
                f"<td style='padding:12px;'>{m.get('section','')}</td>"
                f"<td style='padding:12px;'>{_inr(m.get('current_amount',0))}</td>"
                f"<td style='padding:12px;'>{_inr(m.get('limit',0))}</td>"
                f"<td style='padding:12px;'>{_inr(m.get('gap',0))}</td>"
                f"<td style='color:#34d399;font-weight:bold;padding:12px;'>{_inr(pot)}</td></tr>"
            )
        st.markdown(
            f"""<table style="width:100%;border-collapse:collapse;font-size:0.9rem;
                background:rgba(99, 102, 241, 0.05);border-radius:12px;overflow:hidden;">
            <thead><tr style="background:linear-gradient(135deg, #6366f1, #a855f7);color:#fff;">
            <th style="padding:12px">Section</th><th>Claimed</th><th>Limit</th>
            <th>Gap</th><th>Tax You Can Save</th></tr></thead>
            <tbody style="color:#e2e8f0;">{rows_html}</tbody></table>""",
            unsafe_allow_html=True,
        )
        total_pot = sum(m.get("potential_tax_saving", 0) for m in missed)
        st.success(f"**Total potential additional tax saving: {_inr(total_pot)}/year**")

        # Waterfall chart
        labels  = [m.get("section", "?") for m in missed] + ["Total Saving"]
        values  = [m.get("potential_tax_saving", 0) for m in missed]
        measures = ["relative"] * len(missed) + ["total"]
        values_wf = values + [sum(values)]

        fig_wf = go.Figure(go.Waterfall(
            name="Tax Savings",
            orientation="v",
            measure=measures,
            x=labels,
            y=values_wf,
            connector={"line": {"color": "#6366f1"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#10b981"}},
            totals={"marker": {"color": "#a855f7"}},
            text=[_inr(v) for v in values_wf],
            textposition="outside",
            textfont=dict(color="#e2e8f0"),
        ))
        fig_wf.update_layout(
            title=dict(text="Tax Savings Breakdown", font=dict(color="#e2e8f0")),
            xaxis=dict(color="#a5b4fc"),
            yaxis=dict(gridcolor="rgba(99, 102, 241, 0.1)", color="#a5b4fc"),
            plot_bgcolor="rgba(15, 23, 42, 0)",
            paper_bgcolor="rgba(15, 23, 42, 0)",
            font=dict(color="#e2e8f0"),
            height=350, margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig_wf, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — MONEY HEALTH
# ════════════════════════════════════════════════════════════════════════════════

with tab2:
    overall = health.get("overall_score", 0)
    scores  = health.get("scores", {})

    col_score, col_radar = st.columns([1, 2])
    with col_score:
        sc_class = _score_color(overall)
        grade = "Excellent 🌟" if overall >= 70 else ("Good 👍" if overall >= 50 else "Needs Attention ⚠️")
        st.markdown(
            f"""<div style="text-align:center; padding: 32px; background:linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(168, 85, 247, 0.1));
                   border-radius:24px; border:2px solid rgba(168, 85, 247, 0.4); backdrop-filter:blur(10px);">
              <div style="font-size:4.5rem; font-weight:800; background:linear-gradient(135deg, #6366f1, #a855f7, #ec4899);
                  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;">{overall:.0f}</div>
              <div style="font-size:1rem; color:#a5b4fc">out of 100</div>
              <div style="margin-top:12px; font-weight:700; font-size:1.1rem; color:#e2e8f0">{grade}</div>
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown("#### Dimension Scores")
        label_map = {
            "emergency": "Emergency Fund",
            "insurance": "Insurance",
            "investment": "Investments",
            "debt": "Debt Health",
            "tax": "Tax Efficiency",
            "retirement": "Retirement",
        }
        for key, label in label_map.items():
            sc = scores.get(key, 0)
            cl = _score_color(sc)
            st.markdown(
                f'<span class="score-badge {cl}">{label}: {sc:.0f}</span>',
                unsafe_allow_html=True,
            )

    with col_radar:
        cats = list(label_map.values())
        vals = [scores.get(k, 0) for k in label_map]
        vals_closed = vals + [vals[0]]
        cats_closed = cats + [cats[0]]

        fig_radar = go.Figure(go.Scatterpolar(
            r=vals_closed, theta=cats_closed,
            fill="toself",
            line=dict(color="#a855f7", width=3),
            fillcolor="rgba(168, 85, 247, 0.25)",
            marker=dict(size=8, color="#ec4899"),
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(99, 102, 241, 0.2)", color="#a5b4fc"),
                angularaxis=dict(gridcolor="rgba(99, 102, 241, 0.2)", color="#a5b4fc")
            ),
            showlegend=False,
            title=dict(text="Financial Health Radar", font=dict(color="#e2e8f0")),
            paper_bgcolor="rgba(15, 23, 42, 0)",
            font=dict(color="#e2e8f0"),
            height=380,
            margin=dict(l=30, r=30, t=50, b=30),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    # Recommendations
    st.markdown("#### 🎯 Top 3 Recommendations")
    recs = health.get("recommendations", [])
    colors = ["rgba(99, 102, 241, 0.15)", "rgba(245, 158, 11, 0.15)", "rgba(236, 72, 153, 0.15)"]
    borders = ["#6366f1", "#f59e0b", "#ec4899"]
    text_colors = ["#a5b4fc", "#fbbf24", "#f472b6"]
    for i, (rec, bg, bd, tc) in enumerate(zip(recs, colors, borders, text_colors)):
        st.markdown(
            f"""<div style="background:{bg}; border-left:4px solid {bd};
                   padding:16px 20px; border-radius:0 16px 16px 0; margin:12px 0;
                   backdrop-filter:blur(10px); transition:all 0.3s ease;">
              <span style="display:inline-block; width:28px; height:28px; border-radius:50%;
                  background:linear-gradient(135deg, {bd}, {tc}); text-align:center; line-height:28px;
                  font-weight:700; color:#fff; margin-right:12px;">{i+1}</span>
              <span style="color:#e2e8f0;">{rec}</span>
            </div>""",
            unsafe_allow_html=True,
        )

    # Expandable dimension details
    detail = health.get("score_detail", {})
    if detail:
        st.markdown("#### 🔍 Detailed Breakdown")
        short_to_long = {
            "EMERGENCY_PREPAREDNESS": "emergency",
            "INSURANCE_COVERAGE": "insurance",
            "INVESTMENT_DIVERSIFICATION": "investment",
            "DEBT_HEALTH": "debt",
            "TAX_EFFICIENCY": "tax",
            "RETIREMENT_READINESS": "retirement",
        }
        for cat, info in detail.items():
            short_key = short_to_long.get(cat, "")
            sc = info.get("score", 0)
            expl = info.get("explanation", "")
            with st.expander(f"{label_map.get(short_key, cat)} — {sc:.0f}/100"):
                st.write(expl)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — FIRE PLANNER
# ════════════════════════════════════════════════════════════════════════════════

with tab3:
    fire_num  = fire.get("fire_number", 0)
    proj_corpus = fire.get("current_projection", 0)
    gap       = fire.get("gap", 0)
    req_sip   = fire.get("required_sip", 0)
    years_ret = fire.get("years_to_retire", 0)
    fire_age  = fire.get("fire_achievable_age")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🏁 FIRE Number", _inr_lakh(fire_num))
    m2.metric("📈 Projected Corpus", _inr_lakh(proj_corpus))
    m3.metric(
        "🔥 Gap",
        _inr_lakh(abs(gap)),
        delta="Surplus" if gap >= 0 else "Shortfall",
        delta_color="normal" if gap >= 0 else "inverse",
    )
    m4.metric("💸 Required SIP", _inr(req_sip) + "/mo")

    # Return rate slider
    return_rate = st.slider(
        "Expected Annual Return (%)",
        min_value=8, max_value=15, value=12, step=1,
        format="%d%%",
    )

    # Recompute projections with selected return rate
    try:
        from utils.projections import fire_plan as _fp
        recalc = _fp(
            current_age=ud["age"],
            retirement_age=ud["retirement_age"],
            monthly_income=ud["annual_income"] / 12,
            monthly_expenses=ud["monthly_expenses"],
            current_corpus=ud["total_equity"] + ud["total_debt"],
            current_monthly_sip=ud["monthly_sip"],
            expected_return=return_rate / 100,
        )
        proj_list = recalc["year_by_year"]
    except Exception:
        proj_list = fire.get("projections", [])

    if proj_list:
        years_list    = [e["year"] for e in proj_list]
        corpus_list   = [e.get("corpus", e.get("value", 0)) for e in proj_list]
        # Cumulative invested = corpus at year 0 + sip * 12 * year
        sip = ud["monthly_sip"]
        init_corpus = ud["total_equity"] + ud["total_debt"]
        invested_list = [round(init_corpus + sip * 12 * e["year"], 0) for e in proj_list]

        fig_fire = go.Figure()
        fig_fire.add_trace(go.Scatter(
            x=years_list, y=invested_list,
            name="Amount Invested",
            fill="tozeroy",
            line=dict(color="#f59e0b", width=2),
            fillcolor="rgba(245, 158, 11, 0.15)",
        ))
        fig_fire.add_trace(go.Scatter(
            x=years_list, y=corpus_list,
            name="Portfolio Value",
            fill="tonexty",
            line=dict(color="#a855f7", width=3),
            fillcolor="rgba(168, 85, 247, 0.2)",
        ))
        # FIRE number line
        fig_fire.add_hline(
            y=fire_num,
            line_dash="dash", line_color="#ec4899", line_width=2,
            annotation_text=f"FIRE Target {_inr_lakh(fire_num)}",
            annotation_position="top left",
            annotation=dict(font=dict(color="#f472b6")),
        )
        fig_fire.update_layout(
            title=dict(text=f"Portfolio Growth @ {return_rate}% Return", font=dict(color="#e2e8f0")),
            xaxis_title=dict(text="Years from Now", font=dict(color="#a5b4fc")),
            yaxis_title=dict(text="Corpus (₹)", font=dict(color="#a5b4fc")),
            xaxis=dict(gridcolor="rgba(99, 102, 241, 0.1)", color="#a5b4fc"),
            yaxis=dict(gridcolor="rgba(99, 102, 241, 0.1)", color="#a5b4fc"),
            plot_bgcolor="rgba(15, 23, 42, 0)",
            paper_bgcolor="rgba(15, 23, 42, 0)",
            font=dict(color="#e2e8f0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(color="#a5b4fc")),
            height=400,
            margin=dict(l=0, r=0, t=50, b=0),
        )
        st.plotly_chart(fig_fire, use_container_width=True)

    # Milestones table
    if proj_list:
        st.markdown("#### 🏁 Milestones")
        milestone_data = [
            e for e in proj_list
            if e["year"] % max(1, years_ret // 5) == 0 or e["year"] == years_ret
        ][:6]
        if milestone_data:
            cols_ms = st.columns(len(milestone_data))
            for col_m, entry in zip(cols_ms, milestone_data):
                col_m.metric(
                    f"Year {entry['year']} (Age {entry.get('age','?')})",
                    _inr_lakh(entry.get("corpus", entry.get("value", 0))),
                )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — PORTFOLIO TRACKER
# ════════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown("### 📊 Manual Portfolio Tracker")
    st.caption("Add your mutual fund / stock holdings to track returns.")

    if "portfolio_holdings" not in st.session_state:
        st.session_state["portfolio_holdings"] = []

    with st.expander("➕ Add Holding"):
        pc1, pc2, pc3 = st.columns(3)
        fund_name  = pc1.text_input("Fund / Stock Name", key="pf_name")
        invested   = pc2.number_input("Invested ₹", min_value=0, step=1000, key="pf_inv")
        curr_value = pc3.number_input("Current Value ₹", min_value=0, step=1000, key="pf_curr")
        if st.button("Add Holding"):
            if fund_name:
                st.session_state["portfolio_holdings"].append({
                    "name": fund_name,
                    "invested": float(invested),
                    "current": float(curr_value),
                })
                st.rerun()

    holdings = st.session_state["portfolio_holdings"]
    # Seed with the equity / debt from sidebar if holdings empty
    if not holdings and (ud["total_equity"] > 0 or ud["total_debt"] > 0):
        holdings = [
            {"name": "Equity Portfolio",  "invested": ud["total_equity"] * 0.85, "current": ud["total_equity"]},
            {"name": "Debt Portfolio",    "invested": ud["total_debt"]  * 0.95, "current": ud["total_debt"]},
        ]

    if holdings:
        total_inv  = sum(h["invested"] for h in holdings)
        total_curr = sum(h["current"]  for h in holdings)
        total_ret  = total_curr - total_inv
        ret_pct    = total_ret / total_inv * 100 if total_inv > 0 else 0

        r1, r2, r3 = st.columns(3)
        r1.metric("Total Invested",  _inr(total_inv))
        r2.metric("Current Value",   _inr(total_curr))
        r3.metric("Total Returns",   _inr(total_ret), delta=f"{ret_pct:+.1f}%")

        # Holdings table
        st.markdown("#### Holdings")
        rows_html = ""
        for h in holdings:
            ret_h = h["current"] - h["invested"]
            ret_pct_h = ret_h / h["invested"] * 100 if h["invested"] > 0 else 0
            color = "#34d399" if ret_h >= 0 else "#f87171"
            rows_html += (
                f"<tr style='border-bottom:1px solid rgba(99, 102, 241, 0.1);'>"
                f"<td style='padding:12px;'>{h['name']}</td>"
                f"<td style='padding:12px;'>{_inr(h['invested'])}</td>"
                f"<td style='padding:12px;'>{_inr(h['current'])}</td>"
                f"<td style='color:{color};font-weight:bold;padding:12px;'>{_inr(ret_h)} ({ret_pct_h:+.1f}%)</td></tr>"
            )
        st.markdown(
            f"""<table style="width:100%;border-collapse:collapse;font-size:0.9rem;
                background:rgba(99, 102, 241, 0.05);border-radius:12px;overflow:hidden;">
            <thead><tr style="background:linear-gradient(135deg, #6366f1, #a855f7);color:#fff;">
            <th style="padding:12px">Name</th><th>Invested</th><th>Current</th><th>Returns</th>
            </tr></thead><tbody style="color:#e2e8f0;">{rows_html}</tbody></table>""",
            unsafe_allow_html=True,
        )

        # Pie chart
        fig_pie = go.Figure(go.Pie(
            labels=[h["name"] for h in holdings],
            values=[h["current"] for h in holdings],
            hole=0.45,
            marker=dict(colors=["#6366f1", "#8b5cf6", "#a855f7", "#c084fc", "#e879f9",
                                 "#f59e0b", "#ec4899", "#10b981"], line=dict(color="rgba(15, 23, 42, 0.5)", width=2)),
            textfont=dict(color="#e2e8f0"),
            textinfo="label+percent",
        ))
        fig_pie.update_layout(
            title=dict(text="Portfolio Allocation by Current Value", font=dict(color="#e2e8f0")),
            paper_bgcolor="rgba(15, 23, 42, 0)",
            font=dict(color="#e2e8f0"),
            height=380,
            margin=dict(l=0, r=0, t=50, b=0),
            legend=dict(font=dict(color="#a5b4fc")),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        if st.button("🗑️ Clear Holdings"):
            st.session_state["portfolio_holdings"] = []
            st.rerun()
    else:
        st.info("Add your first holding above to start tracking.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — DOWNLOAD REPORT
# ════════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("### 📥 Download Your Personal Report")

    # Summary
    st.markdown("#### Summary of Key Findings")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f"**Tax**\n\n"
            f"- Recommended: **{tax.get('recommended','—')} Regime**\n"
            f"- Annual saving: **{_inr(tax.get('savings',0))}**\n"
            f"- Missed deductions: **{len(tax.get('missed_deductions',[]))} found**",
        )
    with s2:
        st.markdown(
            f"**Health**\n\n"
            f"- Overall score: **{health.get('overall_score',0):.0f}/100**\n"
            f"- Weakest area: **{min(health.get('scores',{}).items(), key=lambda x:x[1])[0] if health.get('scores') else '—'}**",
        )
    with s3:
        st.markdown(
            f"**FIRE**\n\n"
            f"- FIRE number: **{_inr_lakh(fire.get('fire_number',0))}**\n"
            f"- Status: **{'On Track ✅' if fire.get('gap',0)>=0 else 'Shortfall ⚠️'}**\n"
            f"- Required SIP: **{_inr(fire.get('required_sip',0))}/mo**",
        )

    st.divider()

    # PDF download
    col_pdf, col_txt = st.columns(2)

    with col_pdf:
        if st.button("📄 Generate PDF Report", type="primary"):
            with st.spinner("Generating PDF with Gemini narrative…"):
                try:
                    pdf_bytes = generate_report(
                        results,
                        gemini_api_key=config.GEMINI_API_KEY,
                    )
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=(
                            f"WealthPilot_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
                        ),
                        mime="application/pdf",
                    )
                except Exception as exc:
                    st.error(f"PDF generation failed: {exc}")

    with col_txt:
        # Plain-text summary
        txt_lines = [
            "WEALTHPILOT FINANCIAL REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 50,
            "",
            "TAX ANALYSIS",
            f"  Old Regime Tax: {_inr(tax.get('old_regime_tax',0))}",
            f"  New Regime Tax: {_inr(tax.get('new_regime_tax',0))}",
            f"  Recommended:    {tax.get('recommended','—')} Regime",
            f"  Annual Saving:  {_inr(tax.get('savings',0))}",
            "",
            "FINANCIAL HEALTH",
            f"  Overall Score: {health.get('overall_score',0):.0f}/100",
        ]
        for k, v in health.get("scores", {}).items():
            txt_lines.append(f"  {k.capitalize()}: {v:.0f}/100")
        txt_lines += [
            "",
            "FIRE PLAN",
            f"  FIRE Number:     {_inr_lakh(fire.get('fire_number',0))}",
            f"  Projected Corpus:{_inr_lakh(fire.get('current_projection',0))}",
            f"  Gap:             {_inr_lakh(fire.get('gap',0))}",
            f"  Required SIP:    {_inr(fire.get('required_sip',0))}/mo",
            "",
            "=" * 50,
            "WealthPilot | Confidential",
        ]
        txt_content = "\n".join(txt_lines)
        st.download_button(
            label="📝 Download Text Summary",
            data=txt_content,
            file_name=f"WealthPilot_Summary_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
        )

