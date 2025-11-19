"""
Invoice Data Extraction Module
Handles OCR processing and intelligent data extraction from invoice images using AI.
"""

import re
import os
import requests
import json


def extract_invoice_data(image_path, known_vendors=None, ocr_api_key=None):
    """
    Extract key invoice information from an image using OCR and AI.
    
    Args:
        image_path (str): Path to the invoice image file
        known_vendors (list, optional): Legacy parameter, not used with AI extraction
        ocr_api_key (str, optional): OCR.space API key. If not provided, uses env variable.
    
    Returns:
        dict: Dictionary containing vendor, date, and total amount
    """
    # Get API key from parameter or environment variable
    api_key = ocr_api_key or os.environ.get('OCR_API_KEY', 'K87899142388957')
    
    # Perform OCR on the image using OCR.space API
    try:
        raw_text = perform_ocr(image_path, api_key)
        if not raw_text:
            return {
                'vendor': None,
                'date': None,
                'total': None,
                'error': 'OCR failed: No text extracted'
            }
    except Exception as e:
        return {
            'vendor': None,
            'date': None,
            'total': None,
            'error': f'OCR failed: {str(e)}'
        }
    
    # Try AI-powered extraction first
    print(f"OCR extracted {len(raw_text)} characters of text")
    print(f"First 200 chars: {raw_text[:200]}...")
    
    ai_result = extract_with_ai(raw_text)
    if ai_result:
        ai_result['_ai_used'] = True
        print("✅ AI extraction successful!")
        return ai_result
    
    print("⚠️ AI extraction failed, falling back to regex")
    # Fallback to regex-based extraction
    vendor = extract_vendor_nlp(raw_text)
    date = extract_date(raw_text)
    total = extract_total(raw_text)
    
    return {
        'vendor': vendor,
        'date': date,
        'total': total,
        'invoice_number': None,
        'tax': None,
        'subtotal': None,
        'summary': None,
        'line_items': [],
        '_ai_used': False
    }


