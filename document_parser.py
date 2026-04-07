import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image
import io
import json
import re
from typing import Dict, List, Tuple, Any
from pathlib import Path

# Configure Gemini
def configure_gemini(api_key: str):
    """Configure Gemini API with the provided key."""
    genai.configure(api_key=api_key)

def pdf_page_to_image(pdf_path: str, page_num: int, dpi: int = 300) -> Image.Image:
    """
    Convert a PDF page to PIL Image.
    
    Args:
        pdf_path: Path to the PDF file
        page_num: Page number (0-indexed)
        dpi: Resolution for conversion
    
    Returns:
        PIL Image object
    """
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Convert to image with specified DPI
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to PIL Image
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    
    doc.close()
    return img

def get_pdf_page_count(pdf_path: str) -> int:
    """Get total number of pages in PDF."""
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count

def create_gemini_prompt() -> str:
    """
    Create a detailed prompt for Gemini Vision to parse Form 16.
    """
    prompt = """
You are an expert at parsing Indian Income Tax Form 16 documents. 
Analyze this Form 16 image and extract ALL the following information accurately.

Form 16 typically has:
- PART A: Details of tax deducted (TDS)
- PART B: Computation of income and tax

Extract these fields (return "null" if not found, along with confidence 0-100):

EMPLOYEE DETAILS:
- employee_name: Full name of the employee
- pan: PAN number (format: ABCDE1234F)
- employer_name: Name of the employer/company
- financial_year: Financial year (e.g., "2023-24")

SALARY DETAILS (Part B - Section A):
- gross_salary: Total gross salary
- basic_salary: Basic salary component
- hra_received: House Rent Allowance received
- standard_deduction: Standard deduction claimed (usually 50,000)
- professional_tax: Professional tax paid

DEDUCTIONS (Part B - Section B & C):
- section_80c: Total under 80C (PF, PPF, ELSS, LIC, etc.)
- section_80d: Medical insurance premium (80D)
- section_80ccd_1b: NPS contribution (80CCD(1B))
- section_80e: Education loan interest (80E)
- home_loan_interest: Home loan interest (Section 24)
- other_deductions: Any other deductions

TAX COMPUTATION:
- total_income: Total income / Gross total income
- net_taxable_income: Net taxable income after deductions
- tax_payable: Total tax payable
- tds_deducted: Total TDS deducted

For each field, provide:
1. The value (as string or number)
2. Confidence score (0-100)

Return ONLY a valid JSON object in this exact format:
{
  "employee_name": {"value": "John Doe", "confidence": 95},
  "pan": {"value": "ABCDE1234F", "confidence": 100},
  "employer_name": {"value": "ABC Company Ltd", "confidence": 90},
  "financial_year": {"value": "2023-24", "confidence": 100},
  "gross_salary": {"value": 1200000, "confidence": 95},
  "basic_salary": {"value": 600000, "confidence": 90},
  "hra_received": {"value": 240000, "confidence": 85},
  "standard_deduction": {"value": 50000, "confidence": 100},
  "professional_tax": {"value": 2400, "confidence": 90},
  "section_80c": {"value": 150000, "confidence": 95},
  "section_80d": {"value": 25000, "confidence": 90},
  "section_80ccd_1b": {"value": 50000, "confidence": 85},
  "section_80e": {"value": 0, "confidence": 100},
  "home_loan_interest": {"value": 200000, "confidence": 80},
  "other_deductions": {"value": 0, "confidence": 100},
  "total_income": {"value": 1200000, "confidence": 95},
  "net_taxable_income": {"value": 725000, "confidence": 90},
  "tax_payable": {"value": 75000, "confidence": 95},
  "tds_deducted": {"value": 75000, "confidence": 95}
}

IMPORTANT:
- Return ONLY the JSON object, no explanatory text
- Use numeric values for amounts (not strings)
- If a field is not found, use null for value and 0 for confidence
- Be precise with numbers - extract exactly what's written
"""
    return prompt

