# portfolio_analyzer.py

import requests
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from functools import lru_cache
import json

# Holdings database with approximate top 10 stocks for popular Indian mutual funds
HOLDINGS_DATABASE = {
    "HDFC Top 100": {
        "scheme_code": "119551",
        "holdings": {
            "HDFC Bank": 8.5,
            "ICICI Bank": 7.2,
            "Infosys": 6.8,
            "Reliance Industries": 6.5,
            "TCS": 5.9,
            "Kotak Mahindra Bank": 4.2,
            "Axis Bank": 3.8,
            "Larsen & Toubro": 3.5,
            "Bharti Airtel": 3.2,
            "ITC": 2.9
        },
        "expense_ratio": 1.05
    },
    "SBI Bluechip": {
        "scheme_code": "119597",
        "holdings": {
            "Reliance Industries": 8.1,
            "HDFC Bank": 7.8,
            "ICICI Bank": 6.9,
            "Infosys": 6.3,
            "TCS": 5.7,
            "State Bank of India": 4.5,
            "Bajaj Finance": 3.9,
            "Kotak Mahindra Bank": 3.6,
            "Larsen & Toubro": 3.4,
            "HUL": 3.1
        },
        "expense_ratio": 0.98
    },
    "ICICI Prudential Bluechip": {
        "scheme_code": "120503",
        "holdings": {
            "HDFC Bank": 8.2,
            "Reliance Industries": 7.5,
            "ICICI Bank": 7.1,
            "Infosys": 6.4,
            "TCS": 5.8,
            "Kotak Mahindra Bank": 4.3,
            "Bajaj Finance": 3.7,
            "Axis Bank": 3.5,
            "Larsen & Toubro": 3.3,
            "Asian Paints": 2.8
        },
        "expense_ratio": 1.12
    },
    "Axis Bluechip": {
        "scheme_code": "120503",
        "holdings": {
            "HDFC Bank": 9.1,
            "ICICI Bank": 7.8,
            "Reliance Industries": 7.3,
            "Infosys": 6.6,
            "TCS": 6.2,
            "Kotak Mahindra Bank": 4.8,
            "Bajaj Finance": 4.1,
            "Axis Bank": 3.9,
            "Bharti Airtel": 3.4,
            "Maruti Suzuki": 2.7
        },
        "expense_ratio": 1.18
    },
    "Mirae Asset Large Cap": {
        "scheme_code": "125497",
        "holdings": {
            "Reliance Industries": 8.8,
            "HDFC Bank": 8.3,
            "ICICI Bank": 7.4,
            "Infosys": 6.9,
            "TCS": 6.1,
            "Bajaj Finance": 4.5,
            "Kotak Mahindra Bank": 4.2,
            "Larsen & Toubro": 3.6,
            "Bharti Airtel": 3.3,
            "HUL": 2.9
        },
        "expense_ratio": 0.91
    },
    "Parag Parikh Flexi Cap": {
        "scheme_code": "122639",
        "holdings": {
            "Alphabet Inc": 6.5,
            "HDFC Bank": 5.8,
            "Meta Platforms": 5.2,
            "Infosys": 4.9,
            "Microsoft": 4.6,
            "Reliance Industries": 4.3,
            "ICICI Bank": 4.1,
            "Bajaj Finance": 3.8,
            "Axis Bank": 3.5,
            "Maruti Suzuki": 3.2
        },
        "expense_ratio": 0.82
    },
    "UTI Nifty 50 Index": {
        "scheme_code": "120716",
        "holdings": {
            "Reliance Industries": 9.8,
            "HDFC Bank": 9.2,
            "ICICI Bank": 7.6,
            "Infosys": 6.8,
            "TCS": 6.3,
            "ITC": 4.2,
            "Kotak Mahindra Bank": 3.9,
            "Larsen & Toubro": 3.7,
            "Bajaj Finance": 3.5,
            "HUL": 3.4
        },
        "expense_ratio": 0.18
    },
    "HDFC Mid-Cap Opportunities": {
        "scheme_code": "118989",
        "holdings": {
            "Tube Investments": 3.8,
            "Prestige Estates": 3.5,
            "Persistent Systems": 3.3,
            "Coforge": 3.1,
            "Dixon Technologies": 2.9,
            "PI Industries": 2.7,
            "Trent": 2.6,
            "Polycab India": 2.5,
            "Astral": 2.4,
            "Cummins India": 2.3
        },
        "expense_ratio": 1.35
    },
    "SBI Small Cap": {
        "scheme_code": "119794",
        "holdings": {
            "Data Patterns": 2.1,
            "CEAT": 1.9,
            "Fine Organic": 1.8,
            "Apar Industries": 1.7,
            "KPIT Technologies": 1.6,
            "Swan Energy": 1.5,
            "Sobha": 1.4,
            "JBM Auto": 1.3,
            "CCL Products": 1.2,
            "Raymond": 1.1
        },
        "expense_ratio": 1.58
    },
    "Nippon India Small Cap": {
        "scheme_code": "118825",
        "holdings": {
            "Chemplast Sanmar": 2.3,
            "Sudarshan Chemical": 2.1,
            "CG Power": 2.0,
            "PNC Infratech": 1.9,
            "NCC": 1.8,
            "BEML": 1.7,
            "Praj Industries": 1.6,
            "CarTrade Tech": 1.5,
            "Welspun Corp": 1.4,
            "KEI Industries": 1.3
        },
        "expense_ratio": 1.62
    },
    "Kotak Emerging Equity": {
        "scheme_code": "119551",
        "holdings": {
            "HDFC Bank": 7.2,
            "ICICI Bank": 6.5,
            "Bajaj Finance": 5.8,
            "Axis Bank": 4.9,
            "Bharti Airtel": 4.3,
            "Max Healthcare": 3.7,
            "Zomato": 3.2,
            "Divi's Labs": 2.9,
            "Cholamandalam": 2.6,
            "Prestige Estates": 2.4
        },
        "expense_ratio": 1.28
    },
    "Motilal Oswal Midcap": {
        "scheme_code": "135760",
        "holdings": {
            "Kalyan Jewellers": 4.2,
            "Dixon Technologies": 3.9,
            "Persistent Systems": 3.6,
            "Coforge": 3.4,
            "Trent": 3.2,
            "Prestige Estates": 3.0,
            "Polycab India": 2.8,
            "Tube Investments": 2.6,
            "Phoenix Mills": 2.5,
            "Cummins India": 2.4
        },
        "expense_ratio": 1.42
    },
    "Quant Active Fund": {
        "scheme_code": "112310",
        "holdings": {
            "Adani Enterprises": 5.8,
            "Adani Ports": 5.2,
            "Jio Financial": 4.9,
            "Reliance Industries": 4.6,
            "Adani Power": 4.3,
            "HDFC Bank": 3.9,
            "Tata Motors": 3.6,
            "ICICI Bank": 3.4,
            "Larsen & Toubro": 3.2,
            "Bharti Airtel": 2.9
        },
        "expense_ratio": 0.64
    },
    "Franklin India Equity": {
        "scheme_code": "101462",
        "holdings": {
            "HDFC Bank": 6.8,
            "ICICI Bank": 6.2,
            "Reliance Industries": 5.9,
            "Infosys": 5.4,
            "Bharti Airtel": 4.7,
            "Axis Bank": 4.2,
            "Larsen & Toubro": 3.8,
            "Maruti Suzuki": 3.5,
            "Mahindra & Mahindra": 3.2,
            "Sun Pharma": 2.9
        },
        "expense_ratio": 1.15
    },
    "DSP Equity Opportunities": {
        "scheme_code": "131181",
        "holdings": {
            "HDFC Bank": 7.9,
            "ICICI Bank": 7.1,
            "Reliance Industries": 6.4,
            "Infosys": 5.7,
            "Bajaj Finance": 4.8,
            "Kotak Mahindra Bank": 4.3,
            "TCS": 3.9,
            "Axis Bank": 3.6,
            "Larsen & Toubro": 3.3,
            "Bharti Airtel": 3.1
        },
        "expense_ratio": 1.21
    }
}


