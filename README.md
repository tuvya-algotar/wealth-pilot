# 💰 WealthPilot

**WealthPilot** is an AI-powered personal finance co-pilot for India. Built with Streamlit, it provides a comprehensive financial planning dashboard covering tax optimisation, financial health scoring, FIRE planning, and portfolio tracking.

---

## ✨ Features

| Module | Description |
|---|---|
| 🧾 **Tax Optimiser** | Compares Old vs. New Tax Regime (Budget 2024–25), identifies missed deductions and calculates potential savings |
| ❤️ **Money Health Score** | 6-dimension financial health radar (Emergency Fund, Insurance, Investments, Debt, Tax Efficiency, Retirement Readiness) |
| 🔥 **FIRE Planner** | Interactive corpus projection with customisable return rates and SIP step-up calculator |
| 📊 **Portfolio Tracker** | Manual equity / debt holding tracker with returns breakdown |
| 📄 **Form 16 Parser** | Gemini Vision-powered automatic data extraction from Form 16 PDF |
| 📥 **PDF Report** | Professional downloadable financial report with AI-generated executive summary |

---

## 🛠️ Tech Stack

- **Frontend / UI**: [Streamlit](https://streamlit.io/) + Plotly
- **AI / LLM**: [Google Gemini](https://ai.google.dev/) (document parsing & report generation), [Groq](https://groq.com/) (fast intake agent)
- **Calculations**: Pure Python (tax engine, health scorer, FIRE projections, SIP calculator)
- **PDF**: FPDF2 + PyMuPDF

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/tuvya-algotar/wealth-pilot.git
cd wealthpilot
```

### 2. Set up a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

Create a `.env` file (or set environment variables):

```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

> Keys are read automatically from environment variables in `config.py`.

### 5. Run the app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## 📁 Project Structure

```
wealthpilot/
├── app.py                  # Main Streamlit application
├── config.py               # API keys & financial constants
├── requirements.txt        # Python dependencies
├── agents/
│   ├── document_parser.py  # Gemini Vision Form 16 parser
│   └── report_generator.py # AI-powered PDF report generator
├── engine/
│   ├── tax_engine.py       # Old/New regime tax calculations
│   ├── health_scorer.py    # 6-dimension health scoring
│   └── sip_calculator.py   # SIP & FIRE projection engine
└── utils/
    ├── adapter.py           # Unified analysis runner
    └── projections.py       # Year-by-year corpus projections
```

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.