def parse_form16_pdf(pdf_path: str, api_key: str) -> Dict[str, Any]:
    """
    Parse Form 16 PDF using Gemini Vision API.
    
    Args:
        pdf_path: Path to the Form 16 PDF file
        api_key: Google Gemini API key
    
    Returns:
        Dictionary with extracted fields and confidence scores
    """
    try:
        # Configure Gemini
        configure_gemini(api_key)
        
        # Initialize the model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Get page count
        page_count = get_pdf_page_count(pdf_path)
        print(f"PDF has {page_count} pages")
        
        # Form 16 is typically 2-3 pages, process all relevant pages
        all_results = []
        
        for page_num in range(min(page_count, 3)):  # Process up to 3 pages
            print(f"Processing page {page_num + 1}...")
            
            # Convert page to image
            image = pdf_page_to_image(pdf_path, page_num)
            
            # Create prompt
            prompt = create_gemini_prompt()
            
            # Send to Gemini
            response = model.generate_content([prompt, image])
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            try:
                parsed_data = json.loads(response_text)
                all_results.append(parsed_data)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON from page {page_num + 1}: {e}")
                print(f"Response text: {response_text[:200]}...")
                continue
        
        if not all_results:
            raise ValueError("Failed to parse any pages")
        
        # Merge results from multiple pages, keeping highest confidence values
        merged_result = merge_results(all_results)
        
        return merged_result
        
    except Exception as e:
        print(f"Error in parse_form16_pdf: {e}")
        raise

def merge_results(results: List[Dict]) -> Dict[str, Any]:
    """
    Merge results from multiple pages, keeping the value with highest confidence.
    
    Args:
        results: List of parsed dictionaries from different pages
    
    Returns:
        Merged dictionary with best values
    """
    if not results:
        return create_empty_template()
    
    if len(results) == 1:
        return results[0]
    
    merged = {}
    
    # Get all possible keys
    all_keys = set()
    for result in results:
        all_keys.update(result.keys())
    
    # For each key, pick the value with highest confidence
    for key in all_keys:
        best_value = {"value": None, "confidence": 0}
        
        for result in results:
            if key in result:
                current = result[key]
                if isinstance(current, dict) and "confidence" in current:
                    if current["confidence"] > best_value["confidence"]:
                        best_value = current
                else:
                    # Handle non-standard format
                    best_value = {"value": current, "confidence": 50}
        
        merged[key] = best_value
    
    return merged