def fetch_fund_nav(scheme_code: str) -> Optional[Dict]:
    """
    Fetch latest NAV and fund name from MFAPI
    
    Args:
        scheme_code: Mutual fund scheme code
        
    Returns:
        Dict with fund_name, latest_nav, and date or None on error
    """
    try:
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'SUCCESS' or 'meta' in data:
            return {
                'fund_name': data.get('meta', {}).get('scheme_name', 'Unknown'),
                'latest_nav': float(data['data'][0]['nav']),
                'date': data['data'][0]['date']
            }
        else:
            print(f"Error: API returned unsuccessful status for scheme {scheme_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching NAV for scheme {scheme_code}: {e}")
        return None
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error parsing NAV data for scheme {scheme_code}: {e}")
        return None


@lru_cache(maxsize=100)
def search_fund(query: str) -> List[Dict]:
    """
    Search for mutual funds by name (with caching)
    
    Args:
        query: Search query string
        
    Returns:
        List of dicts with schemeCode and schemeName
    """
    try:
        url = f"https://api.mfapi.in/mf/search?q={query}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data if isinstance(data, list) else []
        
    except requests.exceptions.RequestException as e:
        print(f"Network error searching funds: {e}")
        return []
    except ValueError as e:
        print(f"Error parsing search results: {e}")
        return []


