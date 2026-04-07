"""
Conversational Financial Profiling Agent using Groq API (Llama 3.1 70B)
Manages a friendly, WhatsApp-like conversation to gather financial profile data
"""

import re
import json
from typing import Tuple, Dict, List, Optional, Any
from groq import Groq


def parse_indian_number(text: str) -> float:
    """
    Parse Indian number formats to float.
    
    Examples:
        '12 lakh' -> 1200000
        '1.2L' -> 120000
        '12,00,000' -> 1200000
        '50k' -> 50000
        '1.5 crore' -> 15000000
        '25000' -> 25000
        'nil' / 'none' / 'no' / '0' -> 0
    """
    if text is None:
        return 0.0
    
    # Convert to string and clean up
    text = str(text).strip().lower()
    
    # Handle zero/none cases
    if text in ['nil', 'none', 'no', 'nothing', 'zero', 'na', 'n/a', '-', '']:
        return 0.0
    
    # Remove commas and spaces for processing
    text_clean = text.replace(',', '').replace(' ', '')
    
    # Try direct numeric conversion first
    try:
        return float(text_clean)
    except ValueError:
        pass
    
    # Pattern for crore(s)
    crore_pattern = r'(\d+\.?\d*)\s*(?:cr|crore|crores)'
    crore_match = re.search(crore_pattern, text.replace(',', ''))
    if crore_match:
        return float(crore_match.group(1)) * 10000000
    
    # Pattern for lakh(s) - various formats
    lakh_pattern = r'(\d+\.?\d*)\s*(?:l|lac|lakh|lakhs|lacs)'
    lakh_match = re.search(lakh_pattern, text.replace(',', ''))
    if lakh_match:
        return float(lakh_match.group(1)) * 100000
    
    # Pattern for thousands (k)
    k_pattern = r'(\d+\.?\d*)\s*k'
    k_match = re.search(k_pattern, text.replace(',', ''))
    if k_match:
        return float(k_match.group(1)) * 1000
    
    # Try to extract just numbers (Indian format: 12,00,000)
    numbers_only = re.sub(r'[^\d.]', '', text)
    if numbers_only:
        try:
            return float(numbers_only)
        except ValueError:
            pass
    
    return 0.0


# List of metro cities in India
METRO_CITIES = [
    'mumbai', 'delhi', 'bangalore', 'bengaluru', 'chennai', 'kolkata',
    'hyderabad', 'pune', 'ahmedabad', 'new delhi', 'ncr', 'gurgaon',
    'gurugram', 'noida', 'ghaziabad', 'faridabad', 'navi mumbai', 
    'thane', 'calcutta', 'bombay'
]


def is_metro_city(city: str) -> bool:
    """Check if a city is a metro city for HRA purposes."""
    if not city:
        return False
    city_lower = city.lower().strip()
    return any(metro in city_lower or city_lower in metro for metro in METRO_CITIES)