def extract_with_ai(text):
    """
    Use Google's Gemini AI to extract invoice data intelligently.
    
    Args:
        text (str): Raw OCR text from invoice
    
    Returns:
        dict: Extracted data or None if AI extraction fails
    """
    try:
        # Get Gemini API key from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("No GEMINI_API_KEY found, using fallback")
            return None  # Fallback to regex if no API key
        
        print(f"Using Gemini AI with key: {api_key[:10]}...")
        
        # Gemini API endpoint - try multiple models for better compatibility
        # gemini-2.0-flash has wider availability than 2.5-flash
        model = "gemini-2.0-flash"  # More stable, widely available
        url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}"
        print(f"Using model: {model}")
        
        prompt = f"""You are an expert invoice data extraction system. Extract the following information from this invoice text:

1. Vendor/Company Name (the business issuing the invoice)
2. Invoice Date (in original format)
3. Total Amount (with currency symbol - keep €, $, £, ¥, etc.)
4. Invoice Number (if present)
5. Tax Amount (if present, with currency symbol)
6. Subtotal (amount before tax, with currency symbol)
7. Summary (1-2 sentence description of what this invoice is for)
8. Line Items (list of main items/services with quantities and prices if available)

Invoice Text:
{text}

Respond ONLY with a valid JSON object in this exact format:
{{
  "vendor": "Company Name",
  "date": "MM/DD/YYYY",
  "total": "$XXX.XX",
  "invoice_number": "INV-12345",
  "tax": "$XX.XX",
  "subtotal": "$XXX.XX",
  "summary": "Brief description of invoice purpose",
  "line_items": [
    {{"description": "Item name", "quantity": "X", "price": "$XX.XX"}},
    {{"description": "Service name", "quantity": "X", "price": "$XX.XX"}}
  ]
}}

If you cannot find a field, use null. Keep currency symbols with amounts. For line_items, extract up to 5 main items.
"""

        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 800
            }
        }
        
        print("Calling Gemini API...")
        print(f"Request URL: {url[:80]}...")
        print(f"Payload size: {len(json.dumps(payload))} chars")
        
        response = requests.post(url, json=payload, timeout=20)
        
        print(f"Gemini API Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"Gemini API Error: {response.text}")
            return None
        
        result = response.json()
        print(f"Gemini response received: {result}")
        
        # Extract the generated text
        if 'candidates' in result and len(result['candidates']) > 0:
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            print(f"Generated text: {generated_text}")
            
            # Parse JSON from response
            # Remove markdown code blocks if present
            generated_text = generated_text.replace('```json', '').replace('```', '').strip()
            
            data = json.loads(generated_text)
            print(f"Parsed data: {data}")
            
            return {
                'vendor': data.get('vendor'),
                'date': data.get('date'),
                'total': data.get('total'),
                'invoice_number': data.get('invoice_number'),
                'tax': data.get('tax'),
                'subtotal': data.get('subtotal'),
                'summary': data.get('summary'),
                'line_items': data.get('line_items', [])
            }
        
        print("No candidates in Gemini response")
        return None
        
    except requests.exceptions.Timeout:
        print("AI extraction failed: Request timeout after 20 seconds")
        return None
    except requests.exceptions.RequestException as e:
        print(f"AI extraction failed: Request error - {type(e).__name__}: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"AI extraction failed: JSON parsing error - {str(e)}")
        print(f"Raw generated text was: {generated_text if 'generated_text' in locals() else 'N/A'}")
        return None
    except KeyError as e:
        print(f"AI extraction failed: Missing key in response - {str(e)}")
        print(f"Response structure: {result if 'result' in locals() else 'N/A'}")
        return None
    except Exception as e:
        print(f"AI extraction failed with exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def perform_ocr(image_path, api_key):
    """
    Perform OCR using OCR.space API.
    
    Args:
        image_path (str): Path to the image file
        api_key (str): OCR.space API key
    
    Returns:
        str: Extracted text from the image
    """
    url = 'https://api.ocr.space/parse/image'
    
    with open(image_path, 'rb') as f:
        payload = {
            'apikey': api_key,
            'language': 'eng',
            'isOverlayRequired': False,
            'detectOrientation': True,
            'scale': True,
            'OCREngine': 2  # Engine 2 is more accurate
        }
        
        files = {
            'file': f
        }
        
        response = requests.post(url, files=files, data=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('IsErroredOnProcessing'):
            error_msg = result.get('ErrorMessage', ['Unknown error'])[0]
            raise Exception(f'OCR.space API error: {error_msg}')
        
        # Extract text from parsed results
        if result.get('ParsedResults'):
            parsed_text = result['ParsedResults'][0].get('ParsedText', '')
            return parsed_text
        
        return None


def extract_vendor(text, known_vendors):
    """
    DEPRECATED: Legacy function for fuzzy matching.
    Use extract_vendor_nlp() or extract_with_ai() instead.
    
    Args:
        text (str): Raw OCR text
        known_vendors (list): List of known vendor names
    
    Returns:
        str: None (deprecated)
    """
    return None


def extract_vendor_nlp(text):
    """
    Extract vendor/company name from invoice text using NLP patterns.
    Looks for common invoice patterns like company headers, "Bill To", "From", etc.
    
    Args:
        text (str): Raw OCR text from invoice
    
    Returns:
        str: Extracted vendor name or None
    """
    if not text:
        return None
    
    lines = text.strip().split('\n')
    
    # Strategy 1: Look for "Bill From", "From:", "Vendor:", "Sold by:" etc.
    vendor_patterns = [
        r"(?:Bill\s+From|From|Vendor|Sold\s+by|Invoice\s+from)[\s:]+(.+)",
        r"(?:Billed\s+by|Supplier|Company)[\s:]+(.+)",
    ]
    
    for pattern in vendor_patterns:
        for line in lines:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                # Clean up the vendor name
                vendor = re.sub(r'[^\w\s&.-]', '', vendor)
                if vendor and len(vendor) > 2:
                    return vendor
    
    # Strategy 2: Look at the first few lines (company name is usually at the top)
    # Skip very short lines and lines with only numbers
    for line in lines[:5]:
        line = line.strip()
        # Skip empty lines, very short lines, or lines that are mostly numbers
        if not line or len(line) < 3:
            continue
        if re.match(r'^\d+$', line):  # Skip lines with only numbers
            continue
        if re.match(r'^[\d\s\-/()]+$', line):  # Skip lines with only numbers and separators
            continue
        
        # Look for lines that seem like company names (usually capitalized, contains letters)
        if re.search(r'[A-Z][a-z]+', line):
            # Clean up the name
            cleaned = re.sub(r'[^\w\s&.-]', '', line).strip()
            if cleaned and len(cleaned) > 2 and len(cleaned) < 100:
                return cleaned
    
    # Strategy 3: Look for patterns like "Company Name Inc." or "Company LLC"
    company_suffix_pattern = r"([A-Z][A-Za-z\s&.-]+(?:Inc|LLC|Ltd|Corp|Corporation|Co|Company|Group|Enterprises|Solutions)\.?)"
    
    for line in lines[:10]:
        match = re.search(company_suffix_pattern, line)
        if match:
            vendor = match.group(1).strip()
            if len(vendor) > 3:
                return vendor
    
    return None


def extract_date(text):
    """
    Extract invoice date from text using multiple regex patterns.
    
    Supports formats:
    - MM/DD/YYYY or DD/MM/YYYY
    - MM-DD-YYYY or DD-MM-YYYY
    - Month DD, YYYY (e.g., January 15, 2024)
    - DD Month YYYY
    - YYYY-MM-DD (ISO format)
    - DD.MM.YYYY (European format)
    
    Args:
        text (str): Raw OCR text
    
    Returns:
        str: Extracted date or None
    """
    # Pattern 1: MM/DD/YYYY or DD/MM/YYYY (with slashes)
    pattern1 = r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"
    
    # Pattern 2: MM-DD-YYYY or DD-MM-YYYY (with dashes)
    pattern2 = r"\b\d{1,2}-\d{1,2}-\d{2,4}\b"
    
    # Pattern 3: YYYY-MM-DD (ISO format)
    pattern3 = r"\b\d{4}-\d{1,2}-\d{1,2}\b"
    
    # Pattern 4: DD.MM.YYYY (European format)
    pattern4 = r"\b\d{1,2}\.\d{1,2}\.\d{2,4}\b"
    
    # Pattern 5: Month DD, YYYY (e.g., January 15, 2024)
    pattern5 = r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}\b"
    
    # Pattern 6: DD Month YYYY (e.g., 15 January 2024)
    pattern6 = r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}\b"
    
    # Pattern 7: Date near "Date:" or "Invoice Date:" keywords
    pattern7 = r"(?:Date|Invoice\s+Date|Bill\s+Date|Due\s+Date)[\s:]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"
    
    # Try keyword-based pattern first (more accurate)
    match = re.search(pattern7, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Try each pattern in order
    patterns = [pattern3, pattern4, pattern1, pattern2, pattern5, pattern6]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    
    return None


def extract_total(text):
    """
    Extract total amount from text using regex patterns.
    
    Supports:
    - Currency symbols: $, €, £
    - Comma separators (1,234.56)
    - Keywords: Total, Amount Due, Balance Due, Grand Total
    
    Args:
        text (str): Raw OCR text
    
    Returns:
        str: Extracted total amount or None
    """
    # Pattern to match currency amounts near "total" keywords
    # Matches: $1,234.56 or €1.234,56 or 1234.56
    
    # Pattern 1: Total/Amount keywords followed by currency amount
    pattern1 = r"(?:Total|Amount\s+Due|Balance\s+Due|Grand\s+Total|Invoice\s+Total)[\s:]*[\$€£]?\s*(\d{1,3}(?:[,.\s]\d{3})*(?:[.,]\d{2})?)"
    
    # Pattern 2: Currency symbol with amount
    pattern2 = r"[\$€£]\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)"
    
    # Try pattern 1 first (more specific - near "Total" keywords)
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    
    # Try pattern 2 - find all currency amounts and return the largest
    matches = re.findall(pattern2, text)
    if matches:
        # Convert to float for comparison (remove commas)
        amounts = [(m, float(m.replace(',', ''))) for m in matches]
        if amounts:
            # Return the largest amount (likely the total)
            largest = max(amounts, key=lambda x: x[1])
            return f"${largest[0]}"  # Return with $ symbol
    
    return None