def xirr_npv(rate: float, transactions: List[Tuple[float, datetime]]) -> float:
    """
    Calculate NPV for XIRR calculation
    
    Args:
        rate: Discount rate
        transactions: List of (amount, date) tuples
        
    Returns:
        Net present value
    """
    first_date = transactions[0][1]
    npv = 0.0
    
    for amount, date in transactions:
        days_diff = (date - first_date).days
        npv += amount / ((1 + rate) ** (days_diff / 365.0))
    
    return npv


def calculate_xirr(transactions: List[Tuple[float, datetime]], 
                   guess: float = 0.1) -> Optional[float]:
    """
    Calculate XIRR (annualized return) using Newton-Raphson method
    
    Args:
        transactions: List of (amount, date) tuples
                     Negative = investment, Positive = redemption/current value
        guess: Initial guess for rate
        
    Returns:
        Annualized return percentage or None if calculation fails
    """
    # Edge case handling
    if not transactions or len(transactions) == 0:
        return None
    
    if len(transactions) == 1:
        return None  # Cannot calculate return with single transaction
    
    # Check if all dates are the same
    dates = [t[1] for t in transactions]
    if len(set(dates)) == 1:
        return None  # Cannot calculate XIRR if all transactions on same date
    
    # Sort transactions by date
    transactions = sorted(transactions, key=lambda x: x[1])
    
    # Check if sum is zero (no net cash flow)
    total = sum(t[0] for t in transactions)
    if abs(total) < 0.01:  # Close to zero
        return 0.0
    
    # Newton-Raphson method
    rate = guess
    epsilon = 1e-6
    max_iterations = 100
    
    for i in range(max_iterations):
        npv = xirr_npv(rate, transactions)
        
        # Calculate derivative (NPV')
        first_date = transactions[0][1]
        npv_derivative = 0.0
        for amount, date in transactions:
            days_diff = (date - first_date).days
            years = days_diff / 365.0
            npv_derivative -= years * amount / ((1 + rate) ** (years + 1))
        
        # Avoid division by zero
        if abs(npv_derivative) < epsilon:
            break
        
        # Newton-Raphson iteration
        new_rate = rate - npv / npv_derivative
        
        # Check for convergence
        if abs(new_rate - rate) < epsilon:
            return new_rate * 100  # Return as percentage
        
        rate = new_rate
        
        # Bounds checking to avoid unrealistic values
        if rate < -0.99:
            rate = -0.99
        elif rate > 10:
            rate = 10
    
    # If didn't converge, try scipy if available
    try:
        from scipy.optimize import newton
        
        def f(r):
            return xirr_npv(r, transactions)
        
        result = newton(f, guess, maxiter=100)
        return result * 100
    except:
        # Return best estimate if scipy not available
        return rate * 100 if abs(npv) < 1 else None


def calculate_absolute_returns(invested: float, current_value: float, 
                               years: float) -> Dict[str, float]:
    """
    Calculate absolute returns and CAGR
    
    Args:
        invested: Total invested amount
        current_value: Current portfolio value
        years: Investment duration in years
        
    Returns:
        Dict with absolute_return_pct and cagr_pct
    """
    if invested <= 0:
        return {'absolute_return_pct': 0.0, 'cagr_pct': 0.0}
    
    absolute_return = ((current_value - invested) / invested) * 100
    
    if years > 0:
        cagr = (((current_value / invested) ** (1 / years)) - 1) * 100
    else:
        cagr = 0.0
    
    return {
        'absolute_return_pct': round(absolute_return, 2),
        'cagr_pct': round(cagr, 2)
    }


