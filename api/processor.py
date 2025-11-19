"""
Invoice Data Extraction Module
Handles OCR processing and intelligent data extraction from invoice images.
"""

import re
import os
import requests
from fuzzywuzzy import process


def extract_invoice_data(image_path, known_vendors, ocr_api_key=None):
    """
    Extract key invoice information from an image using OCR and pattern matching.
    
    Args:
        image_path (str): Path to the invoice image file
        known_vendors (list): List of known vendor names for fuzzy matching
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
    
    # Extract vendor name using fuzzy matching
    vendor = extract_vendor(raw_text, known_vendors)
    
    # Extract invoice date using regex
    date = extract_date(raw_text)
    
    # Extract total amount using regex
    total = extract_total(raw_text)
    
    return {
        'vendor': vendor,
        'date': date,
        'total': total
    }


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
    Find the best matching vendor name from the text using fuzzy matching.
    
    Args:
        text (str): Raw OCR text
        known_vendors (list): List of known vendor names
    
    Returns:
        str: Best matching vendor name or None
    """
    if not known_vendors or not text:
        return None
    
    # Use fuzzywuzzy to find the best match
    # extractOne returns (best_match, score)
    result = process.extractOne(text, known_vendors)
    
    if result and result[1] >= 60:  # 60% confidence threshold
        return result[0]
    
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
