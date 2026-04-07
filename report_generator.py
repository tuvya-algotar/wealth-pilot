"""
report_generator.py
WealthPilot Professional Financial Report Generator

Generates beautiful, multi-page PDF financial reports using fpdf2.
"""

from fpdf import FPDF
from datetime import datetime
from typing import Dict, List, Any, Optional
import io


# ============================================================================
# COLOR DEFINITIONS
# ============================================================================

class Colors:
    """Brand and status colors for the report"""
    # Brand colors
    PRIMARY_BLUE = (41, 65, 122)       # #29417A
    SECONDARY_BLUE = (70, 130, 180)    # Steel blue
    LIGHT_BLUE = (230, 240, 250)       # Light background
    
    # Status colors
    GREEN = (34, 139, 34)              # Forest green - positive
    LIGHT_GREEN = (220, 245, 220)      # Light green background
    RED = (220, 53, 69)                # Alert red
    LIGHT_RED = (255, 230, 230)        # Light red background
    ORANGE = (255, 140, 0)             # Warning orange
    LIGHT_ORANGE = (255, 245, 220)     # Light orange background
    
    # Neutral colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (128, 128, 128)
    LIGHT_GRAY = (245, 245, 245)
    DARK_GRAY = (64, 64, 64)


# ============================================================================
# CUSTOM PDF CLASS
# ============================================================================