def calculate_overlap(fund1_holdings: Dict[str, float], 
                     fund2_holdings: Dict[str, float]) -> Dict:
    """
    Calculate portfolio overlap between two funds
    
    Args:
        fund1_holdings: Dict of {stock_name: weight_%}
        fund2_holdings: Dict of {stock_name: weight_%}
        
    Returns:
        Dict with overlap_percentage, common_stocks, unique_to_fund1, unique_to_fund2
    """
    stocks1 = set(fund1_holdings.keys())
    stocks2 = set(fund2_holdings.keys())
    
    common_stocks = stocks1 & stocks2
    unique_to_fund1 = stocks1 - stocks2
    unique_to_fund2 = stocks2 - stocks1
    
    # Calculate overlap percentage (minimum weight for common stocks)
    overlap_pct = 0.0
    if common_stocks:
        overlap_pct = sum(
            min(fund1_holdings[stock], fund2_holdings[stock])
            for stock in common_stocks
        )
    
    return {
        'overlap_percentage': round(overlap_pct, 2),
        'common_stocks': list(common_stocks),
        'unique_to_fund1': list(unique_to_fund1),
        'unique_to_fund2': list(unique_to_fund2),
        'num_common': len(common_stocks)
    }


def analyze_portfolio(holdings: List[Dict]) -> Dict:
    """
    Comprehensive portfolio analysis
    
    Args:
        holdings: List of dicts with:
                 - fund_name: str
                 - invested_amount: float
                 - current_value: float
                 - start_date: str (YYYY-MM-DD)
                 - scheme_code: str (optional)
                 
    Returns:
        Complete portfolio analysis dictionary
    """
    total_invested = 0.0
    total_current = 0.0
    fund_analyses = []
    all_transactions = []
    
    # Analyze each fund
    for holding in holdings:
        fund_name = holding['fund_name']
        invested = holding['invested_amount']
        current = holding['current_value']
        start_date_str = holding['start_date']
        scheme_code = holding.get('scheme_code', '')
        
        total_invested += invested
        total_current += current
        
        # Parse date
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            start_date = datetime.now()
        
        # Calculate years
        years = (datetime.now() - start_date).days / 365.0
        
        # Calculate returns
        returns = calculate_absolute_returns(invested, current, years)
        
        # Fetch latest NAV if scheme code provided
        nav_data = None
        if scheme_code:
            nav_data = fetch_fund_nav(scheme_code)
        
        # Get fund info from database
        fund_info = HOLDINGS_DATABASE.get(fund_name, {})
        expense_ratio = fund_info.get('expense_ratio', 'N/A')
        
        fund_analysis = {
            'fund_name': fund_name,
            'invested_amount': invested,
            'current_value': current,
            'absolute_return_pct': returns['absolute_return_pct'],
            'cagr_pct': returns['cagr_pct'],
            'gain_loss': current - invested,
            'years_invested': round(years, 2),
            'expense_ratio': expense_ratio,
            'latest_nav': nav_data['latest_nav'] if nav_data else 'N/A',
            'nav_date': nav_data['date'] if nav_data else 'N/A'
        }
        
        fund_analyses.append(fund_analysis)
        
        # Add to transactions for XIRR
        all_transactions.append((-invested, start_date))
        all_transactions.append((current, datetime.now()))
    
    # Calculate overall XIRR
    overall_xirr = calculate_xirr(all_transactions)
    
    # Calculate pairwise overlaps
    overlaps = []
    for i, holding1 in enumerate(holdings):
        fund1_name = holding1['fund_name']
        fund1_data = HOLDINGS_DATABASE.get(fund1_name, {})
        fund1_holdings = fund1_data.get('holdings', {})
        
        for j, holding2 in enumerate(holdings[i+1:], i+1):
            fund2_name = holding2['fund_name']
            fund2_data = HOLDINGS_DATABASE.get(fund2_name, {})
            fund2_holdings = fund2_data.get('holdings', {})
            
            if fund1_holdings and fund2_holdings:
                overlap = calculate_overlap(fund1_holdings, fund2_holdings)
                overlaps.append({
                    'fund1': fund1_name,
                    'fund2': fund2_name,
                    **overlap
                })
    
    # Overall portfolio metrics
    overall_returns = calculate_absolute_returns(total_invested, total_current, 
                                                 (datetime.now() - min(
                                                     datetime.strptime(h['start_date'], '%Y-%m-%d') 
                                                     for h in holdings
                                                 )).days / 365.0)
    
    return {
        'total_invested': round(total_invested, 2),
        'total_current_value': round(total_current, 2),
        'total_gain_loss': round(total_current - total_invested, 2),
        'overall_absolute_return_pct': overall_returns['absolute_return_pct'],
        'overall_cagr_pct': overall_returns['cagr_pct'],
        'overall_xirr_pct': round(overall_xirr, 2) if overall_xirr else 'N/A',
        'num_funds': len(holdings),
        'fund_analyses': fund_analyses,
        'overlaps': overlaps
    }