class IntakeAgent:
    """
    Conversational agent for financial profiling using Groq API.
    Asks questions one at a time in a friendly, WhatsApp-like tone.
    """
    
    def __init__(self, groq_api_key: str):
        """Initialize the intake agent with Groq API key."""
        self.client = Groq(api_key=groq_api_key)
        self.model = "llama-3.1-70b-versatile"
        
        # Initialize empty profile
        self.profile: Dict[str, Any] = {
            'age': None,
            'annual_income': None,
            'city': None,
            'is_metro': None,
            'monthly_rent': None,
            'has_term_insurance': None,
            'term_cover': 0.0,
            'has_health_insurance': None,
            'health_cover': 0.0,
            'ppf_annual': 0.0,
            'elss_annual': 0.0,
            'nps_annual': 0.0,
            'epf_annual': 0.0,
            'monthly_expenses': None,
            'monthly_sip': 0.0,
            'emergency_fund': 0.0,
            'primary_goal': None
        }
        
        # Question tracking
        self.current_question = 0
        self.questions_flow = [
            'age', 'income', 'city', 'rent', 'insurance', 
            'investments', 'expenses', 'sip', 'emergency_fund', 'goal'
        ]
        
        # System prompt for the LLM
        self.system_prompt = """You are a friendly financial advisor assistant helping someone understand their finances. 
You communicate in a warm, WhatsApp-like conversational tone - like a knowledgeable friend, not a bank form.

Your job is to:
1. Understand the user's response to the current question
2. Extract relevant data points
3. Generate the next question in a friendly way

IMPORTANT RULES:
- Keep responses SHORT and conversational (1-3 sentences max)
- Use casual language with occasional emojis (but don't overdo it)
- Be encouraging and supportive
- If the user's response is unclear, gently ask for clarification
- Handle Indian number formats (lakh, crore, L, k, etc.)
- For insurance questions, try to get coverage amounts if they have insurance

RESPONSE FORMAT:
You must respond in valid JSON format with these fields:
{
    "extracted_data": {
        // relevant data extracted from user's response
        // use null if not applicable or not provided
    },
    "needs_clarification": false,
    "next_message": "Your friendly response and next question"
}

Current profile state will be provided. Extract data relevant to the current question being asked."""

    def _get_question_prompt(self, question_type: str) -> str:
        """Get the specific extraction instructions for each question type."""
        prompts = {
            'age': '''Current question: AGE
Extract: age (integer)
If user gives birth year, calculate age.
Example extractions:
- "I'm 28" -> {"age": 28}
- "born in 1995" -> {"age": 29} (assuming 2024)
- "late twenties" -> ask for specific age''',

            'income': '''Current question: ANNUAL INCOME
Extract: annual_income (float), income_type (ctc/in_hand)
Handle Indian formats: "12 lakh", "12L", "12,00,000", "1.2 crore"
Example extractions:
- "12 lakh CTC" -> {"annual_income": 1200000, "income_type": "ctc"}
- "80k per month in hand" -> {"annual_income": 960000, "income_type": "in_hand"}''',

            'city': '''Current question: CITY
Extract: city (string)
This helps determine metro/non-metro status for HRA calculations.
Example extractions:
- "I live in Mumbai" -> {"city": "Mumbai"}
- "Bangalore" -> {"city": "Bangalore"}''',

            'rent': '''Current question: MONTHLY RENT
Extract: monthly_rent (float)
Handle: own house = 0, parents house = 0
Example extractions:
- "25000 per month" -> {"monthly_rent": 25000}
- "own house" -> {"monthly_rent": 0}
- "staying with parents" -> {"monthly_rent": 0}''',

            'insurance': '''Current question: INSURANCE (Term & Health)
Extract: has_term_insurance (bool), term_cover (float), has_health_insurance (bool), health_cover (float)
Example extractions:
- "I have term insurance of 1 crore" -> {"has_term_insurance": true, "term_cover": 10000000, "has_health_insurance": null}
- "Both, term is 50L and health is 10L" -> {"has_term_insurance": true, "term_cover": 5000000, "has_health_insurance": true, "health_cover": 1000000}
- "Neither" -> {"has_term_insurance": false, "term_cover": 0, "has_health_insurance": false, "health_cover": 0}''',

            'investments': '''Current question: CURRENT INVESTMENTS (80C)
Extract: ppf_annual (float), elss_annual (float), nps_annual (float), epf_annual (float)
These are ANNUAL amounts for tax-saving investments.
Example extractions:
- "50k in PPF, 1 lakh in ELSS yearly" -> {"ppf_annual": 50000, "elss_annual": 100000, "nps_annual": 0, "epf_annual": 0}
- "Just EPF, around 1.5 lakh per year" -> {"epf_annual": 150000, "ppf_annual": 0, "elss_annual": 0, "nps_annual": 0}
- "None" -> {"ppf_annual": 0, "elss_annual": 0, "nps_annual": 0, "epf_annual": 0}''',

            'expenses': '''Current question: MONTHLY EXPENSES
Extract: monthly_expenses (float)
This is total monthly spending (rent excluded as we captured it separately).
Example extractions:
- "Around 40k per month" -> {"monthly_expenses": 40000}
- "50000" -> {"monthly_expenses": 50000}''',

            'sip': '''Current question: EXISTING SIPs
Extract: monthly_sip (float)
This is the total monthly SIP amount.
Example extractions:
- "Yes, 15k per month" -> {"monthly_sip": 15000}
- "No SIPs currently" -> {"monthly_sip": 0}
- "25000 in various funds" -> {"monthly_sip": 25000}''',

            'emergency_fund': '''Current question: EMERGENCY FUND
Extract: emergency_fund (float)
This is total emergency savings (liquid cash/FD/savings).
Example extractions:
- "Around 3 lakh in savings" -> {"emergency_fund": 300000}
- "Not really, maybe 50k" -> {"emergency_fund": 50000}
- "None" -> {"emergency_fund": 0}''',

            'goal': '''Current question: PRIMARY FINANCIAL GOAL
Extract: primary_goal (string)
Valid goals: retirement, house, car, child_education, fire, wealth_building, travel, wedding, other
Example extractions:
- "Want to retire early" -> {"primary_goal": "fire"}
- "Buying a house" -> {"primary_goal": "house"}
- "Kids education" -> {"primary_goal": "child_education"}'''
        }
        return prompts.get(question_type, '')

    def _get_initial_question(self) -> str:
        """Get the opening message."""
        return """Hey there! 👋 

I'm here to help you get a clear picture of your finances. Think of me as that friend who's good with money stuff!

I'll ask you a few quick questions (takes about 2-3 mins), and then we can figure out the best plan for you.

Let's start simple - **how old are you?**"""

    def _get_next_question_context(self, question_type: str) -> str:
        """Get context for generating the next question."""
        contexts = {
            'income': "Now ask about their annual income (CTC or in-hand). Be casual.",
            'city': "Ask which city they live in. Mention it helps with HRA calculations.",
            'rent': "Ask about monthly rent. Mention it's okay if they own their place or stay with family.",
            'insurance': "Ask about insurance - do they have term insurance, health insurance, both, or neither. Keep it light.",
            'investments': "Ask about their current tax-saving investments - PPF, ELSS, NPS, EPF. Yearly amounts.",
            'expenses': "Ask about their typical monthly expenses (excluding rent since we already have that).",
            'sip': "Ask if they have any running SIPs and how much per month.",
            'emergency_fund': "Ask about their emergency fund - savings they can access quickly.",
            'goal': "Final question! Ask about their top financial goal - retirement, buying a house, car, kids education, or FIRE (early retirement)."
        }
        return contexts.get(question_type, '')

    def _call_groq(self, messages: List[Dict], question_type: str) -> Dict:
        """Make API call to Groq and parse response."""
        try:
            # Build the full system message with question-specific context
            full_system = f"{self.system_prompt}\n\n{self._get_question_prompt(question_type)}"
            
            api_messages = [{"role": "system", "content": full_system}] + messages
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=0.7,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON from response
            # Handle cases where LLM might wrap JSON in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                content = json_match.group(1)
            
            # Try to find JSON object in the content
            json_pattern = r'\{[\s\S]*\}'
            json_match = re.search(json_pattern, content)
            if json_match:
                return json.loads(json_match.group())
            
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Raw content: {content}")
            # Return a default response if parsing fails
            return {
                "extracted_data": {},
                "needs_clarification": True,
                "next_message": "Sorry, I didn't quite catch that. Could you rephrase? 🤔"
            }
        except Exception as e:
            print(f"Groq API error: {e}")
            raise

    def _update_profile(self, extracted_data: Dict) -> None:
        """Update the profile with extracted data."""
        if not extracted_data:
            return
            
        # Direct mappings
        direct_fields = [
            'age', 'annual_income', 'city', 'monthly_rent',
            'has_term_insurance', 'term_cover', 'has_health_insurance', 'health_cover',
            'ppf_annual', 'elss_annual', 'nps_annual', 'epf_annual',
            'monthly_expenses', 'monthly_sip', 'emergency_fund', 'primary_goal'
        ]
        
        for field in direct_fields:
            if field in extracted_data and extracted_data[field] is not None:
                value = extracted_data[field]
                
                # Parse numeric values that might be in Indian format
                if field in ['annual_income', 'monthly_rent', 'term_cover', 'health_cover',
                            'ppf_annual', 'elss_annual', 'nps_annual', 'epf_annual',
                            'monthly_expenses', 'monthly_sip', 'emergency_fund']:
                    if isinstance(value, str):
                        value = parse_indian_number(value)
                    else:
                        value = float(value) if value else 0.0
                
                self.profile[field] = value
        
        # Update is_metro based on city
        if self.profile['city']:
            self.profile['is_metro'] = is_metro_city(self.profile['city'])

    def _is_question_complete(self, question_type: str) -> bool:
        """Check if the current question has been adequately answered."""
        completeness_checks = {
            'age': lambda: self.profile['age'] is not None,
            'income': lambda: self.profile['annual_income'] is not None,
            'city': lambda: self.profile['city'] is not None,
            'rent': lambda: self.profile['monthly_rent'] is not None,
            'insurance': lambda: (self.profile['has_term_insurance'] is not None and 
                                  self.profile['has_health_insurance'] is not None),
            'investments': lambda: True,  # Can be all zeros, that's valid
            'expenses': lambda: self.profile['monthly_expenses'] is not None,
            'sip': lambda: True,  # Can be zero
            'emergency_fund': lambda: True,  # Can be zero
            'goal': lambda: self.profile['primary_goal'] is not None
        }
        
        check = completeness_checks.get(question_type, lambda: True)
        return check()

    def _generate_completion_message(self) -> str:
        """Generate a friendly completion message with summary."""
        profile = self.profile
        
        # Format income nicely
        income_lakhs = profile['annual_income'] / 100000 if profile['annual_income'] else 0
        
        message = f"""Awesome, we're all done! 🎉

Here's a quick summary of your financial profile:

📊 **Your Profile:**
• Age: {profile['age']} years
• Annual Income: ₹{income_lakhs:.1f}L
• City: {profile['city']} ({'Metro' if profile['is_metro'] else 'Non-Metro'})
• Monthly Rent: ₹{profile['monthly_rent']:,.0f}
• Monthly Expenses: ₹{profile['monthly_expenses']:,.0f}

🛡️ **Insurance:**
• Term Insurance: {'Yes (₹' + f"{profile['term_cover']/100000:.0f}L)" if profile['has_term_insurance'] else 'No'}
• Health Insurance: {'Yes (₹' + f"{profile['health_cover']/100000:.0f}L)" if profile['has_health_insurance'] else 'No'}

💰 **Investments:**
• PPF: ₹{profile['ppf_annual']:,.0f}/year
• ELSS: ₹{profile['elss_annual']:,.0f}/year
• NPS: ₹{profile['nps_annual']:,.0f}/year
• EPF: ₹{profile['epf_annual']:,.0f}/year
• Monthly SIP: ₹{profile['monthly_sip']:,.0f}
• Emergency Fund: ₹{profile['emergency_fund']:,.0f}

🎯 **Primary Goal:** {profile['primary_goal'].replace('_', ' ').title() if profile['primary_goal'] else 'Not specified'}

Now I can help you create a personalized financial plan! 💪"""
        
        return message

    def process_message(
        self, 
        user_message: str, 
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[str, bool, Optional[Dict]]:
        """
        Process a user message and return the response.
        
        Args:
            user_message: The user's input message
            conversation_history: List of previous messages [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            Tuple of (response_text, is_complete, extracted_profile)
            - response_text: The agent's response
            - is_complete: True if all questions have been answered
            - extracted_profile: The full profile dict if complete, None otherwise
        """
        
        # Handle initial message (empty history)
        if not conversation_history or len(conversation_history) == 0:
            initial_message = self._get_initial_question()
            return (initial_message, False, None)
        
        # Determine current question based on profile state
        question_type = self.questions_flow[self.current_question]
        
        # Build messages for API call
        messages = conversation_history.copy()
        messages.append({"role": "user", "content": user_message})
        
        # Add context about what we're extracting
        context_message = f"""
Current question type: {question_type}
Current profile state: {json.dumps(self.profile, default=str)}
User just said: "{user_message}"

Extract the relevant data and generate the next response.
If this question is complete, include the next question context: {self._get_next_question_context(self.questions_flow[min(self.current_question + 1, len(self.questions_flow) - 1)])}
"""
        messages.append({"role": "system", "content": context_message})
        
        # Call Groq API
        response = self._call_groq(messages[:-1] + [{"role": "user", "content": user_message + "\n\n" + context_message}], question_type)
        
        # Update profile with extracted data
        if response.get('extracted_data'):
            self._update_profile(response['extracted_data'])
        
        # Check if current question is complete
        if not response.get('needs_clarification', False) and self._is_question_complete(question_type):
            self.current_question += 1
        
        # Check if we're done
        if self.current_question >= len(self.questions_flow):
            completion_message = self._generate_completion_message()
            return (completion_message, True, self.profile.copy())
        
        # Return the response
        return (response.get('next_message', "Could you tell me more?"), False, None)

    def reset(self) -> None:
        """Reset the agent to start a new conversation."""
        self.profile = {
            'age': None,
            'annual_income': None,
            'city': None,
            'is_metro': None,
            'monthly_rent': None,
            'has_term_insurance': None,
            'term_cover': 0.0,
            'has_health_insurance': None,
            'health_cover': 0.0,
            'ppf_annual': 0.0,
            'elss_annual': 0.0,
            'nps_annual': 0.0,
            'epf_annual': 0.0,
            'monthly_expenses': None,
            'monthly_sip': 0.0,
            'emergency_fund': 0.0,
            'primary_goal': None
        }
        self.current_question = 0


# ============================================================
# Demo / Test Code
# ============================================================

def test_parse_indian_number():
    """Test the Indian number parser."""
    test_cases = [
        ('12 lakh', 1200000),
        ('1.2L', 120000),
        ('12,00,000', 1200000),
        ('50k', 50000),
        ('1.5 crore', 15000000),
        ('25000', 25000),
        ('1.5 cr', 15000000),
        ('2.5 lakhs', 250000),
        ('nil', 0),
        ('none', 0),
        ('80000 per month', 80000),
    ]
    
    print("Testing parse_indian_number():\n")
    all_passed = True
    for text, expected in test_cases:
        result = parse_indian_number(text)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} '{text}' -> {result} (expected {expected})")
    
    print(f"\n{'All tests passed!' if all_passed else 'Some tests failed!'}\n")
    return all_passed