class WealthPilotPDF(FPDF):
    """Custom PDF class with WealthPilot branding and utilities"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        
    def header(self):
        """Add header to each page (except cover)"""
        if self.page_no() > 1:
            # Header line
            self.set_draw_color(*Colors.PRIMARY_BLUE)
            self.set_line_width(0.5)
            self.line(10, 10, 200, 10)
            
            # Logo text
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(*Colors.PRIMARY_BLUE)
            self.set_xy(10, 12)
            self.cell(0, 5, 'WealthPilot Financial Report', align='L')
            
            # Page number
            self.set_xy(-30, 12)
            self.set_font('Helvetica', '', 9)
            self.set_text_color(*Colors.GRAY)
            self.cell(0, 5, f'Page {self.page_no()}', align='R')
            
            self.ln(15)
    
    def footer(self):
        """Add footer to each page"""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*Colors.GRAY)
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%B %d, %Y at %H:%M")} | Confidential', align='C')
    
    def section_title(self, title: str, icon: str = ""):
        """Add a styled section title"""
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*Colors.PRIMARY_BLUE)
        self.cell(0, 12, f"{icon} {title}" if icon else title, ln=True)
        
        # Underline
        self.set_draw_color(*Colors.PRIMARY_BLUE)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(8)
    
    def sub_section_title(self, title: str):
        """Add a styled sub-section title"""
        self.set_font('Helvetica', 'B', 12)
        self.set_text_color(*Colors.SECONDARY_BLUE)
        self.cell(0, 8, title, ln=True)
        self.ln(2)
    
    def info_box(self, text: str, box_type: str = "info"):
        """Add a colored info box"""
        colors = {
            "info": (Colors.LIGHT_BLUE, Colors.PRIMARY_BLUE),
            "success": (Colors.LIGHT_GREEN, Colors.GREEN),
            "warning": (Colors.LIGHT_ORANGE, Colors.ORANGE),
            "danger": (Colors.LIGHT_RED, Colors.RED)
        }
        bg_color, text_color = colors.get(box_type, colors["info"])
        
        self.set_fill_color(*bg_color)
        self.set_text_color(*text_color)
        self.set_font('Helvetica', '', 10)
        
        # Calculate height needed
        self.set_x(15)
        self.multi_cell(180, 7, text, fill=True, border=0)
        self.ln(5)
        self.set_text_color(*Colors.BLACK)
    
    def data_table(self, headers: List[str], rows: List[List[str]], 
                   col_widths: Optional[List[int]] = None,
                   highlight_column: Optional[int] = None):
        """Create a styled data table"""
        if col_widths is None:
            col_widths = [190 // len(headers)] * len(headers)
        
        # Header row
        self.set_fill_color(*Colors.PRIMARY_BLUE)
        self.set_text_color(*Colors.WHITE)
        self.set_font('Helvetica', 'B', 10)
        
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            self.cell(width, 8, header, border=1, fill=True, align='C')
        self.ln()
        
        # Data rows
        self.set_text_color(*Colors.BLACK)
        self.set_font('Helvetica', '', 9)
        
        for row_idx, row in enumerate(rows):
            # Alternate row colors
            if row_idx % 2 == 0:
                self.set_fill_color(*Colors.LIGHT_GRAY)
            else:
                self.set_fill_color(*Colors.WHITE)
            
            for col_idx, (cell, width) in enumerate(zip(row, col_widths)):
                # Highlight specific column
                if highlight_column == col_idx:
                    self.set_font('Helvetica', 'B', 9)
                    # Color based on value
                    if any(c in str(cell).lower() for c in ['new regime', 'positive', 'good', 'high']):
                        self.set_text_color(*Colors.GREEN)
                    elif any(c in str(cell).lower() for c in ['old regime', 'negative', 'poor', 'low']):
                        self.set_text_color(*Colors.RED)
                else:
                    self.set_font('Helvetica', '', 9)
                    self.set_text_color(*Colors.BLACK)
                
                self.cell(width, 7, str(cell), border=1, fill=True, align='C')
            self.ln()
        
        self.ln(5)
        self.set_text_color(*Colors.BLACK)
    
    def score_indicator(self, score: float, max_score: float = 100, width: int = 100):
        """Draw a visual score indicator bar"""
        percentage = min(score / max_score, 1.0)
        bar_width = int(width * percentage)
        
        # Determine color based on score
        if percentage >= 0.7:
            color = Colors.GREEN
        elif percentage >= 0.4:
            color = Colors.ORANGE
        else:
            color = Colors.RED
        
        # Background bar
        self.set_fill_color(*Colors.LIGHT_GRAY)
        self.cell(width, 8, '', fill=True, border=1)
        
        # Move back to draw filled portion
        self.set_x(self.get_x() - width)
        self.set_fill_color(*color)
        if bar_width > 0:
            self.cell(bar_width, 8, '', fill=True)
        
        # Score text
        self.set_x(self.get_x() + (width - bar_width) + 5)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*color)
        self.cell(30, 8, f'{score:.0f}/{max_score:.0f}')
        self.set_text_color(*Colors.BLACK)


# ============================================================================
# PAGE GENERATORS
# ============================================================================

def create_cover_page(pdf: WealthPilotPDF, user_profile: Dict, health_score: Dict):
    """Create the cover page"""
    pdf.add_page()
    
    # Background gradient effect (simplified with rectangles)
    pdf.set_fill_color(*Colors.PRIMARY_BLUE)
    pdf.rect(0, 0, 210, 100, 'F')
    
    # Title
    pdf.set_y(30)
    pdf.set_font('Helvetica', 'B', 32)
    pdf.set_text_color(*Colors.WHITE)
    pdf.cell(0, 15, 'WealthPilot', align='C', ln=True)
    
    pdf.set_font('Helvetica', '', 18)
    pdf.cell(0, 10, 'Financial Report', align='C', ln=True)
    
    # Decorative line
    pdf.set_draw_color(*Colors.WHITE)
    pdf.set_line_width(1)
    pdf.line(70, 70, 140, 70)
    
    # User info section
    pdf.set_y(110)
    pdf.set_text_color(*Colors.DARK_GRAY)
    pdf.set_font('Helvetica', '', 14)
    
    user_name = user_profile.get('name', 'Valued Client')
    pdf.cell(0, 10, f'Prepared for: {user_name}', align='C', ln=True)
    
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 8, f'Report Date: {datetime.now().strftime("%B %d, %Y")}', align='C', ln=True)
    
    # Money Health Score - Big Display
    pdf.ln(20)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(*Colors.PRIMARY_BLUE)
    pdf.cell(0, 10, 'YOUR MONEY HEALTH SCORE', align='C', ln=True)
    
    overall_score = health_score.get('overall_score', 0)
    
    # Large score circle (simulated with text)
    pdf.ln(5)
    
    # Determine color based on score
    if overall_score >= 70:
        score_color = Colors.GREEN
        grade = 'EXCELLENT'
    elif overall_score >= 50:
        score_color = Colors.ORANGE
        grade = 'GOOD'
    elif overall_score >= 30:
        score_color = Colors.ORANGE
        grade = 'NEEDS ATTENTION'
    else:
        score_color = Colors.RED
        grade = 'CRITICAL'
    
    pdf.set_font('Helvetica', 'B', 72)
    pdf.set_text_color(*score_color)
    pdf.cell(0, 40, str(int(overall_score)), align='C', ln=True)
    
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 8, f'out of 100 - {grade}', align='C', ln=True)
    
    # Summary stats
    pdf.ln(15)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*Colors.DARK_GRAY)
    
    # Quick stats in a row
    income = user_profile.get('annual_income', 0)
    savings_rate = user_profile.get('savings_rate', 0) * 100 if user_profile.get('savings_rate', 0) <= 1 else user_profile.get('savings_rate', 0)
    
    pdf.cell(63, 8, f"Annual Income: Rs {income:,.0f}", align='C')
    pdf.cell(63, 8, f"Savings Rate: {savings_rate:.1f}%", align='C')
    pdf.cell(63, 8, f"Age: {user_profile.get('age', 'N/A')}", align='C', ln=True)


def create_tax_analysis_page(pdf: WealthPilotPDF, tax_result: Dict):
    """Create the tax analysis page"""
    pdf.add_page()
    
    pdf.section_title("Tax Analysis", "📊")
    
    # Regime Comparison Table
    pdf.sub_section_title("Tax Regime Comparison")
    
    old_regime = tax_result.get('old_regime', {})
    new_regime = tax_result.get('new_regime', {})
    
    comparison_data = [
        ["Gross Income", f"₹{old_regime.get('gross_income', 0):,.0f}", f"₹{new_regime.get('gross_income', 0):,.0f}"],
        ["Total Deductions", f"₹{old_regime.get('total_deductions', 0):,.0f}", f"₹{new_regime.get('total_deductions', 0):,.0f}"],
        ["Taxable Income", f"₹{old_regime.get('taxable_income', 0):,.0f}", f"₹{new_regime.get('taxable_income', 0):,.0f}"],
        ["Tax Payable", f"₹{old_regime.get('tax_payable', 0):,.0f}", f"₹{new_regime.get('tax_payable', 0):,.0f}"],
        ["Effective Rate", f"{old_regime.get('effective_rate', 0):.1f}%", f"{new_regime.get('effective_rate', 0):.1f}%"],
    ]
    
    pdf.data_table(
        headers=["Component", "Old Regime", "New Regime"],
        rows=comparison_data,
        col_widths=[80, 55, 55]
    )
    
    # Recommendation Box
    recommendation = tax_result.get('recommendation', 'new_regime')
    savings = abs(old_regime.get('tax_payable', 0) - new_regime.get('tax_payable', 0))
    
    rec_text = f"✓ RECOMMENDED: {'Old Regime' if recommendation == 'old_regime' else 'New Regime'}"
    rec_text += f"\n   Potential Annual Savings: ₹{savings:,.0f}"
    
    pdf.info_box(rec_text, "success")
    
    # Missed Deductions
    missed_deductions = tax_result.get('missed_deductions', [])
    if missed_deductions:
        pdf.ln(5)
        pdf.sub_section_title("Missed Tax-Saving Opportunities")
        
        deduction_rows = []
        total_potential = 0
        for d in missed_deductions[:6]:  # Top 6
            potential = d.get('potential_savings', 0)
            total_potential += potential
            deduction_rows.append([
                d.get('section', 'N/A'),
                d.get('description', '')[:40],
                f"₹{d.get('limit', 0):,.0f}",
                f"₹{potential:,.0f}"
            ])
        
        pdf.data_table(
            headers=["Section", "Description", "Limit", "Potential Savings"],
            rows=deduction_rows,
            col_widths=[30, 80, 40, 40]
        )
        
        # Total savings box
        pdf.info_box(f"💰 TOTAL POTENTIAL ANNUAL TAX SAVINGS: ₹{total_potential:,.0f}", "success")


def create_health_score_page(pdf: WealthPilotPDF, health_score: Dict):
    """Create the money health score detailed page"""
    pdf.add_page()
    
    pdf.section_title("Money Health Score Breakdown", "💪")
    
    # Dimension scores
    dimensions = health_score.get('dimensions', {})
    
    pdf.sub_section_title("Score by Dimension")
    
    # Create visual score table
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(*Colors.PRIMARY_BLUE)
    pdf.set_text_color(*Colors.WHITE)
    pdf.cell(60, 8, 'Dimension', border=1, fill=True, align='C')
    pdf.cell(30, 8, 'Score', border=1, fill=True, align='C')
    pdf.cell(100, 8, 'Visual Indicator', border=1, fill=True, align='C')
    pdf.ln()
    
    dimension_labels = {
        'emergency_fund': '🛡️ Emergency Fund',
        'debt_management': '💳 Debt Management',
        'savings_rate': '💰 Savings Rate',
        'insurance_coverage': '🏥 Insurance Coverage',
        'investment_diversification': '📈 Investment Diversification',
        'retirement_readiness': '🏖️ Retirement Readiness'
    }
    
    pdf.set_font('Helvetica', '', 10)
    for key, label in dimension_labels.items():
        score = dimensions.get(key, {})
        if isinstance(score, dict):
            score_value = score.get('score', 0)
        else:
            score_value = score
        
        # Determine color
        if score_value >= 70:
            color = Colors.GREEN
            status = '●●●●● Excellent'
        elif score_value >= 50:
            color = Colors.ORANGE
            status = '●●●○○ Good'
        elif score_value >= 30:
            color = Colors.ORANGE
            status = '●●○○○ Fair'
        else:
            color = Colors.RED
            status = '●○○○○ Needs Work'
        
        # Row background
        pdf.set_fill_color(*Colors.LIGHT_GRAY)
        pdf.set_text_color(*Colors.BLACK)
        pdf.cell(60, 8, label, border=1, fill=True)
        
        pdf.set_text_color(*color)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(30, 8, f'{score_value:.0f}/100', border=1, fill=True, align='C')
        
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(100, 8, status, border=1, fill=True, align='C')
        pdf.ln()
    
    pdf.set_text_color(*Colors.BLACK)
    pdf.ln(10)
    
    # Top Recommendations
    pdf.sub_section_title("Top Recommendations")
    
    recommendations = health_score.get('recommendations', [])
    
    for i, rec in enumerate(recommendations[:5], 1):
        # Priority badge
        priority = rec.get('priority', 'medium').upper()
        if priority == 'HIGH':
            pdf.set_fill_color(*Colors.LIGHT_RED)
            pdf.set_text_color(*Colors.RED)
        elif priority == 'MEDIUM':
            pdf.set_fill_color(*Colors.LIGHT_ORANGE)
            pdf.set_text_color(*Colors.ORANGE)
        else:
            pdf.set_fill_color(*Colors.LIGHT_GREEN)
            pdf.set_text_color(*Colors.GREEN)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(8, 7, str(i), border=0, fill=False)
        pdf.cell(18, 7, priority, border=0, fill=True, align='C')
        
        pdf.set_text_color(*Colors.BLACK)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 7, f"  {rec.get('title', rec.get('recommendation', ''))}", ln=True)
        
        # Description
        pdf.set_x(36)
        pdf.set_font('Helvetica', 'I', 9)
        pdf.set_text_color(*Colors.GRAY)
        description = rec.get('description', rec.get('action', ''))[:80]
        pdf.cell(0, 5, description, ln=True)
        pdf.ln(2)
    
    pdf.set_text_color(*Colors.BLACK)


def create_portfolio_page(pdf: WealthPilotPDF, portfolio_result: Dict):
    """Create the portfolio analysis page"""
    pdf.add_page()
    
    pdf.section_title("Portfolio Analysis", "📈")
    
    # Portfolio Summary
    summary = portfolio_result.get('summary', {})
    
    pdf.sub_section_title("Portfolio Overview")
    
    total_invested = summary.get('total_invested', 0)
    current_value = summary.get('current_value', 0)
    total_returns = current_value - total_invested
    returns_pct = (total_returns / total_invested * 100) if total_invested > 0 else 0
    xirr = summary.get('xirr', portfolio_result.get('xirr', 0))
    
    # Summary cards
    pdf.set_fill_color(*Colors.LIGHT_BLUE)
    
    # Row 1
    pdf.cell(63, 15, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 63 + 5, pdf.get_y() + 2)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(53, 5, 'Total Invested')
    pdf.set_xy(pdf.get_x() - 53, pdf.get_y() + 5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*Colors.PRIMARY_BLUE)
    pdf.cell(53, 5, f'Rs {total_invested:,.0f}')
    pdf.set_xy(pdf.get_x() + 10, pdf.get_y() - 7)
    
    pdf.cell(63, 15, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 63 + 5, pdf.get_y() + 2)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(53, 5, 'Current Value')
    pdf.set_xy(pdf.get_x() - 53, pdf.get_y() + 5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*Colors.GREEN if current_value >= total_invested else Colors.RED)
    pdf.cell(53, 5, f'Rs {current_value:,.0f}')
    pdf.set_xy(pdf.get_x() + 10, pdf.get_y() - 7)
    
    pdf.cell(63, 15, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 63 + 5, pdf.get_y() + 2)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(53, 5, 'Overall XIRR')
    pdf.set_xy(pdf.get_x() - 53, pdf.get_y() + 5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(*Colors.GREEN if xirr >= 0 else Colors.RED)
    pdf.cell(53, 5, f'{xirr:.1f}%')
    
    pdf.ln(20)
    pdf.set_text_color(*Colors.BLACK)
    
    # Holdings Table
    holdings = portfolio_result.get('holdings', [])
    if holdings:
        pdf.sub_section_title("Holdings Breakdown")
        
        holdings_rows = []
        for h in holdings[:8]:  # Top 8 holdings
            invested = h.get('invested', 0)
            current = h.get('current_value', 0)
            returns_val = current - invested
            returns_pct_h = (returns_val / invested * 100) if invested > 0 else 0
            
            holdings_rows.append([
                h.get('fund_name', h.get('name', 'N/A'))[:25],
                f"₹{invested:,.0f}",
                f"₹{current:,.0f}",
                f"{returns_pct_h:+.1f}%"
            ])
        
        pdf.data_table(
            headers=["Fund Name", "Invested", "Current", "Returns"],
            rows=holdings_rows,
            col_widths=[80, 40, 40, 30],
            highlight_column=3
        )
    
    # Overlap Analysis
    overlaps = portfolio_result.get('overlaps', [])
    if overlaps:
        pdf.sub_section_title("Portfolio Overlap Findings")
        
        for overlap in overlaps[:3]:
            funds = overlap.get('funds', [])
            overlap_pct = overlap.get('overlap_percentage', 0)
            
            pdf.set_font('Helvetica', '', 10)
            pdf.set_text_color(*Colors.ORANGE)
            pdf.cell(0, 6, f"⚠️ {overlap_pct:.0f}% overlap detected between:", ln=True)
            
            pdf.set_text_color(*Colors.DARK_GRAY)
            pdf.set_x(20)
            for fund in funds[:2]:
                pdf.cell(0, 5, f"• {fund}", ln=True)
                pdf.set_x(20)
            pdf.ln(2)
    
    # Rebalancing Suggestions
    suggestions = portfolio_result.get('rebalancing_suggestions', 
                                       portfolio_result.get('recommendations', []))
    if suggestions:
        pdf.ln(5)
        pdf.sub_section_title("Rebalancing Suggestions")
        
        pdf.set_text_color(*Colors.BLACK)
        for i, suggestion in enumerate(suggestions[:4], 1):
            if isinstance(suggestion, dict):
                text = suggestion.get('suggestion', suggestion.get('recommendation', ''))
            else:
                text = str(suggestion)
            
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, f"{i}. {text[:80]}", ln=True)


def create_fire_plan_page(pdf: WealthPilotPDF, fire_plan: Dict):
    """Create the FIRE plan page"""
    pdf.add_page()
    
    pdf.section_title("FIRE Plan - Financial Independence", "🔥")
    
    # Key Metrics
    pdf.sub_section_title("Your Path to Financial Independence")
    
    target_corpus = fire_plan.get('target_corpus', 0)
    current_corpus = fire_plan.get('current_corpus', 0)
    monthly_sip = fire_plan.get('monthly_sip_required', fire_plan.get('required_monthly_investment', 0))
    years_to_fire = fire_plan.get('years_to_fire', fire_plan.get('years_to_goal', 0))
    fire_age = fire_plan.get('fire_age', fire_plan.get('target_age', 0))
    
    # Big numbers display
    pdf.set_fill_color(*Colors.LIGHT_BLUE)
    
    # Target Corpus
    pdf.cell(95, 25, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 90, pdf.get_y() + 3)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(85, 5, 'Target Retirement Corpus')
    pdf.set_xy(pdf.get_x() - 85, pdf.get_y() + 7)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(*Colors.PRIMARY_BLUE)
    pdf.cell(85, 8, f'Rs {target_corpus:,.0f}')
    pdf.set_xy(pdf.get_x() + 10, pdf.get_y() - 10)
    
    # Monthly SIP Required
    pdf.set_fill_color(*Colors.LIGHT_GREEN)
    pdf.cell(95, 25, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 90, pdf.get_y() + 3)
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(85, 5, 'Monthly SIP Required')
    pdf.set_xy(pdf.get_x() - 85, pdf.get_y() + 7)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_text_color(*Colors.GREEN)
    pdf.cell(85, 8, f'Rs {monthly_sip:,.0f}')
    
    pdf.ln(30)
    
    # Additional Info Row
    pdf.set_fill_color(*Colors.LIGHT_GRAY)
    pdf.cell(63, 20, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 58, pdf.get_y() + 3)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(53, 5, 'Current Corpus')
    pdf.set_xy(pdf.get_x() - 53, pdf.get_y() + 6)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*Colors.BLACK)
    pdf.cell(53, 5, f'Rs {current_corpus:,.0f}')
    pdf.set_xy(pdf.get_x() + 10, pdf.get_y() - 9)
    
    pdf.cell(63, 20, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 58, pdf.get_y() + 3)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(53, 5, 'Years to FIRE')
    pdf.set_xy(pdf.get_x() - 53, pdf.get_y() + 6)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*Colors.PRIMARY_BLUE)
    pdf.cell(53, 5, f'{years_to_fire:.0f} years')
    pdf.set_xy(pdf.get_x() + 10, pdf.get_y() - 9)
    
    pdf.cell(63, 20, '', border=1, fill=True)
    pdf.set_xy(pdf.get_x() - 58, pdf.get_y() + 3)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*Colors.GRAY)
    pdf.cell(53, 5, 'FIRE Age')
    pdf.set_xy(pdf.get_x() - 53, pdf.get_y() + 6)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*Colors.GREEN)
    pdf.cell(53, 5, f'{fire_age:.0f} years old')
    
    pdf.ln(25)
    pdf.set_text_color(*Colors.BLACK)
    
    # Milestone Table
    pdf.sub_section_title("Year-by-Year Milestones (Every 5 Years)")
    
    milestones = fire_plan.get('milestones', fire_plan.get('yearly_projection', []))
    
    if milestones:
        milestone_rows = []
        for m in milestones:
            year = m.get('year', 0)
            if year % 5 == 0 or year == 1 or year == years_to_fire:  # Show every 5 years + first + last
                corpus = m.get('corpus', m.get('projected_corpus', 0))
                contributions = m.get('total_contributions', 0)
                growth = m.get('growth', corpus - contributions)
                
                milestone_rows.append([
                    f"Year {year}",
                    f"₹{corpus:,.0f}",
                    f"₹{contributions:,.0f}",
                    f"₹{growth:,.0f}"
                ])
        
        # Limit to reasonable number
        milestone_rows = milestone_rows[:8]
        
        pdf.data_table(
            headers=["Timeline", "Projected Corpus", "Total Invested", "Investment Growth"],
            rows=milestone_rows,
            col_widths=[35, 55, 50, 50]
        )
    
    # Assumptions
    pdf.ln(5)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(*Colors.GRAY)
    
    assumptions = fire_plan.get('assumptions', {})
    expected_return = assumptions.get('expected_return', 12)
    inflation = assumptions.get('inflation', 6)
    
    pdf.cell(0, 5, f"* Assumptions: Expected Return: {expected_return}% | Inflation: {inflation}% | SIP increases annually with inflation", ln=True)
    pdf.set_text_color(*Colors.BLACK)


def create_action_checklist_page(pdf: WealthPilotPDF, 
                                  tax_result: Dict, 
                                  health_score: Dict, 
                                  portfolio_result: Dict,
                                  fire_plan: Dict):
    """Create the action checklist page"""
    pdf.add_page()
    
    pdf.section_title("Action Checklist", "✅")
    
    # Compile all actions from different sources
    all_actions = []
    
    # Tax actions
    if tax_result.get('recommendation') == 'old_regime':
        savings = abs(tax_result.get('old_regime', {}).get('tax_payable', 0) - 
                     tax_result.get('new_regime', {}).get('tax_payable', 0))
        all_actions.append({
            'action': 'Switch to Old Tax Regime for next FY',
            'priority': 'HIGH',
            'impact': f'₹{savings:,.0f}/year',
            'category': 'Tax'
        })
    
    # Missed deductions
    for d in tax_result.get('missed_deductions', [])[:3]:
        all_actions.append({
            'action': f"Utilize {d.get('section', '')} - {d.get('description', '')[:40]}",
            'priority': 'HIGH' if d.get('potential_savings', 0) > 20000 else 'MEDIUM',
            'impact': f"₹{d.get('potential_savings', 0):,.0f}/year",
            'category': 'Tax'
        })
    
    # Health score recommendations
    for rec in health_score.get('recommendations', [])[:4]:
        impact = rec.get('impact', rec.get('potential_savings', 'Improves financial health'))
        if isinstance(impact, (int, float)):
            impact = f"₹{impact:,.0f}"
        all_actions.append({
            'action': rec.get('title', rec.get('recommendation', ''))[:50],
            'priority': rec.get('priority', 'MEDIUM').upper(),
            'impact': str(impact)[:25],
            'category': 'Health'
        })
    
    # Portfolio actions
    for suggestion in portfolio_result.get('recommendations', 
                                           portfolio_result.get('rebalancing_suggestions', []))[:3]:
        if isinstance(suggestion, dict):
            text = suggestion.get('suggestion', suggestion.get('recommendation', ''))
        else:
            text = str(suggestion)
        all_actions.append({
            'action': text[:50],
            'priority': 'MEDIUM',
            'impact': 'Optimizes returns',
            'category': 'Portfolio'
        })
    
    # FIRE actions
    monthly_sip = fire_plan.get('monthly_sip_required', fire_plan.get('required_monthly_investment', 0))
    if monthly_sip > 0:
        all_actions.append({
            'action': f'Setup monthly SIP of ₹{monthly_sip:,.0f}',
            'priority': 'HIGH',
            'impact': 'Achieves FIRE goal',
            'category': 'FIRE'
        })
    
    # Sort by priority
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    all_actions.sort(key=lambda x: priority_order.get(x.get('priority', 'LOW'), 2))
    
    # Display actions
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(*Colors.PRIMARY_BLUE)
    pdf.set_text_color(*Colors.WHITE)
    pdf.cell(10, 8, '#', border=1, fill=True, align='C')
    pdf.cell(20, 8, 'Priority', border=1, fill=True, align='C')
    pdf.cell(90, 8, 'Action Item', border=1, fill=True, align='C')
    pdf.cell(35, 8, 'Impact', border=1, fill=True, align='C')
    pdf.cell(35, 8, 'Category', border=1, fill=True, align='C')
    pdf.ln()
    
    for i, action in enumerate(all_actions[:15], 1):  # Limit to 15 actions
        priority = action.get('priority', 'MEDIUM')
        
        # Priority-based coloring
        if priority == 'HIGH':
            pdf.set_fill_color(*Colors.LIGHT_RED)
            priority_color = Colors.RED
        elif priority == 'MEDIUM':
            pdf.set_fill_color(*Colors.LIGHT_ORANGE)
            priority_color = Colors.ORANGE
        else:
            pdf.set_fill_color(*Colors.LIGHT_GREEN)
            priority_color = Colors.GREEN
        
        # Row
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*Colors.BLACK)
        pdf.cell(10, 10, str(i), border=1, fill=True, align='C')
        
        pdf.set_text_color(*priority_color)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(20, 10, priority, border=1, fill=True, align='C')
        
        pdf.set_text_color(*Colors.BLACK)
        pdf.set_font('Helvetica', '', 8)
        pdf.cell(90, 10, action.get('action', '')[:45], border=1, fill=True)
        
        pdf.set_text_color(*Colors.GREEN)
        pdf.cell(35, 10, action.get('impact', '')[:18], border=1, fill=True, align='C')
        
        pdf.set_text_color(*Colors.GRAY)
        pdf.cell(35, 10, action.get('category', ''), border=1, fill=True, align='C')
        pdf.ln()
    
    pdf.set_text_color(*Colors.BLACK)
    
    # Summary footer
    pdf.ln(10)
    high_count = sum(1 for a in all_actions if a.get('priority') == 'HIGH')
    medium_count = sum(1 for a in all_actions if a.get('priority') == 'MEDIUM')
    
    pdf.info_box(
        f"📋 Total Actions: {len(all_actions)} | "
        f"🔴 High Priority: {high_count} | "
        f"🟠 Medium Priority: {medium_count}\n"
        f"Start with HIGH priority items for maximum financial impact!",
        "info"
    )


# ============================================================================
# MAIN REPORT GENERATOR
# ============================================================================

def generate_report(
    user_profile: Dict[str, Any],
    tax_result: Dict[str, Any],
    health_score: Dict[str, Any],
    portfolio_result: Optional[Dict[str, Any]] = None,
    fire_plan: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Generate a comprehensive PDF financial report.
    
    Args:
        user_profile: User profile data (name, age, income, etc.)
        tax_result: Tax analysis results
        health_score: Money health score with dimensions
        portfolio_result: Portfolio analysis (optional)
        fire_plan: FIRE plan details (optional)
    
    Returns:
        PDF document as bytes
    """
    # Initialize PDF
    pdf = WealthPilotPDF()
    
    # Set document properties
    pdf.set_title('WealthPilot Financial Report')
    pdf.set_author('WealthPilot')
    pdf.set_creator('WealthPilot Report Generator')
    
    # Provide defaults for optional parameters
    if portfolio_result is None:
        portfolio_result = {}
    if fire_plan is None:
        fire_plan = {}
    
    # Generate pages
    # Page 1: Cover
    create_cover_page(pdf, user_profile, health_score)
    
    # Page 2: Tax Analysis
    create_tax_analysis_page(pdf, tax_result)
    
    # Page 3: Money Health Score
    create_health_score_page(pdf, health_score)
    
    # Page 4: Portfolio Analysis (if data available)
    if portfolio_result and (portfolio_result.get('holdings') or portfolio_result.get('summary')):
        create_portfolio_page(pdf, portfolio_result)
    
    # Page 5: FIRE Plan (if data available)
    if fire_plan and (fire_plan.get('target_corpus') or fire_plan.get('monthly_sip_required')):
        create_fire_plan_page(pdf, fire_plan)
    
    # Page 6: Action Checklist
    create_action_checklist_page(pdf, tax_result, health_score, portfolio_result, fire_plan)
    
    # Output to bytes
    return bytes(pdf.output())