def generate_rebalancing_suggestions(portfolio_analysis: Dict) -> List[str]:
    """
    Generate actionable portfolio rebalancing suggestions
    
    Args:
        portfolio_analysis: Output from analyze_portfolio()
        
    Returns:
        List of suggestion strings
    """
    suggestions = []
    
    # Check for high overlap
    for overlap in portfolio_analysis['overlaps']:
        if overlap['overlap_percentage'] > 50:
            suggestions.append(
                f"⚠️ HIGH OVERLAP ({overlap['overlap_percentage']}%): "
                f"{overlap['fund1']} and {overlap['fund2']} have significant overlap. "
                f"Consider consolidating to reduce redundancy."
            )
    
    # Check for high expense ratios in large cap funds
    large_cap_keywords = ['bluechip', 'large cap', 'top 100', 'nifty 50']
    for fund in portfolio_analysis['fund_analyses']:
        fund_name_lower = fund['fund_name'].lower()
        expense_ratio = fund['expense_ratio']
        
        if any(keyword in fund_name_lower for keyword in large_cap_keywords):
            if isinstance(expense_ratio, (int, float)) and expense_ratio > 1.5:
                suggestions.append(
                    f"💰 HIGH EXPENSE RATIO: {fund['fund_name']} has {expense_ratio}% "
                    f"expense ratio. Consider switching to a low-cost index fund like "
                    f"UTI Nifty 50 Index (0.18%)."
                )
    
    # Check for debt allocation
    fund_names = [f['fund_name'].lower() for f in portfolio_analysis['fund_analyses']]
    has_debt = any('debt' in name or 'liquid' in name or 'bond' in name 
                   for name in fund_names)
    
    if not has_debt and portfolio_analysis['num_funds'] >= 2:
        suggestions.append(
            "🔄 ASSET ALLOCATION: Your portfolio has no debt allocation. "
            "Consider adding 20-30% debt funds for stability and risk reduction."
        )
    
    # Check for underperforming funds
    for fund in portfolio_analysis['fund_analyses']:
        if isinstance(fund['cagr_pct'], (int, float)) and fund['cagr_pct'] < 8:
            suggestions.append(
                f"📉 UNDERPERFORMANCE: {fund['fund_name']} has CAGR of {fund['cagr_pct']}%, "
                f"below inflation. Review and consider replacing."
            )
    
    # Check for over-diversification
    if portfolio_analysis['num_funds'] > 8:
        suggestions.append(
            f"📊 OVER-DIVERSIFICATION: You have {portfolio_analysis['num_funds']} funds. "
            f"Consider consolidating to 5-7 funds for better tracking and management."
        )
    
    # Check for concentration risk
    for fund in portfolio_analysis['fund_analyses']:
        fund_percentage = (fund['current_value'] / portfolio_analysis['total_current_value']) * 100
        if fund_percentage > 40:
            suggestions.append(
                f"⚡ CONCENTRATION RISK: {fund['fund_name']} represents {fund_percentage:.1f}% "
                f"of your portfolio. Consider rebalancing for better diversification."
            )
    
    if not suggestions:
        suggestions.append("✅ Your portfolio looks well-balanced! Keep monitoring quarterly.")
    
    return suggestions