def validate_parsed_data(parsed_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate parsed Form 16 data.
    
    Args:
        parsed_dict: Dictionary with parsed data
    
    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "needs_review": []
    }
    
    # Mandatory fields
    mandatory_fields = [
        "employee_name", "pan", "employer_name", 
        "financial_year", "gross_salary", "tds_deducted"
    ]
    
    # Check mandatory fields
    for field in mandatory_fields:
        if field not in parsed_dict:
            validation_result["errors"].append(f"Missing mandatory field: {field}")
            validation_result["is_valid"] = False
        elif parsed_dict[field].get("value") is None:
            validation_result["errors"].append(f"Mandatory field is null: {field}")
            validation_result["is_valid"] = False
        elif parsed_dict[field].get("confidence", 0) < 50:
            validation_result["warnings"].append(
                f"Low confidence for mandatory field {field}: {parsed_dict[field]['confidence']}%"
            )
            validation_result["needs_review"].append(field)
    
    # Validate PAN format
    if "pan" in parsed_dict and parsed_dict["pan"].get("value"):
        pan = str(parsed_dict["pan"]["value"])
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
            validation_result["warnings"].append(f"Invalid PAN format: {pan}")
            validation_result["needs_review"].append("pan")
    
    # Validate numeric fields
    numeric_fields = [
        "gross_salary", "basic_salary", "hra_received", 
        "standard_deduction", "professional_tax",
        "section_80c", "section_80d", "section_80ccd_1b", 
        "section_80e", "home_loan_interest", "other_deductions",
        "total_income", "net_taxable_income", 
        "tax_payable", "tds_deducted"
    ]
    
    for field in numeric_fields:
        if field in parsed_dict and parsed_dict[field].get("value") is not None:
            value = parsed_dict[field]["value"]
            
            # Check if numeric
            try:
                value = float(value)
                
                # Salary fields should be positive
                if field in ["gross_salary", "basic_salary", "total_income"]:
                    if value <= 0:
                        validation_result["errors"].append(
                            f"{field} should be positive, got {value}"
                        )
                        validation_result["is_valid"] = False
                
                # Tax and deduction fields should be non-negative
                if value < 0:
                    validation_result["errors"].append(
                        f"{field} should be non-negative, got {value}"
                    )
                    validation_result["is_valid"] = False
                
                # Reasonable value checks
                if field == "gross_salary" and value > 100000000:  # 10 crores
                    validation_result["warnings"].append(
                        f"Unusually high gross salary: {value}"
                    )
                    validation_result["needs_review"].append(field)
                
                if field == "section_80c" and value > 150000:
                    validation_result["warnings"].append(
                        f"80C deduction exceeds limit: {value}"
                    )
                    validation_result["needs_review"].append(field)
                
                if field == "section_80ccd_1b" and value > 50000:
                    validation_result["warnings"].append(
                        f"80CCD(1B) deduction exceeds limit: {value}"
                    )
                    validation_result["needs_review"].append(field)
                
            except (ValueError, TypeError):
                validation_result["errors"].append(
                    f"{field} should be numeric, got {value}"
                )
                validation_result["is_valid"] = False
    
    # Check confidence scores
    low_confidence_threshold = 60
    for field, data in parsed_dict.items():
        if isinstance(data, dict) and "confidence" in data:
            if data["confidence"] < low_confidence_threshold:
                validation_result["needs_review"].append(field)
    
    # Remove duplicates from needs_review
    validation_result["needs_review"] = list(set(validation_result["needs_review"]))
    
    return validation_result

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from PDF using PyMuPDF.
    
    Args:
        pdf_path: Path to PDF file
    
    Returns:
        Extracted text
    """
    doc = fitz.open(pdf_path)
    text = ""
    
    for page in doc:
        text += page.get_text()
    
    doc.close()
    return text

def parse_text_fallback(text: str) -> Dict[str, Any]:
    """
    Attempt to parse Form 16 from extracted text as fallback.
    
    Args:
        text: Extracted text from PDF
    
    Returns:
        Dictionary with extracted fields
    """
    result = create_empty_template()
    
    # Try to extract PAN
    pan_match = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
    if pan_match:
        result["pan"] = {"value": pan_match.group(), "confidence": 70}
    
    # Try to extract financial year
    fy_match = re.search(r'20\d{2}-\d{2}', text)
    if fy_match:
        result["financial_year"] = {"value": fy_match.group(), "confidence": 70}
    
    # Try to extract amounts (this is very basic)
    # Look for patterns like "Gross Salary: 1,200,000"
    gross_salary_patterns = [
        r'Gross\s+Salary[:\s]+Rs\.?\s*([\d,]+)',
        r'Gross\s+Salary[:\s]+([\d,]+)',
    ]
    
    for pattern in gross_salary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                result["gross_salary"] = {"value": amount, "confidence": 60}
                break
            except ValueError:
                pass
    
    # Similar patterns for other fields...
    # This is a simplified fallback, real implementation would be more comprehensive
    
    return result

def create_empty_template() -> Dict[str, Any]:
    """
    Create an empty template for manual entry.
    
    Returns:
        Dictionary with all fields set to None
    """
    fields = [
        "employee_name", "pan", "employer_name", "financial_year",
        "gross_salary", "basic_salary", "hra_received", 
        "standard_deduction", "professional_tax",
        "section_80c", "section_80d", "section_80ccd_1b", 
        "section_80e", "home_loan_interest", "other_deductions",
        "total_income", "net_taxable_income", 
        "tax_payable", "tds_deducted"
    ]
    
    return {field: {"value": None, "confidence": 0} for field in fields}

def parse_with_fallback(pdf_path: str, api_key: str) -> Dict[str, Any]:
    """
    Parse Form 16 with fallback mechanisms.
    
    Args:
        pdf_path: Path to PDF file
        api_key: Gemini API key
    
    Returns:
        Dictionary with parsed data
    """
    print("Attempting to parse with Gemini Vision...")
    
    try:
        # Try Gemini Vision first
        result = parse_form16_pdf(pdf_path, api_key)
        print("✓ Successfully parsed with Gemini Vision")
        return result
        
    except Exception as e:
        print(f"✗ Gemini Vision failed: {e}")
        print("\nAttempting text extraction fallback...")
        
        try:
            # Try text extraction
            text = extract_text_from_pdf(pdf_path)
            result = parse_text_fallback(text)
            print("✓ Partially parsed with text extraction")
            return result
            
        except Exception as e2:
            print(f"✗ Text extraction failed: {e2}")
            print("\nReturning empty template for manual entry...")
            
            # Return empty template
            return create_empty_template()

def print_parsed_results(parsed_data: Dict[str, Any]):
    """Pretty print parsed results."""
    print("\n" + "="*80)
    print("PARSED FORM 16 DATA")
    print("="*80)
    
    categories = {
        "Employee Details": ["employee_name", "pan", "employer_name", "financial_year"],
        "Salary Details": ["gross_salary", "basic_salary", "hra_received", 
                          "standard_deduction", "professional_tax"],
        "Deductions": ["section_80c", "section_80d", "section_80ccd_1b", 
                      "section_80e", "home_loan_interest", "other_deductions"],
        "Tax Computation": ["total_income", "net_taxable_income", 
                           "tax_payable", "tds_deducted"]
    }
    
    for category, fields in categories.items():
        print(f"\n{category}:")
        print("-" * 80)
        
        for field in fields:
            if field in parsed_data:
                data = parsed_data[field]
                value = data.get("value", "N/A")
                confidence = data.get("confidence", 0)
                
                # Format value
                if isinstance(value, (int, float)) and value is not None:
                    value_str = f"₹{value:,.2f}"
                else:
                    value_str = str(value) if value is not None else "N/A"
                
                # Color code based on confidence
                if confidence >= 80:
                    status = "✓"
                elif confidence >= 60:
                    status = "⚠"
                else:
                    status = "✗"
                
                print(f"  {status} {field:25s}: {value_str:20s} (confidence: {confidence}%)")

def print_validation_results(validation: Dict[str, Any]):
    """Pretty print validation results."""
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    
    if validation["is_valid"]:
        print("✓ Data is valid")
    else:
        print("✗ Data has errors")
    
    if validation["errors"]:
        print("\nErrors:")
        for error in validation["errors"]:
            print(f"  ✗ {error}")
    
    if validation["warnings"]:
        print("\nWarnings:")
        for warning in validation["warnings"]:
            print(f"  ⚠ {warning}")
    
    if validation["needs_review"]:
        print("\nFields needing human review:")
        for field in validation["needs_review"]:
            print(f"  → {field}")

# Test function
def test_sample_flow():
    """
    Test the Form 16 parser with a sample flow.
    This demonstrates how to use the functions.
    """
    print("="*80)
    print("FORM 16 PARSER - SAMPLE FLOW")
    print("="*80)
    
    # Sample configuration
    pdf_path = "sample_form16.pdf"  # Replace with actual path
    api_key = "YOUR_API_KEY_HERE"  # Replace with actual API key
    
    print(f"\nPDF Path: {pdf_path}")
    print(f"API Key: {api_key[:10]}..." if len(api_key) > 10 else "Not set")
    
    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"\n✗ Error: File not found: {pdf_path}")
        print("\nTo test this script:")
        print("1. Place a Form 16 PDF in the same directory")
        print("2. Update pdf_path variable")
        print("3. Get Gemini API key from https://makersuite.google.com/app/apikey")
        print("4. Update api_key variable")
        return
    
    if api_key == "YOUR_API_KEY_HERE":
        print("\n✗ Error: Please set your Gemini API key")
        return
    
    try:
        # Parse with fallback
        print("\n" + "-"*80)
        parsed_data = parse_with_fallback(pdf_path, api_key)
        
        # Print results
        print_parsed_results(parsed_data)
        
        # Validate
        print("\n" + "-"*80)
        validation = validate_parsed_data(parsed_data)
        print_validation_results(validation)
        
        # Save to JSON
        output_file = "parsed_form16.json"
        with open(output_file, 'w') as f:
            json.dump({
                "parsed_data": parsed_data,
                "validation": validation
            }, f, indent=2)
        
        print(f"\n✓ Results saved to {output_file}")
        
    except Exception as e:
        print(f"\n✗ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run test
    test_sample_flow()
    
    # Example of direct usage:
    """
    # Configure your API key
    api_key = "your-gemini-api-key"
    pdf_path = "path/to/form16.pdf"
    
    # Parse the PDF
    result = parse_form16_pdf(pdf_path, api_key)
    
    # Validate the results
    validation = validate_parsed_data(result)
    
    # Print results
    print_parsed_results(result)
    print_validation_results(validation)
    """