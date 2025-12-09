import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
import pdf2image
import os

# WINDOWS USERS: Uncomment and update path below
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# MAC USERS: Usually auto-detected, but if issues uncomment:
# pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'

# LINUX USERS: Usually auto-detected, but if issues uncomment:
# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

class InvoiceAnalyzer:
    """
    AI-powered document analyzer using OCR and pattern matching.
    Uses lightweight pretrained models - no training required!
    """
    
    def __init__(self):
        self.currency_symbols = {
            '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY',
            '₹': 'INR', 'Rs': 'INR', 'PKR': 'PKR'
        }
        
        self.document_keywords = {
            'invoice': ['invoice', 'bill', 'inv no', 'invoice no', 'invoice #'],
            'receipt': ['receipt', 'payment received', 'paid'],
            'bill': ['bill', 'statement', 'amount due']
        }
    
    def analyze_document(self, filepath):
        """Main analysis function"""
        try:
            # Extract text based on file type
            if filepath.lower().endswith('.pdf'):
                text = self._extract_text_from_pdf(filepath)
            else:
                text = self._extract_text_from_image(filepath)
            
            if not text.strip():
                raise ValueError("No text could be extracted from document")
            
            # Analyze extracted text
            doc_type = self._classify_document(text)
            amount = self._extract_amount(text)
            currency = self._extract_currency(text)
            vendor = self._extract_vendor(text)
            confidence = self._calculate_confidence(text)
            
            return {
                'document_type': doc_type,
                'total_amount': amount,
                'currency': currency,
                'vendor_name': vendor,
                'text': text,
                'confidence': confidence,
                'status': 'success'
            }
        
        except Exception as e:
            return {
                'document_type': 'unknown',
                'total_amount': 0.0,
                'currency': 'USD',
                'vendor_name': 'Unknown',
                'text': '',
                'confidence': 0.0,
                'status': 'error',
                'error': str(e)
            }
    
    def _extract_text_from_image(self, filepath):
        """Extract text from image using OCR"""
        # Read and preprocess image
        img = cv2.imread(filepath)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding for better OCR
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Apply slight blur to reduce noise
        gray = cv2.medianBlur(gray, 3)
        
        # OCR with Tesseract
        text = pytesseract.image_to_string(gray)
        return text
    
    def _extract_text_from_pdf(self, filepath):
        """Extract text from PDF"""
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(filepath, dpi=300, first_page=1, last_page=1)
            
            if not images:
                return ""
            
            # Process first page only (for speed)
            text = pytesseract.image_to_string(images[0])
            return text
        except Exception as e:
            print(f"PDF extraction error: {e}")
            return ""
    
    def _classify_document(self, text):
        """Classify document type based on keywords"""
        text_lower = text.lower()
        
        scores = {}
        for doc_type, keywords in self.document_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[doc_type] = score
        
        # Return type with highest score
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return 'invoice'  # Default
    
    def _extract_amount(self, text):
        """Extract monetary amounts using regex"""
        # Pattern: Look for currency symbols followed by numbers
        patterns = [
            r'(?:total|amount|sum|pay|due)[\s:]*[\$€£¥₹Rs]*\s*(\d+[,.]?\d*\.?\d+)',
            r'[\$€£¥₹]\s*(\d+[,.]?\d*\.?\d+)',
            r'(?:Rs\.?|PKR)\s*(\d+[,.]?\d*\.?\d+)',
        ]
        
        amounts = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount_str = match.group(1).replace(',', '')
                    amounts.append(float(amount_str))
                except:
                    continue
        
        # Return the largest amount found (likely the total)
        return max(amounts) if amounts else 0.0
    
    def _extract_currency(self, text):
        """Extract currency from text"""
        for symbol, code in self.currency_symbols.items():
            if symbol in text:
                return code
        return 'USD'  # Default
    
    def _extract_vendor(self, text):
        """Extract vendor/company name (first line usually)"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Filter out common noise
        noise_words = ['invoice', 'receipt', 'bill', 'tax', 'date']
        
        for line in lines[:5]:  # Check first 5 lines
            line_lower = line.lower()
            if len(line) > 3 and not any(word in line_lower for word in noise_words):
                # Likely the vendor name
                return line[:100]  # Limit length
        
        return 'Unknown Vendor'
    
    def _calculate_confidence(self, text):
        """Calculate confidence score based on text quality"""
        if not text:
            return 0.0
        
        # Factors for confidence
        has_amount = bool(re.search(r'\d+\.?\d*', text))
        has_keywords = any(kw in text.lower() for keywords in self.document_keywords.values() for kw in keywords)
        text_length = len(text.split())
        
        confidence = 0.0
        if has_amount:
            confidence += 0.4
        if has_keywords:
            confidence += 0.3
        if text_length > 20:
            confidence += 0.3
        
        return min(confidence, 1.0)