# ============================================================================
# TEST CASE
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("INDIAN MUTUAL FUND PORTFOLIO ANALYZER - TEST CASE")
    print("=" * 80)
    
    # Test 1: Fetch NAV
    print("\n1. Testing fetch_fund_nav()...")
    nav_result = fetch_fund_nav("119551")
    if nav_result:
        print(f"   ✓ Fund: {nav_result['fund_name']}")
        print(f"   ✓ NAV: ₹{nav_result['latest_nav']} (Date: {nav_result['date']})")
    
    # Test 2: Search Fund
    print("\n2. Testing search_fund()...")
    search_results = search_fund("hdfc top 100")
    if search_results:
        print(f"   ✓ Found {len(search_results)} matching funds")
        print(f"   ✓ First result: {search_results[0]['schemeName']}")
    
    # Test 3: Calculate XIRR
    print("\n3. Testing calculate_xirr()...")
    transactions = [
        (-10000, datetime(2020, 1, 1)),
        (-5000, datetime(2020, 6, 1)),
        (-5000, datetime(2021, 1, 1)),
        (25000, datetime(2024, 1, 1))
    ]
    xirr = calculate_xirr(transactions)
    print(f"   ✓ XIRR: {xirr:.2f}%")
    
    # Test 4: Calculate Returns
    print("\n4. Testing calculate_absolute_returns()...")
    returns = calculate_absolute_returns(20000, 25000, 3)
    print(f"   ✓ Absolute Return: {returns['absolute_return_pct']}%")
    print(f"   ✓ CAGR: {returns['cagr_pct']}%")
    
    # Test 5: Calculate Overlap
    print("\n5. Testing calculate_overlap()...")
    overlap = calculate_overlap(
        HOLDINGS_DATABASE["HDFC Top 100"]["holdings"],
        HOLDINGS_DATABASE["SBI Bluechip"]["holdings"]
    )
    print(f"   ✓ Overlap: {overlap['overlap_percentage']}%")
    print(f"   ✓ Common stocks: {overlap['num_common']}")
    
    # Test 6: Full Portfolio Analysis
    print("\n6. Testing analyze_portfolio()...")
    test_portfolio = [
        {
            'fund_name': 'HDFC Top 100',
            'invested_amount': 50000,
            'current_value': 62000,
            'start_date': '2021-01-01',
            'scheme_code': '119551'
        },
        {
            'fund_name': 'SBI Bluechip',
            'invested_amount': 30000,
            'current_value': 36500,
            'start_date': '2021-06-01',
            'scheme_code': '119597'
        },
        {
            'fund_name': 'Parag Parikh Flexi Cap',
            'invested_amount': 40000,
            'current_value': 52000,
            'start_date': '2020-12-01',
            'scheme_code': '122639'
        }
    ]
    
    analysis = analyze_portfolio(test_portfolio)
    
    print(f"\n   PORTFOLIO SUMMARY:")
    print(f"   {'─' * 70}")
    print(f"   Total Invested:      ₹{analysis['total_invested']:,.2f}")
    print(f"   Current Value:       ₹{analysis['total_current_value']:,.2f}")
    print(f"   Total Gain/Loss:     ₹{analysis['total_gain_loss']:,.2f}")
    print(f"   Overall CAGR:        {analysis['overall_cagr_pct']}%")
    print(f"   Overall XIRR:        {analysis['overall_xirr_pct']}%")
    print(f"   Number of Funds:     {analysis['num_funds']}")
    
    print(f"\n   INDIVIDUAL FUND PERFORMANCE:")
    print(f"   {'─' * 70}")
    for fund in analysis['fund_analyses']:
        print(f"\n   📈 {fund['fund_name']}")
        print(f"      Invested: ₹{fund['invested_amount']:,.2f} | Current: ₹{fund['current_value']:,.2f}")
        print(f"      CAGR: {fund['cagr_pct']}% | Gain/Loss: ₹{fund['gain_loss']:,.2f}")
        print(f"      Expense Ratio: {fund['expense_ratio']}%")
    
    print(f"\n   FUND OVERLAPS:")
    print(f"   {'─' * 70}")
    for overlap in analysis['overlaps']:
        print(f"   {overlap['fund1']} ↔ {overlap['fund2']}: {overlap['overlap_percentage']}% overlap")
    
    # Test 7: Rebalancing Suggestions
    print("\n7. Testing generate_rebalancing_suggestions()...")
    suggestions = generate_rebalancing_suggestions(analysis)
    print(f"\n   REBALANCING SUGGESTIONS:")
    print(f"   {'─' * 70}")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. {suggestion}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)