def run_demo():
    """Run an interactive demo of the intake agent."""
    import os
    
    # Get API key from environment
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        print("Please set GROQ_API_KEY environment variable")
        print("Example: export GROQ_API_KEY='your-api-key-here'")
        return
    
    # Create agent
    agent = IntakeAgent(api_key)
    
    print("=" * 60)
    print("Financial Profile Intake Agent Demo")
    print("=" * 60)
    print("Type 'quit' to exit, 'reset' to start over\n")
    
    # Conversation history
    conversation_history = []
    
    # Get initial message
    response, is_complete, profile = agent.process_message("", conversation_history)
    print(f"\n🤖 Agent: {response}\n")
    conversation_history.append({"role": "assistant", "content": response})
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'quit':
            print("\nGoodbye! 👋")
            break
        
        if user_input.lower() == 'reset':
            agent.reset()
            conversation_history = []
            response, is_complete, profile = agent.process_message("", conversation_history)
            print(f"\n🤖 Agent: {response}\n")
            conversation_history.append({"role": "assistant", "content": response})
            continue
        
        if not user_input:
            continue
        
        # Add user message to history
        conversation_history.append({"role": "user", "content": user_input})
        
        # Process message
        try:
            response, is_complete, profile = agent.process_message(user_input, conversation_history)
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            continue
        
        # Add agent response to history
        conversation_history.append({"role": "assistant", "content": response})
        
        print(f"\n🤖 Agent: {response}\n")
        
        if is_complete:
            print("\n" + "=" * 60)
            print("Profile Complete! Here's the extracted data:")
            print("=" * 60)
            print(json.dumps(profile, indent=2, default=str))
            print("=" * 60)
            
            # Ask if they want to start over
            again = input("\nStart a new profile? (yes/no): ").strip().lower()
            if again in ['yes', 'y']:
                agent.reset()
                conversation_history = []
                response, is_complete, profile = agent.process_message("", conversation_history)
                print(f"\n🤖 Agent: {response}\n")
                conversation_history.append({"role": "assistant", "content": response})
            else:
                print("\nGoodbye! 👋")
                break