# ============================================================================
# EXAMPLE USAGE & TESTING
# ============================================================================

def create_sample_data():
    """Create sample data for testing"""
    
    user_profile = {
        'name': 'Rahul Sharma',
        'age': 32,
        'annual_income': 1800000,
        'monthly_expenses': 60000,
        'savings_rate': 0.35,
        'risk_profile': 'moderate'
    }
    
    tax_result = {
        'recommendation': 'old_regime',
        'old_regime': {
            'gross_income': 1800000,
            'total_deductions': 250000,
            'taxable_income': 1550000,
            'tax_payable': 195000,
            'effective_rate': 10.8
        },
        'new_regime': {
            'gross_income': 1800000,
            'total_deductions': 75000,
            'taxable_income': 1725000,
            'tax_payable': 228000,
            'effective_rate': 12.7
        },
        'missed_deductions': [
            {'section': '80C', 'description': 'PPF/ELSS Investment', 'limit': 150000, 'potential_savings': 46800},
            {'section': '80D', 'description': 'Health Insurance Premium', 'limit': 25000, 'potential_savings': 7800},
            {'section': '80CCD(1B)', 'description': 'NPS Additional Contribution', 'limit': 50000, 'potential_savings': 15600},
            {'section': '80E', 'description': 'Education Loan Interest', 'limit': 100000, 'potential_savings': 31200},
            {'section': '24(b)', 'description': 'Home Loan Interest', 'limit': 200000, 'potential_savings': 62400}
        ]
    }
    
    health_score = {
        'overall_score': 68,
        'dimensions': {
            'emergency_fund': {'score': 75, 'status': 'good'},
            'debt_management': {'score': 85, 'status': 'excellent'},
            'savings_rate': {'score': 70, 'status': 'good'},
            'insurance_coverage': {'score': 45, 'status': 'needs_attention'},
            'investment_diversification': {'score': 60, 'status': 'fair'},
            'retirement_readiness': {'score': 55, 'status': 'fair'}
        },
        'recommendations': [
            {'title': 'Increase Term Insurance Coverage', 'priority': 'HIGH', 
             'description': 'Current coverage is below 10x annual income', 'impact': 50000},
            {'title': 'Build Emergency Fund', 'priority': 'HIGH',
             'description': 'Increase to 6 months of expenses', 'impact': 'Financial security'},
            {'title': 'Diversify into International Funds', 'priority': 'MEDIUM',
             'description': 'Add 10-15% allocation to US/Global funds', 'impact': 'Better diversification'},
            {'title': 'Start NPS for Retirement', 'priority': 'MEDIUM',
             'description': 'Tax benefits under 80CCD(1B)', 'impact': 15600},
            {'title': 'Review Insurance Policies', 'priority': 'LOW',
             'description': 'Check for adequate health coverage', 'impact': 'Risk mitigation'}
        ]
    }
    
    portfolio_result = {
        'summary': {
            'total_invested': 1500000,
            'current_value': 1875000,
            'xirr': 14.2
        },
        'holdings': [
            {'fund_name': 'HDFC Mid-Cap Opportunities Fund', 'invested': 400000, 'current_value': 520000},
            {'fund_name': 'Axis Long Term Equity Fund', 'invested': 300000, 'current_value': 375000},
            {'fund_name': 'SBI Blue Chip Fund', 'invested': 350000, 'current_value': 402500},
            {'fund_name': 'ICICI Prudential Technology Fund', 'invested': 250000, 'current_value': 337500},
            {'fund_name': 'Parag Parikh Flexi Cap Fund', 'invested': 200000, 'current_value': 240000}
        ],
        'overlaps': [
            {'funds': ['HDFC Mid-Cap Opportunities', 'SBI Blue Chip Fund'], 'overlap_percentage': 35},
            {'funds': ['Axis Long Term Equity', 'SBI Blue Chip Fund'], 'overlap_percentage': 28}
        ],
        'recommendations': [
            {'recommendation': 'Reduce overlap by consolidating large-cap exposure'},
            {'recommendation': 'Add debt allocation (currently 0%) - target 20%'},
            {'recommendation': 'Consider international diversification'},
            {'recommendation': 'Rebalance mid-cap allocation from 35% to 25%'}
        ]
    }
    
    fire_plan = {
        'target_corpus': 50000000,
        'current_corpus': 1875000,
        'monthly_sip_required': 85000,
        'years_to_fire': 18,
        'fire_age': 50,
        'milestones': [
            {'year': 1, 'corpus': 2937000, 'total_contributions': 2895000, 'growth': 42000},
            {'year': 5, 'corpus': 8500000, 'total_contributions': 6975000, 'growth': 1525000},
            {'year': 10, 'corpus': 19200000, 'total_contributions': 12075000, 'growth': 7125000},
            {'year': 15, 'corpus': 36500000, 'total_contributions': 17175000, 'growth': 19325000},
            {'year': 18, 'corpus': 50000000, 'total_contributions': 20295000, 'growth': 29705000}
        ],
        'assumptions': {
            'expected_return': 12,
            'inflation': 6,
            'annual_sip_increase': 10
        }
    }
    
    return user_profile, tax_result, health_score, portfolio_result, fire_plan


def main():
    """Test the report generator"""
    print("🚀 WealthPilot Report Generator")
    print("=" * 50)
    
    # Create sample data
    print("📊 Creating sample data...")
    user_profile, tax_result, health_score, portfolio_result, fire_plan = create_sample_data()
    
    # Generate report
    print("📝 Generating PDF report...")
    pdf_bytes = generate_report(
        user_profile=user_profile,
        tax_result=tax_result,
        health_score=health_score,
        portfolio_result=portfolio_result,
        fire_plan=fire_plan
    )
    
    # Save to file for testing
    output_path = "wealthpilot_report.pdf"
    with open(output_path, 'wb') as f:
        f.write(pdf_bytes)
    
    print(f"✅ Report generated successfully!")
    print(f"📁 Saved to: {output_path}")
    print(f"📦 Size: {len(pdf_bytes):,} bytes")
    
    return pdf_bytes


if __name__ == "__main__":
    main()