def run_simulated_conversation():
    """Run a simulated conversation for testing without API calls."""
    print("=" * 60)
    print("Simulated Conversation Flow (No API)")
    print("=" * 60)
    
    # Simulated user responses
    simulated_responses = [
        "I'm 28 years old",
        "My CTC is 18 lakh per annum",
        "I live in Bangalore",
        "I pay 22000 rent per month",
        "I have both term and health insurance. Term is 1 crore, health is 5 lakh",
        "I put 50k in PPF, 1 lakh in ELSS yearly. EPF is around 1.8 lakh",
        "My monthly expenses are around 35000",
        "Yes I have SIPs of 15000 per month",
        "I have about 2 lakh saved as emergency fund",
        "I want to buy a house in the next 5 years"
    ]
    
    questions = [
        "How old are you?",
        "What's your annual income (CTC or in-hand)?",
        "Which city do you live in?",
        "How much rent do you pay monthly?",
        "Do you have term insurance, health insurance, both, or neither?",
        "What are your current tax-saving investments (PPF, ELSS, NPS, EPF)?",
        "What are your monthly expenses (excluding rent)?",
        "Do you have any SIPs running? How much per month?",
        "Do you have an emergency fund? How much?",
        "What's your top financial goal?"
    ]
    
    print("\nSimulating conversation:\n")
    
    for i, (question, response) in enumerate(zip(questions, simulated_responses)):
        print(f"🤖 Agent: {question}")
        print(f"👤 User: {response}")
        print()
    
    # Show what the profile would look like
    profile = {
        'age': 28,
        'annual_income': 1800000,
        'city': 'Bangalore',
        'is_metro': True,
        'monthly_rent': 22000,
        'has_term_insurance': True,
        'term_cover': 10000000,
        'has_health_insurance': True,
        'health_cover': 500000,
        'ppf_annual': 50000,
        'elss_annual': 100000,
        'nps_annual': 0,
        'epf_annual': 180000,
        'monthly_expenses': 35000,
        'monthly_sip': 15000,
        'emergency_fund': 200000,
        'primary_goal': 'house'
    }
    
    print("=" * 60)
    print("Extracted Profile:")
    print("=" * 60)
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            test_parse_indian_number()
        elif sys.argv[1] == 'simulate':
            run_simulated_conversation()
        elif sys.argv[1] == 'demo':
            run_demo()
        else:
            print("Usage: python intake_agent.py [test|simulate|demo]")
    else:
        # Default: run tests then demo
        print("Running tests first...\n")
        test_parse_indian_number()
        print("\n" + "=" * 60 + "\n")
        
        # Check if API key is available
        import os
        if os.environ.get('GROQ_API_KEY'):
            print("API key found. Starting interactive demo...\n")
            run_demo()
        else:
            print("No GROQ_API_KEY found. Running simulated conversation...\n")
            run_simulated_conversation()